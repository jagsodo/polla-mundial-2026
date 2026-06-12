"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Descarga un JSON de /public y lo re-consulta cada `intervalMs` (def. 60s),
 * con cache-busting para refrescar una pestaña abierta sin recargar.
 */
export function usePolling<T>(url: string, intervalMs = 60_000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchOnce = useCallback(async () => {
    try {
      const res = await fetch(`${url}?t=${Date.now()}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData((await res.json()) as T);
      setError(null);
      setUpdatedAt(Date.now());
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    }
  }, [url]);

  useEffect(() => {
    fetchOnce();
    timer.current = setInterval(fetchOnce, intervalMs);
    const onFocus = () => fetchOnce();
    window.addEventListener("focus", onFocus);
    return () => {
      if (timer.current) clearInterval(timer.current);
      window.removeEventListener("focus", onFocus);
    };
  }, [fetchOnce, intervalMs]);

  return { data, error, updatedAt, refetch: fetchOnce };
}
