"""
Skill system — core data structures (no logic yet)
"""

import time


VALID_SKILLSETS = ("primary", "secondary", "tertiary")
MINDSTATE_MAX = 34
MIND_LOCK = MINDSTATE_MAX
PULSE_INTERVAL = 200
PULSE_OFFSET = 20
ACTIVE_WINDOW = 600
GRACE_WINDOW = 30
FEEDBACK_THRESHOLD = 5
FEEDBACK_COOLDOWN = 10

MINDSTATE_NAMES = {
    0: "clear",
    1: "dabbling",
    2: "perusing",
    3: "learning",
    4: "thoughtful",
    5: "thinking",
    6: "considering",
    7: "pondering",
    8: "ruminating",
    9: "concentrating",
    10: "attentive",
    15: "engaged",
    20: "absorbed",
    25: "focused",
    30: "riveted",
    34: "mind lock",
}

SKILL_GROUPS = {
    "evasion": 100,
    "brawling": 100,
    "athletics": 100,
    "stealth": 120,
    "perception": 120,
    "locksmithing": 120,
    "appraisal": 140,
    "light_edge": 140,
    "targeted_magic": 160,
    "debilitation": 160,
    "first_aid": 160,
    "scholarship": 180,
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

TEMPLATE_EXP_SKILLS = (
    *FIRST_WAVE_EXP_SKILLS,
    *SECOND_WAVE_EXP_SKILLS,
)

DRAIN_RATES = {
    "primary": 0.067,
    "secondary": 0.050,
    "tertiary": 0.035,
}

BASE_POOL_NUMERATOR = 15000.0
BASE_POOL_OFFSET = 900.0
BASE_POOL_FLOOR = 1000.0

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
    return max(0, min(MINDSTATE_MAX, int(ratio * MINDSTATE_MAX)))


def get_mindstate_name(value):
    current = "clear"
    for threshold in sorted(MINDSTATE_NAMES):
        if int(value or 0) >= threshold:
            current = MINDSTATE_NAMES[threshold]
    return current


def base_pool(rank, skillset):
    normalized_rank = max(0, int(rank or 0))
    normalize_skillset(skillset)
    return (BASE_POOL_NUMERATOR * normalized_rank / (normalized_rank + BASE_POOL_OFFSET)) + BASE_POOL_FLOOR


def rank_cost(rank):
    return 200 + max(0, int(rank or 0))


def award_xp(skill, amount):
    skill.recalc_pool()
    if skill.mindstate >= MIND_LOCK:
        return 0.0

    gained_amount = max(0.0, float(amount or 0.0))
    before = skill.pool
    skill.pool += gained_amount
    skill.pool = min(skill.pool, skill.max_pool)
    skill.update_mindstate()
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


def award_exp_skill(char, skill_name, difficulty, success=True, outcome=None, event_key=None, context_multiplier=1.0):
    if char is None:
        return 0.0
    if hasattr(char, "ensure_core_defaults"):
        char.ensure_core_defaults()
    handler = getattr(char, "exp_skills", None)
    if handler is None:
        return 0.0
    skill = handler.get(skill_name)
    return train(
        skill,
        difficulty,
        success=success,
        outcome=outcome,
        event_key=event_key,
        context_multiplier=context_multiplier,
    )


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
    if str(new_name or "") == str(getattr(skill, "last_mindstate_name", "clear") or "clear"):
        return False

    owner = getattr(skill, "owner", None)
    if owner is None or not hasattr(owner, "msg"):
        return False
    if not bool(getattr(getattr(owner, "db", None), "exp_feedback", True)):
        return False

    last_feedback_time = float(getattr(skill, "last_feedback_time", 0.0) or 0.0)
    if current_time - last_feedback_time < FEEDBACK_COOLDOWN:
        return False

    if new_name == "mind lock":
        owner.msg(f"Your {skill.name} is fully absorbed. You can learn no more.")
    elif new_name == "clear":
        owner.msg(f"Your {skill.name} clears from your mind.")
    else:
        owner.msg(f"You feel your {skill.name} settling into {new_name}.")

    skill.last_mindstate_sent = int(skill.mindstate)
    skill.last_feedback_time = current_time
    return True


def wisdom_modifier(wis):
    return 1 + (float(wis or 0.0) - 30.0) * 0.003


def drain_skill(skill, wisdom=30):
    skill.recalc_pool()
    skill.rank_progress = max(0.0, float(getattr(skill, "rank_progress", 0.0) or 0.0))
    rate = float(DRAIN_RATES.get(skill.skillset, DRAIN_RATES["primary"]))
    mod = wisdom_modifier(wisdom)
    drain = skill.max_pool * rate * mod
    drain = min(drain, skill.pool)

    skill.pool -= drain
    if skill.pool < 0:
        skill.pool = 0.0

    skill.rank_progress += drain
    skill.rank_progress = max(0.0, skill.rank_progress)
    skill.update_mindstate()
    return drain


def process_rank(skill):
    skill.rank_progress = max(0.0, float(getattr(skill, "rank_progress", 0.0) or 0.0))
    cost = rank_cost(skill.rank)

    while skill.rank_progress >= cost:
        skill.rank_progress -= cost
        skill.rank += 1
        skill.recalc_pool()
        cost = rank_cost(skill.rank)

    skill.rank_progress = max(0.0, skill.rank_progress)
    return skill.rank


def pulse(skill, wisdom=30):
    drained = drain_skill(skill, wisdom=wisdom)
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
        self.max_pool = base_pool(self.rank, self.skillset)
        self.pool = max(0.0, min(float(self.pool or 0.0), float(self.max_pool or 0.0)))
        self.update_mindstate()


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
