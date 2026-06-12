# -*- coding: utf-8 -*-
"""World Football Elo calculado desde results.csv.

- K segun importancia del torneo (Mundial > continentales > clasificatorias
  > otros torneos > amistosos).
- Ajuste por diferencia de goles (factor G).
- Ventaja de localia: +100 solo para Mexico, Canada y United States cuando
  juegan realmente en casa. En sede neutral no hay bonus.
"""
from collections import defaultdict

HOME_ADV = 100.0
START_RATING = 1500.0
HOST_TEAMS = {"Mexico", "Canada", "United States"}
HOME_COUNTRY_ALIASES = {
    "Mexico": {"Mexico"},
    "Canada": {"Canada"},
    "United States": {"United States", "USA", "United States of America"},
}

_K_RULES = [
    ("FIFA World Cup qualification", 40),
    ("FIFA World Cup", 60),
    ("Confederations Cup", 50),
    ("UEFA Euro qualification", 40),
    ("UEFA Euro", 50),
    ("Copa America", 50),
    ("Copa América", 50),
    ("African Cup of Nations qualification", 40),
    ("African Cup of Nations", 50),
    ("AFC Asian Cup qualification", 40),
    ("AFC Asian Cup", 50),
    ("CONCACAF Championship", 50),
    ("Gold Cup", 50),
    ("Oceania Nations Cup", 50),
    ("UEFA Nations League", 40),
    ("CONCACAF Nations League", 40),
    ("Friendly", 20),
]


def k_factor(tournament: str) -> float:
    for key, k in _K_RULES:
        if key in tournament:
            return k
    return 30


def g_factor(goal_diff: int) -> float:
    d = abs(goal_diff)
    if d <= 1:
        return 1.0
    if d == 2:
        return 1.5
    return (11 + d) / 8.0


def _home_advantage(
    home: str,
    away: str,
    neutral: bool,
    country: str | None = None,
    host_team: str | None = None,
) -> float:
    if neutral:
        return 0.0
    if host_team is not None:
        if host_team == home:
            return HOME_ADV
        if host_team == away:
            return -HOME_ADV
        return 0.0
    if country is None or home not in HOST_TEAMS:
        return 0.0
    return HOME_ADV if country in HOME_COUNTRY_ALIASES.get(home, set()) else 0.0


def expected(r_home: float, r_away: float, advantage: float = 0.0) -> float:
    dr = r_home - r_away + advantage
    return 1.0 / (1.0 + 10 ** (-dr / 400.0))


def update_pair(
    ratings: dict,
    home: str,
    away: str,
    hs: int,
    as_: int,
    tournament: str,
    neutral: bool,
    country: str | None = None,
    host_team: str | None = None,
):
    """Actualiza ratings in-place con un partido. Devuelve (elo_h, elo_a) previos."""
    rh = ratings[home]
    ra = ratings[away]
    adv = _home_advantage(home, away, neutral, country=country, host_team=host_team)
    we = expected(rh, ra, adv)
    w = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
    delta = k_factor(tournament) * g_factor(hs - as_) * (w - we)
    ratings[home] = rh + delta
    ratings[away] = ra - delta
    return rh, ra


def new_ratings() -> dict:
    return defaultdict(lambda: START_RATING)


def compute_ratings(df) -> dict:
    """Recorre el historico y devuelve el rating actual de cada seleccion."""
    ratings = new_ratings()
    for row in df.itertuples(index=False):
        update_pair(
            ratings,
            row.home_team,
            row.away_team,
            int(row.home_score),
            int(row.away_score),
            row.tournament,
            bool(row.neutral),
            country=getattr(row, "country", None),
        )
    return ratings
