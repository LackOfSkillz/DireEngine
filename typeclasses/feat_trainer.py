from __future__ import annotations

from engine.services.feat_training_service import FeatTrainerService
from typeclasses.npcs import NPC


class FeatTrainerNPC(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_trainer = True
        self.db.trainer_kind = "feat"
        self.db.greeting = (
            f"{self.key} studies you with a patient, analytic calm. ASK {self.key} ABOUT FEAT if you want guidance on magical feats."
        )

    def resolve_feat(self, query):
        return FeatTrainerService.resolve_feat_query(query)

    def describe_feat(self, feat):
        requirements = ", ".join(
            f"{skill.replace('_', ' ')} {int(rank or 0)}" for skill, rank in dict(feat.requirements or {}).items()
        )
        if not requirements:
            requirements = "none"
        prerequisites = list(feat.prerequisites or [])
        prereq_text = ""
        if prerequisites:
            prereq_text = f" Prerequisites: {', '.join(item.replace('_', ' ').title() for item in prerequisites)}."
        return (
            f"{feat.name} ({feat.category}): {feat.description} Requirements: {requirements}."
            f" Slot cost: {int(feat.slot_cost or 0)}.{prereq_text}"
        )

    def describe_learning_path(self, actor, feat):
        check = FeatTrainerService.can_learn_feat(actor, feat.id)
        if check.success:
            return (
                f"You are ready to learn {feat.name}. It will consume {int(check.needed_slots or 0)} slot"
                f"{'s' if int(check.needed_slots or 0) != 1 else ''}, and you currently have {int(check.available_slots or 0)} available."
            )
        if check.reason == "already_known":
            return f"You already know {feat.name}."
        if check.reason == "not_magic_user":
            return "You do not use a magic slot pool, so magical feats are closed to you."
        if check.reason == "profession_restricted":
            return f"{feat.name} is restricted to another profession."
        if check.reason == "insufficient_slots":
            return (
                f"You need {int(check.needed_slots or 0)} slot{'s' if int(check.needed_slots or 0) != 1 else ''} for {feat.name}, "
                f"but only have {int(check.available_slots or 0)} available."
            )
        if check.reason == "missing_prerequisites":
            names = []
            for feat_id in list(check.missing_prerequisites or []):
                prereq = FeatTrainerService.resolve_feat_query(feat_id)
                names.append(prereq.name if prereq is not None else feat_id.replace("_", " ").title())
            return f"You must learn these feats first: {', '.join(names)}."
        if check.reason == "insufficient_skills":
            details = []
            for skill_name, values in dict(check.missing_skills or {}).items():
                details.append(
                    f"{skill_name.replace('_', ' ').title()} {int(values.get('current', 0) or 0)}/{int(values.get('required', 0) or 0)}"
                )
            return f"You need more skill before {feat.name}: {'; '.join(details)}."
        return f"You cannot learn {feat.name} right now."

    def describe_forgetting_path(self, actor, feat):
        check = FeatTrainerService.can_forget_feat(actor, feat.id)
        if check.success:
            return (
                f"I can help you forget {feat.name} for {int(check.cost_coins or 0)} kronar. "
                f"You will recover the {int(feat.slot_cost or 0)} slot{'s' if int(feat.slot_cost or 0) != 1 else ''} it occupies."
            )
        if check.reason == "granted_feat_cannot_be_forgotten":
            return f"{feat.name} was granted by your guild and cannot be forgotten."
        if check.reason == "not_learned":
            return f"You do not know {feat.name}."
        if check.reason == "has_dependents":
            return f"You must first forget the feats that depend on {feat.name}: {', '.join(check.dependent_feats or [])}."
        return f"You cannot forget {feat.name} right now."

    def handle_inquiry(self, actor, topic):
        normalized = str(topic or "").strip().lower()
        if not normalized or normalized == "feat":
            return (
                "Magical feats are passive abilities purchased with the same slot pool used by your memorized spells. "
                f"Ask {self.key} about a feat by name, about learning a feat, or about forgetting a feat."
            )

        if normalized.startswith("learning "):
            feat = self.resolve_feat(normalized[9:])
            if feat is None:
                return f"I know of no such feat as '{normalized[9:].strip()}'."
            return self.describe_learning_path(actor, feat)

        if normalized.startswith("forgetting "):
            feat = self.resolve_feat(normalized[11:])
            if feat is None:
                return f"I know of no such feat as '{normalized[11:].strip()}'."
            return self.describe_forgetting_path(actor, feat)

        feat = self.resolve_feat(normalized)
        if feat is not None:
            return self.describe_feat(feat)
        return super().handle_inquiry(actor, topic)