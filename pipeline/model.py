# -*- coding: utf-8 -*-
"""Modelo de goles: XGBoost-Poisson + baseline Elo-Poisson, matriz de
marcadores con ajuste Dixon-Coles, blend y backtest."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.linear_model import PoissonRegressor
from xgboost import XGBRegressor

from .features import FEATURE_COLS

MODELS = Path(__file__).parent / "models"
MAX_GOALS = 7


def train_ml(table: pd.DataFrame) -> XGBRegressor:
    m = XGBRegressor(
        objective="count:poisson",
        n_estimators=500,
        learning_rate=0.05,
        max_depth=4,
        min_child_weight=20,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=2.0,
        n_jobs=-1,
        random_state=42,
    )
    m.fit(table[FEATURE_COLS], table["goals"])
    return m


class EloPoissonBaseline:
    """Baseline serializable: goles ~ Poisson(exp(a + b*elo_diff_adj))."""

    def __init__(self, intercept: float, coef: float):
        self.intercept = intercept
        self.coef = coef

    def predict(self, X):
        x = np.asarray(X, dtype=float).ravel()
        return np.exp(self.intercept + self.coef * x)


def train_baseline(table: pd.DataFrame) -> EloPoissonBaseline:
    m = PoissonRegressor(alpha=1e-6, max_iter=300)
    m.fit(table[["elo_diff_adj"]].to_numpy(), table["goals"])
    return EloPoissonBaseline(float(m.intercept_), float(m.coef_[0]))


def predict_lambdas(ml, baseline, rows: pd.DataFrame, blend_w: float):
    lam_ml = np.clip(ml.predict(rows[FEATURE_COLS]), 0.05, 6.0)
    lam_bl = np.clip(baseline.predict(rows[["elo_diff_adj"]]), 0.05, 6.0)
    return blend_w * lam_ml + (1.0 - blend_w) * lam_bl


def dc_tau(h, a, lh, la, rho):
    if h == 0 and a == 0:
        return 1.0 - lh * la * rho
    if h == 0 and a == 1:
        return 1.0 + lh * rho
    if h == 1 and a == 0:
        return 1.0 + la * rho
    if h == 1 and a == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(lh: float, la: float, rho: float = 0.0, max_goals: int = MAX_GOALS) -> np.ndarray:
    gh = poisson.pmf(np.arange(max_goals + 1), lh)
    ga = poisson.pmf(np.arange(max_goals + 1), la)
    m = np.outer(gh, ga)
    for h in (0, 1):
        for a in (0, 1):
            m[h, a] *= max(dc_tau(h, a, lh, la, rho), 1e-9)
    return m / m.sum()


def one_x_two(m: np.ndarray):
    ph = np.tril(m, -1).sum()
    pd_ = np.trace(m)
    pa = np.triu(m, 1).sum()
    return ph, pd_, pa


def fit_rho(lams_h, lams_a, scores_h, scores_a) -> float:
    best_rho, best_ll = 0.0, -np.inf
    for rho in np.arange(-0.16, 0.09, 0.01):
        ll = 0.0
        for lh, la, h, a in zip(lams_h, lams_a, scores_h, scores_a):
            p = poisson.pmf(h, lh) * poisson.pmf(a, la) * dc_tau(h, a, lh, la, rho)
            ll += np.log(max(p, 1e-12))
        if ll > best_ll:
            best_ll, best_rho = ll, float(rho)
    return best_rho


def rps(probs, outcome_idx):
    cum_p = np.cumsum(probs)
    cum_o = np.cumsum(np.eye(3)[outcome_idx])
    return float(np.sum((cum_p - cum_o) ** 2) / 2)


def evaluate(probs_list, outcomes):
    probs = np.clip(np.array(probs_list), 1e-12, 1)
    out = np.array(outcomes)
    acc = float((probs.argmax(axis=1) == out).mean())
    ll = float(-np.mean(np.log(probs[np.arange(len(out)), out])))
    r = float(np.mean([rps(p, o) for p, o in zip(probs, out)]))
    return {
        "accuracy_1x2": round(acc, 4),
        "log_loss": round(ll, 4),
        "rps": round(r, 4),
        "n": len(out),
    }


def outcome_idx(hs, as_):
    return 0 if hs > as_ else (1 if hs == as_ else 2)


def is_friendly_or_qualifier(tournament: str) -> bool:
    t = tournament.lower()
    return t == "friendly" or "qualification" in t


def _match_level(table: pd.DataFrame) -> pd.DataFrame:
    h = table[table["side"] == "H"].reset_index(drop=True)
    a = table[table["side"] == "A"].reset_index(drop=True)
    assert len(h) == len(a)
    return h, a


def backtest(table: pd.DataFrame, blend_w: float = 0.65) -> dict:
    """Backtest: Mundial 2018, Mundial 2022 y amistosos+clasificatorios 2023-2025."""
    h, a = _match_level(table)
    dates = h["date"]
    splits = {
        "WC2018": (
            dates < "2018-06-01",
            (h["tournament"] == "FIFA World Cup") & (dates.dt.year == 2018),
        ),
        "WC2022": (
            dates < "2022-11-01",
            (h["tournament"] == "FIFA World Cup") & (dates.dt.year == 2022),
        ),
        "intl_2023_2025": (
            dates < "2023-01-01",
            (dates >= "2023-01-01")
            & (dates < "2026-01-01")
            & h["tournament"].map(is_friendly_or_qualifier),
        ),
    }
    report = {}
    for name, (train_m, test_m) in splits.items():
        idx_train = h.index[train_m]
        idx_test = h.index[test_m]
        train_rows = pd.concat([h.loc[idx_train], a.loc[idx_train]])
        ml = train_ml(train_rows)
        bl = train_baseline(train_rows)

        tail = idx_train[-3000:]
        lam_h_t = predict_lambdas(ml, bl, h.loc[tail], blend_w)
        lam_a_t = predict_lambdas(ml, bl, a.loc[tail], blend_w)
        rho = fit_rho(
            lam_h_t,
            lam_a_t,
            h.loc[tail, "goals"].to_numpy(),
            a.loc[tail, "goals"].to_numpy(),
        )

        out = [outcome_idx(hs, as_) for hs, as_ in zip(h.loc[idx_test, "goals"], a.loc[idx_test, "goals"])]
        variants = {}
        for vname, w in [("ml", 1.0), ("elo_poisson", 0.0), ("blend", blend_w)]:
            lam_h = predict_lambdas(ml, bl, h.loc[idx_test], w)
            lam_a = predict_lambdas(ml, bl, a.loc[idx_test], w)
            probs = [one_x_two(score_matrix(lh, la, rho)) for lh, la in zip(lam_h, lam_a)]
            variants[vname] = evaluate(probs, out)

        fav = (h.loc[idx_test, "elo_diff_adj"] > 0).map({True: 0, False: 2}).to_numpy()
        variants["favorito_elo"] = {
            "accuracy_1x2": round(float((fav == np.array(out)).mean()), 4),
            "log_loss": None,
            "rps": None,
            "n": len(out),
        }
        report[name] = {"rho": rho, **variants}
    return report


def save_artifacts(ml, bl, rho, blend_w):
    MODELS.mkdir(exist_ok=True)
    ml.save_model(MODELS / "goal_model.json")
    params = {
        "rho": rho,
        "blend_w": blend_w,
        "baseline_intercept": bl.intercept,
        "baseline_coef": bl.coef,
    }
    (MODELS / "params.json").write_text(json.dumps(params, indent=2))


def load_artifacts():
    ml = XGBRegressor()
    ml.load_model(MODELS / "goal_model.json")
    params = json.loads((MODELS / "params.json").read_text())
    bl = EloPoissonBaseline(params["baseline_intercept"], params["baseline_coef"])
    return ml, bl, params
