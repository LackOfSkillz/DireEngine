"""
Skill system — core data structures (no logic yet)
"""

import time

from domain.learning.mindstate import MINDSTATE_BANDS, get_mindstate_band, get_mindstate_name as get_canonical_mindstate_name
from domain.learning.pool_size import total_pool_size, wisdom_pulse_multiplier
from domain.learning.skill_groups import get_skill_group_for_skill
from engine.bundles.builtin_skills import LEGACY_SKILL_PULSE_GROUPS, normalize_skill_registry_key
from engine.bundles.skill_registry import skill_registry
from engine.services.messaging import send_untargeted_action


VALID_SKILLSETS = ("primary", "secondary", "tertiary")
MINDSTATE_MAX = 34
MIND_LOCK = MINDSTATE_MAX
PULSE_INTERVAL = 200
PULSE_OFFSET = 20
ACTIVE_WINDOW = 600
GRACE_WINDOW = 30
FEEDBACK_THRESHOLD = 5
FEEDBACK_COOLDOWN = 10

MINDSTATE_NAMES = {value: band.name for value, band in MINDSTATE_BANDS.items()}

LEGACY_SKILL_ALIASES = {
    "hand_to_hand": "brawling",
    "lockpicking": "locksmithing",
}

FIRST_WAVE_EXP_SKILLS = (
    "evasion",
    "stealth",
    "perception",
    "brawling",
    "targeted_magic",
    "appraisal",
)

SECOND_WAVE_EXP_SKILLS = (
    "athletics",
    "locksmithing",
    "light_edge",
    "debilitation",
)

THIRD_WAVE_EXP_SKILLS = (
    "empathy",
    "first_aid",
    "scholarship",
)

TEMPLATE_EXP_SKILLS = (
    *FIRST_WAVE_EXP_SKILLS,
    *SECOND_WAVE_EXP_SKILLS,
    *THIRD_WAVE_EXP_SKILLS,
)

DRAIN_RATES = {
    "primary": 0.067,
    "secondary": 0.05025,
    "tertiary": 0.0335,
}

MAJOR_MINDSTATE_THRESHOLDS = {25, 30, 33, 34}
MIND_LOCK_NOTIFICATION_WINDOW_SECONDS = 1800

SKILL_GAIN_MODIFIERS = {
    "perception": 0.40,
    "stealth": 0.18,
}

EVENT_WEIGHTS = {
    "stealth": 1.0,
    "perception": 1.0,
    "brawling": 0.7,
    "light_edge": 0.6,
    "evasion": 0.5,
    "locksmithing": 2.5,
    "trap_disarm": 3.5,
}

DEFAULT_OUTCOME_MODIFIERS = {
    "success": 1.0,
    "strong": 1.0,
    "partial": 0.7,
    "failure": 0.5,
}

SUCCESS_MODIFIERS = {
    "stealth": {
        "success": 1.0,
        "strong": 1.0,
        "partial": 0.7,
        "failure": 0.35,
    },
}


def normalize_skill_name(name):
    normalized = str(name or "").strip().lower().replace(" ", "_")
    if not normalized:
        raise ValueError("Skill name cannot be empty.")
    return normalized


def resolve_skill_registry_key(name):
    normalized = normalize_skill_name(name)
    return LEGACY_SKILL_ALIASES.get(normalized, normalize_skill_registry_key(normalized))


def get_skill_definition(name):
    try:
        return skill_registry.get(resolve_skill_registry_key(name))
    except ValueError:
        return None


def get_skill_display_name(name):
    definition = get_skill_definition(name) or {}
    display_name = str(definition.get("display_name") or "").strip()
    if display_name:
        return display_name
    try:
        from typeclasses.characters import SKILL_REGISTRY  # Local import avoids module-cycle load order issues.

        metadata = dict(SKILL_REGISTRY.get(resolve_skill_registry_key(name), {}))
        display_name = str(metadata.get("display_name") or "").strip()
        if display_name:
            return display_name
    except Exception:
        pass
    return normalize_skill_name(name).replace("_", " ").title()


def list_skills_in_group(group):
    normalized_group = str(group or "").strip().lower()
    return sorted(
        key
        for key in skill_registry.list_keys()
        if str((skill_registry.get(key) or {}).get("group") or "").strip().lower() == normalized_group
    )


def list_skill_groups():
    return sorted(
        {
            str((skill_registry.get(key) or {}).get("group") or "").strip().lower()
            for key in skill_registry.list_keys()
            if str((skill_registry.get(key) or {}).get("group") or "").strip()
        }
    )


def get_skill_pulse_group(name):
    canonical_group = get_skill_group_for_skill(name)
    if canonical_group is not None:
        return int(canonical_group.offset_seconds or 0)
    definition = get_skill_definition(name) or {}
    if definition.get("pulse_group") is not None:
        return int(definition.get("pulse_group") or 100)
    return int(LEGACY_SKILL_PULSE_GROUPS.get(normalize_skill_name(name), 100) or 100)


def normalize_event_key(event_key, skill_name=None):
	return normalize_skill_name(event_key or skill_name)


def normalize_skillset(skillset):
    normalized = str(skillset or "primary").strip().lower()
    if normalized not in VALID_SKILLSETS:
        return "primary"
    return normalized


def calculate_mindstate(pool, max_pool):
    if max_pool <= 0:
        return 0
    ratio = max(0.0, min(1.0, float(pool) / float(max_pool)))
    return max(0, min(MINDSTATE_MAX, int(MINDSTATE_MAX * ratio)))


def get_mindstate_name(value):
    return get_canonical_mindstate_name(int(value or 0))


def base_pool(rank, skillset):
    normalized_rank = max(0, int(rank or 0))
    return total_pool_size(normalized_rank, normalize_skillset(skillset), 10, 10)


def pool_stat_modifier(owner):
    if owner is None:
        return 1.0

    stats = getattr(getattr(owner, "db", None), "stats", None)
    if isinstance(stats, dict):
        intelligence = float(stats.get("intelligence", 10.0) or 10.0)
        discipline = float(stats.get("discipline", 10.0) or 10.0)
    else:
        intelligence = 10.0
        discipline = 10.0

    baseline_pool = total_pool_size(100, "primary", 10, 10)
    if baseline_pool <= 0:
        return 1.0
    modified_pool = total_pool_size(100, "primary", intelligence, discipline)
    return max(0.1, float(modified_pool) / float(baseline_pool))


def rank_cost(rank):
    return 200 + max(0, int(rank or 0))


def award_xp(skill, amount):
    skill.recalc_pool()
    if skill.mindstate >= MIND_LOCK:
        notify_mind_lock_blocked_xp(skill)
        return 0.0

    gained_amount = max(0.0, float(amount or 0.0))
    before = skill.pool
    skill.pool += gained_amount
    skill.pool = min(skill.pool, skill.max_pool)
    skill.update_mindstate()
    persist_skill_state(skill)
    return skill.pool - before


def difficulty_factor(rank, difficulty):
    gap = float(difficulty or 0.0) - max(0.0, float(rank or 0.0))

    if gap < -20:
        return 0.2
    if gap < 0:
        return 0.6
    if gap < 20:
        return 1.0
    if gap < 50:
        return 0.7
    return 0.3


def difficulty_multiplier(rank, difficulty):
    normalized_rank = max(0.0, float(rank or 0.0))
    normalized_difficulty = max(0.0, float(difficulty or 0.0))
    denominator = normalized_difficulty + normalized_rank
    if denominator <= 0.0:
        return 0.5
    return 0.5 + (normalized_difficulty / denominator)


def normalize_learning_outcome(success=True, outcome=None):
    if outcome is not None:
        normalized_outcome = str(outcome or "").strip().lower()
        if normalized_outcome == "fail":
            return "failure"
        if normalized_outcome in {"failure", "partial", "success", "strong"}:
            return normalized_outcome
    return "success" if success else "failure"


def success_modifier(skill_name, success=True, outcome=None):
    normalized_name = normalize_skill_name(skill_name)
    normalized_outcome = normalize_learning_outcome(success=success, outcome=outcome)
    mods = dict(DEFAULT_OUTCOME_MODIFIERS)
    mods.update(dict(SUCCESS_MODIFIERS.get(normalized_name, {}) or {}))
    return float(mods.get(normalized_outcome, mods["success"]))


def rank_scaling(rank):
    normalized_rank = max(0.0, float(rank or 0.0))
    return 1.0 / (1.0 + (normalized_rank / 50.0))


def skill_gain_modifier(skill_name):
    normalized_name = normalize_skill_name(skill_name)
    return float(SKILL_GAIN_MODIFIERS.get(normalized_name, 1.0))


def event_weight(event_key, skill_name=None):
    normalized_event_key = normalize_event_key(event_key, skill_name=skill_name)
    return float(EVENT_WEIGHTS.get(normalized_event_key, 1.0))


def calculate_xp(skill, difficulty, success=True, outcome=None, event_key=None, context_multiplier=1.0):
    skill.recalc_pool()
    factor = difficulty_factor(skill.rank, difficulty)
    difficulty_mod = difficulty_multiplier(skill.rank, difficulty)
    normalized_outcome = normalize_learning_outcome(success=success, outcome=outcome)
    success_mod = success_modifier(skill.name, success=success, outcome=normalized_outcome)
    base = skill.max_pool * 0.035
    xp_amount = base * factor * difficulty_mod * success_mod
    xp_amount *= rank_scaling(skill.rank)
    xp_amount *= skill_gain_modifier(skill.name)
    xp_amount *= event_weight(event_key, skill_name=skill.name)
    xp_amount *= max(0.0, float(context_multiplier or 0.0))
    return max(0.0, xp_amount)


def train(skill, difficulty, success=True, outcome=None, event_key=None, context_multiplier=1.0):
    xp_amount = calculate_xp(
        skill,
        difficulty,
        success=success,
        outcome=outcome,
        event_key=event_key,
        context_multiplier=context_multiplier,
    )
    skill.last_trained = time.time()
    return award_xp(skill, xp_amount)


 # SKILL_GAIN_ENTRYPOINT
def award_exp_skill(char, skill_name, difficulty, success=True, outcome=None, event_key=None, context_multiplier=1.0):
    from engine.services.skill_service import SkillService

    return SkillService.award_xp(
        char,
        skill_name,
        difficulty,
        source={"mode": "difficulty"},
        success=success,
        outcome=outcome,
        event_key=event_key,
        context_multiplier=context_multiplier,
    ).amount


def is_active(skill, now=None):
    current_time = float(now if now is not None else time.time())
    return (current_time - float(getattr(skill, "last_trained", 0) or 0.0)) <= (ACTIVE_WINDOW + GRACE_WINDOW)


def send_feedback(skill):
    owner = getattr(skill, "owner", None)
    if owner is None or not hasattr(owner, "msg"):
        return False
    owner.msg(f"Your {skill.name} improves.")
    return True


def handle_mindstate_change(skill, new_name, now=None):
    current_time = float(now if now is not None else time.time())
    old_value = int(getattr(skill, "last_mindstate_sent", getattr(skill, "mindstate", 0)) or 0)
    new_value = int(getattr(skill, "mindstate", 0) or 0)
    if new_value == old_value:
        return False

    owner = getattr(skill, "owner", None)
    if owner is None:
        skill.last_mindstate_sent = new_value
        return False
    if not bool(getattr(getattr(owner, "db", None), "exp_feedback", True)):
        skill.last_mindstate_sent = new_value
        return False

    last_feedback_time = float(getattr(skill, "last_feedback_time", 0.0) or 0.0)
    if current_time - last_feedback_time < FEEDBACK_COOLDOWN:
        return False

    if new_value <= old_value:
        skill.last_mindstate_sent = new_value
        return False
    crossed_thresholds = sorted(threshold for threshold in MAJOR_MINDSTATE_THRESHOLDS if old_value < threshold <= new_value)
    if not crossed_thresholds:
        skill.last_mindstate_sent = new_value
        return False

    threshold = crossed_thresholds[-1]
    band = get_mindstate_band(threshold)
    if threshold >= MIND_LOCK:
        actor_message = (
            f"Your mind locks with {get_skill_display_name(skill.name)}. "
            f"You cannot absorb more experience in this skill until the pool drains."
        )
    else:
        actor_message = f"Your mind reaches a {band.name} state with {get_skill_display_name(skill.name)}."
    send_untargeted_action(actor=owner, actor_message=actor_message)

    skill.last_mindstate_sent = new_value
    skill.last_feedback_time = current_time
    return True


def wisdom_modifier(wis):
    return float(wisdom_pulse_multiplier(wis or 10.0))


def normalized_mindstate_drain_modifier(mindstate):
    raw_modifier = float(get_mindstate_band(int(mindstate or 0)).pulse_modifier or 1.0)
    return 1.0 + ((raw_modifier - 1.0) * 0.30)


def drain_skill(skill, wisdom=30, drain_multiplier=1.0):
    skill.recalc_pool()
    skill.rank_progress = max(0.0, float(getattr(skill, "rank_progress", 0.0) or 0.0))
    rate = float(DRAIN_RATES.get(skill.skillset, DRAIN_RATES["primary"]))
    mod = wisdom_modifier(wisdom) * normalized_mindstate_drain_modifier(skill.mindstate)
    drain = skill.max_pool * rate * mod * max(0.0, float(drain_multiplier or 0.0))
    drain = min(drain, skill.pool)

    skill.pool -= drain
    if skill.pool < 0:
        skill.pool = 0.0

    skill.rank_progress += drain
    skill.rank_progress = max(0.0, skill.rank_progress)
    skill.update_mindstate()
    persist_skill_state(skill)
    return drain


def process_rank(skill):
    skill.rank_progress = max(0.0, float(getattr(skill, "rank_progress", 0.0) or 0.0))
    cost = rank_cost(skill.rank)
    owner = getattr(skill, "owner", None)

    while skill.rank_progress >= cost:
        skill.rank_progress -= cost
        previous_rank = int(skill.rank or 0)
        skill.rank += 1
        if owner is not None and hasattr(owner, "on_skill_rank_gained"):
            owner.on_skill_rank_gained(skill.name, previous_rank, int(skill.rank or 0), 1)
        skill.recalc_pool()
        cost = rank_cost(skill.rank)

    skill.rank_progress = max(0.0, skill.rank_progress)
    persist_skill_state(skill)
    return skill.rank


def resolve_wisdom(skill, wisdom=None):
    if wisdom is not None:
        return wisdom
    owner = getattr(skill, "owner", None)
    if owner is not None and hasattr(owner, "get_stat"):
        return owner.get_stat("wisdom")
    return 30


def notify_mind_lock_blocked_xp(skill, now=None):
    owner = getattr(skill, "owner", None)
    if owner is None:
        return False
    current_time = float(now if now is not None else time.time())
    notification_store = getattr(getattr(owner, "ndb", None), "mind_lock_notifications", None) or {}
    last_notification = float(notification_store.get(skill.name, 0.0) or 0.0)
    if current_time - last_notification < MIND_LOCK_NOTIFICATION_WINDOW_SECONDS:
        return False
    notification_store = dict(notification_store)
    notification_store[skill.name] = current_time
    owner.ndb.mind_lock_notifications = notification_store
    send_untargeted_action(
        actor=owner,
        actor_message=f"Your mind is too saturated with {get_skill_display_name(skill.name)} to absorb more right now.",
    )
    return True


def persist_skill_state(skill):
    owner = getattr(skill, "owner", None)
    if owner is not None and hasattr(owner, "_persist_exp_skill_state"):
        owner._persist_exp_skill_state(skill)
    return skill


def pulse(skill, wisdom=None, drain_multiplier=1.0):
    wisdom = resolve_wisdom(skill, wisdom=wisdom)
    drained = drain_skill(skill, wisdom=wisdom, drain_multiplier=drain_multiplier)
    process_rank(skill)
    return drained


class SkillState:
    def __init__(self, name, owner=None):
        self.name = normalize_skill_name(name)
        self.owner = owner
        self.rank = 0
        self.rank_progress = 0.0
        self.pool = 0.0
        self.max_pool = 0.0
        self.skillset = "primary"
        self.mindstate = 0
        self.last_trained = 0.0
        self.last_mindstate_name = "clear"
        self.last_mindstate_sent = 0
        self.last_feedback_time = 0.0
        self.max_pool = base_pool(self.rank, self.skillset)

    def update_mindstate(self):
        self.mindstate = calculate_mindstate(self.pool, self.max_pool)
        new_name = self.mindstate_name()
        if new_name != self.last_mindstate_name:
            handle_mindstate_change(self, new_name)
        self.last_mindstate_name = new_name

    def mindstate_name(self):
        return get_mindstate_name(self.mindstate)

    def recalc_pool(self):
        self.skillset = normalize_skillset(self.skillset)
        self.rank = max(0, int(self.rank or 0))
        self.rank_progress = max(0.0, float(getattr(self, "rank_progress", 0.0) or 0.0))
        stats = getattr(getattr(self.owner, "db", None), "stats", None)
        if isinstance(stats, dict):
            intelligence = float(stats.get("intelligence", 10.0) or 10.0)
            discipline = float(stats.get("discipline", 10.0) or 10.0)
        else:
            intelligence = 10.0
            discipline = 10.0
        self.max_pool = total_pool_size(self.rank, self.skillset, intelligence, discipline)
        self.pool = max(0.0, min(float(self.pool or 0.0), float(self.max_pool or 0.0)))
        self.update_mindstate()
        persist_skill_state(self)


class SkillHandler:
    def __init__(self, obj):
        self.obj = obj
        self.skills = {}

    def get(self, name):
        normalized_name = normalize_skill_name(name)
        try:
            from world.systems.exp_pulse import register_exp_character

            register_exp_character(self.obj)
        except Exception:
            pass
        if normalized_name not in self.skills:
            self.skills[normalized_name] = SkillState(normalized_name, owner=self.obj)
        return self.skills[normalized_name]
