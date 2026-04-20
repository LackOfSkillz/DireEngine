OCR_HIGH_CONF = 0.75
OCR_MED_CONF = 0.5
OCR_LOW_CONF = 0.3


def score_label_confidence(distance, ocr_conf):
    """
    Combine spatial distance and OCR confidence into a single score.
    """
    if distance is None:
        return 0.0

    distance_score = max(0.0, 1.0 - (distance / 100.0))
    return (distance_score * 0.6) + (ocr_conf * 0.4)


def classify_confidence(score):
    if score >= OCR_HIGH_CONF:
        return "high"
    if score >= OCR_MED_CONF:
        return "medium"
    if score >= OCR_LOW_CONF:
        return "low"
    return "none"
