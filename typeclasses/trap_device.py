import random
import time

from django.db import close_old_connections
from evennia.objects.objects import DefaultObject


class TrapDevice(DefaultObject):
    def at_object_creation(self):
        self.db.is_trap_device = True
        self.db.owner = None
        self.db.trap_type = "needle"
        self.db.hidden = True
        self.db.armed = True
        self.db.triggered = False
        self.db.expire_time = 60
        self.db.placed_time = None
        self.db.concealment = 0
        self.db.detected_by = []

    def at_init(self):
        super().at_init()
        if getattr(self.db, "is_trap_device", False):
            self.schedule_expiry()

    def at_object_delete(self):
        self.cancel_expiry()
        return super().at_object_delete()

    def _get_expiry_schedule_key(self):
        object_id = int(getattr(self, "id", 0) or 0)
        if object_id > 0:
            return f"trap:expiry:{object_id}"
        dbref = str(getattr(self, "dbref", "") or "").strip().lstrip("#")
        if dbref.isdigit():
            return f"trap:expiry:{dbref}"
        stable_name = str(getattr(self, "key", "trap") or "trap").strip().lower().replace(" ", "-")
        return f"trap:expiry:{stable_name}"

    def get_expiry_timestamp(self):
        placed_time = float(getattr(self.db, "placed_time", 0.0) or 0.0)
        expire_time = float(getattr(self.db, "expire_time", 0.0) or 0.0)
        if placed_time <= 0.0 or expire_time <= 0.0:
            return 0.0
        return placed_time + expire_time

    def cancel_expiry(self):
        from world.systems.scheduler import cancel

        return cancel(self._get_expiry_schedule_key())

    def schedule_expiry(self):
        from world.systems.scheduler import schedule
        from world.systems.time_model import SCHEDULED_EXPIRY

        if not getattr(self.db, "is_trap_device", False):
            self.cancel_expiry()
            return None
        expiry_at = self.get_expiry_timestamp()
        if expiry_at <= 0.0 or not bool(getattr(self.db, "armed", False)) or bool(getattr(self.db, "triggered", False)):
            self.cancel_expiry()
            return None
        delay_seconds = max(0.0, expiry_at - time.time())
        return schedule(
            delay_seconds,
            self._expire_if_due,
            key=self._get_expiry_schedule_key(),
            system="world.trap_expiry",
            timing_mode=SCHEDULED_EXPIRY,
            expected_expiry_time=expiry_at,
        )

    def _expire_if_due(self, expected_expiry_time=None):
        if not getattr(self.db, "is_trap_device", False):
            return None
        current_expiry = self.get_expiry_timestamp()
        if current_expiry <= 0.0:
            return None
        if expected_expiry_time is not None and current_expiry > float(expected_expiry_time or 0.0) + 0.01:
            return None
        if time.time() + 0.01 < current_expiry:
            return None
        if bool(getattr(self.db, "triggered", False)):
            return None
        close_old_connections()
        try:
            self.delete()
        except Exception as error:
            if "database is locked" in str(error or "").lower():
                from world.systems.scheduler import schedule
                from world.systems.time_model import SCHEDULED_EXPIRY

                schedule(
                    0.1,
                    self._expire_if_due,
                    key=self._get_expiry_schedule_key(),
                    system="world.trap_expiry",
                    timing_mode=SCHEDULED_EXPIRY,
                    expected_expiry_time=current_expiry,
                )
                return False
            raise
        return True

    def has_expired(self):
        expiry_at = self.get_expiry_timestamp()
        if expiry_at <= 0.0:
            return False
        return time.time() >= expiry_at

    def at_tick(self, **kwargs):
        return self._expire_if_due(expected_expiry_time=self.get_expiry_timestamp())

    def is_active(self):
        if self.has_expired():
            self._expire_if_due(expected_expiry_time=self.get_expiry_timestamp())
            return False
        return bool(self.db.armed) and not bool(self.db.triggered)

    def remember_detection(self, observer):
        if not observer or getattr(observer, "id", None) is None:
            return
        detected_by = set(self.db.detected_by or [])
        detected_by.add(observer.id)
        self.db.detected_by = sorted(detected_by)

    def check_trigger(self, target):
        if not self.is_active() or not target:
            return False

        owner = self.db.owner
        if owner is None or target == owner:
            return False
        if getattr(target, "location", None) != self.location:
            return False

        if random.random() > 0.25:
            return False

        self.trigger(target)
        return True

    def trigger(self, target):
        if not self.is_active() or not target:
            return False

        self.cancel_expiry()
        self.db.triggered = True
        self.db.armed = False

        owner = self.db.owner
        if owner and getattr(owner, "pk", None):
            owner.msg("Your trap detonates!")

        if target and getattr(target, "account", None):
            target.msg("A hidden trap detonates near you!")

        if self.location:
            self.location.msg_contents("A concealed device suddenly detonates!", exclude=[owner, target])

        if hasattr(target, "apply_box_trap_effect"):
            target.apply_box_trap_effect(self.db.trap_type)

        self.delete()
        return True