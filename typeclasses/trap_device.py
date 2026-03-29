import random
import time

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

    def has_expired(self):
        placed_time = self.db.placed_time
        expire_time = int(self.db.expire_time or 0)
        if placed_time is None or expire_time <= 0:
            return False
        return (time.time() - float(placed_time)) > expire_time

    def at_tick(self, **kwargs):
        if self.has_expired():
            self.delete()

    def is_active(self):
        if self.has_expired():
            self.delete()
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