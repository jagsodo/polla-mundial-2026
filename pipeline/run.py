# -*- coding: utf-8 -*-
"""Pipeline completo: datos -> seed -> entrenamiento (+backtest) -> pronosticos.

Uso: python -m pipeline.run [--skip-backtest]
"""
import argparse
import json
import sys
from pathlib import Path

from . import model as M
from .build_seed import build as build_seed
from .config.teams import TEAMS_ES_EN
from .features import build_training_table, load_history
from .update import RESULTS_URL, WC2026_URL, download

DATA = Path(__file__).parent / "data"
REPORTS = Path(__file__).parent / "reports"
BLEND_W = 0.65


def ensure_data():
    if not (DATA / "results.csv").exists():
        download(RESULTS_URL, DATA / "results.csv")
    if not (DATA / "worldcup2026_raw.json").exists():
        download(WC2026_URL, DATA / "worldcup2026_raw.json")


def validate_teams(df):
    hist = set(df["home_team"]) | set(df["away_team"])
    missing = [en for en in TEAMS_ES_EN.values() if en not in hist]
    if missing:
        sys.exit(f"Equipos sin historico (revisar mapeo): {missing}")
    counts = {
        en: int(((df["home_team"] == en) | (df["away_team"] == en)).sum())
        for en in TEAMS_ES_EN.values()
    }
    print(
        f"Mapeo OK: 48/48 equipos en el historico "
        f"(min. {min(counts, key=counts.get)}={min(counts.values())} partidos)"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-backtest", action="store_true")
    args = ap.parse_args()

    ensure_data()
    build_seed()
    df = load_history()
    print(
        f"Historico: {len(df)} partidos jugados "
        f"({df['date'].min().date()} -> {df['date'].max().date()})"
    )
    validate_teams(df)

    print("Construyendo features...")
    table, _ = build_training_table(df)
    print(f"Tabla de entrenamiento: {len(table)} filas-perspectiva ({len(table)//2} partidos)")

    report = None
    if not args.skip_backtest:
        print("Backtest (WC2018, WC2022, 2023-2025)...")
        report = M.backtest(table, BLEND_W)
        REPORTS.mkdir(exist_ok=True)
        (REPORTS / "backtest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))

    print("Entrenando modelo final con todo el historico...")
    ml = M.train_ml(table)
    bl = M.train_baseline(table)
    h = table[table["side"] == "H"].reset_index(drop=True)
    a = table[table["side"] == "A"].reset_index(drop=True)
    tail = h.index[-3000:]
    lam_h = M.predict_lambdas(ml, bl, h.loc[tail], BLEND_W)
    lam_a = M.predict_lambdas(ml, bl, a.loc[tail], BLEND_W)
    rho = M.fit_rho(lam_h, lam_a, h.loc[tail, "goals"].to_numpy(), a.loc[tail, "goals"].to_numpy())
    print(f"rho (Dixon-Coles) = {rho:.3f}")
    M.save_artifacts(ml, bl, rho, BLEND_W)

    from .predict import predict_all

    bt = None
    if report:
        bt = {
            k: {
                "accuracy_1x2": v["blend"]["accuracy_1x2"],
                "log_loss": v["blend"]["log_loss"],
                "rps": v["blend"]["rps"],
                "n": v["blend"]["n"],
            }
            for k, v in report.items()
        }
    matches, _meta = predict_all(backtest_report=bt)
    print(f"predictions.json: {len(matches)} partidos -> frontend/public/data/")


if __name__ == "__main__":
    main()
