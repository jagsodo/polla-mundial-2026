"use client";

import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("tema", next ? "dark" : "light");
    } catch {}
  }

  return (
    <button
      onClick={toggle}
      aria-label="Cambiar tema"
      title={dark ? "Activar modo claro" : "Activar modo oscuro"}
      className="inline-flex h-10 items-center gap-2 rounded-lg border border-border bg-card px-3 text-sm font-medium transition-colors hover:border-accent"
    >
      <span
        aria-hidden="true"
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-border text-[10px] font-semibold"
      >
        {dark ? "L" : "O"}
      </span>
      <span>{dark ? "Claro" : "Oscuro"}</span>
    </button>
  );
}
