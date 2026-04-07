def get_eavesdrop_level(listener, speaker):
    """
    Return a flat leak level for listeners in the same room.

    This is intentionally simple for now so the whisper/eavesdrop path stays
    deterministic and easy to tune before perception and stealth stats are added.
    """

    if not listener or not speaker:
        return 0.0
    if getattr(listener, "location", None) != getattr(speaker, "location", None):
        return 0.0
    return 0.3