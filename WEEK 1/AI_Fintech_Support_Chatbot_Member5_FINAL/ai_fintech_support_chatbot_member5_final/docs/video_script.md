# 5–10 Minute Mandatory Video Speaking Guide

Explain naturally in your own words rather than reading every line.

## 0:00–0:40 — Introduction
"Assalam-o-Alaikum. This is my individual contribution to our AI Customer Support Chatbot for a Fintech App. I am Member 5 and my assigned primary technology is Hugging Face Transformers. My module identifies the customer's support intent and routes it to a safe predefined response."

## 0:40–1:30 — Project structure
Show the project folder.

Mention:
- `app/main.py` — FastAPI web/API application
- `app/model_service.py` — Hugging Face AI logic
- `app/config.py` — intents and safe responses
- `data/test_cases.csv` — labelled test set
- `run_tests.py` — automated evaluation
- `static/` — browser interface

## 1:30–2:30 — Hugging Face concept
Show `model_service.py`.

Say:
"Hugging Face Transformers provides pretrained NLP models. I used zero-shot classification because I can define support labels at runtime without first training a classifier on a large dataset."

Show the `pipeline("zero-shot-classification")` code.

## 2:30–3:30 — Processing logic
Explain:
1. User enters a support question.
2. Input is cleaned and validated.
3. The Transformer compares it with candidate intents.
4. The top intent and confidence are returned.
5. Low confidence triggers a fallback.
6. High confidence routes to a controlled response.

## 3:30–5:00 — Live browser demo
Run:
`uvicorn app.main:app --reload`

Open:
`http://127.0.0.1:8000`

Try:
- My bank transfer is still pending
- The ATM charged me but did not give me cash
- I forgot my password and cannot log in
- Why was I charged an extra service fee?

Point out:
- Predicted intent
- Confidence
- Safe response

## 5:00–5:40 — Error handling
Try an empty message or explain the backend validation.

Say:
"I added validation for empty, too-short, and overly long input. API-level model errors are also caught so the application returns a controlled error instead of crashing."

## 5:40–6:50 — Testing
Run:
`python run_tests.py`

Open:
`data/test_results.csv`

Say:
"I created 15 labelled test cases, which is more than the required ten. The test script compares expected and predicted intent and records the confidence and PASS or FAIL result."

If any test fails, say what actually happened. Do not hide it.

## 6:50–7:40 — Fintech safety
Say:
"Because this is a fintech project, the chatbot never asks for passwords, PINs, CVVs, OTPs, or real banking credentials. It also does not access accounts or execute transactions. The Transformer is used for intent understanding while the response is controlled."

## 7:40–8:30 — What I learned
Mention:
- Hugging Face pipelines
- Zero-shot classification
- Confidence scores
- FastAPI
- Input validation
- Testing NLP predictions
- Safe chatbot architecture

## Closing
"This completes my Member 5 contribution. The API can later be connected to our group's main frontend or backend."
