import type { PricePoint } from "@/lib/types";

interface Props {
  points: PricePoint[];
  width?: number;
  height?: number;
  maxPoints?: number;
}

/** Tiny SVG line of recent prices; colored by direction since the first point shown. */
export default function Sparkline({ points, width = 84, height = 22, maxPoints = 120 }: Props) {
  const data = points.length > maxPoints ? points.slice(points.length - maxPoints) : points;
  if (data.length < 2) {
    return (
      <svg width={width} height={height} aria-hidden="true" data-testid="sparkline">
        <line x1={0} x2={width} y1={height / 2} y2={height / 2} stroke="#33404f" strokeDasharray="2 3" />
      </svg>
    );
  }
  let min = Infinity;
  let max = -Infinity;
  for (const p of data) {
    min = Math.min(min, p.value);
    max = Math.max(max, p.value);
  }
  const range = max - min || 1;
  const pad = 2;
  const step = (width - pad * 2) / (data.length - 1);
  const d = data
    .map((p, i) => {
      const x = pad + i * step;
      const y = pad + (height - pad * 2) * (1 - (p.value - min) / range);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const up = data[data.length - 1].value >= data[0].value;
  return (
    <svg width={width} height={height} aria-hidden="true" data-testid="sparkline">
      <path d={d} fill="none" stroke={up ? "#2fbf71" : "#ef5a5a"} strokeWidth={1.25} strokeLinejoin="round" />
    </svg>
  );
}
