# Testing Documentation

## Automated Tests
Automated tests are located in `backend/test_main.py` and cover the core FastAPI endpoints and AI pipeline behaviors.

### Run Tests
```bash
cd backend
.\.venv\Scripts\activate
pytest test_main.py -v
```

### Coverage
1. **Health Check (`test_health_check`)**: Validates the API is online.
2. **Sentiment Positive (`test_analyze_feedback_positive`)**: Ensures the NLP model correctly classifies positive input and returns confidence + theme keys.
3. **Empty Input (`test_analyze_feedback_empty`)**: Validates that 400 Bad Request is triggered on empty strings.
4. **Whitespace Input (`test_analyze_feedback_whitespace`)**: Validates that 400 Bad Request is triggered on spaces/newlines.
5. **Theme Detection (`test_theme_detection`)**: Tests the rule-based logic assigning "clean" to the `Cleanliness` theme.

## Manual QA Checklist

| Component | Status | Notes |
| :--- | :---: | :--- |
| **API Endpoints** | ✅ | Responding properly to POST/GET requests. CORS is correctly configured. |
| **Sentiment Pipeline** | ✅ | Successfully loads model once on startup to prevent blocking UI requests. Confidence and classes returned properly. |
| **Theme Engine** | ✅ | Maps strings properly. Falls back to "General". |
| **CSV Upload** | ✅ | Safely ignores invalid rows, drops duplicates, assigns fallback dates to poorly formatted times. |
| **Dashboard UI** | ✅ | Recharts loading correctly. Metric cards display dynamically computed values. |
| **Analyzer UI** | ✅ | Loading states, error states, and slide-in animations trigger perfectly on API response. |
| **Batch Interface** | ✅ | File selection and progress states work. Handles non-csv file rejection via backend. |
| **Explorer UI** | ✅ | Multi-filter works dynamically on the array state without additional server calls. |

All items have been verified locally.
