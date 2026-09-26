# Revisión de calidad de datos — pendientes

Revisión del 2026-09-24. Foco: todo lo que pueda llevar a mostrar datos falsos o engañosos.

## Tier 1

### [x] 1. Win % y Pts/Combate falseados al deduplicar
- `scraper.py`: el `groupby` de duplicados suma Wins/Partidas pero hace media simple de `Win %` y de los puntos por combate. Si uno de los duplicados está a 0, el valor sale a la mitad.
- Detectado en 24 combos del CSV actual. Ej.: Silver Wolf 9-60 Free Ball muestra 49,3 % y en realidad es 146-55 (72,6 %); Sharke Edge 3-60 Low Flat muestra 66,65 % y es 36,8 %.
- Afecta a Meta Tracker, Arquetipos, Matchup, Deck Match y a la evolución del histórico. El Wilson no se ve afectado.
- Causa: la SBBL lista el mismo combo en varias filas con estadísticas distintas (p.ej. Wizard Rod 9-60 Ball: 10-3 y 387-133). Sumar es correcto; promediar no.
- Además hay filas corruptas en origen ("Wizard Rod 3-60 X Low Orb: 125 %, 5W - -1L").
- [x] `scraper.py`: nueva `agregar_duplicados()` → Win % = Wins/Partidas, Pts Ganados ponderados por Wins y Pts Cedidos por Losses.
- [x] `scraper.py`: las filas con W/L ausentes o negativos se descartan antes de agregar, con log; aviso si Wins+Losses != Partidas.
- [x] Win % recalculado en `beyblade_stats.csv` y en todo `history/` (arquetipos recalculados: ninguno cambia).
- [x] (Alex) Pts/Combate de los combos duplicados: se corrigen relanzando el Action. Se corrigen en la próxima ejecución del Action (o lanzándolo a mano con workflow_dispatch). En el histórico se quedan mal.
- Nota: Pts Ganados/Combate es por combate GANADO (pts×Wins sale entero en el 96 % de los casos), no por combate jugado.

### [x] 4. Fuga de información en el modelo
- `train_model.py`: las features BR/BB/RB (Wilson por pares) incluyen los resultados del propio combo. Entre el 12 % y el 20 % de las filas son el único combo de su par, así que la feature es el target.
- No hay validación (ni split ni CV).
- Medido con CV de 5 folds (Wilson, 903 combos):
  | Variante | R² | Spearman |
  |---|---|---|
  | Actual (features con todo el dataset, con fuga) | 0,69 | 0,80 |
  | Uso real con el modelo actual (combo no visto) | 0,22 | 0,50 |
  | **Leave-one-out en train (arreglo)** | **0,46** | **0,66** |
  | Baseline: solo log(Partidas) | 0,44 | 0,67 |
- [x] `train_model.py`: `features_desde_stats(..., loo=True)`. En entrenamiento, los scores de pieza y par excluyen el propio combo. En inferencia se siguen usando los diccionarios con todos los datos.
- [x] `train_model.py`: `evaluar_cv()` simula predecir combos no vistos, imprime las métricas junto a un baseline y las guarda en `model.pkl` como `cv_metrics`.
- [x] (Alex) Reentrenar `model.pkl` con el Action o en local.
- [x] Fallback unificado: `train_model.construir_payload()` es la única forma de entrenar. Si no hay model.pkl, `core/model_loader.py` entrena en memoria con esa función. Eliminado `_entrenar_modelo_local` de `core/recommender.py` (tenía la fuga y features distintas).
- Conclusión para el TFM: sin fuga, el modelo apenas supera al baseline de popularidad, y sin Partidas su R² es 0,13. Enlaza con la 5.

### [x] 6. "Win % Predicho" no es un winrate
- Era Wilson × 100 (límite inferior), duplicado y engañoso.
- Recomendador: sustituido por "Win % Real" (winrate observado en combos reales, vacío/"—" en los predichos; el modelo no estima winrate).
- META Oculto: columna eliminada (todos los combos son predichos). La métrica "Mejor Win % Predicho" pasa a ser el número de combos con confianza Media.
- Archivos: core/recommender.py, core/meta_hidden.py, pages/3_Recomendador.py, pages/5_META_Oculto.py.

## Tier 2

### [ ] 5. El target premia la popularidad (EN PAUSA: análisis hecho, sin implementar)
- El Wilson correlaciona 0,67 con log(Partidas) y `Partidas_log` es una feature.
- En inferencia se fija a mano: 10 en Recomendador y 50 en META Oculto. El mismo combo da predicciones distintas según la página.
- Comparativa (CV 5 folds, evaluada con log-loss por combate sobre las victorias reales de combos no vistos; menos es mejor):
  | Modelo | log-loss | sesgo | Spearman (n≥20) |
  |---|---|---|---|
  | Media global | 0,6828 | -4,3 pp | — |
  | ACTUAL: target Wilson + Partidas=10 | 0,8254 | **-26,8 pp** | 0,43 |
  | GBR con WR bruto ponderado | 0,6705 | +1,1 pp | 0,44 |
  | GBR con WR encogido (Beta-binomial) | 0,6744 | -2,3 pp | 0,49 |
  | Media de las 3 piezas encogidas (sin ML) | 0,6677 | -0,4 pp | 0,60 |
  | **Logística aditiva por piezas (C=0,03)** | **0,6645** | -0,4 pp | **0,60** |
  | Logística piezas + pares | 0,6645 | -0,8 pp | 0,57 |
- Conclusiones:
  - El modelo actual es peor que predecir la media: infravalora los combos no vistos en 27 pp, así que siempre quedan por debajo de los combos reales populares.
  - El GBR no aporta sobre modelos simples. Los pares (sinergias) no mejoran con este volumen de datos.
  - Prior Beta-binomial (MLE): a=14,8, b=12,6 (equivale a ~27 partidas de evidencia previa).
- Sinergias (caso Cobalt Dragoon + Elevate, Bullet Griffon + Merge):
  - El 95 % de las partidas de Elevate son con Cobalt Dragoon. Fuera de él solo hay 46 partidas (65 % WR), casi todas con Cobalt Drake, Dragoon Storm, L-Drago, Silver Wolf... Los datos no bastan para separar "Elevate es buena" de "Cobalt + Elevate es buena".
  - Bullet Griffon + Merge: 0 partidas; Merge tiene 5 en total. Ningún modelo puede aprenderlo de estos datos.
  - Pares con menos penalización que las piezas: la sinergia se atribuye antes al par. Con x2, Phoenix Wing 1-60 Elevate baja del 64 % al 56 %, y el log-loss empeora solo 0,002.
  - Elevate es la única pieza (entre las que tienen ≥50 partidas) con más del 80 % de su evidencia en un solo compañero.
  - Alex confirma: Elevate se usa con blades de giro izquierdo, pero no con todos (Meteor Dragoon + Elevate no funciona; 0 partidas en los datos).
  - Diseño en tres capas:
    1. ~~Sentido de giro como feature~~: descartado, porque obliga a mantener a mano la lista de blades nuevos.
    2. Pares con menos penalización: las excepciones que sí tienen datos.
    3. Tabla manual de sinergias (opcional, solo excepciones sin datos). Tiene el mismo problema de mantenimiento, pero solo afecta a casos puntuales.
  - Alternativa automática por explorar: el perfil de uso de cada blade (con qué bits y ratchets se juega) como medida de similitud. Captura indirectamente el tipo de blade sin mantener listas, y Meteor Dragoon quedaría fuera del grupo de Elevate porque no se juega con él.
- Sesgo de selección (señalado por Alex): se juega lo que ya se sabe que funciona y solo registran datos los jugadores más hardcore.
  - Un combo sin datos no es neutro: muchas veces no se juega porque ya se sabe que es malo. El modelo sobrevalora los combos no explorados.
  - El nivel del jugador va mezclado con el combo: los combos del meta los juegan los mejores jugadores. No se puede separar sin datos por jugador.
  - Explica también la 11 (más victorias que derrotas registradas).
  - Implicaciones: META Oculto debe presentarse como "hipótesis a probar"; el prior de un combo nunca jugado debería estar por debajo de la media; la tabla manual cobra más peso.
  - Prueba posible con `history/`: entrenar con la captura de abril y comparar con el rendimiento real de los combos que aparecieron después.
- Obsolescencia (para más adelante): combos que fueron muy buenos (p.ej. Hells Scythe) pero ya no aguantan contra lo nuevo. Los datos acumulados les siguen dando un WR alto.
  - El scraping no da fechas, pero `history/` sí: las capturas son acumuladas, así que la diferencia de Wins/Losses entre dos capturas da el rendimiento de ese periodo.
  - Idea: ponderar las partidas por antigüedad (decaimiento temporal) o mostrar el WR reciente frente al histórico.
  - Limitaciones: todo lo anterior al 2026-04-15 va en un único bloque; hay semanas sin cambios; si la SBBL corrige datos, pueden salir diferencias negativas.
- Propuesta (pendiente de aprobar): modelo logístico aditivo por piezas, entrenado con victorias y derrotas ponderadas, que prediga el winrate esperado sin usar Partidas. El Wilson se queda solo para rankings de combos observados. La misma fuerza por pieza serviría para la 8.

### [ ] 8. Matchup y Deck Match inconsistentes
- Matchup usa la media de las piezas aunque el combo tenga datos reales (ignora su Wilson propio).
- Las medias por pieza son medias simples de los Wilson de cada combo, sin ponderar por partidas. Deberían usar el Wilson agregado de la pieza.
- Deck Match usa el Wilson real en los combos vistos y una media sin pesos en los no vistos, así que el mismo enfrentamiento da otro número en cada página.
- `prob_victoria = ws_a / (ws_a + ws_b)` no tiene base estadística. Justificarla o cambiarla (Bradley-Terry o similar).

## Tier 3

### [x] 2. Recomendaciones con combos ilegales
- Regla UX Expanded (Alex): un UX Expanded solo puede cambiar el Bit. Blade UX ⇔ Ratchet "UX Expanded".
- [x] `core/compatibility.py`: `combo_valido()` y `filtrar_combos_validos()` reúnen todas las reglas: formato del Ratchet, Clock Mirage y UX Expanded en los dos sentidos.
- [x] `blades_con_ux_expanded()` se deduce de los datos, sin listas manuales: al menos 3 partidas y al menos el 80 % de las partidas del Blade con UX Expanded. Así los errores de registro no activan un Blade normal. Actuales: Bullet Griffon, Glory Valkyrie, Hells Nether, Rampart Aegis, Shinobi Cutter.
- [x] `filtrar_df` (loader) descarta los errores de registro de UX Expanded en los dos sentidos.
- [x] Aplicado en el Recomendador (y por tanto en el Deckbuilder), en META Oculto y en los selectores de Ratchet de Matchup y Deck Match.
- Limitación: un UX Expanded nuevo no aparece hasta que tenga 3 partidas registradas.
- Pendiente de confirmar: Turbo/Operate (ratchet y bit integrados). No hay datos ahora mismo y no he añadido ninguna regla.

### [x] 3. Regla de piezas compartidas en el deck
- Regla (Alex): no se puede repetir ninguna pieza física. UX/BX = 2 palabras (1 pieza). CX = 3 (lock chip, main blade, assist blade). CX Expanded = 4 (+ over blade). Cada assist, over, main blade y lock chip es una sola palabra.
- [x] `core/compatibility.py`: `piezas_blade()` y `blade_repetido()`. Un UX nunca choca con un CX aunque compartan palabra.
- [x] Aplicado en `core/deckbuilder.py`, en `pages/6_Deckbuilder.py` (selectores, demo y alternativas) y en `pages/8_Deck_Match.py` (selectores y demo).
- [x] De paso: `pages/8_Deck_Match.py` tenía una f-string con barra invertida (solo válida en Python ≥3.12; el devcontainer usa 3.11). Corregido.

### [x] 12. Assist de los CX como pieza aparte
- Regla (Alex): el Assist es una pieza propia de los CX, intercambiable entre CX. Los UX/BX no llevan Assist.
- [x] `scraper.py`: nombres de 3 o más palabras → la última va a la columna `Assist` ("Pegasus Blast Wheel" → Blade "Pegasus Blast" + Assist "Wheel"; "Brachio Whip Outer Wheel" → "Brachio Whip Outer" + "Wheel"). El over blade sigue dentro del Blade. Nuevo `assist_stats.csv`; `blade_stats.csv` agrupa por lock chip + main blade.
- [x] `beyblade_stats.csv` y todo `history/` migrados con la misma regla. `asegurar_assist()` separa al vuelo cualquier CSV antiguo sin la columna.
- [x] `core/compatibility.py`: `blades_cx()` deduce los CX de los datos como los UX Expanded (≥3 partidas con Assist y ≥50 % de sus partidas). `combo_valido()` exige Assist si y solo si el Blade es CX. `generar_candidatos()` construye solo combos legales. `piezas_blade()`/`blade_repetido()` tratan el Assist como pieza física.
  - Umbral del 50 % (no 80 %): en los CX es habitual registrar sin Assist ("Sol Eclipse": 13 con Assist, 4 sin él).
  - Descartados por el loader como errores de registro: CX sin Assist (Bucks Antler 2p, Cerberus Flame 7p, Lightning L-Drago 4p, Sol Eclipse 4p, Wizard Arc 5p) y "Dran Sword Free" (3p, Dran Sword es BX).
- [x] Modelo: `Assist_enc` y `Assist_score` como features; "sin Assist" usa ws_mean (con leave-one-out el grupo UX/BX codificaba el target y el R² CV caía de 0,45 a 0,34). R² CV 0,45 / Spearman 0,65 (antes 0,46 / 0,66). `par_ba` (Blade+Assist) como evidencia del ancla. `formato` en el payload: `model_loader` reentrena en memoria si `model.pkl` es antiguo.
- [x] Recomendador, META Oculto y Deckbuilder proponen Blade CX + cualquier Assist aunque no se haya jugado. Ancla y predicción unificadas en `core/recommender.predecir()` (META Oculto la reutiliza).
- [x] Selector de Assist en Recomendador, META Oculto, Deckbuilder, Matchup y Deck Match (desactivado en UX/BX, sin repetir en el deck). Filtro de Assist en META Tracker y Arquetipos, top 10 de Assists y tendencias por Assist (cuota sobre las partidas de CX).
- Matchup / Deck Match: en combos no jugados, el hueco "Blade" de un CX es la media de Blade y Assist (provisional, pendiente de la 8).
- Pendiente: META Oculto tiene ahora ~3 veces más candidatos (442k frente a 154k) y sigue muestreando 2000 al azar (la 7).

### [ ] 7. META Oculto
- Toma 2000 combos al azar antes de ordenar, así que el top es el de una muestra aleatoria y no de todos los candidatos.
- `_arquetipos_esperados` busca columnas que no existen y siempre devuelve "Desconocido".

### [x] 10. Trending poco fiable (rediseñado)
- Compara solo las dos últimas capturas, con intervalos irregulares (la última es de 3 días frente a 7).
- Con semanas idénticas todos los scores dan 0 y el top 10 sale arbitrario.
- Los combos nuevos nunca aparecen.
- El texto de la página dice que usa el winrate y el código no lo usa.
- Actividad real (partidas nuevas entre capturas): entre 0 y 150 por semana; de mediados de junio a finales de julio casi nada; el último mes, ~440 partidas repartidas en 61 combos.
- Artefacto: los combos UX Expanded salen como "nuevos" el 2026-09-24 por el cambio del parser, no porque sean nuevos.
- Rediseño (aprobado por Alex e implementado en `core/trending.py`, `pages/1_META_Tracker.py` y `components/charts.py`):
  - Ventana adaptativa: ir hacia atrás en el histórico hasta reunir un mínimo de partidas nuevas (p.ej. 300) o 4 semanas. Mostrar el periodo y el número de partidas. Sin actividad, decir "sin actividad desde X" en vez de ceros.
  - Métrica: cuota de uso en la ventana frente a la cuota histórica anterior, con un mínimo de partidas.
  - Tres listas: En alza, En caída (conecta con la obsolescencia tipo Hells Scythe) y Novedades (excluyendo artefactos del parser).
  - Tendencias por pieza además de por combo, porque son más robustas con este volumen.
  - WR reciente (Wilson de la ventana) al lado del histórico.
  - Gráfica de evolución: partidas y cuota por periodo, en lugar del WR acumulado (que casi no se mueve).
  - Parámetros en `core/trending.py`: MIN_DIAS=28, MIN_PARTIDAS=300, K_SHRINK=100, MIN_RECIENTES=5, MIN_HISTORICAS=20, MIN_NOVEDAD=3.
  - Artefactos del parser: `CAMBIOS_PARSER` guarda la fecha en que el scraper empezó a reconocer cada Ratchet (UX Expanded: 2026-09-24). Hay que añadir una entrada cada vez que el parser empiece a reconocer algo nuevo.
  - Probado con AppTest de Streamlit sobre datos reales, sin excepciones en ningún nivel.

### [x] 9. La simulación del Deck Match no sigue el formato real (implementado)
- `core/matchup.py::simular_deck_match`: solo avanza el bey del que pierde, y si se acaban los beys sin llegar a 4 cuenta derrota de A (sesgo contra A).
- Comprobar el reglamento de la SBBL (rotación de beys, empates, puntos por tipo de finish) y rehacer la simulación.
- Usa Pts Ganados/Combate medio como puntos fijos por victoria.
- Análisis (sin arreglar todavía):
  - a) Fin de partida: se para cuando un lado agota sus 3 beys (cada lado gana 3 combates como mucho). Si 3×pts < 4 nadie puede llegar a 4, y la partida sin ganador cuenta como derrota de A. El 40 % de los combos tiene pts < 4/3 (el 27 % de los que tienen 10 o más partidas), entre ellos Wizard Rod 1-60 Hexa (1,27). En un espejo con pts 1,3, P(A) = 0 %.
  - Formato real (confirmado por Alex): los dos jugadores avanzan al siguiente bey tras cada combate, ganen o pierdan. Tras los 3 combates, si nadie tiene 4 puntos, cada uno elige un orden nuevo y se repite hasta que alguien llegue a 4.
  - b) Rotación: el código solo hace avanzar al bey del que pierde, lo que no corresponde al formato real.
  - Más reglas confirmadas: los órdenes se eligen a la vez y a ciegas, viendo las piezas del rival. El orden de cada ronda nueva se elige conociendo el marcador. No hay empates. Spin = 1, Burst/Over = 2, Xtreme = 3.
  - Propuesta de diseño (pendiente de aprobar):
    - Cálculo exacto por programación dinámica sobre el marcador (sa, sb), sin Monte Carlo.
    - Cada ronda es un juego de suma cero de 6×6 órdenes. Se resuelve con programación lineal y da la estrategia mixta óptima y P(victoria) con juego óptimo.
    - Resultados: P(ganar) con juego óptimo, P(ganar) con órdenes al azar, mejor respuesta si se conoce el orden del rival, y estrategia recomendada según el marcador.
    - Puntos por combate: media entre Pts Ganados de A y Pts Cedidos de B, repartida en {1,2,3} (por decidir cómo).
    - P(A gana un combate): depende de lo que se decida en la 8. Con esta regla el orden casi no influye (mismo deck en otro orden: 49,48 % frente a 49,48 %), así que el "orden óptimo" es básicamente ruido.
  - c) Puntos: se usa la media como valor fijo. En realidad son 1/2/3 según el tipo de finish, dependen de cómo pierde el rival (no se usan los Pts Cedidos de B) y no se modelan empates.
  - d) La probabilidad por combate es la de la 8 (ws_a/(ws_a+ws_b) sobre límites inferiores de Wilson).
  - [x] `core/deck_match.py`: cálculo exacto por marcador con juego de suma cero 6×6 por ronda (programación lineal). Validado: espejo = 50 %, P(A)+P(B) = 1, y coincide con Monte Carlo (55,9 % frente a 55,85 %).
  - [x] `pages/8_Deck_Match.py`: P(ganar) si ambos juegan bien, P(ganar) si ambos eligen al azar, orden de la 1ª ronda, mejor respuesta si se intuye el orden del rival, y estrategia según el marcador. Eliminado el Monte Carlo antiguo de `core/matchup.py`. Añadido `scipy` a requirements.
  - Hallazgo: con la P por combate actual, el orden en la 1ª ronda apenas influye (<1 pp). Influye más en rondas posteriores según el marcador. Con matchups tipo piedra-papel-tijera el efecto sería enorme (19-81 %), pero no hay datos de enfrentamientos directos.
  - Decisiones tomadas por defecto (revisables):
    - Reparto de puntos: propuesto repartir la media en los dos enteros más cercanos (1,27 → 73 % spin, 27 % burst/over). Es una suposición: el dato bueno sería el desglose de finishes (fuera de alcance, no se amplía la fuente).
    - P(A gana un combate): se decide con la 8 (winrate encogido con prior Beta o Bradley-Terry en lugar del límite inferior del Wilson). La simulación debe aceptar cualquier probabilidad por combate.

### [-] 11. Faltan derrotas en el dataset (ACEPTADO: se asume como limitación de la fuente)
- En el CSV hay 7.605 victorias y 5.421 derrotas; en un registro completo deberían coincidir. El WR medio sale 58,4 % en lugar de 50 %.
- Posible sesgo de selección: combos incompletos ("Selecciona un bit") o no registrados, que acumulan derrotas y se descartan. Afecta al nivel absoluto de todos los winrates y al Matchup (la 8).
- Hipótesis de Alex: sobre todo, la gente no apunta las derrotas (problema de la fuente, no del scraper).
- Opciones:
  - Tasa de registro de derrotas r = derrotas/victorias totales (hoy ≈0,71). WR ajustado = W / (W + L/r): la media vuelve al 50 % y el orden por WR no cambia. Supone que todos infrarregistran igual.
  - Mostrar WR relativo a la media (+X pp) en vez del absoluto.
  - En Matchup/Deck Match usar diferencias entre combos (el sesgo común se anula). Se resuelve con la 8.
  - Opcional: medir en el scraper las victorias y derrotas descartadas por cada filtro, para confirmar que no es culpa nuestra.

## Menores (sin prioridad)
- [ ] "Winrate medio" de los filtros sin ponderar por partidas.
- [ ] Lógica de arquetipos duplicada en `scraper.py` y `pages/2_Arquetipos.py`.
- [ ] Wilson implementado en 4 sitios, con resultados distintos para n=0 (None o 0).
- [ ] El scraper asume fila de combo + fila de detalle (`i += 2`). Si falta una, los puntos se asignan al combo equivocado sin avisar.
- [ ] `dropna` descarta filas sin detalle sin dejar registro.
