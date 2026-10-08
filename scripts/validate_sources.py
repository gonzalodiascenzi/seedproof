#!/usr/bin/env python3
"""
Validación diaria de fuentes de SeedProof — sin IA.

Para cada URL citada en data/cases.json:
  - la abre y registra si responde (up), si no responde o da error (down) o
    si bloquea a los bots (blocked: 401/403/429), porque eso no es un cambio
    del contenido sino una limitación de la verificación;
  - si el hecho trae `anchors` (textos que deben aparecer literalmente en la
    fuente), chequea que sigan apareciendo;
  - si el caso está marcado `live: true` (páginas cuyo contenido cambia a
    propósito, como un dashboard de ingresos), guarda un hash del texto y
    avisa cuando cambia.

Solo se REPORTA un cambio de estado respecto de la corrida anterior (la
primera corrida es la línea base). Si no cambió nada, no escribe nada y sale
con código 3: nunca hay commit de relleno.

Nunca modifica data/cases.json ni los boletines: detectar un cambio no es
decidir qué significa. Genera un reporte para que una persona revise la fuente.

Exit codes:
  0 = hay cambios (o línea base): se escribió validation/<fecha>.md
  3 = nada cambió
"""
import hashlib
import html
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

from jinja2 import Environment, FileSystemLoader

BLOCKED = {401, 403, 429}


def fetch(url, timeout):
    """Devuelve (estado, texto). estado: 'up' | 'down' | 'blocked'."""
    req = urllib.request.Request(url, headers={"User-Agent": common.USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(2_000_000)
            charset = resp.headers.get_content_charset() or "utf-8"
            return "up", raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        return ("blocked" if e.code in BLOCKED else "down"), ""
    except (urllib.error.URLError, TimeoutError, OSError):
        return "down", ""


def normalize(page_html):
    text = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", page_html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def collect_sources(cases):
    """url -> {cases: set, anchors: set, live: bool}"""
    out = {}
    for c in cases:
        for f in c["facts"]:
            s = out.setdefault(
                f["source_url"], {"cases": set(), "anchors": set(), "live": False}
            )
            s["cases"].add(c["name"])
            s["anchors"].update(f.get("anchors") or [])
            s["live"] = s["live"] or bool(c.get("live"))
    return out


def check_source(url, info, prev, timeout, fetch_fn=fetch):
    """Devuelve (estado_nuevo, [cambios])."""
    status, page = fetch_fn(url, timeout)
    text = normalize(page) if status == "up" else ""
    new = {"status": status}
    if info["anchors"]:
        new["anchors"] = {a: (a in text) for a in sorted(info["anchors"])} if status == "up" else (prev or {}).get("anchors", {})
    if info["live"]:
        new["hash"] = hashlib.sha256(text.encode("utf-8")).hexdigest() if status == "up" else (prev or {}).get("hash")

    changes = []
    if prev is None:
        # Línea base: se informa lo que no se pudo confirmar, una sola vez.
        if status != "up":
            changes.append(f"línea base: la fuente no se pudo abrir ({status})")
        for a, found in new.get("anchors", {}).items():
            if status == "up" and not found:
                changes.append(f"línea base: el texto «{a}» no aparece en la fuente")
        return new, changes

    if prev.get("status") != status:
        changes.append(f"estado {prev.get('status')} → {status}")
    if status == "up":
        for a, found in new.get("anchors", {}).items():
            was = prev.get("anchors", {}).get(a)
            if was and not found:
                changes.append(f"el texto «{a}» dejó de aparecer en la fuente")
            elif was is False and found:
                changes.append(f"el texto «{a}» volvió a aparecer en la fuente")
        if info["live"] and prev.get("hash") and new.get("hash") != prev.get("hash"):
            changes.append("el contenido de la página cambió (revisar si la cifra citada sigue vigente)")
    return new, changes


def main(fetch_fn=fetch):
    config = common.load_config()
    cases = common.load_json(os.path.join(common.ROOT, config["cases_file"]), [])
    state_path = os.path.join(common.ROOT, config["validation_state_file"])
    state = common.load_json(state_path, {"last_run_at": None, "sources": {}})
    timeout = int(config.get("fetch_timeout_seconds", 25))

    sources = collect_sources(cases)
    baseline = state.get("last_run_at") is None
    new_sources, report = {}, []
    for url in sorted(sources):
        info = sources[url]
        prev = state["sources"].get(url)
        new, changes = check_source(url, info, prev, timeout, fetch_fn)
        new_sources[url] = new
        if changes:
            report.append({"url": url, "cases": sorted(info["cases"]), "changes": changes})

    if not report and not baseline:
        print(f"Sin cambios en {len(sources)} fuente(s) — nada que reportar.")
        sys.exit(3)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    counts = {s: sum(1 for v in new_sources.values() if v["status"] == s) for s in ("up", "down", "blocked")}
    env = Environment(
        loader=FileSystemLoader(os.path.join(common.ROOT, "templates")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    rendered = env.get_template("validation.md.j2").render(
        generated_at=today, baseline=baseline, total=len(sources), counts=counts, report=report
    )
    out_dir = os.path.join(common.ROOT, config["validation_dir"])
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{today}.md")
    suffix = 2
    while os.path.exists(out_path):
        out_path = os.path.join(out_dir, f"{today}-{suffix}.md")
        suffix += 1
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    state["sources"] = new_sources
    state["last_run_at"] = today
    common.save_json(state_path, state)
    print(f"Escrito: {out_path} ({len(report)} fuente(s) con cambios)")
    sys.exit(0)


if __name__ == "__main__":
    main()
