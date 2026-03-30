from collections.abc import Mapping
import time

from evennia.objects.objects import DefaultObject
from evennia.utils.create import create_object
from evennia.utils.search import search_object

from .objects import ObjectParent


class Corpse(ObjectParent, DefaultObject):
    """Minimal corpse object used by death, depart, and resurrection flows."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_corpse = True
        self.db.owner_id = None
        self.db.owner_name = self.key
        self.db.death_timestamp = 0.0
        self.db.decay_time = 0.0
        self.db.memory_time = 0.0
        self.db.memory_faded = False
        self.db.memory_loss_applied = False
        self.db.favor_snapshot = None
        self.db.condition = 100.0
        self.db.stabilized = False
        self.db.preserve_stacks = 0
        self.db.preparation_stacks = 0
        self.db.devotional_vigil_until = 0.0
        self.db.irrecoverable = False
        self.db.resurrection_failures = 0
        self.db.stored_coins = 0
        self.db.recovery_allowed = []
        self.locks.add("get:false()")

    def get_decay_remaining(self):
        return max(0.0, float(getattr(self.db, "decay_time", 0.0) or 0.0) - time.time())

    def get_memory_remaining(self):
        return max(0.0, float(getattr(self.db, "memory_time", 0.0) or 0.0) - time.time())

    def has_viable_memory(self):
        return self.get_memory_remaining() > 0 and not bool(getattr(self.db, "memory_faded", False))

    def get_memory_state(self):
        remaining = self.get_memory_remaining()
        if remaining <= 0 or bool(getattr(self.db, "memory_faded", False)):
            return "lost"
        if remaining >= 300:
            return "clear"
        if remaining >= 120:
            return "fading"
        return "critical"

    def get_resurrection_condition_state(self):
        condition = self.get_condition()
        decay_remaining = self.get_decay_remaining()
        if not self.has_viable_memory() or condition < 25 or decay_remaining <= 60:
            return "DECAYING"
        if condition >= 75 and decay_remaining >= 360:
            return "INTACT"
        if condition >= 50 and decay_remaining >= 180:
            return "FADING"
        return "CRITICAL"

    def extend_memory(self, seconds, stacks=1):
        current = max(time.time(), float(getattr(self.db, "memory_time", 0.0) or 0.0))
        self.db.memory_time = current + max(0.0, float(seconds or 0.0))
        self.db.memory_faded = False
        self.db.preserve_stacks = max(0, int(getattr(self.db, "preserve_stacks", 0) or 0)) + max(0, int(stacks or 0))
        return self.get_memory_remaining()

    def add_preparation(self, amount=1):
        updated = min(5, max(0, int(getattr(self.db, "preparation_stacks", 0) or 0)) + max(0, int(amount or 0)))
        self.db.preparation_stacks = updated
        return updated

    def apply_memory_loss(self):
        if bool(getattr(self.db, "memory_loss_applied", False)):
            return False
        self.db.memory_faded = True
        self.db.memory_loss_applied = True
        owner = self.get_owner()
        if owner and hasattr(owner, "adjust_exp_debt"):
            owner.adjust_exp_debt(25)
            owner.msg("You feel vital memories slipping beyond recall.")
        return True

    def get_condition(self):
        return max(0.0, min(100.0, float(getattr(self.db, "condition", 100.0) or 0.0)))

    def get_condition_tier(self):
        condition = self.get_condition()
        if condition >= 75:
            return "Fresh"
        if condition >= 50:
            return "Degrading"
        if condition >= 25:
            return "Damaged"
        return "Ruined"

    def update_condition_description(self):
        owner_name = self.db.owner_name or "a fallen adventurer"
        tier = self.get_condition_tier()
        condition = int(round(self.get_condition()))
        if tier == "Fresh":
            detail = "The body lies still, warmth not yet fully gone."
        elif tier == "Degrading":
            detail = "The body shows clear signs of decay."
        elif tier == "Damaged":
            detail = "The corpse is marred by time and neglect."
        else:
            detail = "The remains are barely recognizable."
        stabilized = " The careful work of an Empath has slowed the worst of the decay." if bool(getattr(self.db, "stabilized", False)) else ""
        memory_state = self.get_memory_state()
        if memory_state == "clear":
            memory_detail = " The soul's memories still cling clearly to the remains."
        elif memory_state == "fading":
            memory_detail = " Lingering memories are beginning to fray."
        elif memory_state == "critical":
            memory_detail = " Only a fragile trace of memory remains."
        else:
            memory_detail = " The lingering memories have faded away."
        if self.db.owner_name:
            subject = f"The body of {owner_name} lies here."
        else:
            subject = "The body of a fallen adventurer lies here."
        self.db.desc = f"{subject} {detail} Condition: {condition}/100.{stabilized}{memory_detail}"

    def adjust_condition(self, amount):
        current = self.get_condition()
        self.db.condition = max(0.0, min(100.0, current + float(amount or 0.0)))
        self.update_condition_description()
        return self.get_condition()

    def is_owner(self, player):
        return int(getattr(player, "id", 0) or 0) == int(getattr(self.db, "owner_id", 0) or 0)

    def get_recovery_allowed_ids(self):
        raw = getattr(self.db, "recovery_allowed", None) or []
        allowed = set()
        for entry in raw:
            try:
                value = int(entry)
            except (TypeError, ValueError):
                continue
            if value > 0:
                allowed.add(value)
        owner_id = int(getattr(self.db, "owner_id", 0) or 0)
        if owner_id > 0:
            allowed.add(owner_id)
        return allowed

    def is_recovery_allowed(self, player):
        player_id = int(getattr(player, "id", 0) or 0)
        return player_id > 0 and player_id in self.get_recovery_allowed_ids()

    def grant_recovery_access(self, player):
        allowed = self.get_recovery_allowed_ids()
        player_id = int(getattr(player, "id", 0) or 0)
        if player_id > 0:
            allowed.add(player_id)
        self.db.recovery_allowed = sorted(allowed)
        return self.db.recovery_allowed

    def revoke_recovery_access(self, player):
        allowed = self.get_recovery_allowed_ids()
        owner_id = int(getattr(self.db, "owner_id", 0) or 0)
        player_id = int(getattr(player, "id", 0) or 0)
        if player_id > 0 and player_id != owner_id:
            allowed.discard(player_id)
        self.db.recovery_allowed = sorted(allowed)
        return self.db.recovery_allowed

    def get_owner(self):
        owner_id = int(getattr(self.db, "owner_id", 0) or 0)
        if owner_id <= 0:
            return None
        result = search_object(f"#{owner_id}")
        return result[0] if result else None

    def is_orphaned(self):
        return self.get_owner() is None

    def get_favor_snapshot(self):
        snapshot = getattr(self.db, "favor_snapshot", None)
        return dict(snapshot) if isinstance(snapshot, Mapping) else None

    def _has_admin_access(self, accessing_obj):
        account = getattr(accessing_obj, "account", None)
        if not account:
            return False
        return account.check_permstring("Admin") or account.check_permstring("Developer")

    def access(self, accessing_obj, access_type="read", default=False, **kwargs):
        if access_type in {"view", "read", "search", "get"}:
            if self.is_recovery_allowed(accessing_obj) or self._has_admin_access(accessing_obj):
                return super().access(accessing_obj, access_type=access_type, default=default, **kwargs)
            return False
        return super().access(accessing_obj, access_type=access_type, default=default, **kwargs)

    def decay_to_grave(self):
        if not getattr(self.db, "is_corpse", False):
            return None
        location = self.location
        owner = self.get_owner()
        existing_grave = None
        if location:
            for obj in list(getattr(location, "contents", []) or []):
                if not getattr(getattr(obj, "db", None), "is_grave", False):
                    continue
                if int(getattr(obj.db, "owner_id", 0) or 0) == int(getattr(self.db, "owner_id", 0) or 0):
                    existing_grave = obj
                    break
        if existing_grave is None:
            for obj in search_object(f"grave of {self.db.owner_name or self.key}"):
                if getattr(getattr(obj, "db", None), "is_grave", False) and int(getattr(obj.db, "owner_id", 0) or 0) == int(getattr(self.db, "owner_id", 0) or 0):
                    existing_grave = obj
                    break
        if existing_grave:
            grave = existing_grave
            if location and grave.location != location:
                grave.move_to(location, quiet=True)
        else:
            grave = create_object(
                "typeclasses.grave.Grave",
                key=f"grave of {self.db.owner_name or self.key}",
                location=location,
                home=location,
            )
        grave.db.owner_id = self.db.owner_id
        grave.db.owner_name = self.db.owner_name or self.key
        grave.db.creation_time = time.time()
        grave.db.stored_items = list(getattr(grave.db, "stored_items", []) or [])
        grave.db.stored_coins = int(getattr(grave.db, "stored_coins", 0) or 0) + int(getattr(self.db, "stored_coins", 0) or 0)
        grave.db.recovery_allowed = sorted(self.get_recovery_allowed_ids())
        grave.db.last_grave_damage_tick = time.time()
        grave.db.expiry_time = time.time() + (24 * 60 * 60)
        grave.db.expiry_warned = False
        if location and hasattr(location, "is_shrine_room") and location.is_shrine_room():
            grave.db.desc = f"A small marker stone stands over the fresh grave of {grave.db.owner_name}."
        elif location and str(getattr(location.db, 'environment_type', '') or '').lower() in {"forest", "wilderness"}:
            grave.db.desc = f"A shallow grave marked by disturbed earth holds what remains of {grave.db.owner_name}."
        else:
            grave.db.desc = f"A rough grave marks where {grave.db.owner_name} was laid to rest."
        grave.db.corpse_condition = self.get_condition()

        stored_items = []
        for item in list(self.contents):
            if item.move_to(grave, quiet=True):
                item.db.grave_damage = 0
                stored_items.append(item.id)
        grave.db.stored_items = list(dict.fromkeys(list(getattr(grave.db, "stored_items", []) or []) + stored_items))
        grave.scripts.add("typeclasses.scripts.GraveMaintenanceScript")

        if owner and int(getattr(owner.db, "last_corpse_id", 0) or 0) == int(self.id or 0):
            owner.db.last_corpse_id = None
            if hasattr(owner, "sync_client_state"):
                owner.sync_client_state()
            if hasattr(owner, "emit_death_event"):
                owner.emit_death_event("on_grave_created", grave=grave, corpse=self)

        self.delete()
        return grave
