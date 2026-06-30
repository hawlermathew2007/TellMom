export type StageAssessment = {
  status: string;
  confidence: string;
  evidence: string[];
  reasoning: string;
};

export type OverallAssessment = {
  observedStageCount: number;
  stageOrder: string[];
  behavioralProgression: string;
  uncertainties: string;
  summary: string;
};

export type GroomingAnalysis = {
  victimSelection: StageAssessment;
  accessRelationshipBuilding: StageAssessment;
  trustDevelopment: StageAssessment;
  isolation: StageAssessment;
  boundaryTesting: StageAssessment;
  desensitization: StageAssessment;
  maintainingControl: StageAssessment;
  overallAssessment: OverallAssessment;
};

function parseStage(raw: Record<string, unknown>): StageAssessment {
  return {
    status: String(raw.status ?? ""),
    confidence: String(raw.confidence ?? ""),
    evidence: Array.isArray(raw.evidence) ? raw.evidence.map(String) : [],
    reasoning: String(raw.reasoning ?? ""),
  };
}

export function groomingFromJSON(raw: unknown): GroomingAnalysis | null {
  if (!raw || typeof raw !== "object") return null;
  const data = raw as Record<string, unknown>;
  const overall = data.overall_assessment ?? data.overallAssessment;
  if (!overall || typeof overall !== "object") return null;
  const o = overall as Record<string, unknown>;

  return {
    victimSelection: parseStage(
      (data.victim_selection ?? data.victimSelection) as Record<string, unknown>,
    ),
    accessRelationshipBuilding: parseStage(
      (data.access_relationship_building ??
        data.accessRelationshipBuilding) as Record<string, unknown>,
    ),
    trustDevelopment: parseStage(
      (data.trust_development ?? data.trustDevelopment) as Record<string, unknown>,
    ),
    isolation: parseStage((data.isolation ?? {}) as Record<string, unknown>),
    boundaryTesting: parseStage(
      (data.boundary_testing ?? data.boundaryTesting) as Record<string, unknown>,
    ),
    desensitization: parseStage(
      (data.desensitization ?? {}) as Record<string, unknown>,
    ),
    maintainingControl: parseStage(
      (data.maintaining_control ?? data.maintainingControl) as Record<string, unknown>,
    ),
    overallAssessment: {
      observedStageCount: Number(o.observed_stage_count ?? o.observedStageCount ?? 0),
      stageOrder: (() => {
        const order = o.stage_order ?? o.stageOrder;
        return Array.isArray(order) ? order.map(String) : [];
      })(),
      behavioralProgression: String(
        o.behavioral_progression ?? o.behavioralProgression ?? "",
      ),
      uncertainties: String(o.uncertainties ?? ""),
      summary: String(o.summary ?? ""),
    },
  };
}

export const STAGE_LABELS: Record<keyof Omit<GroomingAnalysis, "overallAssessment">, string> =
  {
    victimSelection: "Victim Selection",
    accessRelationshipBuilding: "Access & Relationship Building",
    trustDevelopment: "Trust Development",
    isolation: "Isolation",
    boundaryTesting: "Boundary Testing",
    desensitization: "Desensitization",
    maintainingControl: "Maintaining Control",
  };

export function statusClass(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized === "observed") return "status-observed";
  if (normalized === "possible") return "status-possible";
  return "status-none";
}
