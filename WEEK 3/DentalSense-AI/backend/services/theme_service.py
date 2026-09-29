class ThemeService:
    def __init__(self):
        self.themes = {
            "Staff": ["staff", "receptionist", "friendly", "rude", "reception", "nurse", "assistant", "hygienist"],
            "Dentist": ["dentist", "doctor", "professional", "explained", "gentle", "rough", "dr.", "dr"],
            "Waiting Time": ["wait", "waiting", "time", "hour", "minutes", "delayed", "late", "prompt", "on time"],
            "Treatment": ["treatment", "procedure", "pain", "hurt", "cleaning", "filling", "extraction", "surgery"],
            "Cleanliness": ["clean", "dirty", "spotless", "hygiene", "messy", "sterile", "dust"],
            "Pricing": ["price", "cost", "expensive", "cheap", "affordable", "bill", "insurance", "charge", "money"],
            "Appointment": ["appointment", "schedule", "booking", "cancel", "reschedule", "easy to book"],
            "Facilities": ["facility", "parking", "waiting room", "bathroom", "chair", "equipment", "modern"],
        }
        self.default_theme = "General"

    def detect_theme(self, text: str) -> str:
        text_lower = text.lower()
        for theme, keywords in self.themes.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return theme
        return self.default_theme

    def get_available_themes(self):
        return list(self.themes.keys()) + [self.default_theme]

theme_service = ThemeService()
