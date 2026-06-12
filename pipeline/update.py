# -*- coding: utf-8 -*-
"""Actualización en vivo: baja el JSON del Mundial 2026 (openfootball),
detecta partidos finalizados, actualiza Elo y re-pronostica los pendientes.

Uso:  python -m pipeline.update [--refresh-history]
"""
import argparse
import json
import warnings
from pathlib import Path

import requests

DATA = Path(__file__).parent / "data"
RESULTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
WC2026_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
RESULTS_2026 = DATA / "results_2026.json"


def download(url: str, dest: Path) -> bytes:
    """GET con reintento sin verificación TLS (proxys corporativos)."""
    try:
        r = requests.get(url, timeout=60)
    except requests.exceptions.SSLError:
        warnings.warn(f"SSL no verificable para {url}; reintentando sin verificar")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = requests.get(url, timeout=60, verify=False)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return r.content


def refresh_results_2026() -> int:
    """Trae resultados finalizados (ESPN en vivo, respaldo openfootball) y los
    fusiona con los ya guardados. Devuelve cuántos resultados nuevos aparecieron."""
    from .sources import fetch_results

    res = {}
    if RESULTS_2026.exists():
        res = json.loads(RESULTS_2026.read_text(encoding="utf-8"))
    nuevos = 0
    for key, score in fetch_results().items():
        if key not in res:
            nuevos += 1
        res[key] = score
    RESULTS_2026.write_text(json.dumps(res, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    print(f"Resultados 2026: {len(res)} finalizados ({nuevos} nuevos)")
    return nuevos


def ensure_history():
    """results.csv no se versiona (gitignore); en un checkout fresco (p.ej. el
    GitHub Action incremental) hay que descargarlo antes de pronosticar."""
    csv = DATA / "results.csv"
    if not csv.exists():
        print("results.csv ausente; descargando histórico...")
        download(RESULTS_URL, csv)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh-history", action="store_true",
                    help="re-descarga results.csv (histórico completo)")
    args = ap.parse_args()

    if args.refresh_history:
        download(RESULTS_URL, DATA / "results.csv")
        print("results.csv actualizado")
    else:
        ensure_history()

    refresh_results_2026()

    from .predict import predict_all
    matches, meta = predict_all()
    print(f"Pronósticos regenerados. Puntos acumulados: {meta['puntos_acumulados']}, "
          f"finalizados: {meta['partidos_finalizados']}")


if __name__ == "__main__":
    main()
