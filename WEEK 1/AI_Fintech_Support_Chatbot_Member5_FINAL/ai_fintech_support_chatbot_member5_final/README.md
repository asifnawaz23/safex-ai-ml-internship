<div align="center">

<!-- ══════════════════════════════════════════════════════════════════ -->
<!--                     3D HEADER BANNER                              -->
<!-- ══════════════════════════════════════════════════════════════════ -->

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    ███████╗██╗███╗   ██╗ █████╗ ███████╗███████╗██╗███████╗████████╗ ║
║    ██╔════╝██║████╗  ██║██╔══██╗██╔════╝██╔════╝██║██╔════╝╚══██╔══╝ ║
║    █████╗  ██║██╔██╗ ██║███████║███████╗███████╗██║███████╗   ██║    ║
║    ██╔══╝  ██║██║╚██╗██║██╔══██║╚════██║╚════██║██║╚════██║   ██║    ║
║    ██║     ██║██║ ╚████║██║  ██║███████║███████║██║███████║   ██║    ║
║    ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚══════╝   ╚═╝    ║
║                                                                  ║
║           🤖  A I   C H A T B O T   ·   F I N T E C H  🏦       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

# 🤖 FinAssist AI — Fintech Customer Support Chatbot

### *Powered by Hugging Face Transformers · Zero-Shot NLP · FastAPI*

<br/>

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![HuggingFace](https://img.shields.io/badge/🤗%20Hugging%20Face-Transformers-FF6B00?style=for-the-badge)](https://huggingface.co/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)

[![Accuracy](https://img.shields.io/badge/Test%20Accuracy-93.33%25-00D26A?style=for-the-badge&logo=checkmarx&logoColor=white)]()
[![Tests](https://img.shields.io/badge/Test%20Cases-14%2F15%20PASS-0080FF?style=for-the-badge&logo=pytest&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)]()
[![Week](https://img.shields.io/badge/SafeX%20Internship-Week%201-gold?style=for-the-badge)]()

<br/>

> 💡 **A portfolio-quality fintech chatbot** that classifies customer support queries into smart intents and routes them to safe, pre-defined banking responses — powered entirely by **Hugging Face Zero-Shot Transformers**, running **100% locally on CPU**. No GPU needed. No training data needed.

<br/>

</div>

---

<div align="center">

## ✨ What Makes This Special?

| 🧠 Zero-Shot AI | 🔒 Fintech-Safe | ⚡ Instant Deploy | 📊 Tested |
|:-:|:-:|:-:|:-:|
| No training required — the model understands English natively | Never asks for passwords, PINs, or sensitive data | Runs on CPU, no cloud, no GPU | 15 real test cases, 93.33% accuracy |

</div>

---

## 📋 Table of Contents

- [🏦 About This Project](#-about-this-project)
- [👤 My Role — Member 5](#-my-role--member-5)
- [⚙️ How It Works — System Architecture](#️-how-it-works--system-architecture)
- [🎯 Supported Fintech Intents](#-supported-fintech-intents)
- [📊 Live Test Results](#-live-test-results)
- [🛠️ Tech Stack](#️-tech-stack)
- [📁 Project Structure](#-project-structure)
- [🚀 Quick Start](#-quick-start)
- [📡 API Reference](#-api-reference)
- [🛡️ Error Handling](#️-error-handling)
- [🔬 Sample Inputs & Outputs](#-sample-inputs--outputs)
- [🔒 Security & Fintech Safety](#-security--fintech-safety)
- [⚠️ Limitations & Future Work](#️-limitations--future-work)

---

## 🏦 About This Project

**FinAssist AI** is a prototype AI-powered customer support chatbot built for a fintech application. When a customer types a support query — like *"My card was declined"* or *"I forgot my password"* — the system uses a pre-trained Hugging Face Transformer model to:

```
 ┌─────────────────────────────────────────────────────┐
 │                                                     │
 │   1. UNDERSTAND   →   What is the customer asking?  │
 │   2. CLASSIFY     →   Which of 9 intents fits best? │
 │   3. ROUTE        →   Return a safe, controlled      │
 │                       banking response               │
 │   4. SAFEGUARD    →   Handle edge cases gracefully   │
 │                                                     │
 └─────────────────────────────────────────────────────┘
```

This is a **fully working** system with:
- 🌐 A browser-based chat interface
- 🔗 A REST API for group integration
- ✅ 15 automated test cases
- 📚 Complete technical documentation

---

## 👤 My Role — Member 5

<div align="center">

```
╭──────────────────────────────────────────────────╮
│                                                  │
│   👤  Member 5  ·  Individual Contributor        │
│   🎓  BS Software Engineering — 5th Semester     │
│   🧪  NLP / AI Intent Classification Module      │
│   🤗  Primary Tool: Hugging Face Transformers    │
│                                                  │
╰──────────────────────────────────────────────────╯
```

</div>

### ✅ What I Built

| Feature | Status | Description |
|---------|--------|-------------|
| Zero-Shot Intent Classifier | ✅ Done | Uses HuggingFace `transformers` — no training needed |
| Input Validation & Error Handling | ✅ Done | Empty, too short, too long, server errors |
| Confidence Threshold + Fallback | ✅ Done | Smart fallback when model is not confident |
| Safe Fintech Response Routing | ✅ Done | Hardcoded, controlled response templates |
| FastAPI REST Endpoint | ✅ Done | `/api/chat` and `/health` endpoints |
| Browser-Based Live Demo | ✅ Done | Full chat UI in vanilla HTML/CSS/JS |
| 15 Automated Test Cases | ✅ Done | PASS/FAIL evaluation with CSV output |
| Full Technical Documentation | ✅ Done | Technical writeup, video script, checklist |

---

## ⚙️ How It Works — System Architecture

```
                    ┌─────────────────────────────────┐
                    │         USER'S BROWSER           │
                    │   Types: "My card was declined"  │
                    └──────────────┬──────────────────┘
                                   │  HTTP POST /api/chat
                                   ▼
                    ┌─────────────────────────────────┐
                    │          FASTAPI SERVER          │
                    │                                 │
                    │  ① Input Validator               │
                    │     ├── Empty message? → 400     │
                    │     ├── Too short? → 400         │
                    │     └── Too long? → 400          │
                    │                                 │
                    │  ② Hugging Face Classifier       │
                    │     Model: deberta-v3-xsmall     │
                    │     Labels: 9 Fintech Intents    │
                    │                                 │
                    │  ③ Confidence Check              │
                    │     ├── ≥ 0.40 → Use intent     │
                    │     └── < 0.40 → Fallback msg   │
                    │                                 │
                    │  ④ Safe Response Lookup          │
                    │     └── Hardcoded template only  │
                    └──────────────┬──────────────────┘
                                   │  JSON Response
                                   ▼
                    ┌─────────────────────────────────┐
                    │         USER'S BROWSER           │
                    │   Shows: Safe banking response   │
                    └─────────────────────────────────┘
```

### 🧠 What is Zero-Shot Classification?

> Normally, an AI model needs **thousands of training examples** to understand text.
> **Zero-Shot Classification** means the model already understands English from its massive pre-training.
> We simply provide the **intent label names** at runtime — the model instantly finds the best match.
> **No training data required. No fine-tuning. No labelling work.**

```
  User Message: "My card was declined at the store"
        │
        ▼
  Compare against 9 labels simultaneously:
  ┌──────────────────────────────┬────────────┐
  │ card payment issue           │  98.53% ✅ │  ← Winner
  │ account access issue         │   0.52%    │
  │ money transfer issue         │   0.44%    │
  │ cash withdrawal issue        │   0.26%    │
  │ ...                          │   ...      │
  └──────────────────────────────┴────────────┘
```

---

## 🎯 Supported Fintech Intents

<div align="center">

```
╔═══╦══════════════════════════════╦══════════════════════════════════════════════╗
║ # ║  Intent Label                ║  Example Customer Query                      ║
╠═══╬══════════════════════════════╬══════════════════════════════════════════════╣
║ 1 ║  card payment issue          ║  "My card was declined at the store"         ║
║ 2 ║  cash withdrawal issue       ║  "ATM charged me but gave no cash"           ║
║ 3 ║  money transfer issue        ║  "My bank transfer is still pending"         ║
║ 4 ║  account access issue        ║  "I forgot my password and can't log in"     ║
║ 5 ║  refund issue                ║  "The merchant refunded me but I can't see"  ║
║ 6 ║  cash deposit issue          ║  "I deposited money but balance not updated" ║
║ 7 ║  fees and charges question   ║  "Why was I charged an extra service fee?"   ║
║ 8 ║  identity verification issue ║  "My identity verification keeps failing"    ║
║ 9 ║  general account question    ║  "How can I manage my account settings?"     ║
╚═══╩══════════════════════════════╩══════════════════════════════════════════════╝
```

</div>

---

## 📊 Live Test Results

> ⚠️ These are **real results** from actually running `python run_tests.py`. Nothing invented.

<div align="center">

| ID | Query | Expected | Predicted | Confidence | Result |
|:--:|-------|----------|-----------|:----------:|:------:|
| 1 | My card payment was declined at a store | card payment issue | card payment issue | 0.9853 | ✅ PASS |
| 2 | I was charged twice for the same card purchase | card payment issue | card payment issue | 0.5358 | ✅ PASS |
| 3 | My card shows a payment I do not recognize | card payment issue | card payment issue | 0.9330 | ✅ PASS |
| 4 | The ATM charged me but did not give me cash | cash withdrawal issue | cash withdrawal issue | 0.8168 | ✅ PASS |
| 5 | I withdrew cash but the amount is wrong | cash withdrawal issue | cash withdrawal issue | 0.8682 | ✅ PASS |
| 6 | My bank transfer is still pending | money transfer issue | money transfer issue | 0.9701 | ✅ PASS |
| 7 | I sent money but the recipient has not received it | money transfer issue | money transfer issue | 0.9572 | ✅ PASS |
| 8 | I forgot my password and cannot log in | account access issue | account access issue | 0.9404 | ✅ PASS |
| 9 | My account is locked after too many login attempts | account access issue | account access issue | 0.9412 | ✅ PASS |
| 10 | The merchant refunded me but I cannot see it | refund issue | refund issue | 0.9493 | ✅ PASS |
| 11 | Why was I charged an extra service fee | fees and charges question | fees and charges question | 0.9751 | ✅ PASS |
| 12 | My identity verification keeps failing | identity verification issue | identity verification issue | 0.9929 | ✅ PASS |
| 13 | I deposited money but my balance has not updated | cash deposit issue | cash deposit issue | 0.7805 | ✅ PASS |
| 14 | How can I manage my account settings | general account question | general account question | 0.5876 | ✅ PASS |
| 15 | Where can I see my recent account activity | general account question | account access issue | 0.6172 | ❌ FAIL |

</div>

<br/>

<div align="center">

```
╔══════════════════════════════════════════════════╗
║                                                  ║
║   ✅  Tests Passed  :  14 / 15                   ║
║   ❌  Tests Failed  :   1 / 15                   ║
║   🎯  Accuracy      :  93.33%                    ║
║   🤖  Model         :  deberta-v3-xsmall-zeroshot ║
║   💻  Execution     :  CPU only (no GPU needed)  ║
║                                                  ║
╚══════════════════════════════════════════════════╝
```

</div>

> **📝 Note on Test #15:** The model predicted `account access issue` for a query about *viewing* account activity. This is a reasonable near-miss — the two intents are semantically close. This demonstrates honest, realistic model behavior and has been documented transparently.

---

## 🛠️ Tech Stack

<div align="center">

```
╭────────────────────────────────────────────────────────────────╮
│                                                                │
│   🐍  Python 3.11+          →  Core language                   │
│   🤗  HuggingFace 4.44+     →  NLP / Zero-Shot Classification  │
│   🔥  PyTorch 2.x           →  Deep learning backend           │
│   ⚡  FastAPI 0.115         →  REST API & web server           │
│   🦄  Uvicorn 0.30+         →  ASGI server                     │
│   ✅  Pydantic 2.x          →  Input validation                 │
│   🌐  HTML / CSS / JS       →  Browser chat interface          │
│                                                                │
╰────────────────────────────────────────────────────────────────╯
```

</div>

| Technology | Version | Role |
|-----------|:-------:|------|
| **Python** | 3.11+ | Core runtime |
| **Hugging Face Transformers** | 4.44+ | Zero-shot NLP classification |
| **PyTorch** | 2.x | Deep learning backend |
| **FastAPI** | 0.115 | REST API endpoints |
| **Uvicorn** | 0.30+ | Production ASGI server |
| **Pydantic** | 2.x | Request/response validation |
| **Vanilla HTML/CSS/JS** | — | Live browser demo UI |

---

## 📁 Project Structure

```
WEEK 1/
└── AI_Fintech_Support_Chatbot_Member5_FINAL/
    └── ai_fintech_support_chatbot_member5_final/
        │
        ├── 📂 app/                        ← Core application logic
        │   ├── __init__.py                # Python package marker
        │   ├── config.py                  # Intent labels + safe response templates
        │   ├── main.py                    # FastAPI routes + browser UI serving
        │   └── model_service.py           # 🤖 Hugging Face AI logic (CORE FILE)
        │
        ├── 📂 data/                       ← Test data
        │   ├── test_cases.csv             # 15 labelled test queries
        │   └── test_results.csv           # Actual PASS/FAIL results (auto-generated)
        │
        ├── 📂 docs/                       ← Documentation
        │   ├── technical_writeup.md       # Full technical explanation
        │   ├── video_script.md            # Demo video speaking script
        │   ├── screenshot_checklist.md    # Submission checklist
        │   └── submission_text.md         # Submission description
        │
        ├── 📂 static/                     ← Browser UI files
        │   ├── index.html                 # Chat interface layout
        │   ├── styles.css                 # Styling
        │   └── app.js                     # Frontend JavaScript logic
        │
        ├── 📂 screenshots/                ← Demo screenshots
        │
        ├── run_tests.py                   # Runs all 15 automated test cases
        ├── validate_project.py            # Offline project structure validator
        ├── requirements.txt               # Python dependencies
        ├── .gitignore                     # Git ignore rules
        └── README.md                      # You are here 📍
```

---

## 🚀 Quick Start

### Prerequisites
- Python **3.11** or higher
- Internet connection *(first run only — downloads the ~200MB AI model once)*

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/asifnawaz23/safex-ai-ml-internship.git
cd "safex-ai-ml-internship/WEEK 1/AI_Fintech_Support_Chatbot_Member5_FINAL/ai_fintech_support_chatbot_member5_final"
```

---

### Step 2 — Create Virtual Environment

```bash
python -m venv .venv
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

---

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4 — Run the Web Application

```bash
uvicorn app.main:app --reload
```

---

### Step 5 — Open in Browser

```
http://127.0.0.1:8000
```

> 💡 On first launch, the Hugging Face model (`deberta-v3-xsmall-zeroshot`) downloads automatically (~200MB). This only happens once — subsequent launches are instant.

---

### (Optional) — Run Automated Tests

```bash
python run_tests.py
```

Results are printed to console and saved to `data/test_results.csv`.

---

### (Optional) — Validate Project Structure

```bash
python validate_project.py
```

---

## 📡 API Reference

### `POST /api/chat` — Send a Support Query

**Request Body:**
```json
{
  "message": "My bank transfer is still pending"
}
```

**Success Response `200`:**
```json
{
  "input": "My bank transfer is still pending",
  "intent": "money transfer issue",
  "confidence": 0.9701,
  "response": "I can help with a transfer issue. Verify the recipient details and transaction status. If the transfer is pending, avoid sending the same payment again until the first transaction is resolved.",
  "fallback": false
}
```

**Low-Confidence Fallback `200`:**
```json
{
  "input": "hmmm",
  "intent": "general account question",
  "confidence": 0.1203,
  "response": "I'm not fully confident about the request category. Please rephrase your question or describe the problem in more detail.",
  "fallback": true
}
```

**Validation Error `400`:**
```json
{
  "detail": "Message is too short. Please describe the problem."
}
```

---

### `GET /health` — Server Health Check

```json
{
  "status": "ok",
  "app": "FinAssist AI",
  "model": "MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33",
  "supported_intents": 9
}
```

---

## 🛡️ Error Handling

<div align="center">

```
╔══════════════════════════════╦═══════════════════════════════════════╗
║  Error Type                  ║  How It Is Handled                    ║
╠══════════════════════════════╬═══════════════════════════════════════╣
║  Empty message               ║  HTTP 400 — friendly guidance         ║
║  Message too short (< 3 ch)  ║  HTTP 400 — asks to describe problem  ║
║  Message too long (> 500 ch) ║  HTTP 400 — shows character limit     ║
║  Model not loaded / failed   ║  HTTP 503 — explains download issue   ║
║  Low confidence prediction   ║  HTTP 200 — graceful fallback reply   ║
║  Any other server error      ║  HTTP 503 — caught, logged, returned  ║
╚══════════════════════════════╩═══════════════════════════════════════╝
```

</div>

---

## 🔬 Sample Inputs & Outputs

<details>
<summary><b>💳 Example 1 — Card Payment Issue</b></summary>

**Input:**
```
The ATM charged me but did not give me cash
```
**Output:**
```json
{
  "intent":     "cash withdrawal issue",
  "confidence": 0.8168,
  "response":   "I can help with an ATM or cash withdrawal issue. Check the transaction status
                 in your activity. If your balance was charged but cash was not received, keep
                 the ATM receipt or reference number and report the transaction through official
                 support.",
  "fallback":   false
}
```

</details>

<details>
<summary><b>💸 Example 2 — Fees Question</b></summary>

**Input:**
```
Why was I charged an extra service fee?
```
**Output:**
```json
{
  "intent":     "fees and charges question",
  "confidence": 0.9751,
  "response":   "I can help explain a fee or charge. Identify the fee shown in your transaction
                 history. For the exact current amount, refer to the fintech app's official fee
                 schedule.",
  "fallback":   false
}
```

</details>

<details>
<summary><b>❌ Example 3 — Input Too Short</b></summary>

**Input:**
```
hi
```
**Output (HTTP 400):**
```json
{
  "detail": "Message is too short. Please describe the problem."
}
```

</details>

<details>
<summary><b>🤔 Example 4 — Low Confidence / Vague Input</b></summary>

**Input:**
```
I have a problem
```
**Output:**
```json
{
  "intent":     "general account question",
  "confidence": 0.1950,
  "response":   "I'm not fully confident about the request category. Please rephrase your question.",
  "fallback":   true
}
```

</details>

---

## 🔒 Security & Fintech Safety

<div align="center">

```
╭──────────────────────────────────────────────────────────────╮
│                                                              │
│   ❌  NEVER asks for passwords, PINs, CVVs, or OTPs         │
│   ❌  NEVER accesses real bank accounts or transactions      │
│   ❌  NEVER stores user messages or personal data           │
│                                                              │
│   ✅  ALL responses are hardcoded, controlled templates      │
│   ✅  The AI model only classifies intent — not decisions    │
│   ✅  Runs entirely offline after first model download       │
│   ✅  Input length limits prevent prompt injection attacks   │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

</div>

---

## ⚠️ Limitations & Future Work

### Current Limitations

- Zero-shot classification may confuse semantically similar intents *(e.g., test case #15)*
- No conversation history or multi-turn context awareness
- Responses are static templates — not personalized to the user
- English-only support — no Urdu or multilingual capability yet

### 🗺️ Roadmap — Future Improvements

- [ ] 🎯 Fine-tune a domain-specific NLP classifier on real fintech support data
- [ ] 🌍 Add Urdu / Roman Urdu language support
- [ ] 🔗 Integrate with a real backend knowledge base and ticketing system
- [ ] 👨‍💼 Add human agent escalation flow for edge cases
- [ ] 🧠 Add conversation context memory (multi-turn support)
- [ ] ☁️ Deploy to cloud with HTTPS, auth, and rate limiting
- [ ] 📊 Add analytics dashboard and model performance monitoring
- [ ] 🔐 Add audit logging for compliance

---

<div align="center">

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         🚀  Built for the SafeX AI/ML Internship            ║
║                                                              ║
║   Member 5  ·  Hugging Face Transformers                     ║
║   BS Software Engineering — 5th Semester                     ║
║                                                              ║
║         ✨  Week 1 — Individual Contribution  ✨              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

**Made with ❤️ · Zero-Shot NLP · Local CPU Inference · 93.33% Accuracy**

[![GitHub](https://img.shields.io/badge/GitHub-asifnawaz23-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/asifnawaz23/safex-ai-ml-internship)

</div>
