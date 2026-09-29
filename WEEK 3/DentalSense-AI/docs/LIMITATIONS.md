# Limitations

The DentalSense AI project successfully demonstrates the integration of a full-stack dashboard with a local Hugging Face NLP model. However, the following limitations must be acknowledged:

1. **General-Purpose Sentiment Model**: The selected model (`distilbert-base-uncased-finetuned-sst-2-english`) is fine-tuned on movie reviews. It is not specifically trained for clinical or dental terminology.
2. **Primarily English**: The model is trained on English corpora and will not reliably perform sentiment extraction on other languages.
3. **Theme Detection is Rule-Based**: The theme assignment (e.g. "Wait Time", "Staff") relies on a hard-coded keyword dictionary. It does not employ deep semantic understanding and cannot interpret sarcasm or zero-shot classes.
4. **Neutral Classification is Application-Level**: The SST-2 model natively outputs only POSITIVE or NEGATIVE labels. The "Neutral" label is a heuristic applied to any prediction with a confidence score below 75%.
5. **Confidence is Not Certainty**: A confidence score of 99% indicates a high probability matching the model's training distribution; it does not indicate clinical certainty.
6. **Synthetic Dataset**: The dataset does not represent actual patient demographics or real-world feedback volumes. 
7. **Mixed Feedback Complexity**: Feedback such as "The dentist was amazing but the front desk was very rude" contains mixed sentiment. The model will resolve to a single aggregate score, which may blur the nuance of the dual-polarity statement.
8. **No Medical Interpretation**: The system evaluates the *tone* of the text, not the medical severity of the content.
9. **No Healthcare Compliance**: This application has not been audited for HIPAA, SOC2, or other healthcare data compliance standards.
