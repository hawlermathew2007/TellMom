import {
  GroomingAnalysis,
  STAGE_LABELS,
  statusClass,
} from "../types/grooming";

type Props = {
  analysis: GroomingAnalysis;
};

function StageRow({
  label,
  stage,
}: {
  label: string;
  stage: GroomingAnalysis[keyof Omit<GroomingAnalysis, "overallAssessment">];
}) {
  return (
    <details className="grooming-stage">
      <summary>
        <span className="stage-label">{label}</span>
        <span className={`stage-status ${statusClass(stage.status)}`}>
          {stage.status}
        </span>
        <span className="stage-confidence">{stage.confidence}</span>
      </summary>
      {stage.evidence.length > 0 && (
        <div className="stage-evidence">
          <strong>Evidence</strong>
          <ul>
            {stage.evidence.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {stage.reasoning && (
        <p className="stage-reasoning">
          <strong>Reasoning:</strong> {stage.reasoning}
        </p>
      )}
    </details>
  );
}

export default function GroomingExplanation({ analysis }: Props) {
  const { overallAssessment } = analysis;
  const stages = Object.entries(STAGE_LABELS) as [
    keyof Omit<GroomingAnalysis, "overallAssessment">,
    string,
  ][];

  return (
    <div className="grooming-explanation">
      <h3>LLM Grooming Analysis</h3>
      <div className="overall-assessment">
        <p>
          <strong>Observed stages:</strong> {overallAssessment.observedStageCount}
        </p>
        {overallAssessment.stageOrder.length > 0 && (
          <p>
            <strong>Stage order:</strong> {overallAssessment.stageOrder.join(" → ")}
          </p>
        )}
        {overallAssessment.behavioralProgression && (
          <p>
            <strong>Progression:</strong> {overallAssessment.behavioralProgression}
          </p>
        )}
        {overallAssessment.summary && (
          <p>
            <strong>Summary:</strong> {overallAssessment.summary}
          </p>
        )}
        {overallAssessment.uncertainties && (
          <p className="uncertainties">
            <strong>Uncertainties:</strong> {overallAssessment.uncertainties}
          </p>
        )}
      </div>
      <div className="grooming-stages">
        {stages.map(([key, label]) => (
          <StageRow key={key} label={label} stage={analysis[key]} />
        ))}
      </div>
    </div>
  );
}
