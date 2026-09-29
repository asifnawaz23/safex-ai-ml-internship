# DentalSense AI - User Guide

Welcome to the DentalSense AI platform. This guide will walk you through analyzing your clinic's patient feedback.

## Starting the Application

To run the application locally, you need to open two terminal windows:

**Terminal 1 (Start the AI Backend):**
1. Navigate to the `backend` folder.
2. Activate the virtual environment (`.\.venv\Scripts\activate` on Windows).
3. Run `uvicorn main:app --reload`.
4. Wait for the terminal to display "Application startup complete."

**Terminal 2 (Start the Dashboard):**
1. Navigate to the `frontend` folder.
2. Run `npm run dev`.
3. Open your browser to the URL displayed (usually `http://localhost:5173`).

---

## Navigating the Platform

### 1. Dashboard
The Dashboard is your high-level overview.
- **KPI Cards:** Instantly view total reviews, positive/negative rates, and the average confidence score of the AI.
- **Charts:** View sentiment breakdowns (Pie Chart) and which themes are most discussed (Bar Chart).
- **Automated Insights:** Short text blurbs automatically pointing out trends (e.g. "Pricing is the most frequent negative theme").

*Note: The bundled synthetic sample dataset is analyzed automatically when the backend starts, so the dashboard is populated for demonstration. Uploading a CSV replaces the current in-memory dataset until the next backend restart.*

### 2. Feedback Analyzer
Use this to check a single review quickly before you respond to a patient.
- Paste the patient's review into the text box.
- Click **Analyze Feedback**.
- The system will immediately color-code the sentiment, show the AI's confidence score, and tag the topic (e.g. "Waiting Time").

### 3. Batch Analysis
Use this at the end of the month to process hundreds of reviews at once.
- Click the upload area to select a CSV file.
- The CSV must have three columns: `id`, `date`, `feedback`.
- Click **Analyze Now**.
- Once complete, the system will redirect your insights directly to the Dashboard and Explorer.

### 4. Feedback Explorer
This is your searchable database of processed feedback.
- **Search:** Type keywords (e.g. "pain") to find specific reviews.
- **Filters:** Use the dropdowns to view only "Negative" reviews, or only reviews about the "Dentist".
- The table dynamically updates as you type or change filters.

---

## Understanding the AI

**Sentiment & Confidence:**
The AI categorizes feedback as **Positive**, **Negative**, or **Neutral**. 
The **Confidence Percentage** represents how sure the AI is about its decision. If a review is highly mixed (e.g., "The dentist was great but the wait was awful"), the confidence score may be lower, and it will often be labeled as Neutral.

**Errors:**
If you receive a red error box during upload, ensure your file is a `.csv` and contains the word `feedback` in the header row.
