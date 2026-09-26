export interface TreemapInput<T> {
  value: number;
  data: T;
}

export interface TreemapRect<T> {
  x: number;
  y: number;
  w: number;
  h: number;
  data: T;
  value: number;
}

/**
 * Squarified treemap (Bruls, Huizing, van Wijk). Lays items out inside a
 * `width` x `height` rectangle with areas proportional to `value`.
 */
export function squarify<T>(items: TreemapInput<T>[], width: number, height: number): TreemapRect<T>[] {
  const valid = items.filter((i) => i.value > 0).sort((a, b) => b.value - a.value);
  const total = valid.reduce((s, i) => s + i.value, 0);
  if (!valid.length || total <= 0 || width <= 0 || height <= 0) return [];

  type Node = TreemapInput<T> & { area: number };
  const scale = (width * height) / total;
  const nodes: Node[] = valid.map((i) => ({ ...i, area: i.value * scale }));
  const out: TreemapRect<T>[] = [];

  let x = 0;
  let y = 0;
  let w = width;
  let h = height;
  let row: Node[] = [];

  const worst = (r: Node[], side: number) => {
    const sum = r.reduce((s, n) => s + n.area, 0);
    let max = -Infinity;
    let min = Infinity;
    for (const n of r) {
      max = Math.max(max, n.area);
      min = Math.min(min, n.area);
    }
    const s2 = side * side;
    const sum2 = sum * sum;
    return Math.max((s2 * max) / sum2, sum2 / (s2 * min));
  };

  const layoutRow = (r: Node[]) => {
    const sum = r.reduce((s, n) => s + n.area, 0);
    if (w >= h) {
      const colW = sum / h;
      let cy = y;
      for (const n of r) {
        const nh = n.area / colW;
        out.push({ x, y: cy, w: colW, h: nh, data: n.data, value: n.value });
        cy += nh;
      }
      x += colW;
      w -= colW;
    } else {
      const rowH = sum / w;
      let cx = x;
      for (const n of r) {
        const nw = n.area / rowH;
        out.push({ x: cx, y, w: nw, h: rowH, data: n.data, value: n.value });
        cx += nw;
      }
      y += rowH;
      h -= rowH;
    }
  };

  for (const node of nodes) {
    const side = Math.min(w, h);
    if (row.length === 0 || worst([...row, node], side) <= worst(row, side)) {
      row.push(node);
    } else {
      layoutRow(row);
      row = [node];
    }
  }
  if (row.length) layoutRow(row);
  return out;
}

/** Map a P&L percentage onto a green/red fill that saturates at +/- `range` percent. */
export function pnlColor(pnlPercent: number, range = 5): string {
  if (!Number.isFinite(pnlPercent) || Math.abs(pnlPercent) < 0.005) return "rgba(125, 136, 152, 0.22)";
  const t = Math.max(-1, Math.min(1, pnlPercent / range));
  const a = (0.22 + Math.abs(t) * 0.6).toFixed(3);
  return t > 0 ? `rgba(47, 191, 113, ${a})` : `rgba(239, 90, 90, ${a})`;
}
