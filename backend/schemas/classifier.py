from pydantic import BaseModel


class ClassifierResult(BaseModel):
    user_id: str
    is_pedo: bool
