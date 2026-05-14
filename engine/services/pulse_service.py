from engine.services.rexp_service import REXP_DRAIN_MULTIPLIER, consume_rexp_for_group_pulse
from world.systems.skills import get_skill_pulse_group, is_active, pulse


class PulseService:

    @staticmethod
    def process_skill_pulse(character, global_tick=None, max_skills=None, skill_group_offsets=None):
        if character is None or not hasattr(character, "exp_skills"):
            return 0
        if hasattr(character, "ensure_sleep_defaults"):
            character.ensure_sleep_defaults()
        if hasattr(character, "is_in_deep_sleep") and character.is_in_deep_sleep():
            return 0

        resolved_tick = None if global_tick is None else int(global_tick)
        resolved_limit = max(0, int(max_skills or 0)) if max_skills is not None else None
        offsets = dict(skill_group_offsets or {})
        processed = 0
        matching_skills = []

        for skill_name, skill in character.exp_skills.skills.items():
            if hasattr(character, "is_in_light_sleep") and character.is_in_light_sleep():
                active = float(getattr(skill, "pool", 0.0) or 0.0) > 0.0
            else:
                active = is_active(skill)
            if not active:
                continue
            if resolved_tick is not None:
                group = get_skill_pulse_group(skill_name)
                if resolved_tick != int(offsets.get(group, 0) or 0):
                    continue
            matching_skills.append(skill)

        if resolved_limit is not None:
            matching_skills = matching_skills[:resolved_limit]

        group_drained = any(float(getattr(skill, "pool", 0.0) or 0.0) > 0.0 for skill in matching_skills)
        rexp_consumed = consume_rexp_for_group_pulse(character, group_drained=group_drained)
        drain_multiplier = REXP_DRAIN_MULTIPLIER if rexp_consumed else 1.0

        for skill in matching_skills:
            if drain_multiplier == 1.0:
                pulse(skill)
            else:
                pulse(skill, drain_multiplier=drain_multiplier)
            processed += 1

        return processed