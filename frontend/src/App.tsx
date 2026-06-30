import { useCallback, useEffect, useState } from "react";
import { apiFetch, clearToken, getToken, setToken } from "./apiClient";

type Parent = { id: number; email: string };
type Child = {
  id: number;
  platform: string;
  platform_user_id: string;
  display_name: string | null;
};
type Alert = {
  id: number;
  child_account_id: number;
  flagged_user_id: string;
  platform: string;
  server_id: string;
  message_preview: string;
  acknowledged: boolean;
  created_at: string;
};

const PLATFORMS = ["roblox", "discord", "minecraft"] as const;

export default function App() {
  const [token, setTokenState] = useState<string | null>(getToken());
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [parent, setParent] = useState<Parent | null>(null);
  const [children, setChildren] = useState<Child[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [liveAlert, setLiveAlert] = useState<Alert | null>(null);

  const [newPlatform, setNewPlatform] = useState<(typeof PLATFORMS)[number]>("roblox");
  const [newUserId, setNewUserId] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");

  const loadDashboard = useCallback(async () => {
    const me = await apiFetch<Parent>("/api/auth/me");
    const kids = await apiFetch<Child[]>("/api/children");
    const alertList = await apiFetch<Alert[]>("/api/alerts");
    setParent(me);
    setChildren(kids);
    setAlerts(alertList);
  }, []);

  useEffect(() => {
    if (!token) return;
    loadDashboard().catch((err: Error) => setError(err.message));
  }, [token, loadDashboard]);

  useEffect(() => {
    if (!token) return;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(
      `${protocol}://${window.location.host}/api/alerts/ws?token=${encodeURIComponent(token)}`,
    );
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data) as Alert;
      setLiveAlert(payload);
      setAlerts((prev) => [payload, ...prev]);
    };
    return () => ws.close();
  }, [token]);

  async function handleAuth(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      if (mode === "register") {
        await apiFetch<Parent>("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
      }
      const { access_token } = await apiFetch<{ access_token: string }>(
        "/api/auth/login",
        { method: "POST", body: JSON.stringify({ email, password }) },
      );
      setToken(access_token);
      setTokenState(access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Auth failed");
    }
  }

  async function addChild(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const child = await apiFetch<Child>("/api/children", {
        method: "POST",
        body: JSON.stringify({
          platform: newPlatform,
          platform_user_id: newUserId,
          display_name: newDisplayName || null,
        }),
      });
      setChildren((prev) => [child, ...prev]);
      setNewUserId("");
      setNewDisplayName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add child");
    }
  }

  async function removeChild(id: number) {
    await apiFetch<void>(`/api/children/${id}`, { method: "DELETE" });
    setChildren((prev) => prev.filter((c) => c.id !== id));
  }

  async function acknowledgeAlert(id: number) {
    const updated = await apiFetch<Alert>(`/api/alerts/${id}/acknowledge`, {
      method: "POST",
    });
    setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
    if (liveAlert?.id === id) setLiveAlert(null);
  }

  function logout() {
    clearToken();
    setTokenState(null);
    setParent(null);
    setChildren([]);
    setAlerts([]);
  }

  if (!token) {
    return (
      <div className="page">
        <h1>TellMom</h1>
        <form className="card" onSubmit={handleAuth}>
          <h2>{mode === "login" ? "Parent login" : "Parent register"}</h2>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password (min 8 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
          {error && <p className="error">{error}</p>}
          <button type="submit">{mode === "login" ? "Login" : "Register"}</button>
          <button
            type="button"
            className="link"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Need an account? Register" : "Have an account? Login"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="page">
      <header>
        <h1>TellMom Dashboard</h1>
        <div>
          <span>{parent?.email}</span>
          <button onClick={logout}>Logout</button>
        </div>
      </header>

      {liveAlert && (
        <div className="banner">
          <strong>Live alert:</strong> flagged user {liveAlert.flagged_user_id} in{" "}
          {liveAlert.platform} server {liveAlert.server_id}
          <button onClick={() => acknowledgeAlert(liveAlert.id)}>Acknowledge</button>
        </div>
      )}

      {error && <p className="error">{error}</p>}

      <section className="card">
        <h2>Registered children</h2>
        <form className="inline-form" onSubmit={addChild}>
          <select
            value={newPlatform}
            onChange={(e) => setNewPlatform(e.target.value as (typeof PLATFORMS)[number])}
          >
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <input
            placeholder="Platform user ID"
            value={newUserId}
            onChange={(e) => setNewUserId(e.target.value)}
            required
          />
          <input
            placeholder="Display name (optional)"
            value={newDisplayName}
            onChange={(e) => setNewDisplayName(e.target.value)}
          />
          <button type="submit">Add</button>
        </form>
        <ul>
          {children.map((child) => (
            <li key={child.id}>
              <span>
                {child.display_name ?? child.platform_user_id} ({child.platform})
              </span>
              <button onClick={() => removeChild(child.id)}>Remove</button>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Alerts</h2>
        <ul>
          {alerts.map((alert) => (
            <li key={alert.id} className={alert.acknowledged ? "muted" : ""}>
              <div>
                <strong>{alert.platform}</strong> / server {alert.server_id}
              </div>
              <div>Flagged: {alert.flagged_user_id}</div>
              <div>{alert.message_preview}</div>
              {!alert.acknowledged && (
                <button onClick={() => acknowledgeAlert(alert.id)}>Acknowledge</button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
