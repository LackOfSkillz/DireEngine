import random

from evennia.utils.create import create_object

from typeclasses.objects import Object


GEM_TYPES = {
    "quartz": 50,
    "amethyst": 100,
    "garnet": 150,
    "opal": 200,
    "topaz": 300,
    "sapphire": 500,
    "emerald": 700,
    "ruby": 900,
    "diamond": 1200,
}

QUALITY_MODIFIERS = {
    1: 0.8,
    2: 1.0,
    3: 1.2,
    4: 1.5,
}

SIZE_MODIFIERS = {
    1: 0.8,
    2: 1.0,
    3: 1.3,
}

GEM_WEIGHTS = {
    "quartz": 20,
    "amethyst": 18,
    "garnet": 16,
    "opal": 14,
    "topaz": 10,
    "sapphire": 8,
    "emerald": 6,
    "ruby": 5,
    "diamond": 3,
}

SIZE_NAMES = {
    1: "small",
    2: "medium",
    3: "large",
}

QUALITY_NAMES = {
    1: "flawed",
    2: "average",
    3: "fine",
    4: "exceptional",
}

GEM_TYPE_ORDER = list(GEM_TYPES.keys())


def build_gem_data(rng=None):
    picker = rng or random
    gem_type = picker.choices(list(GEM_WEIGHTS.keys()), weights=list(GEM_WEIGHTS.values()), k=1)[0]
    quality_tier = picker.randint(1, 4)
    size_tier = picker.randint(1, 3)
    base_value = int(GEM_TYPES[gem_type])
    final_value = int(base_value * QUALITY_MODIFIERS[quality_tier] * SIZE_MODIFIERS[size_tier])
    return {
        "gem_type": gem_type,
        "base_value": base_value,
        "quality_tier": quality_tier,
        "size_tier": size_tier,
        "final_value": final_value,
    }


def describe_gem_data(gem_data):
    size_tier = int(gem_data.get("size_tier", 2) or 2)
    quality_tier = int(gem_data.get("quality_tier", 2) or 2)
    gem_type = str(gem_data.get("gem_type", "quartz") or "quartz")
    return {
        "size_name": SIZE_NAMES.get(size_tier, "medium"),
        "quality_name": QUALITY_NAMES.get(quality_tier, "average"),
        "gem_type": gem_type,
        "name": f"{SIZE_NAMES.get(size_tier, 'medium')} {QUALITY_NAMES.get(quality_tier, 'average')} {gem_type}",
    }


def normalize_gem_data(gem_data):
    data = dict(gem_data or {})
    gem_type = str(data.get("gem_type", "quartz") or "quartz").lower()
    if gem_type not in GEM_TYPES:
        gem_type = "quartz"
    quality_tier = min(4, max(1, int(data.get("quality_tier", 2) or 2)))
    size_tier = min(3, max(1, int(data.get("size_tier", 2) or 2)))
    base_value = int(GEM_TYPES[gem_type])
    final_value = int(base_value * QUALITY_MODIFIERS[quality_tier] * SIZE_MODIFIERS[size_tier])
    return {
        "gem_type": gem_type,
        "base_value": base_value,
        "quality_tier": quality_tier,
        "size_tier": size_tier,
        "final_value": final_value,
    }


def downgrade_gem_data(gem_data):
    data = normalize_gem_data(gem_data)
    if data["size_tier"] > 1:
        data["size_tier"] -= 1
        return normalize_gem_data(data)
    if data["quality_tier"] > 1:
        data["quality_tier"] -= 1
        return normalize_gem_data(data)
    gem_index = GEM_TYPE_ORDER.index(data["gem_type"])
    if gem_index > 0:
        data["gem_type"] = GEM_TYPE_ORDER[gem_index - 1]
        data["quality_tier"] = 1
        data["size_tier"] = 1
    return normalize_gem_data(data)


def create_gem(holder, gem_data=None):
    data = normalize_gem_data(gem_data or build_gem_data())
    naming = describe_gem_data(data)
    gem = create_object(Gem, key=naming["name"], location=holder, home=getattr(holder, "location", None) or holder)
    gem.db.gem_type = data["gem_type"]
    gem.db.base_value = int(data["base_value"])
    gem.db.quality_tier = int(data["quality_tier"])
    gem.db.size_tier = int(data["size_tier"])
    gem.db.final_value = int(data["final_value"])
    gem.sync_gem_state()
    return gem


class Gem(Object):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_gem = True
        self.db.gem_type = "quartz"
        self.db.base_value = 50
        self.db.quality_tier = 2
        self.db.size_tier = 2
        self.db.final_value = 50
        self.db.item_value = 50
        self.db.value = 50
        self.db.weight = 0.1
        self.sync_gem_state()

    def sync_gem_state(self):
        gem_type = str(getattr(self.db, "gem_type", "quartz") or "quartz").lower()
        if gem_type not in GEM_TYPES:
            gem_type = "quartz"
        base_value = int(GEM_TYPES[gem_type])
        quality_tier = int(getattr(self.db, "quality_tier", 2) or 2)
        size_tier = int(getattr(self.db, "size_tier", 2) or 2)
        quality_tier = min(4, max(1, quality_tier))
        size_tier = min(3, max(1, size_tier))
        final_value = int(base_value * QUALITY_MODIFIERS[quality_tier] * SIZE_MODIFIERS[size_tier])
        self.db.gem_type = gem_type
        self.db.base_value = base_value
        self.db.quality_tier = quality_tier
        self.db.size_tier = size_tier
        self.db.final_value = final_value
        self.db.item_value = final_value
        self.db.value = final_value
        self.db.weight = 0.1
        naming = describe_gem_data(
            {
                "gem_type": gem_type,
                "quality_tier": quality_tier,
                "size_tier": size_tier,
            }
        )
        self.key = naming["name"]
        self.db.desc = f"A {naming['size_name']} {naming['quality_name']} {gem_type} catches the light."
