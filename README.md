# polla-mundial-2026

Sistema de pronósticos para la polla del Mundial 2026: descarga datos
históricos, entrena un modelo estadístico + ML, calcula el marcador que
**maximiza los puntos esperados según las reglas de la polla** para los 72
partidos de fase de grupos, y se actualiza solo a medida que se juegan los
partidos.

## Reglas de puntaje (configurables en `pipeline/config/scoring.py`)

Puntos acumulables por partido: resultado 1X2 **+5**, marcador exacto **+2**,
diferencia de goles **+1** (exacto = 8). Eliminatorias: doble. Solo 90 minutos.

## Arquitectura

```
/pipeline   Python: datos -> Elo -> features -> XGBoost-Poisson -> pronósticos
/frontend   Next.js 14 + Tailwind: solo LEE /frontend/public/data/*.json
```

- `predictions.json` — los 72 pronósticos (marcador recomendado, prob. 1X2, estado, puntos)
- `standings.json` — tablas de grupo con resultados reales
- `meta.json` — última actualización + métricas del backtest

Fuentes (todas gratuitas, sin API key):
- **Histórico de entrenamiento**: [martj42/international_results](https://github.com/martj42/international_results) (~49k partidos desde 1872).
- **Fixture 2026**: [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json).
- **Resultados en vivo**: API pública de **ESPN** (`site.api.espn.com`, en vivo, sin
  retraso) como fuente primaria, con openfootball de respaldo. Lógica en
  [`pipeline/sources.py`](pipeline/sources.py); el marcador es el de los 90'
  reglamentarios (en fase de grupos no hay prórroga).

## Modelo

1. **Elo** (World Football Elo: K por importancia, factor G por goleada, +100 localía
   real — solo México/USA/Canadá en casa).
2. **Features**: Elo previo, localía, forma reciente (últimos 8), confederación, importancia.
3. **XGBoost Poisson** (goles esperados por equipo) mezclado con baseline Elo→Poisson.
4. **Matriz de marcadores** Poisson con corrección **Dixon-Coles** (marcadores bajos).
5. **Optimizador**: elige el marcador con mayor `E[puntos]` según las reglas de la polla.
6. **Backtest** sobre Mundiales 2018/2022 e internacionales 2023-2025
   (accuracy 1X2, log-loss, RPS vs "siempre el favorito Elo") → `pipeline/reports/`.

## Correr el pipeline local

```powershell
cd polla-mundial-2026
python -m venv .venv
.venv\Scripts\pip install -r pipeline\requirements.txt
.venv\Scripts\python -m pipeline.run            # completo con backtest (~min)
.venv\Scripts\python -m pipeline.run --skip-backtest
.venv\Scripts\python -m pipeline.update         # solo refrescar resultados + re-pronosticar
.venv\Scripts\python -m pipeline.watch --minutes 30   # watcher local con auto-push
```

(Si pip falla por SSL corporativo: `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org ...`)

## Frontend

```powershell
cd frontend
npm install
npm run dev      # http://localhost:3000
```

La página hace polling de `/data/predictions.json` cada 60 s, así que una
pestaña abierta se refresca sola.

## Despliegue en Vercel + actualización automática

1. Sube el repo a GitHub (`git init && git add -A && git commit && git push`).
2. En [vercel.com/new](https://vercel.com/new) importa el repo y fija
   **Root Directory = `frontend`**. Nada más: el frontend es estático respecto a los datos.
3. El workflow `.github/workflows/update.yml` corre solo (usa el `GITHUB_TOKEN`
   integrado, **no necesitas crear ningún secreto**): cada 30 min baja resultados,
   re-pronostica y hace push si algo cambió; a las 06:15 UTC re-entrena completo.
   Cada push redepliega Vercel con datos frescos.
   - Único requisito: en GitHub → Settings → Actions → General → *Workflow
     permissions* marca **Read and write permissions**.
4. (Opcional) `pipeline/.env` con `ODDS_API_KEY` de the-odds-api.com para
   contrastar contra cuotas de mercado.

## Notas

- Los pronósticos de la polla se pueden editar hasta que cada partido empieza:
  la vista marca los partidos *próximos* (pendientes de cargar) y el botón
  "copiar marcador" facilita pasarlos.
- `results.csv` no se versiona (5 MB, se descarga al vuelo); el resto de datos
  intermedios sí, para que el Action sea incremental.
