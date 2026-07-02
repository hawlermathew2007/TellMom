from pydantic import BaseModel, Field


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
