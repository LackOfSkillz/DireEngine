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

from evennia.scripts.scripts import DefaultScript


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
