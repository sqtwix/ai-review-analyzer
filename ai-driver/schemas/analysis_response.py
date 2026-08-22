from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# ========================= Analysis Response Schemas =========================

# Эти схемы соответствуют контракту ответа от ai-driver к api-core.
# Содержат результаты работы цепочки ИИ-агентов по анализу отзывов и анкет.

class Distribution(BaseModel):
    low: float  # 1-3 %
    mid: float  # 4-7 %
    high: float  # 8-10 %

class NumericMetric(BaseModel):
    average: float
    median: float
    std_dev: float
    distribution: Distribution

class InvolvementMetric(BaseModel):
    detached_percent: float
    involved_percent: float
    yes_count: int
    no_count: int

class CourseStatistics(BaseModel):
    usefulness: NumericMetric
    practicality: NumericMetric
    accessibility: NumericMetric
    interaction: NumericMetric
    involvement: InvolvementMetric

class Section2KeyCriteria(BaseModel):
    usefulness_summary: str
    practicality_summary: str
    accessibility_summary: str
    interaction_summary: str
    involvement_summary: str

class AddedTopic(BaseModel):
    topic: str
    count: int

class Section3Suggestions(BaseModel):
    unwanted_topics: List[str]
    added_topics: List[AddedTopic]
    preferred_format_summary: str

class Section4Trajectory(BaseModel):
    further_implementation_needed: str
    student_selection_correction: str
    added_topics_recommendation: str
    hours_correction_needed: str
    format_correction_needed: str
    conclusions: List[str]

class AnalyticalReport(BaseModel):
    section1_general_info: str
    section2_key_criteria: Section2KeyCriteria
    section3_suggestions: Section3Suggestions
    section4_trajectory: Section4Trajectory

class TrendPoint(BaseModel):
    period: str
    usefulness_avg: float
    practicality_avg: float
    accessibility_avg: float
    interaction_avg: float
    involvement_avg: float

class DashboardData(BaseModel):
    correlation_matrix: Dict[str, Dict[str, float]]
    trend_data: List[TrendPoint] = Field(default_factory=list)
    trend_source: str = "unavailable"
    has_historical_periods: bool = False

class ValidationSummary(BaseModel):
    valid_count: int = 0
    missing_count: int = 0
    invalid_count: int = 0
    total_issues: int = 0

class EvidenceInfo(BaseModel):
    rows: List[str] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)
    coverage: Optional[float] = None

class CourseMetadata(BaseModel):
    education_form: Optional[str] = None
    teachers: List[str] = Field(default_factory=list)
    dates_confirmed: bool = False
    missing_fields: List[str] = Field(default_factory=list)

class CommentRegistryItem(BaseModel):
    question_id: str
    label: str
    non_empty_count: int
    coverage: float
    rows: List[str] = Field(default_factory=list)

class ProcessingLogItem(BaseModel):
    step: str
    status: str
    message: str

class TopicInfo(BaseModel):
    topic: str
    description: str
    frequency: int
    evidence: EvidenceInfo = Field(default_factory=EvidenceInfo)

class SentimentInfo(BaseModel):
    positive: float
    neutral: float
    negative: float

class ProblemInfo(BaseModel):
    problem: str
    frequency_percent: float
    severity: str
    evidence: EvidenceInfo = Field(default_factory=EvidenceInfo)

class QuoteInfo(BaseModel):
    quote: str
    frequency: int
    evidence: EvidenceInfo = Field(default_factory=EvidenceInfo)

class RecommendationInfo(BaseModel):
    target: str
    action_item: str
    priority: str
    evidence: EvidenceInfo = Field(default_factory=EvidenceInfo)

class TextAnalysis(BaseModel):
    top_topics: List[TopicInfo] = Field(default_factory=list)
    sentiment: SentimentInfo
    key_problems: List[ProblemInfo] = Field(default_factory=list)
    quotes: List[QuoteInfo] = Field(default_factory=list)
    recommendations: List[RecommendationInfo] = Field(default_factory=list)

class CourseAnalysisResult(BaseModel):
    course_name: str
    period: str
    students_count: int
    statistics: CourseStatistics
    position_distribution: Dict[str, int]
    preferred_formats: Dict[str, int]
    analytical_report: AnalyticalReport
    dashboard_data: DashboardData
    text_analysis: TextAnalysis
    validation_summary: ValidationSummary = Field(default_factory=ValidationSummary)
    score_counts: Dict[str, int] = Field(default_factory=dict)
    metadata: CourseMetadata = Field(default_factory=CourseMetadata)
    comment_registry: List[CommentRegistryItem] = Field(default_factory=list)
    processing_log: List[ProcessingLogItem] = Field(default_factory=list)
    quality_limitations: List[str] = Field(default_factory=list)

class AnalysisResponse(BaseModel):
    batch_id: str
    courses_analysis: List[CourseAnalysisResult]
