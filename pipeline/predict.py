# -*- coding: utf-8 -*-
"""Genera los pronosticos de los 72 partidos y escribe los JSON que
consume el frontend (predictions.json, standings.json, meta.json).

El marcador recomendado maximiza la esperanza de puntos segun las reglas
de la polla, no la probabilidad puntual del marcador.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import model as M
from .config import scoring
from .config.teams import FLAG_CODES
from .features import State, load_history

ROOT = Path(__file__).parent.parent
DATA = Path(__file__).parent / "data"
OUT = ROOT / "frontend" / "public" / "data"
SEED = DATA / "matches_seed.json"
RESULTS_2026 = DATA / "results_2026.json"
LIVE_WINDOW_H = 2.5


def result_key(m: dict) -> str:
    return f"{m['fecha']}|{m['local_en']}|{m['visitante_en']}"


def load_results_2026() -> dict:
    if RESULTS_2026.exists():
        return json.loads(RESULTS_2026.read_text(encoding="utf-8"))
    return {}


def build_state() -> State:
    """Estado (Elo + forma) con el historico jugado mas resultados 2026 nuevos."""
    df = load_history()
    state = State()
    seen = set()
    for r in df.itertuples(index=False):
        state.advance(
            r.home_team,
            r.away_team,
            r.home_score,
            r.away_score,
            r.tournament,
            r.neutral,
            country=r.country,
        )
        seen.add(f"{r.date.date()}|{r.home_team}|{r.away_team}")

    seed = json.loads(SEED.read_text(encoding="utf-8"))
    res = load_results_2026()
    for m in seed:
        k = result_key(m)
        if k in res and k not in seen:
            host_team = None
            if m["localia"] == "local":
                host_team = m["local_en"]
            elif m["localia"] == "visitante":
                host_team = m["visitante_en"]
            state.advance(
                m["local_en"],
                m["visitante_en"],
                res[k]["home"],
                res[k]["away"],
                "FIFA World Cup",
                m["localia"] == "neutral",
                host_team=host_team,
            )
    return state


def match_estado(m: dict, res: dict, now: datetime) -> str:
    if result_key(m) in res:
        return "finalizado"
    kickoff = datetime.fromisoformat(m["fecha_utc"].replace("Z", "+00:00"))
    if kickoff <= now < kickoff + timedelta(hours=LIVE_WINDOW_H):
        return "en_vivo"
    return "proximo"


def predict_all(backtest_report: dict | None = None):
    state = build_state()
    ml, bl, params = M.load_artifacts()
    rho, blend_w = params["rho"], params["blend_w"]
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    res = load_results_2026()
    now = datetime.now(timezone.utc)

    out_matches = []
    total_pts = 0
    aciertos_exactos = aciertos_resultado = finalizados = 0

    for m in seed:
        home, away = m["local_en"], m["visitante_en"]
        h_home = m["localia"] == "local"
        a_home = m["localia"] == "visitante"

        fh = state.perspective(home, away, h_home, a_home, "FIFA World Cup")
        fa = state.perspective(away, home, a_home, h_home, "FIFA World Cup")
        lams = M.predict_lambdas(ml, bl, pd.DataFrame([fh, fa]), blend_w)
        lh, la = float(lams[0]), float(lams[1])
        matrix = M.score_matrix(lh, la, rho)
        ph, pdr, pa = M.one_x_two(matrix)
        idx = matrix.argmax()
        mas_prob = (int(idx // matrix.shape[1]), int(idx % matrix.shape[1]))
        rec, exp_pts = scoring.mejor_pronostico(matrix.tolist(), "grupos")

        estado = match_estado(m, res, now)
        real = res.get(result_key(m))
        pts_obtenidos = None
        if real is not None:
            pts_obtenidos = scoring.puntos(tuple(rec), (real["home"], real["away"]), "grupos")
            total_pts += pts_obtenidos
            finalizados += 1
            if (rec[0], rec[1]) == (real["home"], real["away"]):
                aciertos_exactos += 1
            if scoring._signo(*rec) == scoring._signo(real["home"], real["away"]):
                aciertos_resultado += 1

        out_matches.append(
            {
                "id": m["id"],
                "jornada": m["jornada"],
                "grupo": m["grupo"],
                "fecha_utc": m["fecha_utc"],
                "sede": m["sede"],
                "equipo_local": m["equipo_local"],
                "equipo_visitante": m["equipo_visitante"],
                "bandera_local": FLAG_CODES.get(home, ""),
                "bandera_visitante": FLAG_CODES.get(away, ""),
                "elo_local": round(state.ratings[home]),
                "elo_visitante": round(state.ratings[away]),
                "lambdas": [round(lh, 3), round(la, 3)],
                "prob_1x2": {
                    "local": round(ph, 4),
                    "empate": round(pdr, 4),
                    "visitante": round(pa, 4),
                },
                "marcador_recomendado": list(rec),
                "marcador_mas_probable": list(mas_prob),
                "puntos_esperados": round(exp_pts, 3),
                "estado": estado,
                "marcador_real": [real["home"], real["away"]] if real else None,
                "puntos_obtenidos": pts_obtenidos,
            }
        )

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "predictions.json").write_text(
        json.dumps(out_matches, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    standings = build_standings(seed, res)
    (OUT / "standings.json").write_text(
        json.dumps(standings, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # "firma" del contenido relevante: si no cambió nada (mismos estados,
    # resultados, puntos y recomendaciones) reutilizamos el timestamp anterior
    # para que meta.json quede idéntico y NO se genere un commit/redeploy inútil.
    firma_src = [(m["id"], m["estado"], m["marcador_real"], m["puntos_obtenidos"],
                  m["marcador_recomendado"]) for m in out_matches]
    firma = hashlib.sha1(json.dumps(firma_src, sort_keys=True).encode()).hexdigest()

    prev_meta = {}
    prev = OUT / "meta.json"
    if prev.exists():
        try:
            prev_meta = json.loads(prev.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            prev_meta = {}  # meta.json corrupto (p.ej. conflicto git): se regenera

    actualizado = now.isoformat().replace("+00:00", "Z")
    if prev_meta.get("firma") == firma and "actualizado" in prev_meta:
        actualizado = prev_meta["actualizado"]  # nada cambió: conserva el sello

    meta = {
        "actualizado": actualizado,
        "firma": firma,
        "partidos_finalizados": finalizados,
        "puntos_acumulados": total_pts,
        "aciertos_marcador_exacto": aciertos_exactos,
        "aciertos_resultado": aciertos_resultado,
        "modelo": {"rho": rho, "blend_w": blend_w},
    }
    if backtest_report:
        meta["backtest"] = backtest_report
    elif "backtest" in prev_meta:
        meta["backtest"] = prev_meta["backtest"]
    (OUT / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return out_matches, meta


def build_standings(seed, res):
    groups = {}
    for m in seed:
        g = groups.setdefault(m["grupo"], {})
        for t_en, t_es in [(m["local_en"], m["equipo_local"]), (m["visitante_en"], m["equipo_visitante"])]:
            g.setdefault(
                t_en,
                {
                    "equipo": t_es,
                    "bandera": FLAG_CODES.get(t_en, ""),
                    "pj": 0,
                    "g": 0,
                    "e": 0,
                    "p": 0,
                    "gf": 0,
                    "gc": 0,
                    "pts": 0,
                },
            )
        r = res.get(result_key(m))
        if not r:
            continue
        hs, as_ = r["home"], r["away"]
        th, ta = g[m["local_en"]], g[m["visitante_en"]]
        th["pj"] += 1
        ta["pj"] += 1
        th["gf"] += hs
        th["gc"] += as_
        ta["gf"] += as_
        ta["gc"] += hs
        if hs > as_:
            th["g"] += 1
            ta["p"] += 1
            th["pts"] += 3
        elif hs < as_:
            ta["g"] += 1
            th["p"] += 1
            ta["pts"] += 3
        else:
            th["e"] += 1
            ta["e"] += 1
            th["pts"] += 1
            ta["pts"] += 1
    return {
        g: sorted(
            t.values(),
            key=lambda x: (-x["pts"], -(x["gf"] - x["gc"]), -x["gf"], x["equipo"]),
        )
        for g, t in sorted(groups.items())
    }


if __name__ == "__main__":
    matches, meta = predict_all()
    print(json.dumps(meta, ensure_ascii=False, indent=2))
