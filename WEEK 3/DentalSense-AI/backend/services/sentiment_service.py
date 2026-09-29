from transformers import pipeline
import torch
import logging

logger = logging.getLogger(__name__)

class SentimentService:
    def __init__(self):
        self.model_name = "distilbert-base-uncased-finetuned-sst-2-english"
        self.pipeline = None
        self.neutral_threshold = 0.75 # Confidence below this is considered Neutral

    def load_model(self):
        if self.pipeline is None:
            try:
                logger.info(f"Loading sentiment model: {self.model_name}")
                self.pipeline = pipeline(
                    "sentiment-analysis", 
                    model=self.model_name,
                    device=-1 # CPU
                )
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise

    def analyze(self, text: str):
        if self.pipeline is None:
            self.load_model()
            
        # Truncate text to avoid model errors on very long inputs
        # DistilBERT handles up to 512 tokens. Roughly 1500 chars is safe.
        safe_text = text[:1500]
        
        try:
            result = self.pipeline(safe_text)[0]
            label = result['label']
            confidence = result['score']
            
            # Application-level Neutral logic
            if confidence < self.neutral_threshold:
                sentiment = "Neutral"
            else:
                sentiment = label.capitalize()
                
            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "raw_label": label
            }
        except Exception as e:
            logger.error(f"Error during sentiment analysis: {e}")
            return {
                "sentiment": "Neutral",
                "confidence": 0.0,
                "raw_label": "ERROR"
            }

sentiment_service = SentimentService()
