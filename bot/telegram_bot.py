# -*- coding: utf-8 -*-
"""Bot de Telegram para la polla Mundial 2026.

Control por chat, sin servidor web (usa long-polling: corre en cualquier lado
con Python, p.ej. clawbot/ClawCloud, un VPS o tu PC). El trabajo pesado lo hace
el GitHub Action en la nube; este bot solo lo dispara y lee los JSON publicados.

Comandos:
  /actualizar     -> dispara el robot (ESPN -> recalcula -> push -> Vercel)
  /estado         -> puntos acumulados, finalizados y última actualización
  /pendientes     -> próximos partidos con el marcador recomendado
  /cargar A x-y B -> carga un resultado a mano (si ESPN se atrasa) y actualiza
  /help

Configuración por variables de entorno (NO hardcodear secretos):
  TELEGRAM_BOT_TOKEN   token de @BotFather
  GH_TOKEN             token de GitHub con Actions:write (+ Contents:write para /cargar)
  GH_REPO              "jagsodo/polla-mundial-2026"
  ALLOWED_CHAT_IDS     ids separados por coma (solo estos pueden dar órdenes)
  SITE_URL             (opcional) URL pública de Vercel para incluir en respuestas
"""
import base64
import json
import os
import time
import warnings

import requests

warnings.simplefilter("ignore")

TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GH_TOKEN = os.environ["GH_TOKEN"]
GH_REPO = os.environ.get("GH_REPO", "jagsodo/polla-mundial-2026")
ALLOWED = {c.strip() for c in os.environ.get("ALLOWED_CHAT_IDS", "").split(",") if c.strip()}
SITE_URL = os.environ.get("SITE_URL", "")

TG = f"https://api.telegram.org/bot{TG_TOKEN}"
GH = f"https://api.github.com/repos/{GH_REPO}"
GH_HDR = {"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"}
RAW = f"https://raw.githubusercontent.com/{GH_REPO}/main"


# ----------------------------------------------------------------- Telegram
def send(chat_id, text):
    requests.post(f"{TG}/sendMessage",
                  json={"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                        "disable_web_page_preview": True},
                  timeout=30, verify=False)


def authorized(chat_id) -> bool:
    return not ALLOWED or str(chat_id) in ALLOWED


# ------------------------------------------------------------------- GitHub
def trigger_action() -> bool:
    r = requests.post(f"{GH}/actions/workflows/update.yml/dispatches",
                      headers=GH_HDR, json={"ref": "main"}, timeout=30, verify=False)
    return r.status_code == 204


def gh_json(path: str):
    """Lee un JSON publicado (raw, con cache-busting)."""
    r = requests.get(f"{RAW}/{path}?t={int(time.time())}", timeout=30, verify=False)
    r.raise_for_status()
    return r.json()


# --------------------------------------------------------------- comandos
def cmd_estado(chat_id):
    try:
        m = gh_json("frontend/public/data/meta.json")
    except Exception:
        send(chat_id, "No pude leer el estado todavía.")
        return
    txt = (f"📊 <b>Estado de la polla</b>\n"
           f"Puntos acumulados: <b>{m['puntos_acumulados']}</b>\n"
           f"Partidos finalizados: {m['partidos_finalizados']}\n"
           f"Marcadores exactos: {m['aciertos_marcador_exacto']}\n"
           f"Resultados 1X2: {m['aciertos_resultado']}\n"
           f"Última actualización: {m['actualizado'][:16].replace('T', ' ')} UTC")
    if SITE_URL:
        txt += f"\n🌐 {SITE_URL}"
    send(chat_id, txt)


def cmd_pendientes(chat_id):
    try:
        ms = gh_json("frontend/public/data/predictions.json")
    except Exception:
        send(chat_id, "No pude leer los pronósticos.")
        return
    prox = [m for m in ms if m["estado"] == "proximo"][:12]
    if not prox:
        send(chat_id, "No hay partidos próximos.")
        return
    lines = ["🔮 <b>Próximos (marcador recomendado)</b>"]
    for m in prox:
        r = m["marcador_recomendado"]
        lines.append(f"J{m['jornada']} {m['equipo_local']} <b>{r[0]}-{r[1]}</b> {m['equipo_visitante']}")
    send(chat_id, "\n".join(lines))


def cmd_actualizar(chat_id):
    if trigger_action():
        send(chat_id, "🤖 Robot disparado. En ~1-2 min reviso ESPN, recalculo y "
                      "actualizo la web. Te aviso con /estado cuando quieras.")
    else:
        send(chat_id, "⚠️ No pude disparar el robot (revisa que GH_TOKEN tenga "
                      "permiso Actions: write).")


def cmd_cargar(chat_id, args):
    """/cargar Mexico 2-0 South Africa  (nombres en inglés del dataset)."""
    try:
        # admite "Equipo1 2-0 Equipo2"
        joined = " ".join(args)
        left, score, right = None, None, None
        for tok in args:
            if "-" in tok and tok.replace("-", "").isdigit():
                score = tok
                idx = args.index(tok)
                left = " ".join(args[:idx])
                right = " ".join(args[idx + 1:])
                break
        if not (left and right and score):
            raise ValueError
        hs, as_ = (int(x) for x in score.split("-"))
    except Exception:
        send(chat_id, "Formato: <code>/cargar Mexico 2-0 South Africa</code>\n"
                      "(usa los nombres en inglés que ves en la web)")
        return

    # localizar el partido en el seed para construir la clave exacta
    try:
        seed = gh_json("pipeline/data/matches_seed.json")
    except Exception:
        send(chat_id, "No pude leer el calendario.")
        return
    match = next((m for m in seed
                  if left.lower() in (m["local_en"].lower(), m["equipo_local"].lower())
                  and right.lower() in (m["visitante_en"].lower(), m["equipo_visitante"].lower())),
                 None)
    if not match:
        send(chat_id, f"No encontré el partido {left} vs {right}. Revisa los nombres.")
        return
    key = f"{match['fecha']}|{match['local_en']}|{match['visitante_en']}"

    # leer results_2026.json actual (con su sha) y reescribirlo vía Contents API
    cur = requests.get(f"{GH}/contents/pipeline/data/results_2026.json",
                       headers=GH_HDR, timeout=30, verify=False).json()
    data = json.loads(base64.b64decode(cur["content"]).decode("utf-8"))
    data[key] = {"home": hs, "away": as_}
    new_content = base64.b64encode(
        json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8")).decode()
    put = requests.put(f"{GH}/contents/pipeline/data/results_2026.json",
                       headers=GH_HDR,
                       json={"message": f"data: carga manual {key} {hs}-{as_}",
                             "content": new_content, "sha": cur["sha"]},
                       timeout=30, verify=False)
    if put.status_code not in (200, 201):
        send(chat_id, f"No pude guardar el resultado: {put.json().get('message')}")
        return
    send(chat_id, f"✅ Cargado {match['equipo_local']} {hs}-{as_} {match['equipo_visitante']}. "
                  "Disparando recálculo...")
    trigger_action()


HELP = ("⚽ <b>Polla Mundial 2026</b>\n"
        "/actualizar — buscar resultados y recalcular\n"
        "/estado — puntos y última actualización\n"
        "/pendientes — próximos con marcador recomendado\n"
        "/cargar Mexico 2-0 South Africa — cargar resultado a mano")


def handle(update):
    msg = update.get("message") or update.get("edited_message")
    if not msg or "text" not in msg:
        return
    chat_id = msg["chat"]["id"]
    if not authorized(chat_id):
        send(chat_id, f"No autorizado. Tu chat id es {chat_id} (pídele al admin que lo agregue).")
        return
    parts = msg["text"].strip().split()
    cmd = parts[0].lower().split("@")[0]
    args = parts[1:]
    if cmd in ("/start", "/help"):
        send(chat_id, HELP)
    elif cmd == "/actualizar":
        cmd_actualizar(chat_id)
    elif cmd == "/estado":
        cmd_estado(chat_id)
    elif cmd == "/pendientes":
        cmd_pendientes(chat_id)
    elif cmd == "/cargar":
        cmd_cargar(chat_id, args)
    else:
        send(chat_id, "No conozco ese comando. /help")


def main():
    print("Bot polla-mundial-2026 iniciado (long-polling).")
    offset = None
    while True:
        try:
            r = requests.get(f"{TG}/getUpdates",
                             params={"timeout": 50, "offset": offset},
                             timeout=60, verify=False).json()
            for upd in r.get("result", []):
                offset = upd["update_id"] + 1
                handle(upd)
        except Exception as e:  # noqa: BLE001 - el bot nunca debe morir
            print("error:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
