# -*- coding: utf-8 -*-
"""Watcher local: corre update.py en bucle y hace commit+push si los JSON
cambian. Alternativa al GitHub Action cuando la maquina esta encendida.

Uso:  python -m pipeline.watch [--minutes 30]
"""
import argparse
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
WATCHED = ["frontend/public/data", "pipeline/data/results_2026.json"]


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=30)
    ap.add_argument("--retrain-hour-utc", type=int, default=6)
    args = ap.parse_args()
    last_retrain_day = None

    while True:
        print(f"[{datetime.now():%H:%M:%S}] actualizando...")
        try:
            now_utc = datetime.now(timezone.utc)
            should_retrain = now_utc.hour >= args.retrain_hour_utc and last_retrain_day != now_utc.date()
            if should_retrain:
                subprocess.run(["python", "-m", "pipeline.update", "--refresh-history"], cwd=ROOT, check=True)
                subprocess.run(["python", "-m", "pipeline.run"], cwd=ROOT, check=True)
                last_retrain_day = now_utc.date()
            else:
                subprocess.run(["python", "-m", "pipeline.update"], cwd=ROOT, check=True)

            if git("status", "--porcelain", "--", *WATCHED):
                git("add", *WATCHED)
                git("commit", "-m", f"data: actualizacion automatica {datetime.now():%Y-%m-%d %H:%M}")
                git("push")
                print("Cambios publicados.")
            else:
                print("Sin cambios.")
        except Exception as e:  # noqa: BLE001
            print(f"Error en el ciclo: {e}")
        time.sleep(args.minutes * 60)


if __name__ == "__main__":
    main()
