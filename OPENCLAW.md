# Operar la polla con OpenClaw

[OpenClaw](https://openclaw.ai/) es un asistente de IA que corre **en tu PC** y al
que le hablas por Telegram/WhatsApp. Puede ejecutar comandos y llamar APIs, así
que puede manejar esta polla por ti. Como OpenClaw ya es tu interfaz de chat +
ejecutor, **no necesitas el bot de `bot/`** si usas OpenClaw (ese bot es la
alternativa para correr en la nube 24/7 sin tu PC).

> ⚠️ OpenClaw corre en tu máquina: para que responda, tu PC debe estar encendida.

Hay dos formas. La **nube** es la recomendada (el cálculo pesado lo hace GitHub,
tu PC solo manda la señal).

---

## Modo NUBE (recomendado) — disparar el robot de GitHub

Cuando le digas a OpenClaw algo como *"actualiza la polla"*, que ejecute:

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $GH_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/jagsodo/polla-mundial-2026/actions/workflows/update.yml/dispatches \
  -d '{"ref":"main"}'
```

- Esto corre el pipeline en la nube (ESPN → recalcula → push → Vercel se actualiza).
- `GH_TOKEN` debe tener permiso **Actions: write**.
- Para re-entrenar el modelo: cambia el cuerpo a `'{"ref":"main","inputs":{"retrain":"true"}}'`.

**Ver cómo voy** (puntos, última actualización):
```bash
curl -s "https://raw.githubusercontent.com/jagsodo/polla-mundial-2026/main/frontend/public/data/meta.json?t=$RANDOM"
```

---

## Modo LOCAL — correr el pipeline en tu PC

Si prefieres que OpenClaw lo haga todo localmente (requiere el repo y el venv ya
instalados, que están en esta carpeta):

```bash
cd "C:/Users/javie/Documents/analizador inteligente polla mundial/polla-mundial-2026"
.venv/Scripts/python -m pipeline.update      # baja resultados de ESPN y recalcula
git add frontend/public/data pipeline/data/results_2026.json
git commit -m "data: actualización manual"
git push
```
(El `git push` necesita credenciales guardadas; en modo nube no hace falta.)

---

## Cargar un resultado a mano (si ESPN se atrasara)

Edita `pipeline/data/results_2026.json` añadiendo la clave
`"FECHA|LocalEN|VisitanteEN": {"home": X, "away": Y}` (nombres en inglés del
dataset, ver `pipeline/data/matches_seed.json`) y luego corre el update. Ejemplo:

```json
{ "2026-06-11|Mexico|South Africa": { "home": 2, "away": 0 } }
```

## Frases que le puedes decir a OpenClaw
- "Actualiza la polla y dime cuántos puntos llevo."
- "¿Cuáles son mis próximos partidos y qué marcador me recomienda?"
- "Re-entrena el modelo de la polla."
- "Carga el resultado Brasil 2-1 Marruecos en la polla."
