// Лёгкие inline-иконки (line, 24x24), чтобы не тянуть icon-библиотеку.
type P = { className?: string };
const base = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export const IconGrid = (p: P) => (
  <svg {...base} {...p}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /></svg>
);
export const IconPlus = (p: P) => (
  <svg {...base} {...p}><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
);
export const IconCard = (p: P) => (
  <svg {...base} {...p}><rect x="2" y="5" width="20" height="14" rx="2" /><line x1="2" y1="10" x2="22" y2="10" /></svg>
);
export const IconUser = (p: P) => (
  <svg {...base} {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 4-6 8-6s8 2 8 6" /></svg>
);
export const IconStar = (p: P) => (
  <svg {...base} {...p} fill="currentColor" stroke="none"><path d="M12 2l2.9 6.3 6.9.6-5.2 4.6 1.6 6.8L12 17.8 5.8 20.9l1.6-6.8L2.2 9.5l6.9-.6z" /></svg>
);
export const IconArrow = (p: P) => (
  <svg {...base} {...p}><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
);
export const IconBack = (p: P) => (
  <svg {...base} {...p}><line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" /></svg>
);
export const IconThumbDown = (p: P) => (
  <svg {...base} {...p}><path d="M17 2h2a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-2" /><path d="M17 13V2H8.5L5 4 3 12l2 2h6l-1 5a2 2 0 0 0 2 2l5-8" /></svg>
);
export const IconThumbUp = (p: P) => (
  <svg {...base} {...p}><path d="M7 22H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h2" /><path d="M7 11V22h8.5L19 20l2-8-2-2h-6l1-5a2 2 0 0 0-2-2l-5 8" /></svg>
);
export const IconBulb = (p: P) => (
  <svg {...base} {...p}><path d="M9 18h6" /><path d="M10 22h4" /><path d="M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.1V18h6v-1.2c0-.8.4-1.6 1-2.1A7 7 0 0 0 12 2z" /></svg>
);
export const IconLogout = (p: P) => (
  <svg {...base} {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
);
