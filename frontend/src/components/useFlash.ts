"use client";

import { useEffect, useRef } from "react";

export const FLASH_MS = 350;

/**
 * Returns a ref for an element that should flash green/red when `value` changes.
 * The flash class is applied directly to the DOM node and removed after FLASH_MS,
 * letting the element's CSS transition fade the highlight out.
 */
export function useFlash<T extends HTMLElement>(value: number | null | undefined) {
  const ref = useRef<T>(null);
  const prev = useRef<number | null | undefined>(value);

  useEffect(() => {
    const before = prev.current;
    prev.current = value;
    const el = ref.current;
    if (!el || before == null || value == null || before === value) return;
    const cls = value > before ? "flash-up" : "flash-down";
    el.classList.remove("flash-up", "flash-down");
    el.classList.add(cls);
    const t = setTimeout(() => el.classList.remove(cls), FLASH_MS);
    return () => {
      clearTimeout(t);
      el.classList.remove(cls);
    };
  }, [value]);

  return ref;
}
