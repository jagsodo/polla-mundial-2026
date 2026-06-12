/* eslint-disable @typescript-eslint/no-explicit-any */
import { NextRequest, NextResponse } from "next/server";

/**
 * Webhook de Telegram (serverless, corre en Vercel).
 * Telegram envía cada mensaje aquí; respondemos y, para /actualizar, disparamos
 * el GitHub Action que actualiza la polla.
 *
 * Variables de entorno (Vercel → Settings → Environment Variables):
 *   TELEGRAM_BOT_TOKEN   token de @BotFather
 *   GH_TOKEN             token de GitHub con Actions:write (+ Contents:write para /cargar)
 *   GH_REPO              "jagsodo/polla-mundial-2026"
 *   ALLOWED_CHAT_IDS     ids separados por coma
 *   TELEGRAM_SECRET      cadena secreta (la mismo que se registra en setWebhook)
 */

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const TG = () => `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}`;
const REPO = () => process.env.GH_REPO || "jagsodo/polla-mundial-2026";
const GH = () => `https://api.github.com/repos/${REPO()}`;
const GH_HDR = () => ({
  Authorization: `Bearer ${process.env.GH_TOKEN}`,
  Accept: "application/vnd.github+json",
  "Content-Type": "application/json",
});

async function send(chatId: number, text: string) {
  await fetch(`${TG()}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: "HTML",
      disable_web_page_preview: true,
    }),
  });
}

async function ghJson(path: string): Promise<any> {
  const r = await fetch(`${GH()}/contents/${path}?ref=main&t=${Date.now()}`, {
    headers: GH_HDR(),
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`gh ${r.status}`);
  const j = await r.json();
  return JSON.parse(Buffer.from(j.content, "base64").toString("utf-8"));
}

async function triggerAction(retrain = false): Promise<boolean> {
  const r = await fetch(`${GH()}/actions/workflows/update.yml/dispatches`, {
    method: "POST",
    headers: GH_HDR(),
    body: JSON.stringify({ ref: "main", inputs: { retrain: String(retrain) } }),
  });
  return r.status === 204;
}

const HELP = `⚽ <b>Polla Mundial 2026</b>
/actualizar — buscar resultados y recalcular
/estado — puntos y última actualización
/pendientes — próximos con marcador recomendado
/cargar Mexico 2-0 South Africa — cargar resultado a mano`;

async function handle(chatId: number, text: string) {
  const parts = text.trim().split(/\s+/);
  const cmd = parts[0].toLowerCase().split("@")[0];
  const args = parts.slice(1);

  if (cmd === "/start" || cmd === "/help") return send(chatId, HELP);

  if (cmd === "/actualizar") {
    const ok = await triggerAction(false);
    return send(
      chatId,
      ok
        ? "🤖 Robot disparado. En ~1-2 min reviso ESPN, recalculo y actualizo la web."
        : "⚠️ No pude disparar el robot (revisa que GH_TOKEN tenga Actions: write)."
    );
  }

  if (cmd === "/estado") {
    try {
      const m = await ghJson("frontend/public/data/meta.json");
      const site = process.env.SITE_URL ? `\n🌐 ${process.env.SITE_URL}` : "";
      return send(
        chatId,
        `📊 <b>Estado de la polla</b>\n` +
          `Puntos acumulados: <b>${m.puntos_acumulados}</b>\n` +
          `Partidos finalizados: ${m.partidos_finalizados}\n` +
          `Marcadores exactos: ${m.aciertos_marcador_exacto}\n` +
          `Resultados 1X2: ${m.aciertos_resultado}\n` +
          `Última actualización: ${String(m.actualizado).slice(0, 16).replace("T", " ")} UTC` +
          site
      );
    } catch {
      return send(chatId, "No pude leer el estado todavía.");
    }
  }

  if (cmd === "/pendientes") {
    try {
      const ms = await ghJson("frontend/public/data/predictions.json");
      const prox = ms.filter((m: any) => m.estado === "proximo").slice(0, 12);
      if (!prox.length) return send(chatId, "No hay partidos próximos.");
      const lines = ["🔮 <b>Próximos (marcador recomendado)</b>"];
      for (const m of prox) {
        const r = m.marcador_recomendado;
        lines.push(`J${m.jornada} ${m.equipo_local} <b>${r[0]}-${r[1]}</b> ${m.equipo_visitante}`);
      }
      return send(chatId, lines.join("\n"));
    } catch {
      return send(chatId, "No pude leer los pronósticos.");
    }
  }

  if (cmd === "/cargar") {
    return cargar(chatId, args);
  }

  return send(chatId, "No conozco ese comando. /help");
}

async function cargar(chatId: number, args: string[]) {
  let score = "", idx = -1;
  args.forEach((tok, i) => {
    if (/^\d+-\d+$/.test(tok)) {
      score = tok;
      idx = i;
    }
  });
  if (idx < 0) {
    return send(chatId, "Formato: <code>/cargar Mexico 2-0 South Africa</code>");
  }
  const left = args.slice(0, idx).join(" ").toLowerCase();
  const right = args.slice(idx + 1).join(" ").toLowerCase();
  const [hs, as_] = score.split("-").map(Number);

  let seed: any[];
  try {
    seed = await ghJson("pipeline/data/matches_seed.json");
  } catch {
    return send(chatId, "No pude leer el calendario.");
  }
  const match = seed.find(
    (m) =>
      [m.local_en.toLowerCase(), m.equipo_local.toLowerCase()].includes(left) &&
      [m.visitante_en.toLowerCase(), m.equipo_visitante.toLowerCase()].includes(right)
  );
  if (!match) return send(chatId, `No encontré ${left} vs ${right}. Revisa los nombres.`);
  const key = `${match.fecha}|${match.local_en}|${match.visitante_en}`;

  const cur = await fetch(`${GH()}/contents/pipeline/data/results_2026.json?ref=main`, {
    headers: GH_HDR(),
    cache: "no-store",
  }).then((r) => r.json());
  const data = JSON.parse(Buffer.from(cur.content, "base64").toString("utf-8"));
  data[key] = { home: hs, away: as_ };
  const put = await fetch(`${GH()}/contents/pipeline/data/results_2026.json`, {
    method: "PUT",
    headers: GH_HDR(),
    body: JSON.stringify({
      message: `data: carga manual ${key} ${hs}-${as_}`,
      content: Buffer.from(JSON.stringify(data, null, 1)).toString("base64"),
      sha: cur.sha,
    }),
  });
  if (!put.ok) return send(chatId, "No pude guardar el resultado.");
  await send(chatId, `✅ Cargado ${match.equipo_local} ${hs}-${as_} ${match.equipo_visitante}. Recalculando...`);
  await triggerAction(false);
}

export async function POST(req: NextRequest) {
  // seguridad: Telegram manda este header con el secreto registrado en setWebhook
  const secret = req.headers.get("x-telegram-bot-api-secret-token");
  if (process.env.TELEGRAM_SECRET && secret !== process.env.TELEGRAM_SECRET) {
    return NextResponse.json({ ok: false }, { status: 401 });
  }
  let update: any;
  try {
    update = await req.json();
  } catch {
    return NextResponse.json({ ok: true });
  }
  const msg = update.message || update.edited_message;
  if (msg?.text) {
    const chatId = msg.chat.id;
    const allowed = (process.env.ALLOWED_CHAT_IDS || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (allowed.length && !allowed.includes(String(chatId))) {
      await send(chatId, `No autorizado. Tu chat id es ${chatId}.`);
    } else {
      try {
        await handle(chatId, msg.text);
      } catch {
        await send(chatId, "Ups, hubo un error procesando el comando.");
      }
    }
  }
  return NextResponse.json({ ok: true });
}

// healthcheck simple
export async function GET() {
  return NextResponse.json({ ok: true, bot: "polla-mundial-2026" });
}
