from collections import OrderedDict


IRREGULAR_PLURALS = {
    "leaf": "leaves",
    "knife": "knives",
    "wolf": "wolves",
    "staff": "staves",
}

ARTICLES = ("a ", "an ", "the ")


def strip_article(text):
    value = str(text or "").strip()
    lowered = value.lower()
    for article in ARTICLES:
        if lowered.startswith(article):
            return value[len(article):].strip()
    return value


def pluralize_label(text, count):
    label = strip_article(text)
    if int(count or 0) == 1:
        return label
    words = label.split()
    if not words:
        return label
    noun = words[-1]
    lower_noun = noun.lower()
    if lower_noun in IRREGULAR_PLURALS:
        words[-1] = IRREGULAR_PLURALS[lower_noun]
        return " ".join(words)
    if lower_noun.endswith("ies"):
        return " ".join(words)
    if lower_noun.endswith("y") and len(lower_noun) > 1 and lower_noun[-2] not in "aeiou":
        words[-1] = f"{noun[:-1]}ies"
        return " ".join(words)
    if lower_noun.endswith(("s", "x", "z", "ch", "sh")):
        words[-1] = f"{noun}es"
        return " ".join(words)
    if lower_noun.endswith("fe"):
        words[-1] = f"{noun[:-2]}ves"
        return " ".join(words)
    if lower_noun.endswith("f"):
        words[-1] = f"{noun[:-1]}ves"
        return " ".join(words)
    words[-1] = f"{noun}s"
    return " ".join(words)


def format_stack_label(label, quantity):
    count = max(1, int(quantity or 1))
    if count == 1:
        return strip_article(label)
    return f"{pluralize_label(label, count)} ({count})"


def aggregate_display_entries(entries):
    grouped = OrderedDict()
    for entry in list(entries or []):
        if not entry:
            continue
        label = str(entry.get("label") or "").strip()
        if not label:
            continue
        key = str(entry.get("aggregation_key") or label).strip().lower()
        quantity = max(1, int(entry.get("quantity", 1) or 1))
        if key not in grouped:
            grouped[key] = {"label": label, "quantity": quantity}
            continue
        grouped[key]["quantity"] += quantity
    results = []
    for group in grouped.values():
        results.append(format_stack_label(group["label"], group["quantity"]))
    return results


def build_object_display_entry(obj, looker=None, **kwargs):
    if not obj:
        return None
    if hasattr(obj, "get_display_name"):
        label = str(obj.get_display_name(looker, **kwargs) or "").strip()
    else:
        label = str(getattr(obj, "key", "") or "").strip()
    if not label:
        return None
    quantity = 1
    if hasattr(obj, "get_stack_quantity"):
        quantity = max(1, int(obj.get_stack_quantity() or 1))
    return {
        "label": strip_article(label),
        "aggregation_key": strip_article(label).lower(),
        "quantity": quantity,
    }


def aggregate_object_labels(objects, looker=None, **kwargs):
    entries = []
    for obj in list(objects or []):
        entry = build_object_display_entry(obj, looker=looker, **kwargs)
        if entry is not None:
            entries.append(entry)
    return aggregate_display_entries(entries)