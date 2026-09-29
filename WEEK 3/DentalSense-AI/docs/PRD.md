# Product Requirements Document (PRD)

## Product Overview
DentalSense AI is an intelligent feedback analysis platform designed specifically for boutique dental clinics. It processes patient reviews and feedback data to automatically detect sentiment, quantify confidence, and extract categorical themes.

## Problem Statement
Boutique dental clinics pride themselves on exceptional patient experiences. However, reading and categorizing feedback manually is inefficient and prone to subjective bias. Clinics need an automated way to digest bulk feedback and quickly visualize operational trends.

## Goals
- Automate sentiment extraction from patient reviews.
- Categorize feedback into actionable clinic themes (e.g., Staff, Wait Time, Cleanliness).
- Provide a clear, professional visual dashboard for clinic managers.
- Reduce manual review processing time from hours to seconds.

## Non-goals
- This system will not handle real medical records or PHI.
- This system will not provide medical or clinical advice.
- This system will not diagnose dental conditions.

## Target Users
- Clinic Managers
- Lead Dentists
- Patient Experience Coordinators

## User Stories
- As a clinic manager, I want to upload a CSV of last month's feedback so that I can see an instant breakdown of patient satisfaction.
- As a dentist, I want to filter feedback specifically related to "Treatment" to ensure clinical service quality is perceived positively.
- As an administrator, I want to paste a single new review into an analyzer tool to quickly assess its tone before responding to the patient.

## AI Architecture
- Uses Hugging Face Transformers (`distilbert-base-uncased-finetuned-sst-2-english`) running locally on CPU.
- Uses rule-based lexical matching for theme classification to ensure complete explainability.
- Implements an application-layer "Neutral" threshold for ambiguous feedback.

## Privacy Requirements
No real patient data is permitted. The system processes synthetic or fully anonymized textual feedback only. It does not ingest demographic identifiers.
