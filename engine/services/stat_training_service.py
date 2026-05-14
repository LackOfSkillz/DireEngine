"""Stat training consult/commit flow for LEARN-002b."""

from dataclasses import dataclass
import time

from domain.learning.tdp_cost import tdp_cost_to_raise
from world.races.utils import get_racial_tdp_modifier


CONSULT_WINDOW_SECONDS = 60


@dataclass
class TrainingResult:
    ok: bool
    message: str
    room_message: str | None = None
    target_message: str | None = None
    stat: str | None = None
    cost: int = 0
    new_value: int = 0


class StatTrainingService:
    @staticmethod
    def _display_name(character):
        return getattr(character, "key", None) or getattr(character, "name", None) or "Someone"

    @staticmethod
    def find_trainer_in_room(character):
        if not getattr(character, "location", None):
            return None
        from typeclasses.npcs import StatTrainerNPC

        for obj in list(getattr(character.location, "contents", []) or []):
            if isinstance(obj, StatTrainerNPC):
                return obj
        return None

    @staticmethod
    def consult(character):
        trainer = StatTrainingService.find_trainer_in_room(character)
        if not trainer:
            return TrainingResult(False, "You are not at a stat trainer.")

        stat = str(getattr(trainer.db, "trains_stat", "") or "").strip().lower()
        if not stat:
            return TrainingResult(False, "This trainer is not yet operational.")

        current_stats = dict(getattr(character.db, "stats", {}) or {})
        current_value = int(current_stats.get(stat, 0) or 0)
        race = getattr(character.db, "race", "human") or "human"
        modifier = get_racial_tdp_modifier(race, stat)
        cost = tdp_cost_to_raise(current_value, modifier)
        available = int(getattr(character.db, "tdp", 0) or 0)

        if cost > available:
            return TrainingResult(
                False,
                f"{trainer.key} studies you and says, 'To raise your {stat.title()} from {current_value} to {current_value + 1} would cost {cost} TDPs. You have only {available}.'",
                stat=stat,
                cost=cost,
            )

        character.ndb.train_consult_state = {
            "stat": stat,
            "trainer_id": getattr(trainer, "id", None),
            "cost": cost,
            "current_value": current_value,
            "timestamp": time.time(),
        }
        return TrainingResult(
            True,
            f"{trainer.key} examines you carefully. 'To raise your {stat.title()} from {current_value} to {current_value + 1} will cost {cost} Time Development Points. Type TRAIN COMMIT to confirm.'",
            room_message=f"{StatTrainingService._display_name(character)} listens closely as {trainer.key} evaluates their {stat.title()} training.",
            stat=stat,
            cost=cost,
            new_value=current_value + 1,
        )

    @staticmethod
    def commit(character):
        state = getattr(character.ndb, "train_consult_state", None)
        if not state:
            return TrainingResult(False, "You have not yet consulted with a trainer. Type TRAIN first.")
        if time.time() - float(state.get("timestamp", 0.0) or 0.0) > CONSULT_WINDOW_SECONDS:
            character.ndb.train_consult_state = None
            return TrainingResult(False, "Too much time has passed. Type TRAIN to consult again.")

        trainer = StatTrainingService.find_trainer_in_room(character)
        if not trainer or getattr(trainer, "id", None) != state.get("trainer_id"):
            character.ndb.train_consult_state = None
            return TrainingResult(False, "You are no longer with the same trainer. Type TRAIN to consult again.")

        stat = str(state.get("stat") or "").strip().lower()
        cost = int(state.get("cost", 0) or 0)
        current_value = int(state.get("current_value", 0) or 0)
        available = int(getattr(character.db, "tdp", 0) or 0)
        if available < cost:
            character.ndb.train_consult_state = None
            return TrainingResult(False, "You no longer have enough TDPs.")

        if not hasattr(character, "spend_tdp") or not character.spend_tdp(cost, reason=f"stat_train_{stat}"):
            character.ndb.train_consult_state = None
            return TrainingResult(False, "You cannot spend those TDPs right now.")

        stats = dict(getattr(character.db, "stats", {}) or {})
        stats[stat] = current_value + 1
        character.db.stats = stats
        character.ndb.train_consult_state = None
        if hasattr(character, "sync_client_state"):
            character.sync_client_state()
        return TrainingResult(
            True,
            f"{trainer.key} nods once. You feel your {stat.title()} sharpen to {current_value + 1}.",
            room_message=f"{StatTrainingService._display_name(character)} trains with {trainer.key}, their {stat.title()} visibly sharpening.",
            stat=stat,
            cost=cost,
            new_value=current_value + 1,
        )