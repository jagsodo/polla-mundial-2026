# -*- coding: utf-8 -*-
"""Fuentes de resultados del Mundial 2026.

Primaria: ESPN (API pública oculta, en vivo, sin API key).
Respaldo: openfootball (lento, ~1 día) y TheSportsDB.

Todas devuelven el mismo formato: dict[result_key] = {"home": int, "away": int}
donde result_key = "YYYY-MM-DD|LocalCanon|VisitanteCanon" (igual que el seed).
Solo se reportan partidos FINALIZADOS, con el marcador de los 90' reglamentarios
(en fase de grupos no hay prórroga, así que el marcador final = 90').
"""
import json
import warnings
from pathlib import Path

import requests

from .config.teams import canon

DATA = Path(__file__).parent / "data"
SEED = DATA / "matches_seed.json"
H = {"User-Agent": "Mozilla/5.0"}

ESPN_URL = ("https://site.api.espn.com/apis/site/v2/sports/soccer/"
            "fifa.world/scoreboard?dates={start}-{end}&limit=300")
WC2026_URL = ("https://raw.githubusercontent.com/openfootball/worldcup.json/"
              "master/2026/worldcup.json")


def _get(url: str) -> dict:
    """GET con fallback a TLS sin verificar (proxys corporativos)."""
    try:
        r = requests.get(url, timeout=60, headers=H)
    except requests.exceptions.SSLError:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = requests.get(url, timeout=60, headers=H, verify=False)
    r.raise_for_status()
    return r.json()


def _seed_date_range():
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    fechas = sorted(m["fecha"] for m in seed)
    return fechas[0].replace("-", ""), fechas[-1].replace("-", "")


def from_espn() -> dict:
    """Resultados en vivo desde ESPN. Vacío si falla (para caer al respaldo)."""
    start, end = _seed_date_range()
    data = _get(ESPN_URL.format(start=start, end=end))
    res = {}
    for ev in data.get("events", []):
        comp = ev["competitions"][0]
        if ev["status"]["type"]["state"] != "post":
            continue  # solo finalizados
        home = away = None
        for c in comp["competitors"]:
            name = canon(c["team"]["displayName"])
            score = int(c["score"]) if c.get("score") not in (None, "") else None
            if c["homeAway"] == "home":
                home, hs = name, score
            else:
                away, as_ = name, score
        if home is None or away is None or hs is None or as_ is None:
            continue
        date = ev["date"][:10]  # ISO -> YYYY-MM-DD (UTC)
        res[f"{date}|{home}|{away}"] = {"home": hs, "away": as_}
    return res


def from_openfootball() -> dict:
    """Respaldo: openfootball (lento)."""
    raw = _get(WC2026_URL)
    res = {}
    for m in raw.get("matches", []):
        if "group" not in m:
            continue
        sc = _of_score(m)
        if sc is None:
            continue
        res[f"{m['date']}|{canon(m['team1'])}|{canon(m['team2'])}"] = {
            "home": sc[0], "away": sc[1]}
    return res


def _of_score(m: dict):
    if m.get("score1") is not None and m.get("score2") is not None:
        return int(m["score1"]), int(m["score2"])
    sc = m.get("score")
    if isinstance(sc, dict) and sc.get("ft"):
        return int(sc["ft"][0]), int(sc["ft"][1])
    return None


# Las fechas ESPN vienen en UTC; un partido nocturno puede caer al día
# siguiente en UTC respecto a la fecha local del seed. Reconciliamos por
# equipos (ignorando la fecha) contra el seed para asegurar el match de claves.
def reconcile_with_seed(raw_results: dict) -> dict:
    """Reescribe las claves al formato exacto del seed, emparejando por equipos."""
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    by_teams = {}
    for m in seed:
        by_teams[(m["local_en"], m["visitante_en"])] = m
    out = {}
    for key, score in raw_results.items():
        _, home, away = key.split("|")
        m = by_teams.get((home, away))
        if m is None:
            continue  # partido que no es de la fase de grupos del seed
        out[f"{m['fecha']}|{m['local_en']}|{m['visitante_en']}"] = score
    return out


def fetch_results(verbose: bool = True) -> dict:
    """Intenta ESPN; si no devuelve nada o falla, cae a openfootball.
    Devuelve resultados con claves reconciliadas al seed."""
    for name, fn in (("ESPN", from_espn), ("openfootball", from_openfootball)):
        try:
            raw = fn()
            reconciled = reconcile_with_seed(raw)
            if reconciled:
                if verbose:
                    print(f"Fuente: {name} -> {len(reconciled)} partidos finalizados")
                return reconciled
            if verbose:
                print(f"Fuente {name}: 0 finalizados, probando siguiente...")
        except Exception as e:  # noqa: BLE001
            if verbose:
                print(f"Fuente {name} falló: {e}")
    if verbose:
        print("Sin resultados de ninguna fuente.")
    return {}
