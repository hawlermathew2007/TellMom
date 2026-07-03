import { AlertResponse, AlertResponseFromJSON } from "../apis";
import { NewlyDetectedStage } from "../apis/models/NewlyDetectedStage";

export type AlertWithExplanation = AlertResponse & {
  detectedStages: NewlyDetectedStage[];
};

export function parseAlert(json: unknown): AlertWithExplanation {
  const alert = AlertResponseFromJSON(json);
  const raw = json as Record<string, unknown>;
  
  // Extract newly detected stages if present in payload (e.g. from WebSocket or API responses)
  const rawStages = raw.detected_stages ?? raw.detectedStages ?? [];
  const detectedStages: NewlyDetectedStage[] = Array.isArray(rawStages) 
    ? rawStages.map((s: any) => ({
        stage: String(s.stage ?? s),
        confidence: String(s.confidence ?? "Medium"),
        messageId: Number(s.message_id ?? s.messageId ?? 0)
      }))
    : [];

  return {
    ...alert,
    detectedStages,
  };
}

export function parseAlerts(json: unknown): AlertWithExplanation[] {
  if (!Array.isArray(json)) return [];
  return json.map(parseAlert);
}
