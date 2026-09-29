from typing import List, Dict
from collections import defaultdict
import datetime
import pandas as pd

class AnalyticsService:
    def calculate_analytics(self, feedback_list: List[Dict]) -> Dict:
        if not feedback_list:
            return {
                "total_reviews": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "positive_percentage": 0.0,
                "negative_percentage": 0.0,
                "neutral_percentage": 0.0,
                "average_confidence": 0.0,
                "theme_counts": {},
                "negative_theme_counts": {},
                "feedback_volume_over_time": {},
                "sentiment_over_time": {},
                "insights": ["No data available to generate insights."]
            }

        total = len(feedback_list)
        pos = sum(1 for f in feedback_list if f['sentiment'] == 'Positive')
        neg = sum(1 for f in feedback_list if f['sentiment'] == 'Negative')
        neu = sum(1 for f in feedback_list if f['sentiment'] == 'Neutral')
        
        avg_conf = sum(f['confidence'] for f in feedback_list) / total
        
        theme_counts = defaultdict(int)
        negative_theme_counts = defaultdict(int)
        volume_over_time = defaultdict(int)
        sentiment_over_time = defaultdict(lambda: {'Positive': 0, 'Neutral': 0, 'Negative': 0})
        
        for f in feedback_list:
            theme_counts[f['theme']] += 1
            if f['sentiment'] == 'Negative':
                negative_theme_counts[f['theme']] += 1
                
            date_str = f.get('date', '')
            if date_str:
                # normalize date
                try:
                    dt = pd.to_datetime(date_str)
                    month_str = dt.strftime('%Y-%m')
                    volume_over_time[month_str] += 1
                    sentiment_over_time[month_str][f['sentiment']] += 1
                except:
                    pass

        insights = []
        if total > 0:
            if neg > 0 and negative_theme_counts:
                top_neg_theme = max(negative_theme_counts.items(), key=lambda x: x[1])[0]
                insights.append(f"'{top_neg_theme}' is the most frequently associated theme with negative feedback.")
            if pos / total > 0.7:
                insights.append("Overall sentiment is strongly positive.")
            elif neg / total > 0.3:
                insights.append("There is a significant portion of negative feedback that requires attention.")

        return {
            "total_reviews": total,
            "positive_count": pos,
            "negative_count": neg,
            "neutral_count": neu,
            "positive_percentage": round((pos / total) * 100, 1),
            "negative_percentage": round((neg / total) * 100, 1),
            "neutral_percentage": round((neu / total) * 100, 1),
            "average_confidence": round(avg_conf, 1),
            "theme_counts": dict(theme_counts),
            "negative_theme_counts": dict(negative_theme_counts),
            "feedback_volume_over_time": dict(sorted(volume_over_time.items())),
            "sentiment_over_time": dict(sorted(sentiment_over_time.items())),
            "insights": insights if insights else ["Not enough distinct data to identify a reliable trend."]
        }

analytics_service = AnalyticsService()
