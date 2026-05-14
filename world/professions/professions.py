DEFAULT_PROFESSION = "commoner"
PROF_EMPATH = "empath"
SKILLSET_TIERS = ("primary", "secondary", "tertiary")


def _skillset_tuple(*values):
    return tuple(str(value or "").strip().lower() for value in values if str(value or "").strip())


def _canonicalize_skill_category(value):
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "armor": "armor",
        "combat": "weapons",
        "lore": "lore",
        "magic": "magic",
        "survival": "survival",
        "weapon": "weapons",
        "weapons": "weapons",
    }
    return aliases.get(normalized, normalized)

COMMON_RANK_LABELS = {
    1: "Novice",
    2: "Apprentice",
    3: "Adept",
    4: "Expert",
    5: "Master",
}

PROFESSION_ALIASES = {
    "mage": "moon_mage",
}

PROFESSION_PROFILES = {
    "commoner": {
        "display": "Commoner",
        "description": "Unaffiliated folk who survive on grit, work, and whatever they can learn on the road.",
        "primary": "survival",
        "secondary": "lore",
        "tertiary": "weapons",
        "primary_skillsets": _skillset_tuple("survival"),
        "secondary_skillsets": _skillset_tuple("lore", "weapons"),
        "tertiary_skillsets": _skillset_tuple("armor", "magic"),
        "guild_tag": "commoner_guildhall",
        "social": "Neutral",
    },
    "barbarian": {
        "display": "Barbarian",
        "description": "Fury-driven warriors who prize raw endurance, battle instinct, and intimidating presence.",
        "primary": "weapons",
        "secondary": "survival",
        "tertiary": "lore",
        "primary_skillsets": _skillset_tuple("weapons"),
        "secondary_skillsets": _skillset_tuple("survival", "armor"),
        "tertiary_skillsets": _skillset_tuple("lore", "magic"),
        "guild_tag": "barbarian_guildhall",
        "social": "Respected",
        "presence_text": "Raw physical power seems to roll ahead of them.",
    },
    "bard": {
        "display": "Bard",
        "description": "Lorekeepers, performers, and subtle influencers who mix story, wit, and practiced technique.",
        "primary": "lore",
        "secondary": "magic",
        "tertiary": "survival",
        "primary_skillsets": _skillset_tuple("lore"),
        "secondary_skillsets": _skillset_tuple("magic", "weapons"),
        "tertiary_skillsets": _skillset_tuple("survival", "armor"),
        "guild_tag": "bard_guildhall",
        "social": "Welcome",
    },
    "cleric": {
        "display": "Cleric",
        "description": "Disciples of sacred mysteries whose strength lies in devotion, warding, and disciplined magic.",
        "primary": "magic",
        "secondary": "lore",
        "tertiary": "weapons",
        "primary_skillsets": _skillset_tuple("magic"),
        "secondary_skillsets": _skillset_tuple("lore", "weapons"),
        "tertiary_skillsets": _skillset_tuple("survival", "armor"),
        "guild_tag": "cleric_guildhall",
        "social": "Trusted",
    },
    PROF_EMPATH: {
        "display": "Empath",
        "description": "Healers who carry the pain of others and move through the world with restorative calm.",
        "primary": "lore",
        "secondary": "magic",
        "tertiary": "weapons",
        "primary_skillsets": _skillset_tuple("lore"),
        "secondary_skillsets": _skillset_tuple("magic", "survival"),
        "tertiary_skillsets": _skillset_tuple("weapons", "armor"),
        "guild_tag": "empath_guildhall",
        "social": "Trusted",
        "presence_text": "A calming presence follows in their wake.",
    },
    "moon_mage": {
        "display": "Moon Mage",
        "description": "Students of hidden patterns, celestial power, and careful magical preparation.",
        "primary": "magic",
        "secondary": "lore",
        "tertiary": "weapons",
        "primary_skillsets": _skillset_tuple("magic"),
        "secondary_skillsets": _skillset_tuple("lore", "survival"),
        "tertiary_skillsets": _skillset_tuple("weapons", "armor"),
        "guild_tag": "moon_mage_guildhall",
        "social": "Wary",
        "magic_text": "faintly radiates magical energy",
    },
    "necromancer": {
        "display": "Necromancer",
        "description": "Forbidden practitioners who bargain with death and the unsettling truths beyond it.",
        "primary": "survival",
        "secondary": "magic",
        "tertiary": "armor",
        "primary_skillsets": _skillset_tuple("survival"),
        "secondary_skillsets": _skillset_tuple("magic", "lore"),
        "tertiary_skillsets": _skillset_tuple("armor", "weapons"),
        "guild_tag": "necromancer_guildhall",
        "social": "Distrusted",
        "magic_text": "radiates unsettling magical energy",
    },
    "paladin": {
        "display": "Paladin",
        "description": "Devout martial champions who balance armor, conviction, and disciplined force.",
        "primary": "armor",
        "secondary": "lore",
        "tertiary": "magic",
        "primary_skillsets": _skillset_tuple("armor"),
        "secondary_skillsets": _skillset_tuple("lore", "weapons"),
        "tertiary_skillsets": _skillset_tuple("magic", "survival"),
        "guild_tag": "paladin_guildhall",
        "social": "Honored",
    },
    "ranger": {
        "display": "Ranger",
        "description": "Hunters and pathfinders who favor the wild, patient observation, and steady arms.",
        "primary": "survival",
        "secondary": "weapons",
        "tertiary": "magic",
        "primary_skillsets": _skillset_tuple("survival"),
        "secondary_skillsets": _skillset_tuple("weapons", "armor"),
        "tertiary_skillsets": _skillset_tuple("magic", "lore"),
        "guild_tag": "ranger_guildhall",
        "social": "Respected",
    },
    "thief": {
        "display": "Thief",
        "description": "Opportunists and shadow-workers who live by stealth, nerve, and precise timing.",
        "primary": "survival",
        "secondary": "weapons",
        "tertiary": "magic",
        "primary_skillsets": _skillset_tuple("survival"),
        "secondary_skillsets": _skillset_tuple("weapons", "lore"),
        "tertiary_skillsets": _skillset_tuple("magic", "armor"),
        "guild_tag": "thief_guildhall",
        "social": "Suspicious",
        "stealth_text": "moves with unsettling subtlety",
    },
    "trader": {
        "display": "Trader",
        "description": "Merchants and negotiators who turn knowledge, patience, and reputation into profit.",
        "primary": "lore",
        "secondary": "survival",
        "tertiary": "weapons",
        "primary_skillsets": _skillset_tuple("lore"),
        "secondary_skillsets": _skillset_tuple("survival", "armor"),
        "tertiary_skillsets": _skillset_tuple("magic", "weapons"),
        "guild_tag": "trader_guildhall",
        "social": "Established",
    },
    "warrior": {
        "display": "Warrior",
        "description": "Battle-trained fighters who build momentum through disciplined aggression and relentless pressure.",
        "primary": "weapons",
        "secondary": "armor",
        "tertiary": "lore",
        "primary_skillsets": _skillset_tuple("weapons"),
        "secondary_skillsets": _skillset_tuple("armor", "survival"),
        "tertiary_skillsets": _skillset_tuple("lore", "magic"),
        "guild_tag": "warrior_guildhall",
        "social": "Respected",
        "presence_text": "Carries the weight of a practiced fighter.",
    },
    "warrior_mage": {
        "display": "Warrior Mage",
        "description": "Battle mages who shape destructive force through practiced arms and relentless will.",
        "primary": "magic",
        "secondary": "weapons",
        "tertiary": "armor",
        "primary_skillsets": _skillset_tuple("magic"),
        "secondary_skillsets": _skillset_tuple("weapons", "lore"),
        "tertiary_skillsets": _skillset_tuple("armor", "survival"),
        "guild_tag": "warrior_mage_guildhall",
        "social": "Wary",
        "magic_text": "radiates martial magical energy",
    },
}

PROFESSION_TO_GUILD = {
    key: profile.get("guild_tag")
    for key, profile in PROFESSION_PROFILES.items()
}


def _normalize(value):
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_") or None


def resolve_profession_name(profession_name, default=DEFAULT_PROFESSION):
    normalized = _normalize(profession_name)
    if not normalized:
        return default
    normalized = PROFESSION_ALIASES.get(normalized, normalized)
    if normalized in PROFESSION_PROFILES:
        return normalized
    return default


def get_profession_profile(profession_name):
    profession = resolve_profession_name(profession_name)
    return dict(PROFESSION_PROFILES.get(profession, PROFESSION_PROFILES[DEFAULT_PROFESSION]))


def get_profession_display_name(profession_name):
    return get_profession_profile(profession_name).get("display", "Commoner")


def get_profession_rank_label(profession_name, rank):
    profession = resolve_profession_name(profession_name)
    display = get_profession_display_name(profession)
    rank_label = COMMON_RANK_LABELS.get(max(1, int(rank or 1)), "Master")
    return f"{rank_label} {display}"


def get_profession_social_standing(profession_name):
    return get_profession_profile(profession_name).get("social", "Neutral")


def get_profession_skillset_placement(profession_name):
    profile = get_profession_profile(profession_name)
    placement = {}
    for tier in SKILLSET_TIERS:
        skillsets = profile.get(f"{tier}_skillsets") or ()
        placement[tier] = tuple(_canonicalize_skill_category(value) for value in skillsets)
    return placement


def get_profession_skillset_tier(profession_name, skill_category, default="primary"):
    canonical_category = _canonicalize_skill_category(skill_category)
    for tier, categories in get_profession_skillset_placement(profession_name).items():
        if canonical_category in categories:
            return tier
    return str(default or "primary")


def get_skillset_tier_for_skill(profession_name, skill_name=None, skill_category=None, default="primary"):
    category = skill_category
    if category is None and skill_name is not None:
        normalized_name = str(skill_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        category_aliases = {
            "backstab": "survival",
            "brawling": "weapons",
            "brigandine": "armor",
            "chain_armor": "armor",
            "conviction": "armor",
            "defending": "armor",
            "expertise": "weapons",
            "heavy_edge": "weapons",
            "instinct": "survival",
            "light_armor": "armor",
            "light_edge": "weapons",
            "parry_ability": "weapons",
            "plate_armor": "armor",
            "polearm": "weapons",
            "shield_usage": "armor",
            "summoning": "magic",
            "thanatology": "survival",
            "theurgy": "magic",
            "thievery": "survival",
            "trading": "lore",
        }
        category = category_aliases.get(normalized_name)
    return get_profession_skillset_tier(profession_name, category, default=default)