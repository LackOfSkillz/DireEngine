import re


_NUMERIC_ORDINAL_RE = re.compile(r"^(?P<value>\d+)(?:st|nd|rd|th)$", re.IGNORECASE)
_NUMERIC_POSITIONAL_RE = re.compile(r"^(?P<value>\d+)\.(?P<name>.+)$")

_SMALL_CARDINALS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

_SCALES = {
    "hundred": 100,
    "thousand": 1_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
    "trillion": 1_000_000_000_000,
}

_ORDINAL_TO_CARDINAL = {
    "first": "one",
    "second": "two",
    "third": "three",
    "fourth": "four",
    "fifth": "five",
    "sixth": "six",
    "seventh": "seven",
    "eighth": "eight",
    "ninth": "nine",
    "tenth": "ten",
    "eleventh": "eleven",
    "twelfth": "twelve",
    "thirteenth": "thirteen",
    "fourteenth": "fourteen",
    "fifteenth": "fifteen",
    "sixteenth": "sixteen",
    "seventeenth": "seventeen",
    "eighteenth": "eighteen",
    "nineteenth": "nineteen",
    "twentieth": "twenty",
    "thirtieth": "thirty",
    "fortieth": "forty",
    "fiftieth": "fifty",
    "sixtieth": "sixty",
    "seventieth": "seventy",
    "eightieth": "eighty",
    "ninetieth": "ninety",
    "hundredth": "hundred",
    "thousandth": "thousand",
    "millionth": "million",
    "billionth": "billion",
    "trillionth": "trillion",
}


def _tokenize_number_phrase(text):
    return [token for token in re.split(r"[\s-]+", str(text or "").strip().lower()) if token and token != "and"]


def parse_ordinal_value(text):
    phrase = str(text or "").strip().lower()
    if not phrase:
        return None

    numeric_match = _NUMERIC_ORDINAL_RE.match(phrase)
    if numeric_match:
        return max(1, int(numeric_match.group("value")))

    if phrase.isdigit():
        return max(1, int(phrase))

    tokens = _tokenize_number_phrase(phrase)
    if not tokens:
        return None

    if tokens[-1] in _ORDINAL_TO_CARDINAL:
        tokens[-1] = _ORDINAL_TO_CARDINAL[tokens[-1]]
    elif tokens[-1] not in _SMALL_CARDINALS and tokens[-1] not in _TENS and tokens[-1] not in _SCALES:
        return None

    total = 0
    current = 0
    for token in tokens:
        if token in _SMALL_CARDINALS:
            current += _SMALL_CARDINALS[token]
            continue
        if token in _TENS:
            current += _TENS[token]
            continue
        if token == "hundred":
            current = max(1, current) * 100
            continue
        scale = _SCALES.get(token)
        if scale:
            if scale == 100:
                current = max(1, current) * scale
            else:
                total += max(1, current) * scale
                current = 0
            continue
        return None

    value = total + current
    return value if value > 0 else None


def split_ordinal_target(raw_text):
    text = str(raw_text or "").strip()
    if not text:
        return None, ""

    positional_match = _NUMERIC_POSITIONAL_RE.match(text)
    if positional_match:
        return max(1, int(positional_match.group("value"))), positional_match.group("name").strip()

    parts = text.split(None, 1)
    if len(parts) == 2:
        value = parse_ordinal_value(parts[0])
        if value is not None:
            return value, parts[1].strip()

    tail_match = re.match(r"^(?P<name>.+?)\s+(?P<value>\d+)$", text)
    if tail_match:
        return max(1, int(tail_match.group("value"))), tail_match.group("name").strip()

    return None, text