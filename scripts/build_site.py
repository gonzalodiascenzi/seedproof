#!/usr/bin/env python3
"""
Genera site/data.json para la web (site/index.html). Reutiliza las funciones
de rank.py para que la web muestre exactamente el mismo ranking que el
reporte en ranking/<fecha>.md. Sin IA, sin red.

Se corre al final del ciclo diario y del boletín. Siempre escribe el archivo;
el workflow decide si hay algo que commitear.
"""
import glob
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import rank as rk

REPO_URL = "https://github.com/gonzalodiascenzi/seedproof"


def ficha_links(root):
    """id del caso -> URL de su ficha en casos/ (los archivos van numerados)."""
    out = {}
    for path in sorted(glob.glob(os.path.join(root, "casos", "*.md"))):
        name = os.path.basename(path)
        m = re.match(r"\d+-(.+)\.md$", name)
        if m:
            out[m.group(1)] = f"{REPO_URL}/blob/main/casos/{name}"
    return out


def main():
    config = common.load_config()
    cfg = config["ranking"]
    root = common.ROOT
    today = datetime.now(timezone.utc).date()

    cases = common.load_json(os.path.join(root, config["cases_file"]), [])
    checks = common.load_json(os.path.join(root, config["ai_checks_file"]), {})
    state = common.load_json(os.path.join(root, config["ranking_state_file"]), {})
    vstate = common.load_json(os.path.join(root, config["validation_state_file"]), {})
    fichas = ficha_links(root)

    ranked, unverified, discarded = rk.build_ranking(cases, checks, cfg, today)
    zones = state.get("zones", {})

    def row(r):
        c = r["case"]
        ck = checks.get(c["id"]) or {}
        return {
            "id": c["id"],
            "name": c["name"],
            "light": rk.LIGHT.get(c.get("light"), "yellow"),
            "category": c.get("category"),
            "ai_role": c.get("ai_role"),
            "evidence_level": c.get("evidence_level"),
            "launched": c.get("launched"),
            "ended": c.get("ended"),
            "metrics": c.get("metrics") or {},
            "flags": c.get("flags", []),
            "status": r["status"],
            "rank": r.get("rank"),
            "zone": zones.get(c["id"]) or (rk.zone_of(r["rank"], cfg) if r.get("rank") else None),
            "score": r["score"],
            "check": {
                "checked_at": ck.get("checked_at"),
                "domains": ck.get("domains", []),
                "evidence": ck.get("evidence", []),
            },
            "facts": [
                {"text": f["text"], "source_url": f["source_url"], "label": f.get("label") or "Fuente"}
                for f in c["facts"]
            ],
            "ficha_url": fichas.get(c["id"]),
        }

    def hist_key(path):
        stem = os.path.basename(path)[:-5]
        m = re.match(r"(\d{4}-\d{2}-\d{2})(?:-(\d+))?$", stem)
        return (m.group(1), int(m.group(2) or 1)) if m else (stem, 0)

    history = []
    for path in sorted(glob.glob(os.path.join(root, config["history_dir"], "*.json")), key=hist_key):
        day = os.path.basename(path)[:-5]
        snap = common.load_json(path, [])
        ranks = {s["id"]: s.get("rank") for s in snap if s.get("rank")}
        podium = sorted(ranks, key=ranks.get)[:3]
        history.append({"date": day, "podium": podium, "ranks": ranks})

    vsources = vstate.get("sources", {})
    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "ranking_date": state.get("date"),
        "repo_url": REPO_URL,
        "podium_size": cfg["podium_size"],
        "repechaje_size": cfg["repechaje_size"],
        "ranked": [row(r) for r in ranked],
        "unverified": [row(r) for r in unverified],
        "discarded": [row(r) for r in discarded],
        "radar": rk.radar(ranked, cfg),
        "history": history,
        "validation": {
            "last_run_at": vstate.get("last_run_at"),
            "total": len(vsources),
            "up": sum(1 for v in vsources.values() if v.get("status") == "up"),
            "down": sum(1 for v in vsources.values() if v.get("status") == "down"),
            "blocked": sum(1 for v in vsources.values() if v.get("status") == "blocked"),
        },
    }
    out_dir = os.path.join(root, "site")
    os.makedirs(out_dir, exist_ok=True)
    common.save_json(os.path.join(out_dir, "data.json"), data)
    print(f"Escrito: site/data.json ({len(ranked)} en ranking, {len(history)} día(s) de historial)")


if __name__ == "__main__":
    main()
