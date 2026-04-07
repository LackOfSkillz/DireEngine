from evennia import DefaultScript as Script


class FirstAreaVendorPromptScript(Script):
    def at_script_creation(self):
        self.key = "first_area_vendor_prompt"
        self.interval = 6
        self.start_delay = True
        self.repeats = 0
        self.persistent = True

    def is_valid(self):
        obj = self.obj
        return bool(obj and getattr(getattr(obj, "db", None), "is_threshold_vendor", False))

    def at_repeat(self):
        obj = self.obj
        room = getattr(obj, "location", None)
        if not obj or not room:
            return
        from systems import first_area

        for occupant in list(getattr(room, "contents", []) or []):
            if not getattr(occupant, "has_account", False):
                continue
            if not first_area.should_prompt_vendor(occupant, idle_threshold=5.0):
                continue
            if first_area.emit_vendor_prompt(occupant, vendor=obj):
                break