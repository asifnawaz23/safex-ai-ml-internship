<div align="center">

# SafeX AI/ML Internship

**Muhammad Asif Nawaz** · [github.com/asifnawaz23](https://github.com/asifnawaz23)

A Day 1 exercise and four weekly projects completed during the SafeX AI/ML Internship, from a first scikit-learn model to a measured PII detection and redaction pipeline.

![Status: Completed](https://img.shields.io/badge/Status-Completed-2EA44F?style=for-the-badge)
![Projects: Day 1 + 4 weeks](https://img.shields.io/badge/Projects-Day%201%20%2B%204%20weeks-0A66C2?style=for-the-badge)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikitlearn&logoColor=white)
![Hugging Face Transformers](https://img.shields.io/badge/Hugging%20Face-Transformers-FFD21E?style=flat-square&logo=huggingface&logoColor=111827)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=082032)
![Microsoft Presidio](https://img.shields.io/badge/Microsoft-Presidio-0A66C2?style=flat-square)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)

</div>

## Completion status

| Week | Project | What it does | Key tech | Status |
|---|---|---|---|---|
| Day 1 | [Iris Dataset Classification](Day-01/README.md) | Trains and evaluates a Decision Tree classifier on the Iris dataset | Python, Jupyter Notebook, NumPy, pandas, scikit-learn | ✅ Completed |
| Week 1 | [FinAssist AI: Fintech Customer Support Chatbot](WEEK%201/AI_Fintech_Support_Chatbot_Member5_FINAL/ai_fintech_support_chatbot_member5_final/README.md) | Classifies customer support queries into 9 fintech intents and returns safe, pre-defined banking responses | Hugging Face Transformers (zero-shot), PyTorch, FastAPI, HTML/CSS/JS | ✅ Completed |
| Week 2 | [AI-Assisted Vulnerability Analysis Tool](WEEK%202/AI-Vulnerability-Analysis-Tool/README.md) | Classifies security findings into vulnerability categories and adds severity, explanation and remediation | Hugging Face Transformers (zero-shot), PyTorch, Python CLI, JSON reports | ✅ Completed |
| Week 3 | [DentalSense AI](WEEK%203/DentalSense-AI/README.md) | Turns dental clinic feedback into sentiment, themes and dashboard analytics | DistilBERT (Transformers), FastAPI, React, Vite, Tailwind CSS, Recharts | ✅ Completed |
| Week 4 | [PII Detection & Redaction Pipeline](WEEK%204/pii-detection-redaction-pipeline/README.md) | Detects and redacts personal data in synthetic company documents and measures recall against ground truth | Microsoft Presidio, spaCy, pandas, matplotlib, pytest | ✅ Completed |

> [!NOTE]
> The Week 4 README still lists three follow-up items as pending: the classmate peer review, the video walkthrough and the 13 evidence screenshots.

## Project highlights

### Day 1 · Iris Dataset Classification

- A beginner ML workflow: load and explore the data, separate features and target, split it 80% / 20% with `random_state=42`, train a `DecisionTreeClassifier`, predict and print the accuracy.
- Files: [README](Day-01/README.md) · [notebook](Day-01/day1_iris_ml.ipynb)

### Week 1 · FinAssist AI

- My role: Member 5, individual contributor on the NLP / AI intent classification module.
- Zero-shot intent classification with `deberta-v3-xsmall` (no training data), a 0.40 confidence threshold with a fallback reply, and a FastAPI `/api/chat` endpoint behind a browser chat UI.
- 15 automated test cases, 14 passed (93.33% accuracy). The one failure (test #15) is documented as a near-miss between two similar intents.
- Details: [Week 1 README](WEEK%201/AI_Fintech_Support_Chatbot_Member5_FINAL/ai_fintech_support_chatbot_member5_final/README.md)

### Week 2 · AI-Assisted Vulnerability Analysis Tool

- A defensive triage assistant: zero-shot classification with `cross-encoder/nli-deberta-v3-xsmall`, combined with a deterministic security validation layer.
- Covers SQL Injection, Cross-Site Scripting (XSS), Authentication Issues, Authorization Issues, Sensitive Data Exposure and Other, and saves structured JSON reports from an interactive CLI.
- 10/10 controlled test scenarios passed. This applies to the controlled test set after the validation rules, not to general zero-shot accuracy.
- Details: [Week 2 README](WEEK%202/AI-Vulnerability-Analysis-Tool/README.md)

### Week 3 · DentalSense AI

- Local CPU sentiment inference with `distilbert-base-uncased-finetuned-sst-2-english`, plus a rule-based theme layer across nine operational themes.
- FastAPI backend and React dashboard with a feedback analyzer, CSV batch analysis, a feedback explorer and a methodology page, seeded with 117 synthetic feedback records.
- 5 automated backend tests with pytest. Synthetic data only; it is a business analytics project, not a clinical system.
- Details: [Week 3 README](WEEK%203/DentalSense-AI/README.md) · [AI Model Card](WEEK%203/DentalSense-AI/docs/AI_MODEL_CARD.md)

### Week 4 · PII Detection & Redaction Pipeline

- My role: Member 5, individual contributor. A Microsoft Presidio pipeline for the fictional Urban Bottled Water Company, run on 870 synthetic records with 3412 planted PII occurrences (seed 42).
- Six custom recognisers (Pakistani phone numbers, CNICs, postal codes, customer IDs, addresses, labelled names) and a company-code allow-list raise exact-span recall from 0.5023 to 0.9071 and precision from 0.6190 to 0.8442 over default Presidio.
- 15 dangerous misses investigated: 10 fixed with regression tests, 5 not fixed by design. Tests: 193 passed, 4 xfailed (local run).
- Scores are in-sample; on held-out formats improved recall is 0.5784. The project also includes a proposed privacy policy.
- Details: [Week 4 README](WEEK%204/pii-detection-redaction-pipeline/README.md) · [Privacy policy](WEEK%204/pii-detection-redaction-pipeline/docs/PRIVACY_POLICY.md) · [Limitations](WEEK%204/pii-detection-redaction-pipeline/docs/LIMITATIONS.md)

## Preview

<table>
  <tr>
    <td width="50%"><img src="WEEK%203/DentalSense-AI/screenshots/dashboard.png" alt="DentalSense AI analytics dashboard populated from synthetic feedback" width="100%" /></td>
    <td width="50%"><img src="WEEK%204/pii-detection-redaction-pipeline/output/charts/recall_by_entity.png" alt="Recall by entity type, default Presidio baseline versus the improved pipeline, with the recall targets as dashed lines" width="100%" /></td>
  </tr>
  <tr>
    <td align="center"><sub>Week 3 · DentalSense AI dashboard</sub></td>
    <td align="center"><sub>Week 4 · recall by entity type, baseline vs improved</sub></td>
  </tr>
</table>

## Skills gained

- **Machine learning basics:** train/test splits, model training, prediction and accuracy evaluation (Day 1).
- **NLP with Hugging Face Transformers:** zero-shot classification (Weeks 1 and 2) and sentiment analysis with DistilBERT (Week 3).
- **Model output plus deterministic rules:** confidence fallbacks, a security validation layer and rule-based themes (Weeks 1 to 3).
- **APIs and interfaces:** REST APIs with FastAPI and Pydantic, a vanilla JS chat UI and a React analytics dashboard (Weeks 1 and 3).
- **Privacy engineering:** PII detection and redaction with Microsoft Presidio, custom recognisers, synthetic data with independent ground truth and a privacy policy (Week 4).
- **Evaluation and testing:** automated test cases in every week, pytest suites (Weeks 3 and 4), precision, recall and F1 (Week 4), and documented limitations.

## Repository structure

```text
safex-ai-ml-internship/
├── README.md                         # this overview
├── Day-01/                           # Iris classification
│   ├── README.md
│   ├── SUBMISSION_CHECKLIST.md
│   └── day1_iris_ml.ipynb
├── WEEK 1/
│   └── AI_Fintech_Support_Chatbot_Member5_FINAL/
│       └── ai_fintech_support_chatbot_member5_final/   # app/, data/, static/, run_tests.py
├── WEEK 2/
│   └── AI-Vulnerability-Analysis-Tool/                 # src/, tests/, data/, reports/
├── WEEK 3/
│   └── DentalSense-AI/                                 # backend/, frontend/, data/, docs/, screenshots/
└── WEEK 4/
    └── pii-detection-redaction-pipeline/               # src/, scripts/, tests/, config/, data/, docs/, output/, evidence/
```

## How to explore or run

Each project has its own setup guide (virtual environment and dependencies) in its README. Start by cloning the repository:

```powershell
git clone https://github.com/asifnawaz23/safex-ai-ml-internship.git
cd safex-ai-ml-internship
```

| Project | Main command after setup | Full instructions |
|---|---|---|
| Day 1 | Open `day1_iris_ml.ipynb` in Jupyter Notebook or VS Code and run the cells from top to bottom | [Day 1 README](Day-01/README.md) |
| Week 1 | `uvicorn app.main:app --reload`, then open `http://127.0.0.1:8000` | [Week 1 README](WEEK%201/AI_Fintech_Support_Chatbot_Member5_FINAL/ai_fintech_support_chatbot_member5_final/README.md) |
| Week 2 | `python src\main.py` | [Week 2 README](WEEK%202/AI-Vulnerability-Analysis-Tool/README.md) |
| Week 3 | Backend: `python -m uvicorn main:app --reload`; frontend: `npm run dev` | [Week 3 README](WEEK%203/DentalSense-AI/README.md) |
| Week 4 | `& $py -m pii_pipeline.cli all`, then `& $py -m pytest -q` (`$py` is the venv Python set up in its README) | [Week 4 README](WEEK%204/pii-detection-redaction-pipeline/README.md) |

## Author

**Muhammad Asif Nawaz**, BS Software Engineering student

GitHub: [asifnawaz23](https://github.com/asifnawaz23)
