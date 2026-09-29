# Development Plan

This document outlines the systematic approach used to build DentalSense AI.

## Phase 1: Planning and Scaffolding
- Define the project scope and non-goals.
- Research professional SaaS patient feedback dashboards to inform UX.
- Scaffold the Git repository (`backend`, `frontend`, `docs`, `data`).

## Phase 2: Core AI and Backend
- Set up Python virtual environment and install dependencies (`FastAPI`, `transformers`, `torch`, `pandas`).
- Build `sentiment_service.py` wrapping the `distilbert-base-uncased-finetuned-sst-2-english` model.
- Implement the confidence-based "Neutral" fallback heuristic.
- Build the deterministic `theme_service.py` to map keywords.
- Create Pydantic schemas for strict I/O validation.
- Implement `csv_service.py` to handle pandas-based data ingesting.
- Connect the layers to a central FastAPI router.

## Phase 3: Analytics Engine
- Build `analytics_service.py` to ingest arrays of processed feedback.
- Calculate key metrics: total reviews, percentage breakdowns, and average confidence.
- Aggregate metrics into time-series buckets (for Volume and Sentiment over time).
- Generate automated English-language insights based on dynamic thresholds.

## Phase 4: Frontend Development
- Initialize React + Vite application.
- Install styling (`tailwindcss`) and charting (`recharts`) libraries.
- Build the Sidebar navigation layout (`react-router-dom`).
- Create `Dashboard.jsx` mapping backend analytics to Recharts components.
- Create `Analyzer.jsx` for single-string evaluation.
- Create `Batch.jsx` for CSV drag-and-drop / upload logic.
- Create `Explorer.jsx` for a filterable data grid.

## Phase 5: Testing & QA
- Construct synthetic dataset `sample_feedback.csv` containing varied edge cases.
- Write Pytest automated tests (`test_main.py`).
- Run backend integration tests.
- Perform manual UI testing across all React views.
- Handle frontend error states (e.g. invalid file uploads, API unavailability).

## Phase 6: Documentation & Handoff
- Draft all Markdown documentation (README, PRD, Scope, Arch, Limits, Privacy).
- Finalize portfolio-ready deployment instructions.
