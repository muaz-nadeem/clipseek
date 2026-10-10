import type { CSSProperties } from "react";

export type IconName = "arrow" | "search" | "play" | "upload" | "library" | "film" | "clock" | "check" | "plus" | "logout" | "trash" | "sliders" | "shield" | "chevron" | "close" | "menu";
const paths: Record<IconName, string> = {
  arrow: "M4 12h16m-6-6 6 6-6 6",
  search: "m20 20-4.5-4.5M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0",
  play: "m9 5 11 7-11 7V5Z",
  upload: "M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5",
  library: "M4 4h5v16H4V4Zm8 0h3v16h-3V4Zm6 1 4 14",
  film: "M3 4h18v16H3V4Zm4 0v16M17 4v16M3 8h4m-4 8h4M17 8h4m-4 8h4",
  clock: "M12 7v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  check: "m5 12 4 4L19 6",
  plus: "M12 4v16M4 12h16",
  logout: "M9 4H4v16h5m-1-8h13m-5-5 5 5-5 5",
  trash: "M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7",
  sliders: "M4 7h9m4 0h3M4 17h3m4 0h9M13 4v6M7 14v6",
  shield: "m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Zm-4 9 3 3 5-6",
  chevron: "m8 5 7 7-7 7",
  close: "m6 6 12 12M6 18 18 6",
  menu: "M4 6h16M4 12h16M4 18h16",
};
export function Icon({ name, size = 20, style }: { name: IconName; size?: number; style?: CSSProperties }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}><path d={paths[name]} /></svg>;
}

export function Brand() {
  return <span className="brand"><span className="brand-mark" aria-hidden="true"><span /><span /><span /></span>clipseek<span className="brand-period">.</span></span>;
}
