import { AlertsApi, AuthApi, ChildrenApi, Configuration, ResponseError } from "./index";
import { AlertWithExplanation, parseAlert, parseAlerts } from "../lib/parseAlert";

const TOKEN_KEY = "tellmom_token";

let token: string | null = localStorage.getItem(TOKEN_KEY);

function createConfiguration(): Configuration {
  return new Configuration({
    basePath: "",
    accessToken: () => token ?? "",
  });
}

function createApis() {
  const config = createConfiguration();
  return {
    auth: new AuthApi(config),
    children: new ChildrenApi(config),
    alerts: new AlertsApi(config),
  };
}

let apis = createApis();

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
  apis = createApis();
}

export function getApis() {
  return apis;
}

async function authFetch(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(path, {
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
