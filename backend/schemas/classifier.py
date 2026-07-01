from pydantic import BaseModel


class ClassifierResult(BaseModel):
    has_pedo: bool
    probability: float
