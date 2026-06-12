export type Estado = "proximo" | "en_vivo" | "finalizado";

export interface Prob1x2 {
  local: number;
  empate: number;
  visitante: number;
}

export interface Match {
  id: number;
  jornada: number;
  grupo: string;
  fecha_utc: string;
  sede: string;
  equipo_local: string;
  equipo_visitante: string;
  bandera_local: string;
  bandera_visitante: string;
  elo_local: number;
  elo_visitante: number;
  lambdas: [number, number];
  prob_1x2: Prob1x2;
  marcador_recomendado: [number, number];
  marcador_mas_probable: [number, number];
  puntos_esperados: number;
  estado: Estado;
  marcador_real: [number, number] | null;
  puntos_obtenidos: number | null;
}

export interface BacktestEntry {
  accuracy_1x2: number;
  log_loss: number | null;
  rps: number | null;
  n: number;
}

export interface Meta {
  actualizado: string;
  partidos_finalizados: number;
  puntos_acumulados: number;
  aciertos_marcador_exacto: number;
  aciertos_resultado: number;
  modelo: { rho: number; blend_w: number };
  backtest?: Record<string, BacktestEntry>;
}

export interface StandingRow {
  equipo: string;
  bandera: string;
  pj: number;
  g: number;
  e: number;
  p: number;
  gf: number;
  gc: number;
  pts: number;
}

export type Standings = Record<string, StandingRow[]>;
