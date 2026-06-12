"use client";

import { useEffect, useMemo, useState } from "react";

import { ThemeToggle } from "@/components/ThemeToggle";
import { editable, favorito, fechaCorta, flagUrl, horaLocal, marcador } from "@/lib/format";
import type { Match, Meta, StandingRow, Standings } from "@/lib/types";
import { usePolling } from "@/lib/usePolling";

type EstadoFiltro = "todos" | Match["estado"];
type JornadaFiltro = "todas" | 1 | 2 | 3;
type GrupoFiltro = "todos" | string;

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function decimal(value: number, digits = 2): string {
  return value.toFixed(digits);
}

function formatUpdate(value: string | null | undefined): string {
  if (!value) return "Sin datos";
  const date = new Date(value);
  return date.toLocaleString("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/** Bandera pequeña inline (para tablas). Imagen de flagcdn con fallback a texto. */
function FlagInline({ code, team }: { code: string; team: string }) {
  const [broken, setBroken] = useState(false);
  if (!code || broken) {
    return (
      <span className="inline-block w-6 text-center text-[10px] font-semibold uppercase text-muted">
        {team.slice(0, 2)}
      </span>
    );
  }
  return (
    /* eslint-disable-next-line @next/next/no-img-element */
    <img
      src={flagUrl(code)}
      alt=""
      aria-hidden="true"
      onError={() => setBroken(true)}
      className="inline-block h-3.5 w-5 rounded-[2px] object-cover ring-1 ring-border"
    />
  );
}

function statusLabel(estado: Match["estado"]): string {
  if (estado === "en_vivo") return "En vivo";
  if (estado === "finalizado") return "Finalizado";
  return "Proximo";
}

function statusClasses(estado: Match["estado"]): string {
  if (estado === "en_vivo") {
    return "border-emerald-500/30 bg-emerald-500/12 text-emerald-700 dark:text-emerald-300";
  }
  if (estado === "finalizado") {
    return "border-sky-500/30 bg-sky-500/12 text-sky-700 dark:text-sky-300";
  }
  return "border-amber-500/30 bg-amber-500/12 text-amber-700 dark:text-amber-300";
}

function StatusBadge({ estado }: { estado: Match["estado"] }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${statusClasses(estado)}`}
    >
      {estado === "en_vivo" ? (
        <span className="inline-block h-1.5 w-1.5 animate-pulse-live rounded-full bg-emerald-500" />
      ) : null}
      {statusLabel(estado)}
    </span>
  );
}

function TeamFlag({ code, team }: { code: string; team: string }) {
  const [broken, setBroken] = useState(false);

  if (!code || broken) {
    return (
      <span
        aria-hidden="true"
        className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-[11px] font-semibold uppercase text-muted shadow-sm"
      >
        {team.slice(0, 2)}
      </span>
    );
  }

  return (
    <span className="inline-flex h-9 w-9 items-center justify-center overflow-hidden rounded-md border border-border bg-background shadow-sm">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={flagUrl(code)}
        alt={team}
        onError={() => setBroken(true)}
        className="h-full w-full object-cover"
      />
    </span>
  );
}

function SectionHeading({
  eyebrow,
  title,
  caption,
}: {
  eyebrow: string;
  title: string;
  caption: string;
}) {
  return (
    <div className="space-y-1">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">{eyebrow}</p>
      <h2 className="text-xl font-semibold text-foreground sm:text-2xl">{title}</h2>
      <p className="text-sm text-muted">{caption}</p>
    </div>
  );
}

function StatTile({
  label,
  value,
  helper,
}: {
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-4 shadow-sm shadow-slate-950/5 dark:shadow-black/10">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">{label}</p>
      <div className="mt-3 flex items-end justify-between gap-3">
        <p className="text-3xl font-semibold tracking-tight text-foreground">{value}</p>
      </div>
      <p className="mt-2 text-sm text-muted">{helper}</p>
    </div>
  );
}

function FilterButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={[
        "h-9 rounded-md border px-3 text-sm font-medium transition-colors",
        active
          ? "border-slate-900 bg-slate-900 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-950"
          : "border-border bg-card text-muted hover:border-slate-400 hover:text-foreground dark:hover:border-slate-500",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function ProbabilityBar({ match }: { match: Match }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-[11px] font-medium uppercase tracking-[0.12em] text-muted">
        <span>Probabilidad 1X2</span>
        <span>
          {pct(match.prob_1x2.local)} / {pct(match.prob_1x2.empate)} / {pct(match.prob_1x2.visitante)}
        </span>
      </div>
      <div className="flex h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
        <div className="bg-emerald-500" style={{ width: `${match.prob_1x2.local * 100}%` }} />
        <div className="bg-slate-400 dark:bg-slate-500" style={{ width: `${match.prob_1x2.empate * 100}%` }} />
        <div className="bg-rose-500" style={{ width: `${match.prob_1x2.visitante * 100}%` }} />
      </div>
    </div>
  );
}

function DetailPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-background px-3 py-2">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className="mt-1 text-sm font-medium text-foreground">{value}</p>
    </div>
  );
}

function MatchCard({
  match,
  copied,
  onCopy,
}: {
  match: Match;
  copied: boolean;
  onCopy: (match: Match) => void;
}) {
  const fav = favorito(match);

  return (
    <article
      className={[
        "rounded-lg border bg-card p-4 shadow-sm shadow-slate-950/5 transition-all dark:shadow-black/10",
        editable(match)
          ? "border-emerald-500/35 ring-1 ring-emerald-500/12"
          : "border-border",
        match.estado === "finalizado" ? "animate-flash" : "",
      ].join(" ")}
    >
      <div className="flex flex-col gap-4 xl:grid xl:grid-cols-[220px_minmax(0,1fr)_260px] xl:items-center">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-border bg-background px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
              Grupo {match.grupo}
            </span>
            <StatusBadge estado={match.estado} />
          </div>

          <div>
            <p className="text-sm font-medium text-foreground">
              {fechaCorta(match.fecha_utc)} - {horaLocal(match.fecha_utc)}
            </p>
            <p className="mt-1 text-sm text-muted">{match.sede}</p>
          </div>

          {editable(match) ? (
            <div className="rounded-md border border-emerald-500/25 bg-emerald-500/8 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
              Pendiente de cargar en la polla
            </div>
          ) : null}
        </div>

        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
            <div className="flex min-w-0 items-center gap-3">
              <TeamFlag code={match.bandera_local} team={match.equipo_local} />
              <div className="min-w-0">
                <p className="truncate text-base font-semibold text-foreground">{match.equipo_local}</p>
                <p className="text-sm text-muted">Elo {match.elo_local}</p>
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-center dark:border-slate-700 dark:bg-slate-900/70">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Marcador recomendado</p>
              <p className="mt-1 text-3xl font-semibold tracking-tight text-foreground">
                {marcador(match.marcador_recomendado)}
              </p>
            </div>

            <div className="flex min-w-0 items-center justify-end gap-3 text-right">
              <div className="min-w-0">
                <p className="truncate text-base font-semibold text-foreground">{match.equipo_visitante}</p>
                <p className="text-sm text-muted">Elo {match.elo_visitante}</p>
              </div>
              <TeamFlag code={match.bandera_visitante} team={match.equipo_visitante} />
            </div>
          </div>

          <ProbabilityBar match={match} />

          <div className="grid gap-2 sm:grid-cols-2 2xl:grid-cols-4">
            <DetailPill label="Favorito" value={`${fav.label} (${pct(fav.pct)})`} />
            <DetailPill label="Mas probable" value={marcador(match.marcador_mas_probable)} />
            <DetailPill label="Puntos esperados" value={decimal(match.puntos_esperados)} />
            <DetailPill label="Marcador real" value={match.marcador_real ? marcador(match.marcador_real) : "-"} />
          </div>
        </div>

        <div className="flex flex-col gap-3 xl:items-end">
          <button
            onClick={() => onCopy(match)}
            className="inline-flex h-10 items-center justify-center rounded-md border border-border bg-background px-4 text-sm font-medium text-foreground transition-colors hover:border-slate-400 dark:hover:border-slate-500"
          >
            {copied ? "Copiado" : "Copiar marcador"}
          </button>

          <div className="grid w-full gap-2 xl:max-w-[240px]">
            <div className="rounded-md border border-border bg-background px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Lambdas</p>
              <p className="mt-1 text-sm font-medium text-foreground">
                {decimal(match.lambdas[0], 2)} / {decimal(match.lambdas[1], 2)}
              </p>
            </div>

            <div className="rounded-md border border-border bg-background px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Id de partido</p>
              <p className="mt-1 text-sm font-medium text-foreground">#{match.id}</p>
            </div>

            {match.puntos_obtenidos !== null ? (
              <div className="rounded-md border border-sky-500/25 bg-sky-500/10 px-3 py-2 text-sm text-sky-700 dark:text-sky-300">
                Puntos obtenidos: <span className="font-semibold">{match.puntos_obtenidos}</span>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </article>
  );
}

function StandingsTable({ group, rows }: { group: string; rows: StandingRow[] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm shadow-slate-950/5 dark:shadow-black/10">
      <div className="flex items-center justify-between border-b border-border bg-slate-50 px-4 py-3 dark:bg-slate-900/70">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Grupo {group}</p>
          <h3 className="mt-1 text-sm font-semibold text-foreground">Tabla de posiciones</h3>
        </div>
        <span className="text-xs text-muted">{rows.length} equipos</span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-background text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
            <tr>
              <th className="px-4 py-3 text-left">#</th>
              <th className="px-4 py-3 text-left">Equipo</th>
              <th className="px-3 py-3 text-right">PJ</th>
              <th className="px-3 py-3 text-right">G</th>
              <th className="px-3 py-3 text-right">E</th>
              <th className="px-3 py-3 text-right">P</th>
              <th className="px-3 py-3 text-right">GF</th>
              <th className="px-3 py-3 text-right">GC</th>
              <th className="px-4 py-3 text-right">Pts</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr
                key={`${group}-${row.equipo}`}
                className="border-t border-border/70 odd:bg-transparent even:bg-slate-50/50 dark:even:bg-slate-900/35"
              >
                <td className="px-4 py-3 text-muted">{index + 1}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <TeamFlag code={row.bandera} team={row.equipo} />
                    <span className="font-medium text-foreground">{row.equipo}</span>
                  </div>
                </td>
                <td className="px-3 py-3 text-right text-muted">{row.pj}</td>
                <td className="px-3 py-3 text-right text-muted">{row.g}</td>
                <td className="px-3 py-3 text-right text-muted">{row.e}</td>
                <td className="px-3 py-3 text-right text-muted">{row.p}</td>
                <td className="px-3 py-3 text-right text-muted">{row.gf}</td>
                <td className="px-3 py-3 text-right text-muted">{row.gc}</td>
                <td className="px-4 py-3 text-right font-semibold text-foreground">{row.pts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function PollaDashboard() {
  const { data: matches, error: matchesError } = usePolling<Match[]>("/data/predictions.json");
  const { data: meta, error: metaError } = usePolling<Meta>("/data/meta.json");
  const { data: standings } = usePolling<Standings>("/data/standings.json");

  const [jornada, setJornada] = useState<JornadaFiltro>("todas");
  const [grupo, setGrupo] = useState<GrupoFiltro>("todos");
  const [estado, setEstado] = useState<EstadoFiltro>("todos");
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [showSummaryTable, setShowSummaryTable] = useState(false);

  useEffect(() => {
    if (copiedId === null) return;
    const timer = window.setTimeout(() => setCopiedId(null), 1600);
    return () => window.clearTimeout(timer);
  }, [copiedId]);

  const grupos = useMemo(() => {
    if (!matches) return [];
    return Array.from(new Set(matches.map((match) => match.grupo))).sort();
  }, [matches]);

  const filtered = useMemo(() => {
    if (!matches) return [];
    return matches.filter((match) => {
      const byJornada = jornada === "todas" || match.jornada === jornada;
      const byGrupo = grupo === "todos" || match.grupo === grupo;
      const byEstado = estado === "todos" || match.estado === estado;
      return byJornada && byGrupo && byEstado;
    });
  }, [estado, grupo, jornada, matches]);

  const groupedByRound = useMemo(
    () =>
      [1, 2, 3].map((round) => ({
        jornada: round,
        matches: filtered.filter((match) => match.jornada === round),
      })),
    [filtered],
  );

  const pendingCount = useMemo(() => filtered.filter((match) => editable(match)).length, [filtered]);
  const liveCount = useMemo(() => filtered.filter((match) => match.estado === "en_vivo").length, [filtered]);
  const finishedCount = useMemo(() => filtered.filter((match) => match.estado === "finalizado").length, [filtered]);
  const averageExpected = useMemo(() => {
    if (!filtered.length) return "0.00";
    const total = filtered.reduce((sum, match) => sum + match.puntos_esperados, 0);
    return decimal(total / filtered.length);
  }, [filtered]);

  const bestEdges = useMemo(() => {
    if (!matches) return [];
    return [...matches].sort((a, b) => b.puntos_esperados - a.puntos_esperados).slice(0, 3);
  }, [matches]);

  const allSortedMatches = useMemo(() => {
    if (!matches) return [];
    return [...matches].sort((a, b) => a.id - b.id);
  }, [matches]);

  async function copyScore(match: Match) {
    const text = `${match.equipo_local} ${marcador(match.marcador_recomendado)} ${match.equipo_visitante}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(match.id);
    } catch {
      setCopiedId(null);
    }
  }

  const modelAccuracy = meta?.backtest?.intl_2023_2025?.accuracy_1x2;

  return (
    <main className="min-h-screen bg-background">
      <section className="border-b border-border bg-card">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="grid gap-8 xl:grid-cols-[minmax(0,1.5fr)_340px]">
            <div className="space-y-5">
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted">
                  Analizador inteligente de polla mundial
                </p>
                <h1 className="max-w-4xl text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                  Pronosticos claros, ordenados y listos para cargar partido por partido
                </h1>
                <p className="max-w-3xl text-base leading-7 text-muted">
                  Vista operativa para revisar los 72 partidos, priorizar los pendientes y copiar rapido
                  el marcador que maximiza valor esperado bajo tu sistema de puntos.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-border bg-background px-4 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Pendientes</p>
                  <p className="mt-2 text-2xl font-semibold text-foreground">{pendingCount}</p>
                </div>
                <div className="rounded-lg border border-border bg-background px-4 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">En vivo</p>
                  <p className="mt-2 text-2xl font-semibold text-foreground">{liveCount}</p>
                </div>
                <div className="rounded-lg border border-border bg-background px-4 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Promedio E[pts]</p>
                  <p className="mt-2 text-2xl font-semibold text-foreground">{averageExpected}</p>
                </div>
              </div>
            </div>

            <aside className="rounded-lg border border-border bg-background p-4 shadow-sm shadow-slate-950/5 dark:shadow-black/10">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Estado del modelo</p>
                  <p className="mt-1 text-lg font-semibold text-foreground">Actualizacion y precision</p>
                </div>
                <ThemeToggle />
              </div>

              <div className="mt-5 space-y-3">
                <div className="rounded-md border border-border bg-card px-3 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Ultima actualizacion</p>
                  <p className="mt-1 text-sm font-medium text-foreground">{formatUpdate(meta?.actualizado)}</p>
                </div>
                <div className="rounded-md border border-border bg-card px-3 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Backtest 2023-2025</p>
                  <p className="mt-1 text-sm font-medium text-foreground">
                    {modelAccuracy ? pct(modelAccuracy) : "-"} accuracy 1X2
                  </p>
                </div>
                <div className="rounded-md border border-border bg-card px-3 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Partidos finalizados</p>
                  <p className="mt-1 text-sm font-medium text-foreground">{finishedCount}</p>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatTile
            label="Puntos acumulados"
            value={String(meta?.puntos_acumulados ?? 0)}
            helper={`${meta?.partidos_finalizados ?? 0} partidos resueltos`}
          />
          <StatTile
            label="Marcadores exactos"
            value={String(meta?.aciertos_marcador_exacto ?? 0)}
            helper="Exactos acertados hasta el momento"
          />
          <StatTile
            label="Resultados 1X2"
            value={String(meta?.aciertos_resultado ?? 0)}
            helper="Ganador o empate acertado"
          />
          <StatTile
            label="RPS backtest"
            value={meta?.backtest?.intl_2023_2025?.rps?.toFixed(3) ?? "-"}
            helper="Referencia del modelo en historico reciente"
          />
        </div>
      </section>

      <section className="border-y border-border bg-card/60">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
            <SectionHeading
              eyebrow="Control"
              title="Filtros de lectura"
              caption="Recorta rapido la vista para revisar una jornada, un grupo o solo partidos editables."
            />

            <div className="grid gap-4 rounded-lg border border-border bg-card p-4 shadow-sm shadow-slate-950/5 dark:shadow-black/10">
              <div>
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Jornada</p>
                <div className="flex flex-wrap gap-2">
                  <FilterButton active={jornada === "todas"} onClick={() => setJornada("todas")}>
                    Todas
                  </FilterButton>
                  {[1, 2, 3].map((round) => (
                    <FilterButton key={round} active={jornada === round} onClick={() => setJornada(round as 1 | 2 | 3)}>
                      Jornada {round}
                    </FilterButton>
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Grupo</p>
                <div className="flex flex-wrap gap-2">
                  <FilterButton active={grupo === "todos"} onClick={() => setGrupo("todos")}>
                    Todos
                  </FilterButton>
                  {grupos.map((group) => (
                    <FilterButton key={group} active={grupo === group} onClick={() => setGrupo(group)}>
                      Grupo {group}
                    </FilterButton>
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Estado</p>
                <div className="flex flex-wrap gap-2">
                  <FilterButton active={estado === "todos"} onClick={() => setEstado("todos")}>
                    Todos
                  </FilterButton>
                  {(["proximo", "en_vivo", "finalizado"] as const).map((item) => (
                    <FilterButton key={item} active={estado === item} onClick={() => setEstado(item)}>
                      {statusLabel(item)}
                    </FilterButton>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <SectionHeading
          eyebrow="Oportunidad"
          title="Partidos con mejor valor esperado"
          caption="Tres picks donde el modelo encuentra mas retorno esperado bajo tus reglas."
        />

        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          {bestEdges.map((match) => (
            <div key={`edge-${match.id}`} className="rounded-lg border border-border bg-card p-4 shadow-sm shadow-slate-950/5 dark:shadow-black/10">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
                    Grupo {match.grupo} - Jornada {match.jornada}
                  </p>
                  <p className="mt-2 truncate text-base font-semibold text-foreground">
                    {match.equipo_local} vs {match.equipo_visitante}
                  </p>
                </div>
                <span className="rounded-md border border-border bg-background px-3 py-2 text-xl font-semibold text-foreground">
                  {marcador(match.marcador_recomendado)}
                </span>
              </div>
              <div className="mt-4 flex items-center justify-between text-sm text-muted">
                <span>{decimal(match.puntos_esperados)} pts esperados</span>
                <span>{pct(Math.max(match.prob_1x2.local, match.prob_1x2.empate, match.prob_1x2.visitante))} lado fuerte</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
        <SectionHeading
          eyebrow="Pronosticos"
          title="Carga operativa por jornada"
          caption="Partidos ordenados para lectura rapida: contexto a la izquierda, enfrentamiento al centro y accion a la derecha."
        />

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3 shadow-sm shadow-slate-950/5 dark:shadow-black/10">
          <div>
            <p className="text-sm font-medium text-foreground">Tabla simple de pronosticos</p>
            <p className="text-sm text-muted">
              Muestra todos los partidos en formato resumido para revisar y cargar rapido.
            </p>
          </div>
          <button
            onClick={() => setShowSummaryTable((current) => !current)}
            className="inline-flex h-10 items-center justify-center rounded-md border border-slate-900 bg-slate-900 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-800 dark:border-slate-100 dark:bg-slate-100 dark:text-slate-950 dark:hover:bg-slate-200"
          >
            {showSummaryTable ? "Ocultar tabla resumen" : "Mostrar tabla resumen"}
          </button>
        </div>

        {showSummaryTable ? (
          <div className="mt-5 overflow-hidden rounded-lg border border-border bg-card shadow-sm shadow-slate-950/5 dark:shadow-black/10">
            <div className="flex items-center justify-between border-b border-border bg-slate-50 px-4 py-3 dark:bg-slate-900/70">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Tabla resumen</p>
                <p className="mt-1 text-sm text-foreground">Los {allSortedMatches.length} pronosticos en una sola vista</p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-background text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
                  <tr>
                    <th className="px-4 py-3 text-left">Id</th>
                    <th className="px-4 py-3 text-left">Horario</th>
                    <th className="px-4 py-3 text-left">Partido</th>
                    <th className="px-4 py-3 text-left">Pronostico</th>
                    <th className="px-4 py-3 text-left">Resultado</th>
                    <th className="px-4 py-3 text-right">Puntaje</th>
                  </tr>
                </thead>
                <tbody>
                  {allSortedMatches.map((match) => (
                    <tr
                      key={`summary-${match.id}`}
                      className="border-t border-border/70 odd:bg-transparent even:bg-slate-50/50 dark:even:bg-slate-900/35"
                    >
                      <td className="px-4 py-3 font-medium text-foreground">{match.id}</td>
                      <td className="px-4 py-3 text-muted">
                        {fechaCorta(match.fecha_utc)} - {horaLocal(match.fecha_utc)}
                      </td>
                      <td className="px-4 py-3 text-foreground">
                        <div className="flex min-w-[260px] items-center gap-2">
                          <FlagInline code={match.bandera_local} team={match.equipo_local} />
                          <span>{match.equipo_local}</span>
                          <span className="text-muted">-</span>
                          <span>{match.equipo_visitante}</span>
                          <FlagInline code={match.bandera_visitante} team={match.equipo_visitante} />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="inline-flex items-center gap-2 rounded-md border border-emerald-500/25 bg-emerald-500/10 px-3 py-1.5 font-semibold text-foreground">
                          <FlagInline code={match.bandera_local} team={match.equipo_local} />
                          <span>{match.marcador_recomendado[0]}</span>
                          <span className="text-muted">-</span>
                          <span>{match.marcador_recomendado[1]}</span>
                          <FlagInline code={match.bandera_visitante} team={match.equipo_visitante} />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {match.marcador_real ? (
                          <div className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-3 py-1.5 text-foreground">
                            <FlagInline code={match.bandera_local} team={match.equipo_local} />
                            <span>{match.marcador_real[0]}</span>
                            <span className="text-muted">-</span>
                            <span>{match.marcador_real[1]}</span>
                            <FlagInline code={match.bandera_visitante} team={match.equipo_visitante} />
                          </div>
                        ) : (
                          <StatusBadge estado={match.estado} />
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-foreground">
                        {match.puntos_obtenidos !== null ? match.puntos_obtenidos : decimal(match.puntos_esperados)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        {matchesError || metaError ? (
          <div className="mt-5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-700 dark:text-rose-300">
            Error cargando datos: {matchesError ?? metaError}
          </div>
        ) : null}

        {!matches ? (
          <div className="mt-5 rounded-lg border border-border bg-card px-4 py-10 text-center text-muted">
            Cargando pronosticos...
          </div>
        ) : (
          <div className="mt-6 space-y-10">
            {groupedByRound.map((section) => (
              <section key={section.jornada} className="space-y-4">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <h3 className="text-2xl font-semibold text-foreground">Jornada {section.jornada}</h3>
                    <p className="text-sm text-muted">{section.matches.length} partidos en esta vista.</p>
                  </div>
                </div>

                {section.matches.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border px-4 py-8 text-sm text-muted">
                    No hay partidos con estos filtros.
                  </div>
                ) : (
                  <div className="grid gap-4">
                    {section.matches.map((match) => (
                      <MatchCard key={match.id} match={match} copied={copiedId === match.id} onCopy={copyScore} />
                    ))}
                  </div>
                )}
              </section>
            ))}
          </div>
        )}
      </section>

      <section className="border-t border-border bg-card/60">
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow="Grupos"
            title="Tablas mas legibles"
            caption="Mas columnas utiles y mejor contraste para revisar rapido posicion, rendimiento y puntos."
          />

          {!standings ? (
            <div className="mt-5 rounded-lg border border-border bg-card px-4 py-8 text-sm text-muted">
              Cargando tablas...
            </div>
          ) : (
            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {Object.entries(standings)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([group, rows]) => (
                  <StandingsTable key={group} group={group} rows={rows} />
                ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
