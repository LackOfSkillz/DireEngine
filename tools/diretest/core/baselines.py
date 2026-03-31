"""Baseline persistence and delta helpers for DireTest."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path


BASELINE_FILE_VERSION = 1

METRIC_SPECS = [
    ("combat_damage", "combat damage"),
    ("combat_target_hp_after", "combat target hp after"),
    ("combat_entered", "combat entered"),
    ("combat_exited", "combat exited"),
    ("combat_duration_ms", "combat duration ms"),
    ("vendor_purchase_cost", "vendor purchase cost"),
    ("vendor_sale_return", "vendor sale return"),
    ("vendor_net_coin_delta", "vendor coin delta"),
    ("vendor_haggle_bonus", "vendor haggle bonus"),
    ("bank_deposit_delta", "bank deposit delta"),
    ("bank_withdraw_delta", "bank withdraw delta"),
    ("bank_net_carried_coin_delta", "bank carried coin delta"),
    ("onboarding_duration_ms", "onboarding duration ms"),
    ("onboarding_steps", "onboarding steps"),
    ("onboarding_tokens", "onboarding tokens"),
    ("onboarding_exit_ready", "onboarding exit ready"),
]


def _slugify_name(name):
    raw = str(name or "").strip().lower()
    slug = re.sub(r"[^a-z0-9_-]+", "-", raw).strip("-")
    if not slug:
        raise ValueError("Baseline name must contain at least one alphanumeric character.")
    return slug


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def get_baseline_root(base_path=None):
    return Path(base_path or (Path.cwd() / "artifacts" / "baselines"))


def get_baseline_path(name, base_path=None):
    return get_baseline_root(base_path=base_path) / f"{_slugify_name(name)}.json"


def normalize_balance_baseline(report):
    payload = dict(report or {})
    baselines = dict(payload.get("baselines", {}) or {})
    combat = dict(baselines.get("combat_outcomes", {}) or {})
    economy = dict(baselines.get("economy_flows", {}) or {})
    vendor_trade = dict(economy.get("vendor_trade", {}) or {})
    banking = dict(economy.get("banking", {}) or {})
    progression = dict(baselines.get("progression_pacing", {}) or {})

    return {
        "combat_damage": combat.get("hit_damage"),
        "combat_target_hp_after": combat.get("target_hp_after"),
        "combat_entered": bool(combat.get("entered_combat", False)),
        "combat_exited": bool(combat.get("exited_combat", False)),
        "combat_duration_ms": _safe_int(combat.get("duration_ms", 0), 0),
        "vendor_purchase_cost": _safe_int(vendor_trade.get("purchase_cost", 0), 0),
        "vendor_sale_return": _safe_int(vendor_trade.get("sale_return", 0), 0),
        "vendor_net_coin_delta": _safe_int(vendor_trade.get("net_coin_delta", 0), 0),
        "vendor_haggle_bonus": round(_safe_float(vendor_trade.get("haggle_bonus", 0.0), 0.0), 4),
        "bank_deposit_delta": _safe_int(banking.get("deposit_to_bank", 0), 0),
        "bank_withdraw_delta": _safe_int(banking.get("withdraw_to_hand", 0), 0),
        "bank_net_carried_coin_delta": _safe_int(banking.get("net_carried_coin_delta", 0), 0),
        "onboarding_duration_ms": _safe_int(progression.get("duration_ms", 0), 0),
        "onboarding_steps": _safe_int(progression.get("completed_step_count", 0), 0),
        "onboarding_tokens": _safe_int(progression.get("token_count", 0), 0),
        "onboarding_exit_ready": bool(progression.get("exit_ready", False)),
    }


def build_baseline_record(name, report):
    slug = _slugify_name(name)
    payload = dict(report or {})
    return {
        "version": BASELINE_FILE_VERSION,
        "name": slug,
        "saved_at": time.time(),
        "scenario": str(payload.get("scenario", "balance-baseline") or "balance-baseline"),
        "seed": _safe_int(payload.get("seed", 0), 0),
        "artifact_dir": str(payload.get("artifact_dir", "") or ""),
        "metrics": normalize_balance_baseline(payload),
    }


def save_named_baseline(name, report, base_path=None):
    path = get_baseline_path(name, base_path=base_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = build_baseline_record(name, report)
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return path, record


def load_named_baseline(name, base_path=None):
    path = get_baseline_path(name, base_path=base_path)
    if not path.exists():
        raise FileNotFoundError(f"Saved baseline not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return path, dict(payload or {})


def _numeric_delta(before, after):
    if isinstance(before, bool) or isinstance(after, bool):
        return None
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        return after - before
    return None


def compare_named_baseline(saved_record, current_report):
    baseline_metrics = dict((saved_record or {}).get("metrics", {}) or {})
    current_metrics = normalize_balance_baseline(current_report)
    deltas = []

    for key, label in METRIC_SPECS:
        before = baseline_metrics.get(key)
        after = current_metrics.get(key)
        entry = {
            "key": key,
            "label": label,
            "baseline": before,
            "current": after,
        }
        numeric_delta = _numeric_delta(before, after)
        if numeric_delta is not None:
            entry["delta"] = numeric_delta
        else:
            entry["changed"] = before != after
        deltas.append(entry)

    return {
        "baseline_metrics": baseline_metrics,
        "current_metrics": current_metrics,
        "deltas": deltas,
    }