from __future__ import annotations

from collections.abc import Mapping

from server.systems import item_loader


def make_ammo_stack(item_id: str, quantity: int = 1, **overrides) -> dict:
    normalized_item_id = str(item_id or "").strip()
    try:
        record = item_loader.get_item_record(normalized_item_id) if normalized_item_id else {}
    except ValueError:
        record = {}
    stack = {
        "item_id": normalized_item_id,
        "quantity": max(0, int(quantity or 0)),
        "ammo_type": str(overrides.get("ammo_type") or record.get("ammo_type") or "arrow").strip().lower(),
        "ammo_class": str(overrides.get("ammo_class") or record.get("ammo_class") or "").strip().lower(),
        "tier": str(overrides.get("tier") or record.get("tier") or "").strip().lower(),
        "name": str(overrides.get("name") or record.get("name") or normalized_item_id).strip(),
    }
    if stack["quantity"] <= 0 or not stack["item_id"]:
        return {}
    return stack


def normalize_ammo_stack(stack) -> dict:
    if not isinstance(stack, Mapping):
        return {}
    return make_ammo_stack(
        str(stack.get("item_id") or "").strip(),
        quantity=int(stack.get("quantity", 0) or 0),
        ammo_type=stack.get("ammo_type"),
        ammo_class=stack.get("ammo_class"),
        tier=stack.get("tier"),
        name=stack.get("name"),
    )


def merge_ammo_stacks(stacks) -> list[dict]:
    buckets = {}
    for raw in list(stacks or []):
        stack = normalize_ammo_stack(raw)
        if not stack:
            continue
        key = (stack["item_id"], stack.get("tier") or "")
        existing = buckets.get(key)
        if existing is None:
            buckets[key] = dict(stack)
            continue
        existing["quantity"] = int(existing.get("quantity", 0) or 0) + int(stack.get("quantity", 0) or 0)
    return sorted(
        (stack for stack in buckets.values() if int(stack.get("quantity", 0) or 0) > 0),
        key=lambda entry: (str(entry.get("name") or entry.get("item_id") or "").lower(), str(entry.get("tier") or "")),
    )


def split_ammo_stack(stack, quantity: int = 1) -> tuple[dict, dict]:
    normalized = normalize_ammo_stack(stack)
    if not normalized:
        return {}, {}
    requested = max(0, int(quantity or 0))
    if requested <= 0:
        return {}, normalized
    take_quantity = min(int(normalized.get("quantity", 0) or 0), requested)
    taken = dict(normalized)
    taken["quantity"] = take_quantity
    remainder = dict(normalized)
    remainder["quantity"] = max(0, int(normalized.get("quantity", 0) or 0) - take_quantity)
    return (taken if take_quantity > 0 else {}), (remainder if int(remainder.get("quantity", 0) or 0) > 0 else {})


def format_ammo_label(stack, quantity: int | None = None) -> str:
    normalized = normalize_ammo_stack(stack)
    if not normalized:
        return "ammo"
    amount = int(normalized.get("quantity", 0) or 0) if quantity is None else max(0, int(quantity or 0))
    name = str(normalized.get("name") or normalized.get("item_id") or "ammo")
    return f"{amount} {name}" if amount > 0 else name


def matches_ammo_query(stack, query: str) -> bool:
    normalized = normalize_ammo_stack(stack)
    lowered = str(query or "").strip().lower()
    if not normalized or not lowered:
        return False
    haystacks = {
        str(normalized.get("name") or "").strip().lower(),
        str(normalized.get("item_id") or "").strip().lower(),
        str(normalized.get("ammo_type") or "").strip().lower(),
    }
    return any(lowered in text for text in haystacks if text)


def find_matching_ammo_stack(stacks, query: str) -> tuple[int, dict]:
    for index, raw in enumerate(list(stacks or [])):
        if matches_ammo_query(raw, query):
            return index, normalize_ammo_stack(raw)
    return -1, {}