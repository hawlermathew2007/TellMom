import { useCallback, useEffect, useState } from "react";
import {
  ChatPlatform,
  ChildAccountResponse,
  ParentResponse,
  ResponseError,
} from "./apis";
import {
  acknowledgeAlertWithExplanation,
  clearToken,
  fetchAlerts,
  getApis,
  getToken,
  setToken,
} from "./apis/client";
import GroomingExplanation from "./components/GroomingExplanation";
import { AlertWithExplanation, parseAlert } from "./lib/parseAlert";

const PLATFORMS = [
  ChatPlatform.Roblox,
  ChatPlatform.Discord,
  ChatPlatform.Minecraft,
] as const;

function apiErrorMessage(err: unknown): string {
  if (err instanceof ResponseError) {
    return err.message || `Request failed (${err.response.status})`;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Request failed";
}

export default function App() {
  const [token, setTokenState] = useState<string | null>(getToken());
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [parent, setParent] = useState<ParentResponse | null>(null);
  const [children, setChildren] = useState<ChildAccountResponse[]>([]);
  const [alerts, setAlerts] = useState<AlertWithExplanation[]>([]);
  const [liveAlert, setLiveAlert] = useState<AlertWithExplanation | null>(null);
  const [expandedExplanationId, setExpandedExplanationId] = useState<number | null>(
    null,
  );

  const [newPlatform, setNewPlatform] = useState<(typeof PLATFORMS)[number]>(
    ChatPlatform.Roblox,
  );
  const [newUserId, setNewUserId] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");

  const loadDashboard = useCallback(async () => {
    const { auth, children: childrenApi } = getApis();
    const [me, kids, alertList] = await Promise.all([
      auth.getMeApiAuthMeGet(),
      childrenApi.listChildrenApiChildrenGet(),
      fetchAlerts(),
    ]);
    setParent(me);
    setChildren(kids);
    setAlerts(alertList);
  }, []);

  useEffect(() => {
    if (!token) return;
    loadDashboard().catch((err: unknown) => setError(apiErrorMessage(err)));
  }, [token, loadDashboard]);

  useEffect(() => {
    if (!token) return;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(
      `${protocol}://${window.location.host}/api/alerts/ws?token=${encodeURIComponent(token)}`,
    );
    ws.onmessage = (event) => {
      const alert = parseAlert(JSON.parse(event.data));
      setLiveAlert(alert);
      setAlerts((prev) => [alert, ...prev]);
      if (alert.explanation) {
        setExpandedExplanationId(alert.id);
      }
    };
    return () => ws.close();
  }, [token]);

  async function handleAuth(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const { auth } = getApis();
      if (mode === "register") {
        await auth.registerParentApiAuthRegisterPost({
          parentRegister: { email, password },
        });
      }
      const { accessToken } = await auth.loginParentApiAuthLoginPost({
        parentLogin: { email, password },
      });
      setToken(accessToken);
      setTokenState(accessToken);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  async function addChild(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const child = await getApis().children.createChildApiChildrenPost({
        childAccountCreate: {
          platform: newPlatform,
          platformUserId: newUserId,
          displayName: newDisplayName || null,
        },
      });
      setChildren((prev) => [child, ...prev]);
      setNewUserId("");
      setNewDisplayName("");
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  async function removeChild(id: number) {
    await getApis().children.deleteChildApiChildrenChildIdDelete({ childId: id });
    setChildren((prev) => prev.filter((c) => c.id !== id));
  }

  async function acknowledgeAlert(id: number) {
    const updated = await acknowledgeAlertWithExplanation(id);
    setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
    if (liveAlert?.id === id) setLiveAlert(null);
  }

  function logout() {
    clearToken();
    setTokenState(null);
    setParent(null);
    setChildren([]);
    setAlerts([]);
    setExpandedExplanationId(null);
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
          <strong>Live alert:</strong> flagged conversation in{" "}
          {liveAlert.platform} server {liveAlert.serverId}
          <button onClick={() => acknowledgeAlert(liveAlert.id)}>Acknowledge</button>
        </div>
      )}

      {error && <p className="error">{error}</p>}

      <section className="card">
        <h2>Registered children</h2>
        <form className="inline-form" onSubmit={addChild}>
          <select
            value={newPlatform}
            onChange={(e) =>
              setNewPlatform(e.target.value as (typeof PLATFORMS)[number])
            }
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
                {child.displayName ?? child.platformUserId} ({child.platform})
              </span>
              <button onClick={() => removeChild(child.id)}>Remove</button>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Alerts</h2>
        <ul className="alert-list">
          {alerts.map((alert) => (
            <li key={alert.id} className={alert.acknowledged ? "muted" : ""}>
              <div className="alert-header">
                <div>
                  <div>
                    <strong>{alert.platform}</strong> / server {alert.serverId}
                  </div>
                  <div>{alert.messagePreview}</div>
                </div>
                <div className="alert-actions">
                  {alert.explanation && (
                    <button
                      type="button"
                      className="secondary"
                      onClick={() =>
                        setExpandedExplanationId((current) =>
                          current === alert.id ? null : alert.id,
                        )
                      }
                    >
                      {expandedExplanationId === alert.id
                        ? "Hide analysis"
                        : "View analysis"}
                    </button>
                  )}
                  {!alert.acknowledged && (
                    <button onClick={() => acknowledgeAlert(alert.id)}>
                      Acknowledge
                    </button>
                  )}
                </div>
              </div>
              {alert.explanation && expandedExplanationId === alert.id && (
                <GroomingExplanation analysis={alert.explanation} />
              )}
              {!alert.explanation && !alert.acknowledged && (
                <p className="explanation-pending">
                  Grooming analysis unavailable (Groq not configured or generation failed).
                </p>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
