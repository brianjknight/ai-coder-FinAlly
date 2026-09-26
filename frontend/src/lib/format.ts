const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatUsd(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return usd.format(n);
}

export function formatSignedUsd(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  const s = usd.format(Math.abs(n));
  return n > 0 ? `+${s}` : n < 0 ? `-${s}` : s;
}

export function formatPrice(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatPercent(n: number | null | undefined, digits = 2): string {
  if (n == null || !Number.isFinite(n)) return "—";
  const s = Math.abs(n).toFixed(digits);
  if (Number(s) === 0) return `${(0).toFixed(digits)}%`;
  return n > 0 ? `+${s}%` : `-${s}%`;
}

export function formatQty(n: number): string {
  return n.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

/** Tailwind text color class for a signed value. */
export function signClass(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n) || Math.abs(n) < 1e-9) return "text-muted";
  return n > 0 ? "text-up" : "text-down";
}

/** Convert unix seconds (UTC) to a chart time shifted into the viewer's local zone. */
export function toLocalChartTime(unixSeconds: number): number {
  const offsetMin = new Date(unixSeconds * 1000).getTimezoneOffset();
  return Math.floor(unixSeconds) - offsetMin * 60;
}
