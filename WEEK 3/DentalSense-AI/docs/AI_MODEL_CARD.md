# AI Model Card

## Model Details
- **Model Name**: `distilbert-base-uncased-finetuned-sst-2-english`
- **Task**: Sentiment Analysis (Text Classification)
- **Ecosystem/Provider**: Hugging Face Transformers
- **Language**: English

## Input and Output
- **Input**: Raw text (patient feedback). Truncated safely to prevent token limit crashes.
- **Output**: A sentiment label (`POSITIVE` or `NEGATIVE`) and a confidence score (`0.0` to `1.0`).

## Intended Use
- Intended for analyzing the general sentiment of patient reviews in the DentalSense AI platform.
- Used to aggregate trends and detect operational bottlenecks.

## Limitations
- **Not Domain Specific**: This model was fine-tuned on general movie reviews (SST-2 dataset), not specifically on dental, medical, or clinical literature.
- **Neutral Class Handling**: The model does not natively predict a "Neutral" class. To accommodate mixed or ambiguous feedback, this application implements a heuristic: any prediction with a confidence score below 0.75 is categorized as Neutral.
- **Theme Classification Separation**: This model is strictly used for sentiment. It is **not** responsible for theme detection (which is handled by a deterministic, rule-based layer).

## Performance Interpretations
Confidence values represent the model's statistical probability of a class match based on its training distribution. They do not represent absolute certainty or clinical significance. Mixed feedback (e.g., "The dentist was great but the wait was terrible") may yield volatile confidence scores.
