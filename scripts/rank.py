#!/usr/bin/env python3
"""
Ranking diario de SeedProof — determinístico, sin IA.

Reglas:
  - Solo entran al ranking los casos cuyo ai_check (data/ai_checks.json, escrito
    por scripts/verify_ai.py) está "confirmed" para la `rev` vigente del caso.
    Los demás se listan aparte: "sin validar" (pendiente o sin evidencia
    suficiente) y "descartados" (la evidencia verificada los contradice).
  - El puntaje es una rúbrica transparente (pesos en config.yml, hipótesis
    iniciales sin validar): evidencia + tracción ponderada por la
    independencia de su fuente + antigüedad + semáforo − penalizaciones.
  - Podio = los primeros `podium_size`; repechaje = los siguientes
    `repechaje_size` (puestos 4 a 10); el resto queda en la banca. Todos
    compiten todos los días.
  - Se escribe reporte y se commitea SOLO si cambió el orden del ranking o el
    estado de validación de algún caso. Si no, sale con código 3: no hay commit
    de relleno.
  - También guarda una foto diaria de variables y puntajes en data/history/
    (dataset para modelos futuros; no entrena nada hoy).

Exit codes:
  0 = hubo cambios: se escribió ranking/<fecha>.md
  3 = nada cambió
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

from jinja2 import Environment, FileSystemLoader

LIGHT = {"🟢": "green", "🟡": "yellow", "🔴": "red"}
LIGHT_ICON = {v: k for k, v in LIGHT.items()}


def months_between(ym, today):
    y, m = (int(x) for x in ym.split("-"))
    return (today.year - y) * 12 + (today.month - m)


def age_months(case, today):
    launched = case.get("launched")
    if not launched:
        return None
    end = case.get("ended")
    if end:
        y, m = (int(x) for x in end.split("-"))
        ly, lm = (int(x) for x in launched.split("-"))
        return max(0, (y - ly) * 12 + (m - lm))
    return max(0, months_between(launched, today))


def band_points(value, bands, top):
    for limit, pts in bands:
        if value < limit:
            return pts
    return top


def check_status(case, checks):
    """confirmed | contradicted | unconfirmed | pending"""
    ck = checks.get(case["id"])
    if not ck or ck.get("rev") != case.get("rev", 1):
        return "pending"
    return ck.get("status", "pending")


def score_case(case, cfg, today):
    ev = int(case.get("evidence_level") or 0)
    v = min(4, max(0, ev)) * cfg["evidence_points_per_level"]

    rev = (case.get("metrics") or {}).get("revenue_usd_annual")
    basis = (case.get("metrics") or {}).get("revenue_basis")
    if rev and basis in cfg["basis_multiplier"]:
        t = band_points(rev, cfg["traction_bands"], cfg["traction_top"]) * cfg["basis_multiplier"][basis]
    else:
        t = 0.0

    age = age_months(case, today)
    s = band_points(age, cfg["age_bands"], cfg["age_top"]) if age is not None else 0

    light = LIGHT.get(case.get("light"), "yellow")
    l = cfg["light_points"][light]

    f = sum(cfg["flag_penalties"].get(flag, 0) for flag in case.get("flags", []))

    total = max(0.0, min(100.0, v + t + s + l + f))
    return {
        "total": round(total, 1),
        "evidence": v,
        "traction": round(t, 1),
        "age": s,
        "light": l,
        "flags": f,
        "age_months": age,
        "missing": [k for k, ok in (("antigüedad", age is not None), ("ingresos", bool(rev and basis))) if not ok],
    }


def build_ranking(cases, checks, cfg, today):
    ranked, unverified, discarded = [], [], []
    for c in cases:
        st = check_status(c, checks)
        row = {"case": c, "status": st, "score": score_case(c, cfg, today)}
        if st == "confirmed":
            ranked.append(row)
        elif st == "contradicted":
            discarded.append(row)
        else:
            unverified.append(row)
    # desempate: puntaje, luego nivel de evidencia, luego nombre
    ranked.sort(key=lambda r: (-r["score"]["total"], -int(r["case"].get("evidence_level") or 0), r["case"]["name"].lower()))
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i
    return ranked, unverified, discarded


def zone_of(rank, cfg):
    if rank <= cfg["podium_size"]:
        return "podio"
    if rank <= cfg["podium_size"] + cfg["repechaje_size"]:
        return "repechaje"
    return "banca"


def movement(row, prev_rank):
    if prev_rank is None:
        return "nuevo"
    d = prev_rank - row["rank"]
    return f"▲{d}" if d > 0 else (f"▼{-d}" if d < 0 else "=")


def radar(ranked, cfg):
    """Dónde el mercado entrega bien o mal, solo con casos validados y solo si
    el grupo tiene muestra mínima. Con pocos casos, no opina."""
    out = []
    for key, label in (("category", "categoría"), ("ai_role", "rol de la IA")):
        groups = {}
        for r in ranked:
            groups.setdefault(r["case"].get(key) or "sin dato", []).append(r)
        for name, rows in sorted(groups.items()):
            n = len(rows)
            lights = [LIGHT.get(r["case"].get("light"), "yellow") for r in rows]
            g, y, rd = lights.count("green"), lights.count("yellow"), lights.count("red")
            if n < cfg["min_cases_per_group"]:
                verdict = f"sin muestra suficiente (mínimo {cfg['min_cases_per_group']})"
            elif g / n >= 0.4 and rd / n <= 0.2:
                verdict = "el mercado entrega bien (competido)"
            elif rd / n >= 0.4:
                verdict = "el mercado entrega mal (posible hueco)"
            else:
                verdict = "mixto"
            out.append({"dimension": label, "group": name, "n": n, "green": g, "yellow": y, "red": rd, "verdict": verdict})
    return out


def signature(ranked, unverified, discarded):
    return {
        "order": [r["case"]["id"] for r in ranked],
        "status": {r["case"]["id"]: r["status"] for r in ranked + unverified + discarded},
    }


def main(today=None, config=None):
    config = config or common.load_config()
    cfg = config["ranking"]
    today = today or datetime.now(timezone.utc).date()
    root = common.ROOT
    cases = common.load_json(os.path.join(root, config["cases_file"]), [])
    checks = common.load_json(os.path.join(root, config["ai_checks_file"]), {})
    state_path = os.path.join(root, config["ranking_state_file"])
    state = common.load_json(state_path, {"date": None, "order": [], "status": {}, "zones": {}})

    ranked, unverified, discarded = build_ranking(cases, checks, cfg, today)
    sig = signature(ranked, unverified, discarded)
    baseline = state.get("date") is None
    if not baseline and sig["order"] == state.get("order") and sig["status"] == state.get("status"):
        print(f"Sin cambios en el ranking ({len(ranked)} validado(s), {len(unverified)} sin validar) — nada que reportar.")
        sys.exit(3)

    prev_order = state.get("order", [])
    prev_rank = {cid: i for i, cid in enumerate(prev_order, start=1)}
    prev_zone = state.get("zones", {})
    zones = {}
    for r in ranked:
        cid = r["case"]["id"]
        r["zone"] = zone_of(r["rank"], cfg)
        r["move"] = movement(r, prev_rank.get(cid))
        zones[cid] = r["zone"]

    podium = [r for r in ranked if r["zone"] == "podio"]
    repechaje = [r for r in ranked if r["zone"] == "repechaje"]
    bench = [r for r in ranked if r["zone"] == "banca"]
    zone_changes = []
    for r in ranked:
        cid = r["case"]["id"]
        before = prev_zone.get(cid)
        if before and before != r["zone"]:
            zone_changes.append(f"{r['case']['name']}: {before} → {r['zone']}")
        elif before is None and not baseline:
            zone_changes.append(f"{r['case']['name']}: entra directo a {r['zone']}")
    for cid, before in prev_zone.items():
        if cid not in zones:
            name = next((c["name"] for c in cases if c["id"] == cid), cid)
            zone_changes.append(f"{name}: sale del ranking (estaba en {before})")

    env = Environment(
        loader=FileSystemLoader(os.path.join(root, "templates")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    day = today.strftime("%Y-%m-%d")
    rendered = env.get_template("ranking.md.j2").render(
        generated_at=day,
        baseline=baseline,
        podium=podium,
        repechaje=repechaje,
        bench=bench,
        unverified=unverified,
        discarded=discarded,
        zone_changes=zone_changes,
        radar=radar(ranked, cfg),
        n_total=len(cases),
        light_icon=LIGHT_ICON,
        lights=LIGHT,
    )
    out_dir = os.path.join(root, config["ranking_dir"])
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{day}.md")
    suffix = 2
    while os.path.exists(out_path):
        out_path = os.path.join(out_dir, f"{day}-{suffix}.md")
        suffix += 1
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    hist_dir = os.path.join(root, config["history_dir"])
    os.makedirs(hist_dir, exist_ok=True)
    snapshot = [
        {
            "id": r["case"]["id"],
            "status": r["status"],
            "light": LIGHT.get(r["case"].get("light")),
            "category": r["case"].get("category"),
            "ai_role": r["case"].get("ai_role"),
            "evidence_level": r["case"].get("evidence_level"),
            "revenue_usd_annual": (r["case"].get("metrics") or {}).get("revenue_usd_annual"),
            "revenue_basis": (r["case"].get("metrics") or {}).get("revenue_basis"),
            "age_months": r["score"]["age_months"],
            "flags": r["case"].get("flags", []),
            "score": r["score"]["total"],
            "rank": r.get("rank"),
        }
        for r in ranked + unverified + discarded
    ]
    common.save_json(os.path.join(hist_dir, f"{os.path.basename(out_path)[:-3]}.json"), snapshot)

    common.save_json(state_path, {"date": day, "order": sig["order"], "status": sig["status"], "zones": zones})
    print(f"Escrito: {out_path} ({len(ranked)} en ranking, {len(unverified)} sin validar, {len(discarded)} descartado(s))")
    sys.exit(0)


if __name__ == "__main__":
    main()
