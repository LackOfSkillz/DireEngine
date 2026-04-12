from world.systems.skills import SKILL_GROUPS, is_active, pulse


class PulseService:

    @staticmethod
    def process_skill_pulse(character, global_tick=None, max_skills=None, skill_group_offsets=None):
        if character is None or not hasattr(character, "exp_skills"):
            return 0

        resolved_tick = None if global_tick is None else int(global_tick)
        resolved_limit = max(0, int(max_skills or 0)) if max_skills is not None else None
        offsets = dict(skill_group_offsets or {})
        processed = 0

        for skill_name, skill in character.exp_skills.skills.items():
            if resolved_limit is not None and processed >= resolved_limit:
                break
            if not is_active(skill):
                continue
            if resolved_tick is not None:
                group = SKILL_GROUPS.get(skill_name, 100)
                if resolved_tick != int(offsets.get(group, 0) or 0):
                    continue
            pulse(skill)
            processed += 1

        return processed