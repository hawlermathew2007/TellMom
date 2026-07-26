import { AlertResponse } from "../apis";
import { NewlyDetectedStage } from "../apis/models/NewlyDetectedStage";

export type AlertWithExplanation = AlertResponse & {
    detectedStages: NewlyDetectedStage[];
};

export function parseAlert(alert: AlertResponse): AlertWithExplanation {
    // Extract newly detected stages if present in payload (e.g. from WebSocket or API responses)
    const rawStages = alert.detectedStages ?? [];
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
