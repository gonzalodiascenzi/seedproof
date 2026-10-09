#!/usr/bin/env python3
"""
Exporta los "ingredientes" para tableproof: los emprendimientos automatizables
de punta a punta, en un archivo que el otro repo puede leer sin interpretar
nada (data/ingredients.json).

Reglas:
  - Entra un caso solo si sus 4 campos de `automation` (config.yml) están en
    true. Un false o un null lo deja afuera: nada se asume.
  - No depende de la segunda validación de IA (la IA ya no es requisito del
    criterio), pero cada ingrediente informa su estado de validación.
  - El archivo no lleva fecha: solo se reescribe si cambió el contenido, así
    el ciclo diario no genera commits de relleno.

Exit codes:
  0 = se reescribió data/ingredients.json
  3 = nada cambió
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import rank as rk

OUT = "data/ingredients.json"


def build(cases, checks, cfg, today):
    fields = list((cfg.get("automation") or {}).get("fields") or {})
    out = []
    for c in cases:
        _pts, state, _missing = rk.automation_state(c, cfg)
        if state != "ok":
            continue
        sc = rk.score_case(c, cfg, today)
        out.append({
            "id": c["id"],
            "name": c["name"],
            "category": c.get("category"),
            "ai_role": c.get("ai_role"),
            "light": rk.LIGHT.get(c.get("light")),
            "evidence_level": c.get("evidence_level"),
            "validation": rk.check_status(c, checks),
            "revenue_usd_annual": (c.get("metrics") or {}).get("revenue_usd_annual"),
            "revenue_basis": (c.get("metrics") or {}).get("revenue_basis"),
            "score": sc["total"],
            "missing": sc["missing"],
            "automation": {k: (c.get("automation") or {}).get(k) for k in fields},
            "automation_sources": c.get("automation_sources", {}),
            "automation_notes": c.get("automation_notes", {}),
            "fact_sources": sorted({f["source_url"] for f in c.get("facts", [])}),
        })
    out.sort(key=lambda r: (-r["score"], r["name"].lower()))
    return out


def main(today=None, config=None):
    config = config or common.load_config()
    cfg = config["ranking"]
    today = today or datetime.now(timezone.utc).date()
    root = common.ROOT
    cases = common.load_json(os.path.join(root, config["cases_file"]), [])
    checks = common.load_json(os.path.join(root, config["ai_checks_file"]), {})
    ingredients = build(cases, checks, cfg, today)
    path = os.path.join(root, OUT)
    payload = {"ingredients": ingredients}
    if common.load_json(path, None) == payload:
        print(f"Sin cambios en los ingredientes ({len(ingredients)}) — nada que exportar.")
        sys.exit(3)
    common.save_json(path, payload)
    print(f"Escrito: {OUT} ({len(ingredients)} ingrediente(s))")
    sys.exit(0)


if __name__ == "__main__":
    main()
