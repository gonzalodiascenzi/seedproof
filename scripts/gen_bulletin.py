#!/usr/bin/env python3
"""
Boletín semanal de SeedProof.

1. Los HECHOS salen de la cola curada data/cases.json: cada hecho tiene su
   texto y su URL fuente. Nada se investiga acá.
2. Un modelo de Anthropic redacta UNA oración por emprendimiento, citando los
   ids de hechos en los que se basa. El semáforo (🟢/🟡/🔴) NO lo decide el
   modelo: sale del dato curado.
3. Antes de escribir nada se valida: toda cifra, URL o identificador del texto
   generado tiene que existir literalmente en los hechos entregados; no puede
   haber palabras de opinión o acusación; todo ítem cita hechos reales de un
   solo emprendimiento. Si algo falla, no se commitea nada.

Cada corrida toma como máximo `bulletin_per_run` emprendimientos aún no
cubiertos (o cuyo `rev` subió desde la última vez).

Exit codes:
  0 = boletín generado y validado
  3 = nada nuevo, o falta ANTHROPIC_API_KEY (no es un error)
  1 = error real (API o validador)
"""
import json
import os
import re
import sys
import urllib.error
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

from jinja2 import Environment, FileSystemLoader

SYSTEM_PROMPT = """Sos un reportero de emprendimientos construidos con IA para un boletín automático. Se te da una lista de HECHOS, cada uno con "id", "case" (id del emprendimiento), "name", "text" y "source_url", todos ya curados con una fuente pública.

Tu única tarea es redactar, para cada emprendimiento, UNA oración breve en español que resuma sus hechos — sin agregar ninguna cifra, nombre, fecha, identificador o URL que no esté literalmente en el "text" de los hechos que cites. Copiá las cifras exactamente como están escritas en el hecho. No opines, no recomiendes, no juzgues, no acuses a nadie, no especules y no cambies lo que la fuente afirma: si el hecho dice que algo es una afirmación del propio fundador o de la empresa, la oración tiene que decirlo. No menciones el semáforo.

Respondé ÚNICAMENTE con un objeto JSON, sin texto antes ni después, sin backticks, con esta forma exacta:

{"items": [{"case": "id-del-emprendimiento", "fact_ids": ["fact-1", "fact-2"], "text": "oración"}]}

Reglas:
- "case" es el id del emprendimiento y debe existir en la lista.
- "fact_ids" es una lista no vacía de ids de hechos que pertenecen a ESE emprendimiento.
- Un ítem por emprendimiento, como máximo.
- Si no hay contenido suficiente para una oración con sentido, devolvé {"items": []}.
"""


def numbers_in(text):
    toks = re.findall(r"\d[\d.,]*\d|\d", text)
    return {t.rstrip(".,") for t in toks}


def build_facts(cases, covered, limit):
    facts, meta, pending = [], {}, []
    for c in cases:
        key = f"{c['id']}@{c.get('rev', 1)}"
        if key not in covered:
            pending.append((c, key))
    pending = pending[:limit]

    n = 0
    for c, _ in pending:
        for f in c["facts"]:
            n += 1
            fid = f"fact-{n}"
            facts.append(
                {
                    "id": fid,
                    "case": c["id"],
                    "name": c["name"],
                    "text": f["text"],
                    "source_url": f["source_url"],
                }
            )
            meta[fid] = {"case": c["id"], "label": f.get("label") or "Fuente"}
    return facts, meta, pending


def validate_items(items, facts):
    if not isinstance(items, list) or not items:
        return False, "El modelo no devolvió ningún ítem."

    by_id = {f["id"]: f for f in facts}
    cases = {f["case"] for f in facts}
    blob = " ".join(f"{f['text']} {f['source_url']} {f['name']}" for f in facts)
    allowed_nums = numbers_in(blob)
    allowed_cves = set(re.findall(r"CVE-\d{4}-\d+", blob))
    allowed_urls = {u.rstrip(".,;)") for u in re.findall(r"https?://\S+", blob)}
    banned = [w.lower() for w in common.BANNED_WORDS]

    seen_cases = set()
    for item in items:
        if not isinstance(item, dict):
            return False, f"Ítem con forma inesperada: {item!r}"
        case = item.get("case")
        if case not in cases:
            return False, f"Emprendimiento inventado: {case!r}"
        if case in seen_cases:
            return False, f"Emprendimiento repetido: {case}"
        seen_cases.add(case)

        fact_ids = item.get("fact_ids") or []
        if not fact_ids:
            return False, f"Ítem sin fact_ids: {item!r}"
        for fid in fact_ids:
            if fid not in by_id:
                return False, f"fact_id inventado: {fid}"
            if by_id[fid]["case"] != case:
                return False, f"El hecho {fid} no pertenece a {case}"

        text = (item.get("text") or "").strip()
        if not text:
            return False, "Ítem con texto vacío."
        lower = text.lower()
        for w in banned:
            if w in lower:
                return False, f"Palabra de opinión/acusación detectada: '{w}'"
        for cve in re.findall(r"CVE-\d{4}-\d+", text):
            if cve not in allowed_cves:
                return False, f"CVE no presente en los hechos: {cve}"
        for url in re.findall(r"https?://\S+", text):
            if url.rstrip(".,;)") not in allowed_urls:
                return False, f"URL no presente en los hechos: {url}"
        for num in numbers_in(text):
            if num not in allowed_nums:
                return False, f"Cifra no presente en los hechos: {num}"
    return True, None


def render(env, items, facts, meta, light_by_case, name_by_case, generated_at):
    by_id = {f["id"]: f for f in facts}
    sources, url_to_num, out_items = [], {}, []
    for item in items:
        nums = []
        for fid in item["fact_ids"]:
            url = by_id[fid]["source_url"]
            if url not in url_to_num:
                sources.append({"label": meta[fid]["label"], "url": url})
                url_to_num[url] = len(sources)
            if url_to_num[url] not in nums:
                nums.append(url_to_num[url])
        out_items.append(
            {
                "light": light_by_case[item["case"]],
                "name": name_by_case[item["case"]],
                "text": item["text"],
                "citation_suffix": "".join(f" [{n}]" for n in nums),
            }
        )
    tpl = env.get_template("bulletin.md.j2")
    return tpl.render(generated_at=generated_at, items=out_items, sources=sources)


def main():
    config = common.load_config()
    cases = common.load_json(os.path.join(common.ROOT, config["cases_file"]), [])
    state_path = os.path.join(common.ROOT, config["bulletin_state_file"])
    state = common.load_json(state_path, {"last_run_at": None, "covered": []})
    limit = int(config.get("bulletin_per_run", 3))

    facts, meta, pending = build_facts(cases, set(state.get("covered", [])), limit)
    if not facts:
        print("No hay emprendimientos nuevos en la cola — nada que reportar.")
        sys.exit(3)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Falta el secret ANTHROPIC_API_KEY — el boletín queda deshabilitado.")
        sys.exit(3)

    model = config.get("bulletin_model", "claude-haiku-4-5-20251001")
    try:
        response = common.call_anthropic(SYSTEM_PROMPT, {"facts": facts}, model, api_key)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = "(sin cuerpo)"
        print(f"No se pudo consultar la API de Anthropic: HTTP {e.code} — {body}", file=sys.stderr)
        sys.exit(1)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"No se pudo consultar la API de Anthropic: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        items = common.extract_model_json(response).get("items", [])
    except (json.JSONDecodeError, AttributeError, KeyError) as e:
        print(f"La respuesta del modelo no es JSON válido: {e}", file=sys.stderr)
        sys.exit(1)

    ok, reason = validate_items(items, facts)
    if not ok:
        print(f"El boletín no pasó el validador — no se commitea nada. Motivo: {reason}", file=sys.stderr)
        sys.exit(1)

    light_by_case = {c["id"]: c["light"] for c, _ in pending}
    name_by_case = {c["id"]: c["name"] for c, _ in pending}
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    env = Environment(
        loader=FileSystemLoader(os.path.join(common.ROOT, "templates")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    rendered = render(env, items, facts, meta, light_by_case, name_by_case, generated_at)

    out_dir = os.path.join(common.ROOT, config["bulletin_dir"])
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{generated_at}.md")
    suffix = 2
    while os.path.exists(out_path):
        out_path = os.path.join(out_dir, f"{generated_at}-{suffix}.md")
        suffix += 1
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(rendered)
    print(f"Escrito: {out_path}")

    # Todo lo que se le mandó al modelo queda cubierto, lo haya usado o no.
    for _, key in pending:
        if key not in state["covered"]:
            state["covered"].append(key)
    state["last_run_at"] = generated_at
    common.save_json(state_path, state)
    print(f"OK — {len(items)} ítem(s) validado(s).")
    sys.exit(0)


if __name__ == "__main__":
    main()
