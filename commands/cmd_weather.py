"""@weather admin command - inspect and set per-zone weather."""

from commands.command import Command
from world.weather import (
    _CLIMATE_COMPATIBILITY,
    get_current_weather,
    get_weather_state,
    is_weather_plausible_for_climate,
    resolve_climate,
    run_weather_cycle,
    set_current_weather,
)


ADMIN_PERMISSIONS = ("Admin", "Developer")


class CmdWeather(Command):
    """
    Inspect and set per-zone weather.

    Usage:
      @weather
      @weather <zone_id>
      @weather <zone_id> <state>
      @weather tick
    """

    key = "@weather"
    help_category = "Admin"
    locks = "cmd:perm(Admin) or perm(Developer)"

    def _is_admin(self):
        account = getattr(self.caller, "account", None)
        if not account:
            return False
        return any(account.check_permstring(permission) for permission in ADMIN_PERMISSIONS)

    def func(self):
        if not self._is_admin():
            self.caller.msg("You do not have permission to use this command.")
            return

        args = [part for part in str(self.args or "").split() if part]
        if not args:
            self._show_all()
            return
        if len(args) == 1 and args[0].strip().lower() == "tick":
            self._force_tick()
            return
        if len(args) == 1:
            self._show_zone(args[0])
            return
        self._set_zone(args[0], args[1])

    def _show_all(self):
        state = get_weather_state()
        lines = [
            "DireEngine Weather",
            "─" * 40,
        ]
        for zone in state["zones"]:
            plausibility = "plausible" if zone["plausible"] else "IMPLAUSIBLE — admin override"
            lines.append(
                f"{zone['zone_id'] + ':':18}{zone['weather']:<13} (climate: {zone['climate']}, {plausibility})"
            )
        lines.extend(["", "Active states:"])
        for weather, count in state["counts"].items():
            lines.append(f"  {weather + ':':13}{count}")
        real_minutes = float(state["tick_interval_game_seconds"]) / 60.0 / max(0.0001, float(__import__('django.conf').conf.settings.TIME_FACTOR))
        lines.extend(
            [
                "",
                f"Tick interval:   15 game-minutes (~{real_minutes:.2f} real minutes)",
                f"Lightning:       {int(state['lightning_probability'] * 100)}% chance per tick during storm",
                f"Last tick:       {state['last_tick'] or 'not yet recorded'}",
                f"Next tick:       {state['next_tick'] or 'unknown'} (estimated)",
            ]
        )
        self.caller.msg("\n".join(lines))

    def _show_zone(self, zone_id):
        state = get_weather_state()
        for zone in state["zones"]:
            if zone["zone_id"].lower() != str(zone_id).strip().lower():
                continue
            plausible_states = ", ".join(_CLIMATE_COMPATIBILITY.get(zone["climate"], []))
            lines = [
                f"Weather: {zone['zone_id']}",
                "─" * 32,
                f"Current state:   {zone['weather']}",
                f"Climate:         {zone['climate']} (resolved from {repr(zone['raw_climate'])})",
                f"Current season:  {zone['season']} (real-world)",
                "Plausible states for this climate:",
                f"  {plausible_states}",
            ]
            self.caller.msg("\n".join(lines))
            return
        self.caller.msg(f"Unknown zone: {zone_id}")

    def _set_zone(self, zone_id, weather):
        state = get_weather_state()
        target = None
        for zone in state["zones"]:
            if zone["zone_id"].lower() == str(zone_id).strip().lower():
                target = zone
                break
        if target is None:
            climate = resolve_climate(None)
        else:
            climate = target["climate"]
        warning = None
        if not is_weather_plausible_for_climate(weather, climate):
            warning = f"Warning: {weather} is implausible for climate {climate}, proceeding with admin override."
        set_current_weather(zone_id, weather, source="admin")
        lines = []
        if warning:
            lines.append(warning)
        lines.append(f"Weather for {zone_id} set to {get_current_weather(zone_id)}.")
        self.caller.msg("\n".join(lines))

    def _force_tick(self):
        transitions = run_weather_cycle()
        lines = ["Forced weather tick complete."]
        if transitions:
            lines.append("Transitions:")
            for zone_id, (old, new) in sorted(transitions.items()):
                lines.append(f"  {zone_id}: {old} -> {new}")
        else:
            lines.append("No zones changed state.")
        self.caller.msg("\n".join(lines))