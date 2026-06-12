# -*- coding: utf-8 -*-
"""Construye data/matches_seed.json (los 72 partidos de fase de grupos)
a partir del worldcup.json de openfootball, con nombres en español."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config.teams import canon, TEAMS_EN_ES, host_country

DATA = Path(__file__).parent / "data"
RAW = DATA / "worldcup2026_raw.json"
SEED = DATA / "matches_seed.json"


def parse_utc(date_str: str, time_str: str) -> str:
    """'2026-06-11' + '13:00 UTC-6' -> ISO UTC."""
    m = re.match(r"(\d{1,2}):(\d{2})\s*UTC([+-]\d{1,2})(?::(\d{2}))?", time_str)
    hh, mm = int(m.group(1)), int(m.group(2))
    off_h = int(m.group(3))
    off_m = int(m.group(4) or 0)
    local = datetime.fromisoformat(date_str).replace(hour=hh, minute=mm)
    utc = local - timedelta(hours=off_h, minutes=off_m if off_h >= 0 else -off_m)
    return utc.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def build():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    group_matches = [m for m in raw["matches"] if "group" in m]
    assert len(group_matches) == 72, f"esperaba 72, hay {len(group_matches)}"

    for m in group_matches:
        m["_utc"] = parse_utc(m["date"], m["time"])

    # Jornada: dentro de cada grupo, en orden cronológico, 2 partidos por jornada
    by_group = {}
    for m in group_matches:
        by_group.setdefault(m["group"], []).append(m)
    for g, ms in by_group.items():
        ms.sort(key=lambda m: m["_utc"])
        for i, m in enumerate(ms):
            m["_jornada"] = i // 2 + 1

    group_matches.sort(key=lambda m: (m["_utc"], m["group"]))
    seed = []
    for i, m in enumerate(group_matches, start=1):
        home = canon(m["team1"])
        away = canon(m["team2"])
        ground = m["ground"]
        host = host_country(ground)
        seed.append({
            "id": i,
            "jornada": m["_jornada"],
            "grupo": m["group"].replace("Group ", ""),
            "fecha_utc": m["_utc"],
            "fecha": m["date"],
            "hora_local": m["time"],
            "sede": ground,
            "equipo_local": TEAMS_EN_ES[home],
            "equipo_visitante": TEAMS_EN_ES[away],
            "local_en": home,
            "visitante_en": away,
            # localía real solo si el equipo juega en su propio país
            "localia": "local" if home == host else ("visitante" if away == host else "neutral"),
        })
    SEED.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"matches_seed.json: {len(seed)} partidos")
    return seed


if __name__ == "__main__":
    build()
