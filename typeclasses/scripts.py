"""
Scripts

Scripts are powerful jacks-of-all-trades. They have no in-game
existence and can be used to represent persistent game systems in some
circumstances. Scripts can also have a time component that allows them
to "fire" regularly or a limited number of times.

There is generally no "tree" of Scripts inheriting from each other.
Rather, each script tends to inherit from the base Script class and
just overloads its hooks to have it perform its function.

"""

import time
import random

from evennia.scripts.scripts import DefaultScript
from evennia.utils import logger


GUARD_BEHAVIOR_MIN_INTERVAL = 25.0
GUARD_BEHAVIOR_MAX_INTERVAL = 45.0


def _roll_guard_behavior_interval():
    return random.uniform(GUARD_BEHAVIOR_MIN_INTERVAL, GUARD_BEHAVIOR_MAX_INTERVAL)


def _roll_guard_behavior_start_delay(interval_seconds):
    interval_seconds = max(1.0, float(interval_seconds or GUARD_BEHAVIOR_MIN_INTERVAL))
    return random.uniform(0.0, interval_seconds)


class Script(DefaultScript):
    """
    This is the base TypeClass for all Scripts. Scripts describe
    all entities/systems without a physical existence in the game world
    that require database storage (like an economic system or
    combat tracker). They
    can also have a timer/ticker component.

    A script type is customized by redefining some or all of its hook
    methods and variables.

    * available properties (check docs for full listing, this could be
      outdated).

     key (string) - name of object
     name (string)- same as key
     aliases (list of strings) - aliases to the object. Will be saved
              to database as AliasDB entries but returned as strings.
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation
     permissions (list of strings) - list of permission strings

     desc (string)      - optional description of script, shown in listings
     obj (Object)       - optional object that this script is connected to
                          and acts on (set automatically by obj.scripts.add())
     interval (int)     - how often script should run, in seconds. <0 turns
                          off ticker
     start_delay (bool) - if the script should start repeating right away or
                          wait self.interval seconds
     repeats (int)      - how many times the script should repeat before
                          stopping. 0 means infinite repeats
     persistent (bool)  - if script should survive a server shutdown or not
     is_active (bool)   - if script is currently running

    * Handlers

     locks - lock-handler: use locks.add() to add new lock strings
     db - attribute-handler: store/retrieve database attributes on this
                        self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not
                        create a database entry when storing data

    * Helper methods

     create(key, **kwargs)
     start() - start script (this usually happens automatically at creation
               and obj.script.add() etc)
     stop()  - stop script, and delete it
     pause() - put the script on hold, until unpause() is called. If script
               is persistent, the pause state will survive a shutdown.
     unpause() - restart a previously paused script. The script will continue
                 from the paused timer (but at_start() will be called).
     time_until_next_repeat() - if a timed script (interval>0), returns time
                 until next tick

    * Hook methods (should also include self as the first argument):

     at_script_creation() - called only once, when an object of this
                            class is first created.
     is_valid() - is called to check if the script is valid to be running
                  at the current time. If is_valid() returns False, the running
                  script is stopped and removed from the game. You can use this
                  to check state changes (i.e. an script tracking some combat
                  stats at regular intervals is only valid to run while there is
                  actual combat going on).
      at_start() - Called every time the script is started, which for persistent
                  scripts is at least once every server start. Note that this is
                  unaffected by self.delay_start, which only delays the first
                  call to at_repeat().
      at_repeat() - Called every self.interval seconds. It will be called
                  immediately upon launch unless self.delay_start is True, which
                  will delay the first call of this method by self.interval
                  seconds. If self.interval==0, this method will never
                  be called.
      at_pause()
      at_stop() - Called as the script object is stopped and is about to be
                  removed from the game, e.g. because is_valid() returned False.
      at_script_delete()
      at_server_reload() - Called when server reloads. Can be used to
                  save temporary variables you want should survive a reload.
      at_server_shutdown() - called at a full server shutdown.
      at_server_start()

    """

    def _track_repeat_timing(self, source, callback):
        started_at = time.perf_counter()
        try:
            return callback()
        finally:
            from tools.diretest.core.runtime import record_script_delay

            record_script_delay((time.perf_counter() - started_at) * 1000.0, source=source)


class BleedTicker(Script):
    def at_script_creation(self):
        self.key = "bleed_ticker"
        self.interval = 1
        self.start_delay = True
        self.repeats = 0
        self.persistent = True

    def is_valid(self):
        return False

    def at_repeat(self):
        def _run():
            if self.obj and hasattr(self.obj, "process_bleed"):
                self.obj.process_bleed()

        self._track_repeat_timing("script:BleedTicker", _run)


class CorpseDecayScript(Script):
    def at_script_creation(self):
        self.key = "corpse_decay"
        self.interval = 30
        self.start_delay = True
        self.repeats = 0
        self.persistent = True

    def at_start(self):
        obj = self.obj
        if obj and hasattr(obj, "schedule_decay_transition"):
            obj.schedule_decay_transition()

    def is_valid(self):
        obj = self.obj
        return bool(obj and getattr(getattr(obj, "db", None), "is_corpse", False))

    def at_repeat(self):
        def _run():
            obj = self.obj
            if not obj or not getattr(obj.db, "is_corpse", False):
                return
            if hasattr(obj, "is_orphaned") and obj.is_orphaned():
                obj.delete()
                return
            now = time.time()
            vigil_until = float(getattr(obj.db, "devotional_vigil_until", 0.0) or 0.0)
            protected = bool(getattr(obj.db, "stabilized", False)) or now < vigil_until
            decay_scale = 1.0
            if getattr(obj, "location", None) and hasattr(obj.location, "get_death_zone_profile"):
                decay_scale = float(obj.location.get_death_zone_profile().get("corpse_decay_scale", 1.0) or 1.0)
            if not protected and hasattr(obj, "adjust_condition"):
                obj.adjust_condition(-((self.interval / 60.0) * decay_scale))
            if hasattr(obj, "get_memory_remaining") and obj.get_memory_remaining() <= 0:
                if hasattr(obj, "apply_memory_loss"):
                    obj.apply_memory_loss()

        self._track_repeat_timing("script:CorpseDecayScript", _run)


class GraveMaintenanceScript(Script):
    def at_script_creation(self):
        self.key = "grave_maintenance"
        self.interval = 60
        self.start_delay = True
        self.repeats = 0
        self.persistent = True

    def is_valid(self):
        obj = self.obj
        return bool(obj and getattr(getattr(obj, "db", None), "is_grave", False))

    def at_repeat(self):
        def _run():
            obj = self.obj
            if not obj or not getattr(getattr(obj, "db", None), "is_grave", False):
                return
            if hasattr(obj, "is_orphaned") and obj.is_orphaned():
                obj.delete()
                return
            expiry_remaining = float(getattr(obj, "get_expiry_remaining", lambda: 0.0)() or 0.0)
            owner = obj.get_owner() if hasattr(obj, "get_owner") else None
            if expiry_remaining > 0 and expiry_remaining <= 300 and owner and not bool(getattr(obj.db, "expiry_warned", False)):
                owner.msg("You feel your connection to your lost possessions fading.")
                obj.db.expiry_warned = True
            if hasattr(obj, "process_expiry") and obj.process_expiry(now=time.time()):
                return
            if hasattr(obj, "increment_grave_damage"):
                obj.increment_grave_damage(1)
            obj.db.last_grave_damage_tick = time.time()

        self._track_repeat_timing("script:GraveMaintenanceScript", _run)


class GlobalGuardPatrolScript(Script):
    def at_script_creation(self):
        from world.systems.guards import GUARD_TICK_INTERVAL

        self.key = "global_guard_patrol"
        self.interval = GUARD_TICK_INTERVAL
        self.start_delay = True
        self.repeats = 0
        self.persistent = True

    def at_start(self):
        now = time.time()
        self.db.start_count = int(getattr(self.db, "start_count", 0) or 0) + 1
        self.db.last_started_at = now
        self.db.last_started_message = (
            f"GlobalGuardPatrolScript STARTED at {now:.3f} interval={float(getattr(self, 'interval', 0.0) or 0.0)}"
        )

    def at_repeat(self):
        from django.conf import settings
        from world.systems.guards import GUARD_TICK_INTERVAL, emit_legacy_guard_tripwire, get_last_guard_tick_time, is_diresim_enabled, log_legacy_guard_runtime_block, process_guard_tick

        def _run():
            now = time.time()
            self.db.repeat_count = int(getattr(self.db, "repeat_count", 0) or 0) + 1
            self.db.last_repeat_at = now
            if is_diresim_enabled():
                self.db.last_repeat_result = "blocked_by_diresim"
                emit_legacy_guard_tripwire("GlobalGuardPatrolScript.at_repeat")
                log_legacy_guard_runtime_block("GlobalGuardPatrolScript.at_repeat")
                return
            owner = str(getattr(settings, "GUARD_PATROL_OWNER", "global_script") or "global_script").strip().lower()
            mode = str(getattr(settings, "GUARD_PATROL_MODE", "global") or "global").strip().lower()
            if owner != "global_script" or not bool(getattr(settings, "ENABLE_GUARD_SYSTEM", True)):
                self.db.last_repeat_result = "owner_disabled"
                return
            if mode == "per_guard":
                self.db.last_repeat_result = "per_guard_mode"
                return
            if (time.time() - get_last_guard_tick_time()) < float(GUARD_TICK_INTERVAL):
                self.db.last_repeat_result = "cooldown_skip"
                return
            summary = process_guard_tick(source="global_script")
            self.db.last_repeat_result = str(summary.get("source", "global_script")) if isinstance(summary, dict) else "processed"

        self._track_repeat_timing("script:GlobalGuardPatrolScript", _run)


class GlobalSimulationKernelScript(Script):
    def at_script_creation(self):
        self.key = "global_simulation_kernel"
        self.interval = 1.0
        self.start_delay = True
        self.repeats = 0
        self.persistent = True

    def at_start(self):
        now = time.time()
        self.db.start_count = int(getattr(self.db, "start_count", 0) or 0) + 1
        self.db.last_started_at = now
        self.db.last_started_message = (
            f"GlobalSimulationKernelScript STARTED at {now:.3f} interval={float(getattr(self, 'interval', 0.0) or 0.0)}"
        )

    def at_repeat(self):
        from django.conf import settings
        from world.simulation.kernel import SIM_KERNEL

        def _run():
            now = time.time()
            self.db.repeat_count = int(getattr(self.db, "repeat_count", 0) or 0) + 1
            self.db.last_repeat_at = now
            if not bool(getattr(settings, "ENABLE_DIRESIM_KERNEL", True)):
                self.db.last_repeat_result = "disabled"
                return
            SIM_KERNEL.tick_fast()
            SIM_KERNEL.tick_normal()
            SIM_KERNEL.tick_slow()
            self.db.last_repeat_result = "ticked"

        self._track_repeat_timing("script:GlobalSimulationKernelScript", _run)


class GuardBehaviorScript(Script):
    """
    Owns patrol/enforcement cadence for exactly one guard via ``self.obj``.

    This script is an object-attached per-guard owner and must never iterate
    all guards or recreate global scheduling behavior.
    """

    def at_script_creation(self):
        self.key = "guard_behavior"
        self.interval = _roll_guard_behavior_interval()
        self.start_delay = True
        self.repeats = 0
        self.persistent = True
        self.db.base_interval = float(self.interval)
        self.db.start_delay_seconds = _roll_guard_behavior_start_delay(self.interval)

    def roll_timing(self):
        self.interval = _roll_guard_behavior_interval()
        self.db.base_interval = float(self.interval)
        self.db.start_delay_seconds = _roll_guard_behavior_start_delay(self.interval)
        return float(self.interval), float(self.db.start_delay_seconds or 0.0)

    def is_valid(self):
        obj = self.obj
        return bool(obj and getattr(obj, "pk", None) and bool(getattr(getattr(obj, "db", None), "is_guard", False)))

    def at_start(self, **kwargs):
        from world.systems.guards import is_guard_script_diagnostic_target

        now = time.time()
        guard = self.obj
        guard_id = int(getattr(guard, "id", 0) or 0) if guard else 0
        self.db.start_count = int(getattr(self.db, "start_count", 0) or 0) + 1
        self.db.last_started_at = now
        self.db.last_start_guard_id = guard_id
        self.db.last_start_interval = float(getattr(self, "interval", 0.0) or 0.0)
        self.db.last_start_delay = bool(getattr(self, "start_delay", False))
        self.db.last_start_delay_seconds = float(getattr(self.db, "start_delay_seconds", 0.0) or 0.0)
        self.db.last_start_repeats = int(getattr(self, "repeats", 0) or 0)
        self.db.last_started_message = f"GuardBehaviorScript STARTED for guard {guard_id}"
        if is_guard_script_diagnostic_target(guard):
            logger.log_info(
                f"[Guards][Diag] GuardBehaviorScript STARTED for guard {guard_id} interval={self.interval} start_delay={self.start_delay} start_delay_seconds={self.db.last_start_delay_seconds} repeats={self.repeats}"
            )

    def at_repeat(self):
        from world.systems.guards import emit_legacy_guard_tripwire, is_diresim_enabled, is_guard_script_diagnostic_target, log_legacy_guard_runtime_block, process_guard_behavior_tick, should_guard_use_per_guard_execution

        def _run():
            now = time.time()
            guard = self.obj
            guard_id = int(getattr(guard, "id", 0) or 0) if guard else 0
            self.db.repeat_fire_count = int(getattr(self.db, "repeat_fire_count", 0) or 0) + 1
            self.db.last_repeat_at = now
            self.db.last_repeat_guard_id = guard_id
            self.db.last_interval_seconds = float(getattr(self, "interval", 0.0) or 0.0)
            self.db.last_is_active = bool(getattr(self, "is_active", False))
            self.db.last_fired_message = f"GuardBehaviorScript fired for guard {guard_id}"

            if is_diresim_enabled():
                self.db.last_behavior_called = False
                self.db.last_behavior_result = "blocked_by_diresim"
                emit_legacy_guard_tripwire(f"GuardBehaviorScript.at_repeat:{guard_id}")
                log_legacy_guard_runtime_block(f"GuardBehaviorScript.at_repeat:{guard_id}")
                return

            if not guard or not getattr(guard, "pk", None):
                self.db.last_behavior_result = "missing_obj"
                return
            if not bool(getattr(getattr(guard, "db", None), "is_guard", False)):
                self.db.last_behavior_result = "not_guard"
                return
            if not should_guard_use_per_guard_execution(guard):
                self.db.last_behavior_result = "not_owned_by_per_guard"
                return

            if is_guard_script_diagnostic_target(guard):
                logger.log_info(f"[Guards][Diag] GuardBehaviorScript fired for guard {guard_id} at {now:.3f}")

            result = process_guard_behavior_tick(guard, source=f"per_guard_script:{guard_id}")
            self.db.last_behavior_called = True
            self.db.last_behavior_result = str(result)
            if is_guard_script_diagnostic_target(guard):
                logger.log_info(f"[Guards][Diag] GuardBehaviorScript guard {guard_id} behavior result={result}")

        self._track_repeat_timing("script:GuardBehaviorScript", _run)
