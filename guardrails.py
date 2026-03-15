MEDICAL_KEYWORDS = [
    "diabetes",
    "blood pressure",
    "cholesterol",
    "disease",
    "treatment",
    "prescription",
    "insulin",
    "allergy",
    "diagnosis"
]

EXTREME_DIET_KEYWORDS = [
    "starve",
    "crash diet",
    "extreme weight loss",
    "eat nothing",
    "fast for days"
]

def check_guardrails(text):

    text = text.lower()

    for word in MEDICAL_KEYWORDS:
        if word in text:
            return "medical"

    for word in EXTREME_DIET_KEYWORDS:
        if word in text:
            return "diet"

    return "safe"
