from types import SimpleNamespace

from engine.services.dance_service import DanceService


class DummyExit:
    def __init__(self, destination):
        self.destination = destination


class DummyRoom:
    def __init__(self, room_id):
        self.id = room_id
        self.contents = []


class DummyWeapon:
    def __init__(self, key="blade"):
        self.key = key
        self.location = None

    def move_to(self, destination, **_kwargs):
        self.location = destination


class DummyCombatant:
    def __init__(self, key, room, *, stats=None, circle=100, account=None, group_id=None, is_npc=False):
        self.id = len(room.contents) + 1
        self.key = key
        self.location = room
        self.roundtime = 0
        self.balance = 100
        self.disengaged = False
        self.hidden = False
        self.weapon = None
        self.account = account
        self.db = SimpleNamespace(
            stats=stats or {"discipline": 30, "charisma": 30, "strength": 20, "reflex": 20, "agility": 20, "stamina": 20},
            circle=circle,
            states={},
            invisible=False,
            stunned=False,
            stunned_until=None,
            in_combat=True,
            is_npc=is_npc,
            group_id=group_id,
            hp=100,
            max_hp=100,
            fatigue=20,
            max_fatigue=100,
            balance=100,
            max_balance=100,
            inner_fire=60,
            ccp=100,
            armor_penalty=0,
            encumberance=0,
            spellbook1=0,
            spellbook2=0,
            skills={"multiple_engaged_opponent": 0},
        )
        room.contents.append(self)

    def get_stat(self, name):
        normalized = str(name or "").strip().lower()
        return int(self.db.stats.get(normalized, 0) or 0) + int(DanceService.get_stat_modifier(self, normalized) or 0)

    def get_circle(self):
        return int(self.db.circle or 0)

    def get_skill(self, name):
        normalized = str(name or "").strip().lower().replace("-", "_").replace(" ", "_")
        return int(self.db.skills.get(normalized, 0) or 0) + int(DanceService.get_skill_modifier(self, normalized) or 0)

    def is_profession(self, key):
        return str(key or "").strip().lower() == "barbarian"

    def get_state(self, key):
        return dict(self.db.states or {}).get(key)

    def set_state(self, key, value):
        states = dict(self.db.states or {})
        states[key] = value
        self.db.states = states

    def clear_state(self, key):
        states = dict(self.db.states or {})
        states.pop(key, None)
        self.db.states = states

    def set_roundtime(self, value):
        self.roundtime = float(value)

    def disengage(self, emit_message=False):
        self.disengaged = True
        self.db.in_combat = False

    def move_to(self, destination, **_kwargs):
        if self.location and self in self.location.contents:
            self.location.contents.remove(self)
        self.location = destination
        destination.contents.append(self)
        return True

    def get_balance(self):
        return self.balance, int(self.db.max_balance or 100)

    def set_balance(self, value):
        self.balance = int(value)
        self.db.balance = self.balance

    def get_inner_fire(self):
        return int(self.db.inner_fire or 0)

    def set_inner_fire(self, value, emit_messages=True):
        self.db.inner_fire = max(0, int(value or 0))
        return self.db.inner_fire

    def get_active_barbarian_berserk(self):
        state = self.get_state("barbarian_berserk")
        return state if isinstance(state, dict) else None

    def is_dead(self):
        return False

    def is_hidden(self):
        return bool(self.hidden)

    def break_stealth(self):
        self.hidden = False

    def get_wielded_weapon(self):
        return self.weapon

    def get_weapon(self):
        return self.weapon

    def clear_equipped_weapon(self):
        self.weapon = None

    def sync_client_state(self):
        return None

    def get_spellbook2(self):
        return int(self.db.spellbook2 or 0)

    def set_spellbook2(self, value, emit_messages=True):
        self.db.spellbook2 = int(value or 0)
        return self.db.spellbook2

    def get_barbarian_dance_ccp(self):
        return int(self.db.ccp or 0)

    def get_barbarian_dance_armor_penalty(self):
        return int(self.db.armor_penalty or 0)

    def get_barbarian_dance_encumbrance(self):
        return int(self.db.encumberance or 0)

    def get_barbarian_dance_offense_bonus(self, bonus_name):
        return DanceService.get_offense_bonus(self, bonus_name)

    def get_barbarian_dance_defense_bonus(self, defense_name):
        return DanceService.get_defense_bonus(self, defense_name)

    def get_barbarian_dance_engagement_speed_bonus(self):
        return DanceService.get_engagement_speed_bonus(self)

    def get_active_barbarian_berserk(self):
        state = self.get_state("barbarian_berserk")
        return state if isinstance(state, dict) else None


def make_actor_and_target(*, target_stats=None):
    room = DummyRoom(10)
    actor = DummyCombatant("Barbarian", room)
    target = DummyCombatant(
        "Goblin",
        room,
        stats=target_stats or {"discipline": 5, "charisma": 5, "strength": 5, "reflex": 5, "agility": 5, "stamina": 5},
    )
    return actor, target, room


def make_actor_and_ally(*, ally_stats=None, group_id=77, include_npc=False):
    room = DummyRoom(10)
    actor = DummyCombatant("Barbarian", room, account=object(), group_id=group_id)
    ally = DummyCombatant(
        "Ally",
        room,
        stats=ally_stats or {"discipline": 12, "charisma": 10, "strength": 12, "reflex": 11, "agility": 11, "stamina": 12, "wisdom": 10},
        account=object(),
        group_id=group_id,
    )
    npc = None
    if include_npc:
        npc = DummyCombatant("Wolf", room, stats={"discipline": 8, "charisma": 1, "strength": 10, "reflex": 10, "agility": 10, "stamina": 10}, is_npc=True)
        npc.set_state("effect_360001", {"expires_at": 9999999999.0})
    return actor, ally, npc, room