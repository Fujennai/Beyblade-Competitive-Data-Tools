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

### [ ] 5. El target premia la popularidad
- El Wilson correlaciona 0,67 con log(Partidas) y `Partidas_log` es una feature.
- En inferencia se fija a mano: 10 en Recomendador y 50 en META Oculto. El mismo combo da predicciones distintas según la página.

### [ ] 8. Matchup y Deck Match inconsistentes
- Matchup usa la media de las piezas aunque el combo tenga datos reales (ignora su Wilson propio).
- Las medias por pieza son medias simples de los Wilson de cada combo, sin ponderar por partidas. Deberían usar el Wilson agregado de la pieza.
- Deck Match usa el Wilson real en los combos vistos y una media sin pesos en los no vistos, así que el mismo enfrentamiento da otro número en cada página.
- `prob_victoria = ws_a / (ws_a + ws_b)` no tiene base estadística. Justificarla o cambiarla (Bradley-Terry o similar).

## Tier 3

### [ ] 2. Recomendaciones con combos ilegales
- `recomendar_builds` y `generar_combos` no aplican `ratchets_validos`: Clock Mirage con ratchets que no acaban en 5, y UX Expanded en Blades sin esa versión (solo en el Recomendador).
- El Deckbuilder lo hereda.

### [ ] 3. Regla de las wheels compartidas no implementada
- Deckbuilder y Deck Match solo comparan el nombre completo del Blade: permiten Pegasus Blast Heavy + Pegasus Blast Jaggy o repetir la assist blade (Heavy en dos Blades).

### [ ] 7. META Oculto
- Toma 2000 combos al azar antes de ordenar, así que el top es el de una muestra aleatoria y no de todos los candidatos.
- `_arquetipos_esperados` busca columnas que no existen y siempre devuelve "Desconocido".

### [ ] 10. Trending poco fiable
- Compara solo las dos últimas capturas, con intervalos irregulares (la última es de 3 días frente a 7).
- Con semanas idénticas todos los scores dan 0 y el top 10 sale arbitrario.
- Los combos nuevos nunca aparecen.
- El texto de la página dice que usa el winrate y el código no lo usa.

### [ ] 9. La simulación del Deck Match no sigue el formato real (movido desde el Tier 1; diseño acordado, pendiente de implementar)
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
  - Decisiones pendientes al implementar:
    - Reparto de puntos: propuesto repartir la media en los dos enteros más cercanos (1,27 → 73 % spin, 27 % burst/over). Es una suposición: el dato bueno sería el desglose de finishes (fuera de alcance, no se amplía la fuente).
    - P(A gana un combate): se decide con la 8 (winrate encogido con prior Beta o Bradley-Terry en lugar del límite inferior del Wilson). La simulación debe aceptar cualquier probabilidad por combate.

## Menores (sin prioridad)
- [ ] "Winrate medio" de los filtros sin ponderar por partidas.
- [ ] Lógica de arquetipos duplicada en `scraper.py` y `pages/2_Arquetipos.py`.
- [ ] Wilson implementado en 4 sitios, con resultados distintos para n=0 (None o 0).
- [ ] El scraper asume fila de combo + fila de detalle (`i += 2`). Si falta una, los puntos se asignan al combo equivocado sin avisar.
- [ ] `dropna` descarta filas sin detalle sin dejar registro.
