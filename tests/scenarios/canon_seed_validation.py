from world.systems import canon_seed


def scenario(ctx):
    result = canon_seed.import_controlled_dataset(limit_per_category=20, reset=True)

    weapons = canon_seed.get_items_by_type("weapon")
    guards = canon_seed.get_guards()
    shopkeepers = canon_seed.get_shopkeepers()
    hostile = canon_seed.get_hostile_creatures()
    docile = canon_seed.get_docile_creatures()
    report_lines = canon_seed.generate_summary_report()
    failures = canon_seed.sample_broken_entries(limit_per_category=3)
    normalization_metrics = result.get("normalization_metrics") or {}

    if not isinstance(weapons, list):
        raise AssertionError("get_items_by_type('weapon') did not return a list.")
    if not isinstance(guards, list):
        raise AssertionError("get_guards() did not return a list.")
    if not isinstance(shopkeepers, list):
        raise AssertionError("get_shopkeepers() did not return a list.")
    if not isinstance(hostile, list):
        raise AssertionError("get_creatures_by_aggression('aggressive') did not return a list.")
    if not isinstance(docile, list):
        raise AssertionError("get_docile_creatures() did not return a list.")
    if int(result.get("audit_count", 0) or 0) <= 0:
        raise AssertionError("Canon seed import did not populate the audit table.")
    if not report_lines:
        raise AssertionError("Canon seed import did not produce a summary report.")
    if not all(isinstance(entry.get("normalized_fields"), dict) for entry in weapons[:5] + guards[:5] + docile[:5]):
        raise AssertionError("Normalized fields were not stored on imported canon records.")
    if guards and not all(entry.get("normalized_fields", {}).get("aggression_type") == "defensive" for entry in guards[:5]):
        raise AssertionError("Guard defaults did not normalize aggression_type to defensive.")
    if docile and not all(isinstance(entry.get("normalized_fields", {}).get("flee_behavior"), dict) for entry in docile[:5]):
        raise AssertionError("Docile creature defaults did not normalize flee_behavior.")
    if weapons and any("normalized_fields" in (entry.get("raw_json") or {}) for entry in weapons[:5]):
        raise AssertionError("raw_json was mutated during normalization.")

    ctx.log(
        {
            "imported": result.get("imported"),
            "audit_count": int(result.get("audit_count", 0) or 0),
            "weapon_query_count": len(weapons),
            "guard_query_count": len(guards),
            "shopkeeper_query_count": len(shopkeepers),
            "hostile_query_count": len(hostile),
            "docile_query_count": len(docile),
            "normalization_metrics": normalization_metrics,
            "report_lines": report_lines[:10],
        }
    )

    return {
        "imported": result.get("imported"),
        "summary": result.get("summary"),
        "audit_count": int(result.get("audit_count", 0) or 0),
        "weapon_query_count": len(weapons),
        "guard_query_count": len(guards),
        "shopkeeper_query_count": len(shopkeepers),
        "hostile_query_count": len(hostile),
        "docile_query_count": len(docile),
        "normalization_metrics": normalization_metrics,
        "report_lines": report_lines,
        "sample_failures": failures,
    }