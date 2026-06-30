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
