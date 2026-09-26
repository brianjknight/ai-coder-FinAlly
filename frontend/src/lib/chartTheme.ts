import { ColorType, CrosshairMode, type DeepPartial, type ChartOptions } from "lightweight-charts";

export const CHART_COLORS = {
  text: "#8190a2",
  grid: "rgba(36, 46, 60, 0.55)",
  border: "#242e3c",
  blue: "#209dd7",
  accent: "#ecad0a",
  up: "#2fbf71",
  down: "#ef5a5a",
};

export function baseChartOptions(): DeepPartial<ChartOptions> {
  return {
    autoSize: true,
    layout: {
      background: { type: ColorType.Solid, color: "transparent" },
      textColor: CHART_COLORS.text,
      fontFamily: "IBM Plex Mono, ui-monospace, monospace",
      fontSize: 11,
      attributionLogo: false,
    },
    grid: {
      vertLines: { color: CHART_COLORS.grid },
      horzLines: { color: CHART_COLORS.grid },
    },
    rightPriceScale: { borderColor: CHART_COLORS.border },
    timeScale: {
      borderColor: CHART_COLORS.border,
      timeVisible: true,
      secondsVisible: true,
      rightOffset: 4,
    },
    crosshair: { mode: CrosshairMode.Magnet },
    handleScale: false,
    handleScroll: false,
  };
}
