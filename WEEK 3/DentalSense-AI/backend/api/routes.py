from fastapi import APIRouter, UploadFile, File, HTTPException
from models.schemas import FeedbackRequest, FeedbackResult, BatchAnalysisResponse, AnalyticsResponse
from services.sentiment_service import sentiment_service
from services.theme_service import theme_service
from services.csv_service import csv_service
from services.analytics_service import analytics_service
import os
import logging
import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for MVP demo purposes
stored_feedback = []

# Path to the bundled synthetic dataset (../../data/sample_feedback.csv)
_SAMPLE_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "sample_feedback.csv",
)


def seed_sample_data():
    """Load the bundled synthetic dataset into memory at startup.

    This makes the dashboard show data immediately after a restart without
    requiring a manual CSV upload. All data is synthetic (see docs/PRIVACY.md).
    """
    global stored_feedback
    results, error = csv_service.process_file(_SAMPLE_CSV_PATH)
    if error:
        logger.warning(f"Could not seed sample data: {error}")
        return
    stored_feedback = results
    logger.info(f"Seeded {len(results)} synthetic feedback records from sample dataset.")


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "DentalSense AI Backend"}

@router.post("/api/analyze", response_model=FeedbackResult)
def analyze_feedback(request: FeedbackRequest):
    text = request.feedback.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Feedback text cannot be empty.")
        
    sentiment_data = sentiment_service.analyze(text)
    theme = theme_service.detect_theme(text)
    
    result = FeedbackResult(
        feedback=text,
        sentiment=sentiment_data['sentiment'],
        confidence=round(sentiment_data['confidence'] * 100, 2),
        theme=theme,
        analyzed_at=datetime.datetime.now().isoformat()
    )
    return result

@router.post("/api/analyze/batch", response_model=BatchAnalysisResponse)
async def analyze_batch(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")
        
    results, error = csv_service.process_csv(content)
    if error:
        raise HTTPException(status_code=400, detail=error)
        
    if not results:
        raise HTTPException(status_code=400, detail="No valid feedback found in the CSV.")
        
    # Update global state for demo
    global stored_feedback
    stored_feedback = results
        
    analytics = analytics_service.calculate_analytics(results)
    
    return BatchAnalysisResponse(
        total_processed=analytics["total_reviews"],
        positive_count=analytics["positive_count"],
        neutral_count=analytics["neutral_count"],
        negative_count=analytics["negative_count"],
        average_confidence=analytics["average_confidence"],
        results=results
    )

@router.get("/api/analytics", response_model=AnalyticsResponse)
def get_analytics():
    return analytics_service.calculate_analytics(stored_feedback)

@router.get("/api/feedback")
def get_feedback():
    return {"data": stored_feedback}

@router.get("/api/themes")
def get_themes():
    return {"themes": theme_service.get_available_themes()}
