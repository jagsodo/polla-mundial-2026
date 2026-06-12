# -*- coding: utf-8 -*-
"""Construccion de features para el modelo de goles.

Una pasada cronologica sobre el historico mantiene el estado (Elo + forma
reciente) y emite, por partido, las features previas al pitazo inicial
(sin fuga de informacion futura).
"""
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd

from . import elo
from .config.teams import confed_code

DATA = Path(__file__).parent / "data"
RESULTS_CSV = DATA / "results.csv"

FORM_N = 8
MIN_HISTORY = 10


def load_history() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_CSV)
    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    df["date"] = pd.to_datetime(df["date"])
    df["neutral"] = df["neutral"].astype(bool)
    return df.sort_values("date").reset_index(drop=True)


class State:
    """Elo + forma reciente de todas las selecciones."""

    def __init__(self):
        self.ratings = elo.new_ratings()
        self.form = defaultdict(lambda: deque(maxlen=FORM_N))
        self.played = defaultdict(int)

    def advance(
        self,
        home,
        away,
        hs,
        as_,
        tournament,
        neutral,
        country=None,
        host_team=None,
    ):
        elo.update_pair(
            self.ratings,
            home,
            away,
            hs,
            as_,
            tournament,
            neutral,
            country=country,
            host_team=host_team,
        )
        ph = 3 if hs > as_ else (1 if hs == as_ else 0)
        self.form[home].append((ph, hs, as_))
        self.form[away].append((3 - ph if ph != 1 else 1, as_, hs))
        self.played[home] += 1
        self.played[away] += 1

    def _form_stats(self, team):
        f = self.form[team]
        if not f:
            return 1.0, 1.3, 1.3
        pts = np.mean([x[0] for x in f])
        gf = np.mean([x[1] for x in f])
        ga = np.mean([x[2] for x in f])
        return pts, gf, ga

    def perspective(self, team, opp, team_home, opp_home, tournament):
        r_t = self.ratings[team]
        r_o = self.ratings[opp]
        adj = elo.HOME_ADV * (1 if team_home else 0) - elo.HOME_ADV * (1 if opp_home else 0)
        pts_t, gf_t, ga_t = self._form_stats(team)
        pts_o, gf_o, ga_o = self._form_stats(opp)
        return {
            "elo_own": r_t,
            "elo_opp": r_o,
            "elo_diff_adj": r_t - r_o + adj,
            "is_home": int(team_home),
            "opp_is_home": int(opp_home),
            "form_pts_own": pts_t,
            "form_gf_own": gf_t,
            "form_ga_own": ga_t,
            "form_pts_opp": pts_o,
            "form_gf_opp": gf_o,
            "form_ga_opp": ga_o,
            "confed_own": confed_code(team),
            "confed_opp": confed_code(opp),
            "importance": elo.k_factor(tournament),
        }

    def match_rows(self, home, away, neutral, tournament, country=None):
        h_home = bool(elo._home_advantage(home, away, neutral, country=country) > 0)
        return (
            self.perspective(home, away, h_home, False, tournament),
            self.perspective(away, home, False, h_home, tournament),
        )


FEATURE_COLS = [
    "elo_own",
    "elo_opp",
    "elo_diff_adj",
    "is_home",
    "opp_is_home",
    "form_pts_own",
    "form_gf_own",
    "form_ga_own",
    "form_pts_opp",
    "form_gf_opp",
    "form_ga_opp",
    "confed_own",
    "confed_opp",
    "importance",
]


def build_training_table(df: pd.DataFrame, min_year: int = 1980):
    """Recorre el historico y devuelve (tabla_perspectiva, estado_final)."""
    state = State()
    rows = []
    for r in df.itertuples(index=False):
        usable = (
            r.date.year >= min_year
            and state.played[r.home_team] >= MIN_HISTORY
            and state.played[r.away_team] >= MIN_HISTORY
        )
        if usable:
            fh, fa = state.match_rows(
                r.home_team,
                r.away_team,
                r.neutral,
                r.tournament,
                country=r.country,
            )
            base = {
                "date": r.date,
                "tournament": r.tournament,
                "home_team": r.home_team,
                "away_team": r.away_team,
                "home_score": r.home_score,
                "away_score": r.away_score,
            }
            rows.append({**base, **fh, "goals": r.home_score, "side": "H"})
            rows.append({**base, **fa, "goals": r.away_score, "side": "A"})
        state.advance(
            r.home_team,
            r.away_team,
            r.home_score,
            r.away_score,
            r.tournament,
            r.neutral,
            country=r.country,
        )
    return pd.DataFrame(rows), state
