from engine.services.result import ActionResult


class ManaPresenter:

    @staticmethod
    def render_failure(result):
        resolved = ManaPresenter._as_result(result)
        if resolved.success:
            return ""
        lines = ManaPresenter._render_errors(resolved)
        return " ".join(lines).strip()

    @staticmethod
    def _as_result(result):
        if isinstance(result, ActionResult):
            return result
        return ActionResult.fail(errors=["Invalid mana result."])

    @staticmethod
    def _render_errors(result):
        lines = []
        for error in list(result.errors or []):
            text = str(error or "").strip()
            if text:
                lines.append(text)
        return lines

    @staticmethod
    def render_prepare(result):
        resolved = ManaPresenter._as_result(result)
        if not resolved.success:
            return ManaPresenter._render_errors(resolved)
        data = dict(resolved.data or {})
        mana_input = int(data.get("mana_input", 0))
        prep_cost = int(data.get("prep_cost", 0))
        realm = str(data.get("realm", "mana") or "mana")
        spell_name = str(data.get("spell_name", "") or "").strip()
        if spell_name:
            return [f"You shape {mana_input} {realm} mana into {spell_name} at a cost of {prep_cost} attunement."]
        return [f"You shape {mana_input} {realm} mana into a prepared spell at a cost of {prep_cost} attunement."]

    @staticmethod
    def render_harness(result):
        resolved = ManaPresenter._as_result(result)
        if not resolved.success:
            return ManaPresenter._render_errors(resolved)
        data = dict(resolved.data or {})
        requested = int(data.get("requested_harness", 0))
        spent = int(data.get("attunement_spent", 0))
        held = int(data.get("held_mana", 0))
        return [f"You harness {requested} mana, spending {spent} attunement and raising held mana to {held}."]

    @staticmethod
    def render_cast(result):
        resolved = ManaPresenter._as_result(result)
        if not resolved.success:
            return ManaPresenter._render_errors(resolved)
        data = dict(resolved.data or {})
        power = float(data.get("final_spell_power", 0.0))
        backlash = float(data.get("backlash_chance", 0.0))
        realm = str(data.get("realm", "mana") or "mana")
        spell_name = str(data.get("spell_name", "") or "").strip()
        band = str(data.get("success_band", data.get("band", "solid")) or "solid").strip().lower()
        spell_label = spell_name or f"the prepared {realm} spell"
        if band == "excellent":
            return [f"You cast {spell_label} with exceptional control at {power:.1f} power and {backlash:.1f}% backlash risk."]
        if band == "partial":
            return [f"You cast {spell_label}, but the pattern forms weakly at {power:.1f} power."]
        if band == "failure":
            return [f"{spell_label.capitalize()} fizzles before it can take hold."]
        if band == "backlash":
            return [f"Your control over {spell_label} breaks in a violent backlash."]
        if spell_name:
            return [f"You cast {spell_name} with {power:.1f} final power and {backlash:.1f}% backlash risk."]
        return [f"You cast the prepared {realm} spell with {power:.1f} final power and {backlash:.1f}% backlash risk."]