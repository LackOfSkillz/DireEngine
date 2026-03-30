from world.races import RACE_DEFINITIONS


GENDER_OPTIONS = ("male", "female", "neutral")


CHARGEN_STEPS = (
    "name",
    "race",
    "gender",
    "stats",
    "description",
    "confirm",
)

APPEARANCE_FIELDS = ("build", "height", "hair", "eyes", "skin")

APPEARANCE_OPTIONS = {
    "build": ("slender", "lean", "athletic", "sturdy", "broad", "wiry"),
    "height": ("short", "average", "tall"),
    "hair": ("black", "brown", "auburn", "blonde", "gray", "white"),
    "eyes": ("brown", "hazel", "green", "blue", "gray", "amber"),
    "skin": ("fair", "tan", "bronze", "brown", "dark"),
}


STEP_PROMPTS = {
    "name": "Choose a character name.",
    "race": "Choose a race.",
    "gender": "Choose a gender.",
    "stats": "Assign your starting stats.",
    "description": "Write your description.",
    "confirm": "Review the blueprint and confirm creation.",
}


def format_stats_preview(stats, points_remaining):
    ordered = [
        f"{stat.capitalize()}: {int((stats or {}).get(stat, 0) or 0)}"
        for stat in ("strength", "agility", "reflex", "intelligence", "wisdom", "stamina")
    ]
    return "\n".join(ordered + [f"Points remaining: {int(points_remaining or 0)}"])


def format_chargen_summary(state):
    blueprint = getattr(state, "blueprint", None)
    appearance = dict(getattr(state, "appearance", {}) or {})
    summary_lines = [
        f"Name: {getattr(blueprint, 'name', None) or '(unset)'}",
        f"Race: {getattr(blueprint, 'race', None) or '(unset)'}",
        f"Gender: {getattr(blueprint, 'gender', None) or '(unset)'}",
        f"Profession: {getattr(blueprint, 'profession', None) or 'commoner'}",
        format_stats_preview(getattr(blueprint, "stats", {}) or {}, getattr(state, "points_remaining", 0)),
        f"Appearance: {appearance or '(unset)'}",
        f"Description: {getattr(blueprint, 'description', None) or '(unset)'}",
    ]
    return "\n".join(summary_lines)


def render_step_prompt(state):
    step = str(getattr(state, "current_step", "name") or "name").strip().lower()
    if step == "race":
        race_options = ", ".join(sorted(profile["name"] for profile in RACE_DEFINITIONS.values()))
        return f"{STEP_PROMPTS['race']}\nAvailable races: {race_options}"
    if step == "gender":
        return f"{STEP_PROMPTS['gender']}\nAvailable options: {', '.join(GENDER_OPTIONS)}"
    if step == "stats":
        current_preview = getattr(getattr(state, "blueprint", None), "stats", None) or getattr(state, "base_stats", {})
        points_remaining = getattr(state, "points_remaining", 0)
        instruction = (
            "Starting stats are fixed by race in this version. Review them and use 'next' to continue."
            if int(points_remaining or 0) <= 0
            else "Use 'stat <name> <amount>' to assign points, 'resetstats confirm' to start over, and 'next' when done."
        )
        return (
            f"{STEP_PROMPTS['stats']}\n"
            f"{instruction}\n"
            f"{format_stats_preview(current_preview, points_remaining)}"
        )
    if step == "description":
        parts = []
        appearance = dict(getattr(state, "appearance", {}) or {})
        for field in APPEARANCE_FIELDS:
            selected = appearance.get(field) or "(unset)"
            options = ", ".join(APPEARANCE_OPTIONS[field])
            parts.append(f"{field.capitalize()}: {selected} | options: {options}")
        parts.append("Use build/height/hair/eyes/skin <value>, then 'next' when all are set.")
        return f"{STEP_PROMPTS['description']}\n" + "\n".join(parts)
    if step == "confirm":
        return f"{STEP_PROMPTS['confirm']}\n{format_chargen_summary(state)}\nUse 'confirm' to create the character or 'back' to revise."
    return STEP_PROMPTS.get(step, "Continue character creation.")
