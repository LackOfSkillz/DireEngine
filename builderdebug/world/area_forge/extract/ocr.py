import shutil
from difflib import SequenceMatcher
from pathlib import Path

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


MIN_OCR_CONFIDENCE = 0.45
PROMOTABLE_LANDMARK_QUALITY = 0.78
PROMOTABLE_LANDMARK_WORDS = 3
COMMON_TESSERACT_PATHS = (
    Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
    Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
)
LANDMARK_KEYWORDS = {
    "academy",
    "arch",
    "arena",
    "bridge",
    "court",
    "crossing",
    "docks",
    "ferry",
    "gate",
    "green",
    "hall",
    "manor",
    "market",
    "pier",
    "plaza",
    "quarter",
    "square",
    "tower",
    "trader",
    "way",
}

POI_STUB_KEYWORDS = {
    "academy": ("academy", "Academy"),
    "bank": ("bank", "Bank"),
    "forge": ("forge", "Forge"),
    "general store": ("store", "General Store"),
    "guild": ("guild", "Guildhall"),
    "hall": ("hall", "Hall"),
    "inn": ("inn", "Inn"),
    "office": ("office", "Office"),
    "prison": ("prison", "Prison"),
    "shrine": ("shrine", "Shrine"),
    "shop": ("shop", "Shop"),
    "smithy": ("smithy", "Smithy"),
    "store": ("store", "Store"),
    "tavern": ("tavern", "Tavern"),
    "temple": ("temple", "Temple"),
}
POI_STUB_PRIORITY = [
    "bank",
    "prison",
    "shrine",
    "temple",
    "academy",
    "general store",
    "store",
    "shop",
    "inn",
    "tavern",
    "smithy",
    "forge",
    "office",
    "guild",
    "hall",
]
POI_GENERIC_ONLY_KEYWORDS = {"forge", "smithy"}
KNOWN_GUILD_POI_TITLES = {
    "barbarian": "Barbarian Guildhall",
    "bard": "Bard Guildhall",
    "cleric": "Cleric Guildhall",
    "commoner": "Commoner Guildhall",
    "empath": "Empath Guildhall",
    "moon mage": "Moon Mage Guildhall",
    "necromancer": "Necromancer Guildhall",
    "paladin": "Paladin Guildhall",
    "ranger": "Ranger Guildhall",
    "thief": "Thief Guildhall",
    "trader": "Trader Guildhall",
    "warrior mage": "Warrior Mage Guildhall",
}
SUSPICIOUS_OCR_CHARS = {"|", "Æ", "æ", "?", "=", "º", "¢", "�", "", "", "", "", "", "", "", "\u00105", "\u00141", "\u00153", "\u00162", "\u0017d", "\u00178", "\u00182", "\u00192", "\u001f1"}
SPECIAL_EXIT_KEYWORDS = {
    "barge",
    "gate",
    "arch",
    "bridge",
    "carriage",
    "climb",
    "stair",
    "stairs",
    "dock",
    "down",
    "enter",
    "exit",
    "go",
    "gryphon",
    "horse",
    "lift",
    "map",
    "passage",
    "pier",
    "path",
    "ferry",
    "ramp",
    "road",
    "ship",
    "stairs",
    "teleport",
    "to",
    "trail",
    "up",
}
TRAVEL_PREFIXES = (
    "go ",
    "climb ",
    "enter ",
    "exit ",
    "take ",
    "board ",
    "ride ",
    "cross ",
    "follow ",
    "descend ",
    "ascend ",
    "travel ",
)
TRAVEL_PHRASES = (
    "to map",
    "to the map",
    "go to",
    "path to",
    "road to",
    "stairs to",
    "bridge to",
    "ferry to",
    "up to",
    "down to",
)
DISTRICT_KEYWORDS = {
    "academy",
    "district",
    "gardens",
    "harbor",
    "harbour",
    "market",
    "plaza",
    "quarter",
    "square",
    "ward",
}


def normalize_ocr_text(text):
    normalized = str(text)
    replacements = {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "�": "",
    }
    for old_char, new_char in replacements.items():
        normalized = normalized.replace(old_char, new_char)
    return " ".join(normalized.split()).strip()


def score_ocr_label_quality(text):
    normalized = normalize_ocr_text(text)
    if not normalized:
        return 0.0

    score = 1.0
    words = normalized.split()
    weird_chars = sum(1 for char in normalized if char in SUSPICIOUS_OCR_CHARS)
    non_ascii_chars = sum(1 for char in normalized if ord(char) > 126)
    alpha_chars = sum(1 for char in normalized if char.isalpha())
    digit_chars = sum(1 for char in normalized if char.isdigit())

    if weird_chars:
        score -= min(0.6, weird_chars * 0.18)
    if non_ascii_chars:
        score -= min(0.4, non_ascii_chars * 0.12)
    if len(words) > 5:
        score -= min(0.35, (len(words) - 5) * 0.08)
    if len(words) > 3:
        score -= min(0.18, (len(words) - 3) * 0.06)
    if alpha_chars < max(3, len(normalized) // 3):
        score -= 0.2
    if digit_chars > 2:
        score -= 0.15
    if any(len(word) == 1 and word.lower() not in {"a", "o"} for word in words):
        score -= 0.08
    if any(sum(1 for char in word if not (char.isalpha() or char in "'-&")) >= 2 for word in words):
        score -= 0.2
    if normalized.isupper() and len(normalized) > 5:
        score -= 0.08
    return max(0.0, min(score, 1.0))


def classify_ocr_label(text, quality_score=None):
    normalized = normalize_ocr_text(text)
    lower = normalized.lower()
    quality_score = score_ocr_label_quality(normalized) if quality_score is None else quality_score

    if not normalized or quality_score < 0.35:
        return "noise"
    if is_exit_command(normalized):
        return "travel_label"
    if any(keyword in lower for keyword in POI_STUB_KEYWORDS):
        return "poi_stub"
    if any(keyword in lower for keyword in DISTRICT_KEYWORDS) or (any(keyword in lower for keyword in LANDMARK_KEYWORDS) and len(normalized.split()) >= 3):
        return "district_landmark"
    if any(keyword in lower for keyword in LANDMARK_KEYWORDS):
        return "landmark"
    if len(normalized.split()) >= 2 and quality_score >= 0.6:
        return "room_local"
    if quality_score >= 0.55:
        return "room_local"
    return "noise"


def is_promotable_landmark_text(text, quality_score=None):
    normalized = normalize_ocr_text(text)
    quality_score = score_ocr_label_quality(normalized) if quality_score is None else quality_score
    label_type = classify_ocr_label(normalized, quality_score=quality_score)
    return (
        label_type == "landmark"
        and quality_score >= PROMOTABLE_LANDMARK_QUALITY
        and len(normalized.split()) <= PROMOTABLE_LANDMARK_WORDS
    )


def _canonicalize_guild_poi_title(text, quality):
    normalized = normalize_ocr_text(text)
    lower = normalized.lower()
    if "guild" not in lower or quality < 0.72:
        return None

    cleaned = lower.replace("guildhall", " ").replace("guild", " ")
    tokens = [token.strip("' -") for token in cleaned.split() if token.strip("' -")]
    if not tokens:
        return None

    best_key = None
    best_score = 0.0
    for guild_key in KNOWN_GUILD_POI_TITLES:
        key_tokens = guild_key.split()
        token_scores = []
        for key_token in key_tokens:
            token_scores.append(max(SequenceMatcher(None, token, key_token).ratio() for token in tokens))
        score = sum(token_scores) / len(token_scores)
        if score > best_score:
            best_score = score
            best_key = guild_key

    if best_key and best_score >= 0.74:
        return KNOWN_GUILD_POI_TITLES[best_key]
    return None


def derive_poi_stub(text):
    normalized = normalize_ocr_text(text)
    lower = normalized.lower()
    for keyword in POI_STUB_PRIORITY:
        if keyword not in POI_STUB_KEYWORDS:
            continue
        exit_name, default_title = POI_STUB_KEYWORDS[keyword]
        if keyword in lower:
            quality = score_ocr_label_quality(normalized)
            words = normalized.split()
            matched_keywords = [candidate for candidate in POI_STUB_KEYWORDS if candidate in lower]
            keyword_is_last = bool(words) and words[-1].lower() == keyword.split()[-1]
            canonical_title = None
            extra_aliases = []
            resolved_exit_name = exit_name
            if keyword == "guild":
                canonical_title = _canonicalize_guild_poi_title(normalized, quality)
                if canonical_title:
                    specific_name = canonical_title.replace("Guildhall", "Guild").strip()
                    resolved_exit_name = specific_name.lower()
                    extra_aliases = [
                        "guild",
                        "go guild",
                        "enter guild",
                    ]
            keep_full_title = (
                keyword not in POI_GENERIC_ONLY_KEYWORDS
                and quality >= 0.95
                and len(words) <= 3
                and len(matched_keywords) == 1
                and keyword_is_last
                and all(word[:1].isupper() for word in words if word)
            )
            title = canonical_title or (normalized if keep_full_title else default_title)
            return {
                "exit_name": resolved_exit_name,
                "title": title,
                "keyword": keyword,
                "aliases": extra_aliases,
            }
    return None


def is_promotable_landmark_text(text, quality_score=None):
    normalized = normalize_ocr_text(text)
    quality_score = score_ocr_label_quality(normalized) if quality_score is None else quality_score
    label_type = classify_ocr_label(normalized, quality_score=quality_score)
    return (
        label_type == "landmark"
        and quality_score >= PROMOTABLE_LANDMARK_QUALITY
        and len(normalized.split()) <= PROMOTABLE_LANDMARK_WORDS
    )


def _resolve_tesseract_cmd():
    if pytesseract is None:
        return None

    discovered = shutil.which("tesseract")
    if discovered:
        pytesseract.pytesseract.tesseract_cmd = discovered
        return discovered

    configured = getattr(pytesseract.pytesseract, "tesseract_cmd", None)
    if configured and Path(configured).exists():
        return configured

    for candidate in COMMON_TESSERACT_PATHS:
        if candidate.exists():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return str(candidate)

    return None


def is_noise_text(text):
    cleaned = text.strip()
    if len(cleaned) <= 1:
        return True
    if cleaned in {"|", "-", "_", ".", ",", ":"}:
        return True
    return False


def ocr_available():
    return pytesseract is not None and Image is not None and _resolve_tesseract_cmd() is not None


def dump_ocr_regions(regions):
    for region in regions:
        print(
            f"{region['text']!r} @ "
            f"({region['x']},{region['y']}) "
            f"{region['w']}x{region['h']} "
            f"conf={region['confidence']:.2f}"
        )


def group_ocr_lines(regions, y_tolerance=12):
    lines = []

    for region in sorted(regions, key=lambda item: (item["y"], item["x"])):
        matched = None
        for line in lines:
            if abs(region["y"] - line["y"]) <= y_tolerance:
                matched = line
                break

        if matched is None:
            matched = {
                "text_parts": [],
                "x": region["x"],
                "y": region["y"],
                "w": region["w"],
                "h": region["h"],
                "confidence_values": [],
            }
            lines.append(matched)

        matched["text_parts"].append((region["x"], region["text"]))
        matched["x"] = min(matched["x"], region["x"])
        matched["y"] = min(matched["y"], region["y"])
        matched["w"] = max(matched["w"], region["x"] + region["w"] - matched["x"])
        matched["h"] = max(matched["h"], region["h"])
        matched["confidence_values"].append(region["confidence"])

    output = []
    for line in lines:
        ordered = [part for _x, part in sorted(line["text_parts"], key=lambda item: item[0])]
        output.append(
            {
                "text": normalize_ocr_text(" ".join(ordered)),
                "x": line["x"],
                "y": line["y"],
                "w": line["w"],
                "h": line["h"],
                "confidence": sum(line["confidence_values"]) / max(len(line["confidence_values"]), 1),
            }
        )

    return [line for line in output if not is_noise_text(line["text"])]


def detect_special_exit_labels(lines):
    matches = []
    for line in lines:
        lower = line["text"].lower()
        if line.get("label_type") == "travel_label" or any(word in lower for word in SPECIAL_EXIT_KEYWORDS):
            matches.append(line)
    return matches


def detect_place_name_candidates(lines):
    candidates = []
    for line in lines:
        text = line["text"]
        words = text.split()
        if (
            len(words) >= 2
            and any(word[:1].isupper() for word in words if word)
            and line.get("quality_score", 0) >= 0.6
            and line.get("label_type") in {"landmark", "district_landmark", "room_local"}
        ):
            candidates.append(line)
    return candidates


def is_exit_command(text):
    normalized = normalize_ocr_text(text).lower()
    if any(normalized.startswith(prefix) for prefix in TRAVEL_PREFIXES):
        return True
    if any(phrase in normalized for phrase in TRAVEL_PHRASES):
        return True
    if normalized in {"up", "down", "out", "enter", "exit"}:
        return True
    return any(keyword in normalized for keyword in SPECIAL_EXIT_KEYWORDS) and len(normalized.split()) <= 4


def extract_ocr_bundle(image_path):
    raw_regions = extract_ocr_regions(image_path)
    lines = group_ocr_lines(raw_regions)
    for line in lines:
        line["quality_score"] = score_ocr_label_quality(line["text"])
        line["label_type"] = classify_ocr_label(line["text"], quality_score=line["quality_score"])
        line["is_promotable_landmark"] = is_promotable_landmark_text(
            line["text"],
            quality_score=line["quality_score"],
        )

    return {
        "raw_regions": raw_regions,
        "lines": lines,
        "special_exit_labels": detect_special_exit_labels(lines),
        "place_name_candidates": detect_place_name_candidates(lines),
    }


def extract_ocr_regions(image_path):
    """
    Return OCR text regions for a map image.

    Output:
    [
        {
            "text": "Town Green",
            "x": 120,
            "y": 240,
            "w": 80,
            "h": 18,
            "confidence": 0.91,
        }
    ]
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"OCR image not found: {image_path}")

    if not ocr_available():
        raise RuntimeError(
            "OCR dependencies are not installed. Install pytesseract and Pillow."
        )

    with Image.open(image_path) as image:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    results = []
    for index in range(len(data["text"])):
        text = normalize_ocr_text(data["text"][index])
        if not text:
            continue

        raw_confidence = data["conf"][index]
        confidence = float(raw_confidence) if raw_confidence not in ("", "-1") else -1
        if confidence < 0:
            continue

        normalized_confidence = confidence / 100.0
        if normalized_confidence < MIN_OCR_CONFIDENCE:
            continue

        results.append(
            {
                "text": text,
                "x": int(data["left"][index]),
                "y": int(data["top"][index]),
                "w": int(data["width"][index]),
                "h": int(data["height"][index]),
                "confidence": normalized_confidence,
            }
        )

    return results
