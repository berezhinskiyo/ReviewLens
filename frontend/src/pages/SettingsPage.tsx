import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { resources } from "../api/resources";
import { useAuth } from "../context/AuthContext";

export function SettingsPage() {
  const { token, user, refreshMe, logout } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);

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

  async function exportData() {
    setExporting(true);
    try {
      const data = await resources.dataExport(token);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "reviewlens-data-export.json";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  async function deleteAccount() {
    const ok = window.confirm(
      "Удалить аккаунт? Будут безвозвратно удалены ваши анализы и персональные данные. " +
        "Это действие нельзя отменить."
    );
    if (!ok) return;
    setDeleting(true);
    try {
      await resources.deleteAccount(token);
      await logout();
      navigate("/", { replace: true });
    } finally {
      setDeleting(false);
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

      {/* 152-ФЗ: права субъекта персональных данных */}
      <div className="card" style={{ maxWidth: 560, marginTop: 16 }}>
        <div className="card-body stack">
          <h3>Данные и приватность</h3>
          <p className="muted" style={{ fontSize: 14 }}>
            Вы можете выгрузить все свои данные или удалить аккаунт вместе с
            персональными данными (право на доступ и удаление, 152-ФЗ).
          </p>
          <div className="row">
            <button className="btn btn-secondary" onClick={exportData} disabled={exporting}>
              {exporting ? "Готовим файл…" : "Выгрузить мои данные"}
            </button>
            <button className="btn btn-danger" onClick={deleteAccount} disabled={deleting}>
              {deleting ? "Удаляем…" : "Удалить аккаунт"}
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
