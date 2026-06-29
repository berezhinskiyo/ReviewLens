import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Logo } from "./Logo";
import {
  IconCard,
  IconGrid,
  IconLogout,
  IconPlus,
  IconUser,
} from "./icons";

const NAV = [
  { to: "/dashboard", label: "Дашборд", icon: IconGrid },
  { to: "/analyses/new", label: "Новый анализ", icon: IconPlus },
  { to: "/billing", label: "Тарифы", icon: IconCard },
  { to: "/settings", label: "Профиль", icon: IconUser },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const remaining =
    user?.analyses_remaining == null ? "∞" : user.analyses_remaining;
  const initial = (user?.display_name || user?.email || "U")[0].toUpperCase();

  const handleLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <div className="shell">
      <aside className="shell-side">
        <div className="shell-brand">
          <Logo light />
        </div>
        <nav className="shell-nav">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `shell-link${isActive ? " active" : ""}`
              }
            >
              <Icon />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="shell-spacer" />
        <div className="shell-user">
          <div className="shell-user-row">
            <div className="shell-avatar">{initial}</div>
            <div className="shell-user-meta">
              <strong>{user?.display_name || "Селлер"}</strong>
              <span>{user?.email}</span>
            </div>
          </div>
          <button className="shell-link" onClick={handleLogout} style={{ width: "100%" }}>
            <IconLogout />
            Выйти
          </button>
        </div>
      </aside>

      <div className="shell-main">
        <header className="shell-topbar">
          <span className="badge badge-primary">
            Тариф: {user?.plan} · осталось {remaining}
          </span>
          <NavLink to="/analyses/new" className="btn btn-primary btn-sm">
            <IconPlus /> Новый анализ
          </NavLink>
        </header>
        <main className="shell-content">{children}</main>
      </div>
    </div>
  );
}
