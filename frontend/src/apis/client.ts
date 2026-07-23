import { AlertsApi, AuthApi, ChildrenApi, DefaultApi, Configuration, ResponseError } from "./index";
import { AlertWithExplanation, parseAlert, parseAlerts } from "../lib/parseAlert";

const SESSION_ID_KEY = "tellmom_session_id";
const TOKEN_KEY = "tellmom_token";

let sessionId: string | null = localStorage.getItem(SESSION_ID_KEY);
let token: string | null = localStorage.getItem(TOKEN_KEY);

export const customFetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  let urlStr = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;

  if (sessionId) {
    if (urlStr.startsWith("/")) {
      const cleanPath = urlStr.replace(/^\/+/, "");
      urlStr = `/session/${sessionId}/forward/${cleanPath}`;
    }
  }

  if (typeof input === "object" && "url" in input && !(input instanceof URL)) {
    return fetch(new Request(urlStr, input), init);
  }

  return fetch(urlStr, init);
};

function createConfiguration(): Configuration {
  return new Configuration({
    basePath: "",
    accessToken: () => token ?? "",
    fetchApi: customFetch,
  });
}

function createApis() {
  const config = createConfiguration();
  return {
    auth: new AuthApi(config),
    children: new ChildrenApi(config),
    alerts: new AlertsApi(config),
    ingests: new DefaultApi(config),
  };
}

let apis = createApis();

export function getSessionId(): string | null {
  return sessionId;
}

export function setSessionId(value: string): void {
  sessionId = value;
  localStorage.setItem(SESSION_ID_KEY, value);
}

export function getToken(): string | null {
  return token;
}

export function setToken(value: string): void {
  token = value;
  localStorage.setItem(TOKEN_KEY, value);
  apis = createApis();
}

export function clearToken(): void {
  token = null;
  localStorage.removeItem(TOKEN_KEY);
  sessionId = null;
  localStorage.removeItem(SESSION_ID_KEY);
  apis = createApis();
}

export function getApis() {
  return apis;
}

async function authFetch(path: string, init?: RequestInit): Promise<Response> {
  const response = await customFetch(path, {
    ...init,
    headers: {
      ...init?.headers,
      Authorization: `Bearer ${token ?? ""}`,
    },
  });
  if (!response.ok) {
    throw new ResponseError(response, `Request failed (${response.status})`);
  }
  return response;
}

export async function fetchAlerts(): Promise<AlertWithExplanation[]> {
  const response = await authFetch("/api/alerts");
  return parseAlerts(await response.json());
}

export async function acknowledgeAlertWithExplanation(
  alertId: number,
): Promise<AlertWithExplanation> {
  const response = await authFetch(`/api/alerts/${alertId}/acknowledge`, {
    method: "POST",
  });
  return parseAlert(await response.json());
}
