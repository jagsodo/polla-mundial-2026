# Bot de Telegram — Polla Mundial 2026

Control por Telegram. Usa **long-polling** (no necesita URL pública ni webhook),
así que corre igual en **clawbot/ClawCloud**, un VPS, Railway, Render, o tu PC.
El bot solo **dispara el GitHub Action** (que corre en la nube) y **lee los JSON**
publicados; no hace cálculo pesado.

## Comandos
- `/actualizar` — dispara el robot (ESPN → recalcula → push → Vercel)
- `/estado` — puntos acumulados, finalizados y última actualización
- `/pendientes` — próximos partidos con el marcador recomendado
- `/cargar Mexico 2-0 South Africa` — carga un resultado a mano (si ESPN se atrasa)
- `/help`

## 1. Crear el bot en Telegram
1. En Telegram habla con **@BotFather** → `/newbot` → elige nombre y usuario.
2. Te da un **token** tipo `1234567:ABC...` → ese es `TELEGRAM_BOT_TOKEN`.
3. Escríbele algo a tu bot y abre
   `https://api.telegram.org/bot<TOKEN>/getUpdates` para ver tu **chat id**
   (campo `chat.id`). Ese número va en `ALLOWED_CHAT_IDS` (solo tú podrás darle órdenes).

## 2. Token de GitHub para el bot
El bot dispara el Action y (para `/cargar`) escribe un archivo. Necesita un token con:
- **Actions**: Read and write  (para `/actualizar`)
- **Contents**: Read and write (para `/cargar`)
Puede ser el mismo fine-grained de antes, añadiéndole esos permisos, o uno nuevo.

## 3. Variables de entorno
```
TELEGRAM_BOT_TOKEN=1234567:ABC...
GH_TOKEN=github_pat_...        # con Actions:write (+ Contents:write para /cargar)
GH_REPO=jagsodo/polla-mundial-2026
ALLOWED_CHAT_IDS=123456789     # tu chat id (coma para varios)
SITE_URL=https://polla-mundial-2026.vercel.app   # opcional
```

## 4. Correr

**Local / VPS:**
```bash
cd bot
pip install -r requirements.txt
# exporta las variables de entorno y luego:
python telegram_bot.py
```

**Docker / clawbot / ClawCloud (recomendado, 24/7 sin tu PC):**
```bash
docker build -t polla-bot ./bot
docker run -d --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN=... -e GH_TOKEN=... \
  -e GH_REPO=jagsodo/polla-mundial-2026 \
  -e ALLOWED_CHAT_IDS=... -e SITE_URL=... \
  polla-bot
```
En clawbot/ClawCloud: crea una app desde este `Dockerfile` (o el repo) y pon las
mismas variables de entorno en su panel. No expongas puerto: el bot solo hace
salidas (long-polling), no recibe tráfico entrante.

## Notas
- Los secretos van **solo** como variables de entorno, nunca en el código ni en git.
- Si no defines `ALLOWED_CHAT_IDS`, el bot responde a cualquiera (no recomendado).
- El bot es complementario: puedes dejar además el cron del Action, o quitarlo y
  actualizar solo bajo demanda con `/actualizar`.
