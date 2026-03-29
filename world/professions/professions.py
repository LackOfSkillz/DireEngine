DEFAULT_PROFESSION = "commoner"

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
        "guild_tag": "commoner_guildhall",
        "social": "Neutral",
    },
    "barbarian": {
        "display": "Barbarian",
        "description": "Fury-driven warriors who prize raw endurance, battle instinct, and intimidating presence.",
        "primary": "weapons",
        "secondary": "armor",
        "tertiary": "survival",
        "guild_tag": "barbarian_guildhall",
        "social": "Respected",
        "presence_text": "Raw physical power seems to roll ahead of them.",
    },
    "bard": {
        "display": "Bard",
        "description": "Lorekeepers, performers, and subtle influencers who mix story, wit, and practiced technique.",
        "primary": "lore",
        "secondary": "magic",
        "tertiary": "weapons",
        "guild_tag": "bard_guildhall",
        "social": "Welcome",
    },
    "cleric": {
        "display": "Cleric",
        "description": "Disciples of sacred mysteries whose strength lies in devotion, warding, and disciplined magic.",
        "primary": "magic",
        "secondary": "lore",
        "tertiary": "weapons",
        "guild_tag": "cleric_guildhall",
        "social": "Trusted",
    },
    "empath": {
        "display": "Empath",
        "description": "Healers who carry the pain of others and move through the world with restorative calm.",
        "primary": "lore",
        "secondary": "survival",
        "tertiary": "magic",
        "guild_tag": "empath_guildhall",
        "social": "Trusted",
        "presence_text": "A calming presence follows in their wake.",
    },
    "moon_mage": {
        "display": "Moon Mage",
        "description": "Students of hidden patterns, celestial power, and careful magical preparation.",
        "primary": "magic",
        "secondary": "lore",
        "tertiary": "survival",
        "guild_tag": "moon_mage_guildhall",
        "social": "Wary",
        "magic_text": "faintly radiates magical energy",
    },
    "necromancer": {
        "display": "Necromancer",
        "description": "Forbidden practitioners who bargain with death and the unsettling truths beyond it.",
        "primary": "magic",
        "secondary": "lore",
        "tertiary": "survival",
        "guild_tag": "necromancer_guildhall",
        "social": "Distrusted",
        "magic_text": "radiates unsettling magical energy",
    },
    "paladin": {
        "display": "Paladin",
        "description": "Devout martial champions who balance armor, conviction, and disciplined force.",
        "primary": "weapons",
        "secondary": "armor",
        "tertiary": "magic",
        "guild_tag": "paladin_guildhall",
        "social": "Honored",
    },
    "ranger": {
        "display": "Ranger",
        "description": "Hunters and pathfinders who favor the wild, patient observation, and steady arms.",
        "primary": "survival",
        "secondary": "weapons",
        "tertiary": "lore",
        "guild_tag": "ranger_guildhall",
        "social": "Respected",
    },
    "thief": {
        "display": "Thief",
        "description": "Opportunists and shadow-workers who live by stealth, nerve, and precise timing.",
        "primary": "survival",
        "secondary": "weapons",
        "tertiary": "lore",
        "guild_tag": "thief_guildhall",
        "social": "Suspicious",
        "stealth_text": "moves with unsettling subtlety",
    },
    "trader": {
        "display": "Trader",
        "description": "Merchants and negotiators who turn knowledge, patience, and reputation into profit.",
        "primary": "lore",
        "secondary": "survival",
        "tertiary": "armor",
        "guild_tag": "trader_guildhall",
        "social": "Established",
    },
    "warrior_mage": {
        "display": "Warrior Mage",
        "description": "Battle mages who shape destructive force through practiced arms and relentless will.",
        "primary": "magic",
        "secondary": "weapons",
        "tertiary": "lore",
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