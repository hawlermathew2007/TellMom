import { AlertResponse, AlertResponseFromJSON } from "../apis";
import { GroomingAnalysis, groomingFromJSON } from "../types/grooming";

export type AlertWithExplanation = AlertResponse & {
  explanation: GroomingAnalysis | null;
};

export function parseAlert(json: unknown): AlertWithExplanation {
  const alert = AlertResponseFromJSON(json);
  const raw = json as Record<string, unknown>;
  return {
    ...alert,
    explanation: groomingFromJSON(raw.explanation),
  };
}

export function parseAlerts(json: unknown): AlertWithExplanation[] {
  if (!Array.isArray(json)) return [];
  return json.map(parseAlert);
}
