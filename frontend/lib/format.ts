import type { Match } from "./types";

export function flagUrl(code: string): string {
  return code ? `https://flagcdn.com/h40/${code}.png` : "";
}

export function fechaCorta(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("es-ES", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export function horaLocal(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}

export function desdeAhora(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  const min = Math.round(diff / 60000);
  if (Math.abs(min) < 60) return min >= 0 ? `en ${min} min` : `hace ${-min} min`;
  const h = Math.round(min / 60);
  if (Math.abs(h) < 24) return h >= 0 ? `en ${h} h` : `hace ${-h} h`;
  const dias = Math.round(h / 24);
  return dias >= 0 ? `en ${dias} d` : `hace ${-dias} d`;
}

export function marcador(m: [number, number]): string {
  return `${m[0]}-${m[1]}`;
}

/** Lado más probable del 1X2 y su porcentaje. */
export function favorito(m: Match): { label: string; pct: number } {
  const { local, empate, visitante } = m.prob_1x2;
  const max = Math.max(local, empate, visitante);
  if (max === local) return { label: m.equipo_local, pct: local };
  if (max === visitante) return { label: m.equipo_visitante, pct: visitante };
  return { label: "Empate", pct: empate };
}

/** ¿El pronóstico aún se puede cargar/editar en la polla? */
export function editable(m: Match): boolean {
  return m.estado === "proximo";
}
