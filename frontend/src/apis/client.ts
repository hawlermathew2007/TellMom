import { AlertsApi, AuthApi, ChildrenApi, Configuration } from "./index";

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
