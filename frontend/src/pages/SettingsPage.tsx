import { useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import { resources } from "../api/resources";
import { useAuth } from "../context/AuthContext";

export function SettingsPage() {
  const { token, user, refreshMe } = useAuth();
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (user?.display_name) setName(user.display_name);
  }, [user?.display_name]);

  async function save() {
    setSaving(true);
    setSaved(false);
    try {
      await resources.updateProfile(name, token);
      await refreshMe();
      setSaved(true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <div className="page-head">
        <h1>Профиль</h1>
      </div>

      <div className="card" style={{ maxWidth: 560 }}>
        <div className="card-body stack">
          <div className="row">
            <div className="shell-avatar" style={{ width: 48, height: 48, fontSize: 18 }}>
              {(user?.display_name || user?.email || "U")[0].toUpperCase()}
            </div>
            <div>
              <strong>{user?.display_name || "Селлер"}</strong>
              <div className="muted" style={{ fontSize: 13 }}>
                {user?.email}
                {user?.email_verified ? " · подтверждён" : ""}
              </div>
            </div>
          </div>

          <div>
            <label className="field-label">Отображаемое имя</label>
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Как к вам обращаться"
            />
          </div>

          <div className="row">
            <button className="btn btn-primary" onClick={save} disabled={saving}>
              {saving ? "Сохраняем…" : "Сохранить"}
            </button>
            {saved && <span className="badge badge-success">Сохранено</span>}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
