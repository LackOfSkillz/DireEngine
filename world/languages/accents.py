def apply_accent(text, language):
    spoken = str(text or "")
    lang = str(language or "common").strip().lower()

    if lang == "volgrin":
        return spoken.upper()
    if lang == "saurathi":
        return spoken.replace("s", "ss").replace("S", "Ss")
    if lang == "valran":
        return spoken.lower()
    if lang == "aethari":
        return f"...{spoken}..."
    if lang == "felari":
        return spoken.replace("!", "!!")
    if lang == "lunari":
        return spoken[::-1]
    return spoken