from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# リクエストスキーマ
class QAGenerateRequest(BaseModel):
    lecture_id: int
    difficulty: DifficultyLevel
    num_questions: int = 5


class AnswerSubmissionRequest(BaseModel):
    qa_id: int
    user_id: str
    answer_text: str


# レスポンススキーマ
class LectureMaterialResponse(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True


class QAResponse(BaseModel):
    id: int
    lecture_id: int
    question: str
    answer: str
    difficulty: DifficultyLevel
    generated_at: datetime
    
    class Config:
        from_attributes = True


class AnswerResponse(BaseModel):
    id: int
    qa_id: int
    user_id: str
    answer_text: str
    is_correct: bool
    answered_at: datetime
    
    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    lecture_id: int
    total_questions: int
    total_answers: int
    correct_answers: int
    accuracy_rate: float
    difficulty_breakdown: dict 