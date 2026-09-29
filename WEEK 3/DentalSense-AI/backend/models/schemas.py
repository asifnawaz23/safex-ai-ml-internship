from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class FeedbackRequest(BaseModel):
    feedback: str = Field(..., description="The feedback text to analyze")

class FeedbackResult(BaseModel):
    id: Optional[str] = None
    date: Optional[str] = None
    feedback: str
    sentiment: str
    confidence: float
    theme: str
    analyzed_at: str

class BatchAnalysisResponse(BaseModel):
    total_processed: int
    positive_count: int
    neutral_count: int
    negative_count: int
    average_confidence: float
    results: List[FeedbackResult]

class AnalyticsResponse(BaseModel):
    total_reviews: int
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_percentage: float
    negative_percentage: float
    neutral_percentage: float
    average_confidence: float
    theme_counts: Dict[str, int]
    negative_theme_counts: Dict[str, int]
    feedback_volume_over_time: Dict[str, int]
    sentiment_over_time: Dict[str, Dict[str, int]]
    insights: List[str]
