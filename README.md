# SeedProof

Emprendimientos construidos con IA, investigados con deep research y con la
fuente de cada línea a la vista. Hermano de
[GreenProof](https://github.com/gonzalodiascenzi/greenproof) (ciberseguridad):
misma regla — **nada inventado, nada de relleno** — aplicada a otro tema.

Si una fuente no alcanza para afirmar algo, el caso lo dice. Si el contenido
no cambió, no hay commit.

## Semáforo

- 🟢 ingresos o resultados verificados por una fuente independiente
  (dashboard sincronizado con el procesador de pagos, presentación
  regulatoria, comunicado del adquirente) y sostenidos en el tiempo.
- 🟡 plausible, pero autodeclarado, parcial o con un modelo de negocio frágil.
- 🔴 cifra desmentida, colapso, o sin verificación independiente y con
  evidencia en contra.

El semáforo lo asigna el dato curado en `data/cases.json`. El modelo de IA
nunca lo decide.

## Qué hay

| Qué | Cadencia | IA | Dónde |
|---|---|---|---|
| **Validación de fuentes** | diaria | no | `validation/<fecha>.md` |
| **Boletín** | semanal (hasta 3 casos por corrida) | sí, acotada | `bulletins/<fecha>.md` |
| **Fichas de casos** | a mano | no | `casos/` |
| **Evidencia agregada** | a mano | no | `agregados.md` |

### Validación diaria (`seedproof-validate.yml`)

Abre cada URL citada y la compara con la corrida anterior:

- si responde, si falla o si bloquea a los bots (un bloqueo no es un cambio
  del contenido: se informa como limitación);
- si un hecho trae `anchors` (textos que deben aparecer literalmente en la
  fuente), que sigan apareciendo;
- si el caso es `live: true` (por ejemplo un dashboard de ingresos), avisa
  cuando cambia el contenido de la página.

La primera corrida fija la línea base y reporta lo que no pudo confirmar. Desde
la segunda, **solo commitea si algo cambió**; si no, termina en verde sin
commit. Nunca modifica casos ni boletines: un cambio significa "revisá esta
fuente", no "el dato es falso".

### Boletín semanal (`seedproof-bulletin.yml`)

1. Los hechos salen de `data/cases.json`, cada uno con su texto y su URL.
2. Un modelo de Anthropic redacta una oración por caso, a partir de esos hechos.
3. Un validador rechaza el boletín entero si el texto incluye una cifra, URL o
   identificador que no esté literalmente en los hechos, si cita hechos de
   otro caso, o si usa palabras de opinión o acusación.

Necesita el secret `ANTHROPIC_API_KEY`. Sin él no hace nada (no falla). El
modelo está en `config.yml` (`bulletin_model`): confirmá en
<https://docs.claude.com/en/docs/about-claude/models> qué id está vigente.

## Agregar un caso

1. Leé la fuente primaria.
2. Sumá una entrada en `data/cases.json` con `id`, `name`, `light`, `rev` y
   `facts` (`text`, `source_url`, `label`, y opcionalmente `anchors`).
3. Si querés que la validación diaria vigile el contenido de la página,
   marcá `live: true`.
4. Abrí un PR. Si actualizás un caso ya publicado, subí su `rev` y se vuelve a
   reportar.

Los casos no se agregan solos: alguien tiene que leer la fuente.

## Probar sin GitHub

```bash
pip install -r requirements.txt
python scripts/validate_sources.py                   # validación de fuentes
ANTHROPIC_API_KEY=... python scripts/gen_bulletin.py # boletín
```

Cada script termina con código `3` cuando no hay nada nuevo: no es un error.

## Límites a propósito

- El semáforo no es una opinión del bot: sale de la fuente.
- Los anchors de `data/cases.json` están sin confirmar contra la página real
  hasta la primera corrida: si alguno no aparece, la línea base lo informa.
- Esto no es asesoría financiera ni de inversión.
