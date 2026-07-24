import { AlertsApi, AuthApi, ChildrenApi, DefaultApi, Configuration, ResponseError } from "./index";
import { AlertWithExplanation, parseAlert, parseAlerts } from "../lib/parseAlert";

const PROXY_URL = 'http://localhost:8080';
const SESSION_ID_KEY = "tellmom_session_id";
const TOKEN_KEY = "tellmom_token";

let sessionId: string | null = localStorage.getItem(SESSION_ID_KEY);
let token: string | null = localStorage.getItem(TOKEN_KEY);

export const customFetch = async (input: RequestInfo | URL, init?: RequestInit, forward: boolean = true): Promise<Response> => {
  let urlStr = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  let appliedEncryption = false;
  let sessionIdUsed = sessionId;

  if (sessionId && forward) {
    if (urlStr.startsWith("/")) {
      const cleanPath = urlStr.replace(/^\/+/, "");
      urlStr = PROXY_URL + `/session/${sessionId}/forward/${cleanPath}`;

      const method = init?.method?.toUpperCase() || "GET";
      const hasBody = init?.body && typeof init.body === "string";

      if (hasBody && ["POST", "PUT", "PATCH"].includes(method)) {
        const aesKeyB64 = localStorage.getItem("tellmom_aes_key");
        const nonceBaseB64 = localStorage.getItem("tellmom_nonce_base");
        let seqStr = localStorage.getItem("tellmom_sequence");
        let seq = seqStr ? parseInt(seqStr, 10) : 1;

        if (aesKeyB64 && nonceBaseB64) {
          // Dynamic import to avoid circular dependency issues at the top level
          const { encryptMessage, base64ToBytes } = await import("../lib/security");
          const aesKey = base64ToBytes(aesKeyB64);
          const nonceBase = base64ToBytes(nonceBaseB64);

          const encrypted = await encryptMessage(seq, aesKey, nonceBase, init.body as string, sessionId);

          init = {
            ...init,
            body: JSON.stringify(encrypted),
            headers: {
              ...init.headers,
              "Content-Type": "application/json",
            },
          };

          appliedEncryption = true;
          localStorage.setItem("tellmom_sequence", (seq + 1).toString());
        }
      }
    }
  } else {
      urlStr = PROXY_URL + urlStr;
  }

  let response: Response;
  if (typeof input === "object" && "url" in input && !(input instanceof URL)) {
    response = await fetch(new Request(urlStr, input), init);
  } else {
    response = await fetch(urlStr, init);
  }

  if (appliedEncryption && response.ok && sessionIdUsed) {
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      const cloned = response.clone();
      try {
        const bodyJson = await cloned.json();
        if (bodyJson && typeof bodyJson.ciphertext === "string") {
          const aesKeyB64 = localStorage.getItem("tellmom_aes_key");
          const nonceBaseB64 = localStorage.getItem("tellmom_nonce_base");
          if (aesKeyB64 && nonceBaseB64) {
            const { decryptMessage, base64ToBytes } = await import("../lib/security");
            const aesKey = base64ToBytes(aesKeyB64);
            const nonceBase = base64ToBytes(nonceBaseB64);
            const aad = new TextEncoder().encode(`${sessionIdUsed}:${bodyJson.sequence}`);
            
            const decryptedString = await decryptMessage(aesKey, nonceBase, bodyJson, aad);
            return new Response(decryptedString, {
              status: response.status,
              statusText: response.statusText,
              headers: response.headers
            });
          }
        }
      } catch (e) {
        // Fallback to original response
      }
    }
  }

  return response;
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
