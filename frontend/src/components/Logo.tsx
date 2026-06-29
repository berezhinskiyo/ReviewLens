// Логотип ReviewLens: «лупа над карточкой отзыва» в градиентном бейдже.
export function Logo({ light = false }: { light?: boolean }) {
  return (
    <span className={`brand-logo${light ? " light" : ""}`}>
      <span className="brand-mark" aria-hidden>
        <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="rl-grad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#7c3aed" />
              <stop offset="1" stopColor="#f59e0b" />
            </linearGradient>
          </defs>
          <rect width="40" height="40" rx="12" fill="url(#rl-grad)" />
          {/* карточка с «отзывами» */}
          <rect x="9" y="10" width="15" height="20" rx="3" fill="#ffffff" fillOpacity="0.92" />
          <rect x="12" y="14" width="9" height="2" rx="1" fill="#7c3aed" fillOpacity="0.55" />
          <rect x="12" y="18" width="6" height="2" rx="1" fill="#7c3aed" fillOpacity="0.35" />
          {/* лупа */}
          <circle cx="26" cy="24" r="6.2" fill="none" stroke="#16131f" strokeWidth="2.4" />
          <line x1="30.4" y1="28.4" x2="33.6" y2="31.6" stroke="#16131f" strokeWidth="2.6" strokeLinecap="round" />
        </svg>
      </span>
      <span className="brand-text">
        Review<span className="brand-text-accent">Lens</span>
      </span>
    </span>
  );
}
