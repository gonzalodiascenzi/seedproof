# SeedProof

Ranking diario de emprendimientos basados en IA, con la fuente de cada línea a
la vista y una **segunda validación** de que realmente son lo que dicen ser.
Hermano de [GreenProof](https://github.com/gonzalodiascenzi/greenproof)
(ciberseguridad): misma regla — **nada inventado, nada de relleno**.

## El ciclo diario (`seedproof-daily.yml`)

Corre todos los días, en este orden. Solo commitea si algún paso tuvo cambios;
si no, termina en verde sin commit.

1. **Validar fuentes** (`validate_sources.py`, sin IA). Abre cada URL citada y
   la compara con la corrida anterior: si cayó, si bloquea bots, si un texto
   citado dejó de aparecer, o si cambió una página de ingresos (`live: true`).
   Reporte en `validation/<fecha>.md`.
2. **Verificar que realmente es de IA** (`verify_ai.py`, necesita
   `ANTHROPIC_API_KEY`). Un modelo con búsqueda web investiga cada caso, pero
   **no decide solo**: cada cita se comprueba mecánicamente. Resultado en
   `data/ai_checks.json`.
3. **Rankear** (`rank.py`, sin IA). Podio del día, repechaje y radar de
   mercado. Reporte en `ranking/<fecha>.md`.

### La segunda validación

El modelo propone un veredicto y citas literales. Después el script abre cada
URL y exige que la cita aparezca textualmente en la página:

- **confirmed**: la cita se verifica en al menos 2 dominios distintos.
- **contradicted**: solo si al menos una cita verificada lo respalda. Nunca se
  descarta un caso por una acusación sin evidencia.
- cualquier otra cosa: **unconfirmed**.

Una cita inventada, una página que no abre o una URL interna (IP, localhost,
http) no alcanzan nunca para confirmar ni para descartar. El texto libre del
modelo no se guarda; solo las citas que pasaron la verificación. Esta
verificación todavía no se probó contra la API real: solo con respuestas
simuladas.

Solo los casos **confirmed** compiten. Los demás aparecen como "sin validar" o
"descartados" en el reporte.

### El ranking

- **Podio:** los 3 primeros. **Repechaje:** puestos 4 a 10, compiten todos los
  días. El resto queda en la banca.
- Puntaje de 0 a 100 con una rúbrica transparente (`config.yml`): nivel de
  evidencia (hasta 40), tracción ponderada por cuán independiente es la fuente
  del ingreso (hasta 30), antigüedad (hasta 20), semáforo (+10 / 0 / −25) y
  alertas (margen casi nulo, problema regulatorio, incidente de seguridad,
  cifra retractada o discutida, fuente vencida).
- **Los pesos son hipótesis iniciales, sin validar contra datos.** Se ajustan
  en `config.yml`.
- Si falta la antigüedad o el ingreso de un caso, suma 0 y se informa como dato
  faltante: premia lo documentado.
- Desempate: puntaje, nivel de evidencia, nombre.

### El radar de mercado

Agrupa los casos validados por categoría y por rol de la IA y marca dónde el
mercado "entrega bien" (competido), "entrega mal" (posible hueco) o es mixto.
**No opina con menos de 5 casos validados por grupo** (`min_cases_per_group`).
Hoy casi ningún grupo llega a ese mínimo.

### Sobre la red neuronal

No hay una, a propósito. Una red necesita cientos de casos con resultado
conocido, y hoy el pool tiene 12. Entrenarla con eso aprendería el ruido. Lo
que sí hace el ciclo: guarda cada día una foto de variables y puntajes en
`data/history/`. Con suficientes casos y con resultados observados (por
ejemplo, si el emprendimiento seguía vivo 12 meses después), se puede entrenar
un modelo simple y compararlo contra la rúbrica. Una red neuronal solo tendría
sentido con texto (embeddings) y muchos más casos.

## Boletín semanal (`seedproof-bulletin.yml`)

Una oración por caso redactada por un modelo, a partir de hechos curados con
fuente. Un validador rechaza el boletín entero si el texto trae una cifra, URL o
identificador que no esté literalmente en los hechos, si cita hechos de otro
caso o si usa palabras de opinión o acusación. Necesita `ANTHROPIC_API_KEY`.

## Semáforo

- 🟢 ingresos o resultados verificados por una fuente independiente y sostenidos.
- 🟡 plausible, pero autodeclarado, parcial o con un modelo frágil.
- 🔴 cifra desmentida, colapso, o sin verificación independiente y con
  evidencia en contra.

Lo asigna el dato curado en `data/cases.json`; el modelo nunca lo decide.

## Agregar un caso

Los casos no entran solos: alguien lee la fuente primaria y abre un PR con una
entrada en `data/cases.json`:

- `id`, `name`, `light`, `rev`, `category`, `ai_role` (`built_with_ai`,
  `ai_product` o `ai_assisted`)
- `evidence_level`: 1 = publicación del propio fundador; 2 = prensa o
  declaración de la empresa o del adquirente; 3 = dashboard sincronizado con el
  procesador de pagos o publicación primaria verificable; 4 = presentación
  regulatoria o equivalente.
- `metrics.revenue_usd_annual` y `metrics.revenue_basis` (`filing`,
  `payments_dashboard`, `acquirer`, `press_reported`, `self_reported`), `launched`
  y `ended` (`AAAA-MM`), `flags`.
- `facts`: `text`, `source_url`, `label` y opcionalmente `anchors`.

Si actualizás un caso ya publicado, subí su `rev`: se vuelve a verificar y a
reportar.

**Pendiente a propósito:** el descubrimiento automático de candidatos nuevos
(hoy no existe). Sin candidatos nuevos, el ranking solo se mueve cuando cambia
la validación o los datos de un caso.

## Probar sin GitHub

```bash
pip install -r requirements.txt
python scripts/validate_sources.py
ANTHROPIC_API_KEY=... python scripts/verify_ai.py
python scripts/rank.py
ANTHROPIC_API_KEY=... python scripts/gen_bulletin.py
```

Cada script termina con código `3` cuando no hay nada para hacer: no es un
error. `verify_ai.py` y `gen_bulletin.py` usan la API paga de Anthropic: la
verificación tiene un tope de casos por corrida (`verify.max_cases_per_run`).

## Límites a propósito

- Nada de esto es asesoría financiera ni de inversión.
- Los anchors de `data/cases.json` están sin confirmar contra la página real
  hasta la primera corrida.
- Los casos de hoy salen de una investigación inicial; ninguno está validado por
  `verify_ai.py` hasta que corra con una clave real.
