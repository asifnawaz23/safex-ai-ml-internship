# Technical Write-up — Member 5

## Project
**AI Customer Support Chatbot for a Fintech App**

## Assigned role
**Member 5 — Individual Contributor**

## Primary technology
**Hugging Face Transformers**

## Mini-plan
My responsibility is the intent-understanding component of the fintech chatbot. I use a pretrained Hugging Face Transformer to classify incoming support messages into common fintech categories. After classification, the prediction is routed to a controlled response template. I also validate invalid input and evaluate the module using a labelled set of more than ten test questions.

## Technical approach
I selected **zero-shot classification** because the prototype has a small manually created test dataset and does not require training a model from scratch. The application supplies a list of support categories to the pretrained model at runtime.

The processing flow is:

1. Receive a customer message from the browser or API.
2. Normalize and validate the text.
3. Pass the message and candidate intent labels to the Hugging Face zero-shot pipeline.
4. Read the highest-scoring predicted label and confidence score.
5. Check the score against a confidence threshold.
6. Route high-confidence predictions to a predefined support response.
7. Use a generic fallback for uncertain queries.

## Model
The prototype is configured with:

`MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33`

The Transformers pipeline is loaded only once using Python caching, which avoids reloading the model for every request.

## Why response templates?
For a fintech prototype, unrestricted generation can invent account balances, transaction states, fees, policies, or other sensitive information. Therefore, Hugging Face is used for language understanding while the final user-facing response comes from controlled templates.

## Error handling
The module rejects:
- Empty messages
- Messages shorter than three characters
- Messages longer than 500 characters

It also catches model-loading and inference errors at API level and returns a clear service error instead of crashing the application.

## Dataset and testing
I created 15 labelled examples covering:
- Card issues
- ATM withdrawals
- Transfers
- Account access
- Refunds
- Fees
- Verification
- Deposits
- General account questions

`run_tests.py` evaluates each example, compares expected and predicted intent, records confidence, and saves PASS/FAIL results into `data/test_results.csv`.

## Security and safety decisions
The chatbot does not ask for or process passwords, PINs, CVVs, OTPs, recovery codes, or real banking credentials. It does not perform transactions or access real accounts.

## What I learned
This task helped me understand:
- Hugging Face `pipeline()`
- Pretrained Transformer models
- Zero-shot classification
- Candidate labels
- Confidence scores
- Threshold-based fallback
- NLP evaluation
- FastAPI integration
- Input validation
- Controlled-response design for a sensitive domain

## Limitations
The test dataset is intentionally small and the model is not fine-tuned on proprietary fintech conversations. Similar intents can be misclassified. Production deployment would require larger anonymized datasets, security controls, monitoring, human escalation, policy validation, and compliance review.
