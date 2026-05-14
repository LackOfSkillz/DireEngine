from __future__ import annotations

from commands.command import Command
from domain.feats.feat_definitions import FEAT_REGISTRY
from engine.services.feat_training_service import FeatTrainerService
from engine.services.slot_service import SlotService


class CmdFeats(Command):
    """Display known and currently learnable magical feats."""

    key = "feats"
    help_category = "Magic"

    def func(self):
        caller = self.caller
        if hasattr(caller, "ensure_core_defaults"):
            caller.ensure_core_defaults()

        pool = SlotService.get_pool(caller)
        if pool is None:
            caller.msg("You are not a magic-using profession; you cannot learn feats.")
            return

        feats_state = getattr(getattr(caller, "db", None), "feats", {}) or {}
        learned = list(feats_state.get("learned", []) or [])
        granted = list(feats_state.get("granted", []) or [])
        lines = ["=== Magical Feats ==="]

        if granted:
            lines.append("")
            lines.append("Granted by your guild (no slot cost):")
            for feat_id in sorted(granted):
                feat = FEAT_REGISTRY.get(feat_id)
                if feat is not None:
                    lines.append(f"  - {feat.name} ({feat.category})")

        if learned:
            lines.append("")
            lines.append(f"Learned (consuming {len(learned)} slot{'s' if len(learned) != 1 else ''}):")
            for feat_id in sorted(learned):
                feat = FEAT_REGISTRY.get(feat_id)
                if feat is not None:
                    lines.append(f"  - {feat.name} ({feat.category})")

        available = []
        for feat in sorted(FEAT_REGISTRY.values(), key=lambda entry: entry.name.lower()):
            if feat.id in learned or feat.id in granted:
                continue
            if FeatTrainerService.can_learn_feat(caller, feat.id).success:
                available.append(feat)

        if available:
            lines.append("")
            lines.append(f"Available to learn ({SlotService.get_available_slots(caller)} slot(s) free):")
            for feat in available:
                lines.append(f"  - {feat.name} ({feat.category}) [{int(feat.slot_cost or 0)} slot]")

        if not learned and not granted and not available:
            lines.append("")
            lines.append("You do not currently qualify for any feats.")

        caller.msg("\n".join(lines))