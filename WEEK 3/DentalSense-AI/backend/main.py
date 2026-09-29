import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router, seed_sample_data
from services.sentiment_service import sentiment_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load the model once
    logger.info("Starting up DentalSense AI Backend...")
    sentiment_service.load_model()
    # Seed the dashboard with the bundled synthetic dataset so data is
    # available immediately after a restart (no manual upload required).
    seed_sample_data()
    logger.info("Application startup complete.")
    yield
    # Shutdown: nothing to clean up
    logger.info("Shutting down DentalSense AI Backend.")

# Initialize FastAPI app
app = FastAPI(
    title="DentalSense AI Backend",
    description="Sentiment & Feedback Analysis Engine for a Boutique Dental Clinic",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)
