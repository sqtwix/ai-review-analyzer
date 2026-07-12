from pydantic import BaseModel, Field
from typing import List, Optional

# ========================= Analysis Request Schemas =========================

# Эти схемы соответствуют контракту данных между api-core и ai-driver.
# Представляют полную структуру опроса: анкеты слушателей по курсам.

class SurveyResponse(BaseModel):
    student_id: str
    position_category: str
    usefulness_score: int
    practicality_score: int
    accessibility_score: int
    interaction_score: int
    preferred_format: str
    is_detached: bool
    
    motivation_comment: str
    usefulness_comment: str
    applied_skills_comment: str
    expected_effect: str
    expected_effect_reason: str
    topics_to_exclude_comment: str
    topics_to_add_comment: str
    practicality_comment: str
    practice_tuning_comment: str
    practice_change_comment: str
    accessibility_comment: str
    logic_sequence_reason: str
    ask_questions_comment: str
    ask_questions_reason: str
    detachment_reason_comment: str
    involvement_comment: str
    interaction_comment: str

class CourseSurvey(BaseModel):
    course_name: str
    period: str
    students_count: int
    responses: List[SurveyResponse]

class AnalysisRequest(BaseModel):
    batch_id: str
    courses: List[CourseSurvey]
