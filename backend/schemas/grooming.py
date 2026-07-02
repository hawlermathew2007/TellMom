from pydantic import BaseModel, Field


class StageAssessment(BaseModel):
    status: str = Field(description="Observed | Possible | Not Observed")
    confidence: str = Field(description="High | Medium | Low")
    evidence: list[str] = Field(default_factory=list)
    reasoning: str = ""


class OverallAssessment(BaseModel):
    observed_stage_count: int = 0
    stage_order: list[str] = Field(default_factory=list)
    behavioral_progression: str = ""
    uncertainties: str = ""
    summary: str = ""


class GroomingAnalysis(BaseModel):
    victim_selection: StageAssessment
    access_relationship_building: StageAssessment
    trust_development: StageAssessment
    isolation: StageAssessment
    boundary_testing: StageAssessment
    desensitization: StageAssessment
    maintaining_control: StageAssessment
    overall_assessment: OverallAssessment


class NewlyDetectedStage(BaseModel):
    """A newly detected grooming stage with minimal evidence."""

    stage: str = Field(description="The stage name that was detected")
    confidence: str = Field(description="High | Medium | Low")
    message_id: int = Field(description="The ChatMessage ID with strongest evidence")


class IncrementalAnalysisResponse(BaseModel):
    """Response from incremental grooming analysis."""

    new_stages: list[NewlyDetectedStage] = Field(
        default_factory=list, description="Newly detected stages in this analysis"
    )
