from pydantic import BaseModel

class CandidateSummary(BaseModel):
    summary: str

class InterviewQuestions(BaseModel):
    questions: str

class EmailTemplate(BaseModel):
    template: str
    data: dict
