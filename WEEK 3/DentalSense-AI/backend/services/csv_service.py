import os
import pandas as pd
from io import BytesIO
from typing import List, Dict
from .sentiment_service import sentiment_service
from .theme_service import theme_service
import datetime

class CSVService:
    def process_file(self, file_path: str) -> tuple[List[Dict], str]:
        """Process a CSV located on disk (used for startup seeding)."""
        if not os.path.exists(file_path):
            return [], f"File not found: {file_path}"
        try:
            with open(file_path, "rb") as f:
                content = f.read()
        except Exception as e:
            return [], f"Unable to read file: {e}"
        return self.process_csv(content)

    def process_csv(self, file_content: bytes) -> tuple[List[Dict], str]:
        try:
            df = pd.read_csv(BytesIO(file_content))
        except Exception as e:
            return [], f"Invalid CSV format: {e}"

        required_columns = ['id', 'date', 'feedback']
        for col in required_columns:
            if col not in df.columns:
                return [], f"Missing required column: {col}"

        # Clean data
        df = df.dropna(subset=['feedback'])
        df = df[df['feedback'].str.strip() != '']
        
        # We might want to remove duplicate IDs or just keep first
        df = df.drop_duplicates(subset=['id'], keep='first')

        results = []
        for index, row in df.iterrows():
            feedback = str(row['feedback']).strip()
            if not feedback:
                continue
                
            # Date validation (rudimentary)
            date_val = str(row['date'])
            try:
                # Try to parse it just to see if it's valid, but keep original string or normalize
                pd.to_datetime(date_val)
            except:
                date_val = datetime.datetime.now().strftime("%Y-%m-%d")

            sentiment_data = sentiment_service.analyze(feedback)
            theme = theme_service.detect_theme(feedback)
            
            results.append({
                "id": str(row['id']),
                "date": date_val,
                "feedback": feedback,
                "sentiment": sentiment_data['sentiment'],
                "confidence": round(sentiment_data['confidence'] * 100, 2),
                "theme": theme,
                "analyzed_at": datetime.datetime.now().isoformat()
            })
            
        return results, ""

csv_service = CSVService()
