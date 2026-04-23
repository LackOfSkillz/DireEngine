"""
Room

Rooms are simple containers that has no location of their own.

"""

import time
import logging
from collections.abc import Mapping

from django.utils.translation import gettext as _
from django.utils.text import slugify
from evennia.objects.objects import DefaultRoom
from evennia.utils.search import search_object
from evennia.utils.utils import iter_to_str
from server.systems.ammo_runtime import format_ammo_label, merge_ammo_stacks
from world.law import LAW_NONE, LAW_STANDARD
from world.systems.ranger import (
    TRAIL_DECAY_SECONDS,
    get_trail_quality_label,
    infer_environment_type,
    infer_terrain_type,
    normalize_environment_type,
    normalize_terrain_type,
)

from .objects import ObjectParent


LOGGER = logging.getLogger(__name__)


def is_fishable(room):
    if room is None:
        return False
    return bool(getattr(getattr(room, "db", None), "fishable", False))


class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    def at_object_creation(self):
        super().at_object_creation()
        if not self.db.world_id:
            self.db.world_id = slugify(self.key)
        self.db.guild_tag = None
        self.db.environment_type = infer_environment_type(self.key, getattr(self.db, "desc", "") or "")
        self.db.terrain_type = infer_terrain_type(
            self.key,
            getattr(self.db, "desc", "") or "",
            environment_type=self.db.environment_type,
        )
        self.db.allowed_professions = []
        self.db.has_passage = False
        self.db.passage_links = []
        self.db.trails = []
        self.db.is_bank = False
        self.db.is_guardhouse = False
        self.db.guardhouse_exterior = False
        self.db.is_jail = False
        self.db.is_stocks = False
        self.db.pillory = False
        self.db.high_traffic = False
        self.db.is_shop = False
        self.db.is_shrine = False
        self.db.is_vault = False
        self.db.is_recovery_point = False
        self.db.recovery_point_reference = None
        self.db.recovery_region_override = None
        self.db.no_resurrection = False
        self.db.dangerous_zone = False
        self.db.safe_zone = False
        self.db.corpse_decay_scale = 1.0
        self.db.grave_damage_scale = 1.0
        self.db.alert_level = 0
        self.db.suspicion_level = 0
        self.db.law_type = LAW_STANDARD
        self.db.region = "default_region"
        self.db.zone = "default_region"
        self.db.zone_id = "default_region"
        self.db.room_type = "room"
        self.db.no_npc_wander = False
        self.db.guild_area = False
        self.db.npc_boundary = False
        self.db.fishable = False
        self.db.fish_group = "River 1"
        self.db.ground_ammo = []
        self.db.loose_ammo = []
        if self.db.zone_id is None:
            LOGGER.warning("Room %s created without zone_id; defaulting to default_region.", self.key)

    def _get_ground_ammo_stacks(self):
        ground_ammo = getattr(self.db, "ground_ammo", None)
        if ground_ammo is None:
            ground_ammo = getattr(self.db, "loose_ammo", None)
        ammo = merge_ammo_stacks(ground_ammo or [])
        self.db.ground_ammo = list(ammo)
        self.db.loose_ammo = list(ammo)
        return list(ammo)

    def get_ground_ammo(self, ammo_type=None):
        ammo = self._get_ground_ammo_stacks()
        if ammo_type is None:
            return ammo
        target_type = str(ammo_type or "").strip().lower()
        if not target_type:
            return None
        for stack in ammo:
            if str(stack.get("ammo_type") or "").strip().lower() == target_type:
                return dict(stack)
        return None

    def set_ground_ammo(self, stacks):
        ammo = merge_ammo_stacks(stacks)
        self.db.ground_ammo = list(ammo)
        self.db.loose_ammo = list(ammo)
        return self.get_ground_ammo()

    def add_ground_ammo(self, stacks):
        ammo = merge_ammo_stacks([*self.get_ground_ammo(), *list(stacks or [])])
        self.db.ground_ammo = list(ammo)
        self.db.loose_ammo = list(ammo)
        return self.get_ground_ammo()

    def consume_ground_ammo(self, ammo_type=None, amount=1):
        requested = max(0, int(amount or 0))
        if requested <= 0:
            return {}, self.get_ground_ammo()
        stacks = list(self.get_ground_ammo())
        target_type = str(ammo_type or "").strip().lower()
        for index, stack in enumerate(stacks):
            stack_type = str(stack.get("ammo_type") or "").strip().lower()
            if target_type and stack_type != target_type:
                continue
            quantity = max(0, int(stack.get("quantity", 0) or 0))
            if quantity <= 0:
                continue
            taken = min(quantity, requested)
            consumed = dict(stack)
            consumed["quantity"] = taken
            remaining = dict(stack)
            remaining["quantity"] = quantity - taken
            updated = list(stacks)
            updated.pop(index)
            if remaining["quantity"] > 0:
                updated.append(remaining)
            self.set_ground_ammo(updated)
            return consumed, self.get_ground_ammo()
        return {}, stacks

    def get_loose_ammo(self):
        return self.get_ground_ammo()

    def set_loose_ammo(self, stacks):
        return self.set_ground_ammo(stacks)

    def add_loose_ammo(self, stacks):
        return self.add_ground_ammo(stacks)

    def get_loose_ammo_display_lines(self):
        stacks = self.get_ground_ammo()
        if not stacks:
            return []
        return [f"There {'is' if len(stacks) == 1 and int(stacks[0].get('quantity', 0) or 0) == 1 else 'are'} {', '.join(format_ammo_label(stack) for stack in stacks)} on the ground."]

    def is_bank_room(self):
        if bool(getattr(self.db, "is_bank", False)):
            return True
        tags = getattr(self, "tags", None)
        return bool(tags and tags.get("bank"))

    def is_shrine_room(self):
        if bool(getattr(self.db, "is_shrine", False)):
            return True
        tags = getattr(self, "tags", None)
        return bool(tags and tags.get("shrine"))

    def is_consecrated_room(self):
        return bool(getattr(self.db, "consecrated", False))

    def is_vault_room(self):
        if bool(getattr(self.db, "is_vault", False)):
            return True
        tags = getattr(self, "tags", None)
        return bool(tags and tags.get("vault"))

    def is_recovery_point(self):
        if bool(getattr(self.db, "is_recovery_point", False)):
            return True
        tags = getattr(self, "tags", None)
        return bool(tags and tags.get("recovery_point", category="death"))

    def get_recovery_point_reference(self):
        return getattr(self.db, "recovery_point_reference", None)

    def get_recovery_region_override(self):
        return str(getattr(self.db, "recovery_region_override", "") or "").strip() or None

    def is_no_resurrection_zone(self):
        return bool(getattr(self.db, "no_resurrection", False))

    def get_death_zone_profile(self):
        corpse_decay_scale = float(getattr(self.db, "corpse_decay_scale", 1.0) or 1.0)
        grave_damage_scale = float(getattr(self.db, "grave_damage_scale", 1.0) or 1.0)
        if bool(getattr(self.db, "dangerous_zone", False)):
            corpse_decay_scale = max(corpse_decay_scale, 1.5)
            grave_damage_scale = max(grave_damage_scale, 2.0)
        if bool(getattr(self.db, "safe_zone", False)):
            corpse_decay_scale = min(corpse_decay_scale, 0.6)
            grave_damage_scale = min(grave_damage_scale, 0.5)
        return {
            "corpse_decay_scale": max(0.1, corpse_decay_scale),
            "grave_damage_scale": max(0.1, grave_damage_scale),
            "dangerous": bool(getattr(self.db, "dangerous_zone", False)),
            "safe": bool(getattr(self.db, "safe_zone", False)),
        }

    def get_environment_type(self):
        return normalize_environment_type(
            getattr(self.db, "environment_type", None),
            default=infer_environment_type(self.key, getattr(self.db, "desc", "") or ""),
        )

    def set_environment_type(self, value):
        normalized = normalize_environment_type(value)
        self.db.environment_type = normalized
        return normalized

    def get_terrain_type(self):
        return normalize_terrain_type(
            getattr(self.db, "terrain_type", None),
            default=infer_terrain_type(
                self.key,
                getattr(self.db, "desc", "") or "",
                environment_type=getattr(self.db, "environment_type", None),
            ),
        )

    def set_terrain_type(self, value):
        normalized = normalize_terrain_type(value)
        self.db.terrain_type = normalized
        return normalized

    def prune_trails(self):
        trails = []
        now = time.time()
        for trail in list(getattr(self.db, "trails", None) or []):
            if not isinstance(trail, Mapping):
                continue
            expires_at = float(trail.get("expires_at", 0) or 0)
            if expires_at and now >= expires_at:
                continue
            entry = dict(trail)
            created_at = float(entry.get("created_at", entry.get("timestamp", now)) or now)
            max_lifetime = max(1.0, expires_at - created_at) if expires_at else 1.0
            remaining_ratio = 1.0
            if expires_at:
                remaining_ratio = max(0.0, min(1.0, (expires_at - now) / max_lifetime))
            base_strength = int(entry.get("strength", 0) or 0)
            entry["effective_strength"] = max(1, int(round(base_strength * remaining_ratio))) if base_strength > 0 else 0
            entry["timestamp"] = created_at
            trails.append(entry)
        self.db.trails = trails
        return trails

    def add_trail_entry(self, target, direction, strength=50):
        if not target or not direction:
            return None
        environment = self.get_environment_type()
        lifetime = int(TRAIL_DECAY_SECONDS.get(environment, 90) or 90)
        now = time.time()
        trails = self.prune_trails()
        trails.append(
            {
                "target_id": getattr(target, "id", None),
                "target_key": getattr(target, "key", "someone"),
                "direction": str(direction).strip().lower(),
                "strength": max(1, min(100, int(strength or 0))),
                "created_at": now,
                "timestamp": now,
                "expires_at": now + lifetime,
            }
        )
        self.db.trails = trails[-50:]
        return trails[-1]

    def get_trails_for_target(self, target):
        target_id = getattr(target, "id", None)
        target_key = ""
        if target_id is None:
            if isinstance(target, int):
                target_id = target
            else:
                target_key = str(target or "").strip().lower()
                if not target_key:
                    return []
        trails = []
        for trail in self.prune_trails():
            trail_target_id = int(trail.get("target_id", 0) or 0)
            trail_target_key = str(trail.get("target_key", "") or "").strip().lower()
            if target_id is not None and trail_target_id == int(target_id):
                trails.append(trail)
                continue
            if target_key and trail_target_key == target_key:
                trails.append(trail)
        return sorted(
            trails,
            key=lambda trail: (
                int(trail.get("effective_strength", trail.get("strength", 0)) or 0),
                float(trail.get("created_at", 0) or 0),
            ),
            reverse=True,
        )

    def get_visible_trails_for(self, looker):
        trails = self.prune_trails()
        if not looker:
            return []
        if not hasattr(looker, "is_profession") or not looker.is_profession("ranger"):
            return []

        minimum_strength = 25
        if hasattr(looker, "is_hidden") and looker.is_hidden():
            minimum_strength -= 10
        if hasattr(looker, "get_ranger_tracking_bonus"):
            minimum_strength -= max(0, int(looker.get_ranger_tracking_bonus() / 2))

        visible = []
        for trail in trails:
            perceived_strength = int(trail.get("effective_strength", trail.get("strength", 0)) or 0)
            if hasattr(looker, "get_ranger_trail_read_bonus"):
                perceived_strength += int(looker.get_ranger_trail_read_bonus(trail) or 0)
            if perceived_strength < max(5, minimum_strength):
                continue
            entry = dict(trail)
            entry["apparent_strength"] = perceived_strength
            visible.append(entry)
        return sorted(
            visible,
            key=lambda trail: (
                int(trail.get("apparent_strength", trail.get("effective_strength", trail.get("strength", 0))) or 0),
                float(trail.get("created_at", 0) or 0),
            ),
            reverse=True,
        )

    def describe_trail(self, trail, observer=None):
        quality = get_trail_quality_label(trail.get("apparent_strength", trail.get("effective_strength", trail.get("strength", 0))))
        direction = str(trail.get("direction", "somewhere") or "somewhere").lower()
        target_key = str(trail.get("target_key", "someone") or "someone")
        description = f"{quality} tracks from {target_key} lead {direction}."
        if observer and hasattr(observer, "get_ranger_tracking_depth"):
            depth = observer.get_ranger_tracking_depth()
            strength = int(trail.get("apparent_strength", trail.get("effective_strength", trail.get("strength", 0))) or 0)
            if depth in {"clear", "keen"} and strength >= 45:
                description += " The sign is still easy to read."
            elif depth == "keen" and strength >= 70:
                description += " The passage feels recent and confident."
        return description

    def get_exit_direction_to(self, destination):
        if not destination:
            return None
        destination_id = getattr(destination, "id", None)
        for exit_obj in self.contents_get(content_type="exit"):
            exit_destination = getattr(exit_obj, "destination", None)
            if exit_destination == destination:
                return str(getattr(exit_obj, "key", "") or "").strip().lower() or None
            if destination_id is not None and getattr(exit_destination, "id", None) == destination_id:
                return str(getattr(exit_obj, "key", "") or "").strip().lower() or None
        return None

    def is_shop(self):
        return bool(getattr(self.db, "is_shop", False))

    def has_passage(self):
        return bool(getattr(self.db, "has_passage", False))

    def get_passage_destinations(self):
        destinations = []
        for room_ref in getattr(self.db, "passage_links", None) or []:
            if hasattr(room_ref, "id") and getattr(room_ref, "id", None):
                destinations.append(room_ref)
                continue
            result = search_object(f"#{room_ref}") if str(room_ref).isdigit() else search_object(room_ref)
            if result:
                destinations.append(result[0])
        return destinations

    def get_shopkeeper(self):
        return next(
            (
                obj for obj in self.contents
                if hasattr(obj, "is_shopkeeper") and obj.is_shopkeeper()
            ),
            None,
        )

    def at_object_leave(self, moved_obj, target_location, **kwargs):
        super().at_object_leave(moved_obj, target_location, **kwargs)
        if not moved_obj or not target_location:
            return
        is_character = False
        if hasattr(moved_obj, "is_typeclass"):
            is_character = moved_obj.is_typeclass("typeclasses.characters.Character", exact=False)
        if not is_character:
            return
        direction = self.get_exit_direction_to(target_location)
        if not direction:
            return
        bond_strength = 50
        if hasattr(moved_obj, "get_wilderness_bond"):
            bond_strength += int((moved_obj.get_wilderness_bond() - 50) / 5)
        if hasattr(moved_obj, "is_hidden") and moved_obj.is_hidden():
            bond_strength -= 10
        moved_states = getattr(getattr(moved_obj, "db", None), "states", None)
        cover_data = moved_states.get("ranger_cover_tracks") if isinstance(moved_states, Mapping) else None
        if isinstance(cover_data, Mapping):
            bond_strength -= int(cover_data.get("strength_penalty", 25) or 25)
        self.add_trail_entry(moved_obj, direction, strength=max(5, min(100, bond_strength)))

    def allows_profession(self, profession_name):
        allowed = [
            str(entry).strip().lower().replace("-", "_").replace(" ", "_")
            for entry in (getattr(self.db, "allowed_professions", None) or [])
            if str(entry or "").strip()
        ]
        if not allowed:
            return True
        return str(profession_name or "").strip().lower() in allowed

    def get_law_type(self):
        return getattr(self.db, "law_type", None) or LAW_STANDARD

    def is_lawless(self):
        return self.get_law_type() == LAW_NONE

    def get_region(self):
        return getattr(self.db, "region", None) or "default_region"

    def get_display_characters(self, looker, **kwargs):
        visible = []
        for obj in self.contents:
            is_character = False
            if hasattr(obj, "is_typeclass"):
                is_character = obj.is_typeclass("typeclasses.characters.Character", exact=False)
            if obj == looker or not is_character:
                continue
            if hasattr(looker, "can_detect") and not looker.can_detect(obj):
                continue
            visible.append(obj)

        if not visible:
            return ""

        rendered = []
        for obj in visible:
            name = obj.get_display_name(looker, **kwargs)
            hint = str(obj.get_interaction_hint(looker) if hasattr(obj, "get_interaction_hint") else "" or "").strip()
            rendered.append(f"{name} {hint}".strip())

        names = ", ".join(rendered)
        return f"Characters: {names}"

    def get_display_exits(self, looker, **kwargs):
        try:
            from systems.chargen import mirror as chargen_mirror

            if looker and getattr(looker, "location", None) == self and chargen_mirror.is_chargen_active(looker):
                return ""
        except Exception:
            pass

        def _sort_exits(exit_objects):
            exit_order = kwargs.get("exit_order")
            if not exit_order:
                return sorted(exit_objects, key=lambda exit_obj: str(exit_obj.key).lower())

            sort_index = {name: index for index, name in enumerate(exit_order)}
            end_pos = len(sort_index)
            return sorted(
                exit_objects,
                key=lambda exit_obj: (
                    sort_index.get(str(exit_obj.key).lower(), end_pos),
                    str(exit_obj.key).lower(),
                ),
            )

        exits = self.filter_visible(self.contents_get(content_type="exit"), looker, **kwargs)
        if not exits:
            return ""

        rendered = []
        seen_labels = set()
        for exit_obj in _sort_exits(exits):
            is_hidden = bool(getattr(exit_obj.db, "hidden_exit", False) or getattr(exit_obj.db, "secret", False))
            if is_hidden:
                continue
            if bool(getattr(exit_obj.db, "climb_contest", False)) and str(getattr(exit_obj.db, "climb_action_command", "") or "").strip():
                continue
            exit_key = str(getattr(exit_obj, "key", "") or "").strip().lower()
            if not exit_key or exit_key in seen_labels:
                continue
            seen_labels.add(exit_key)
            display_name = str(exit_obj.get_display_name(looker, **kwargs) or "").strip() or exit_key
            rendered.append(f"|lc__clickmove__ {str(exit_obj.key)}|lt|y{display_name}|n|le")

        exit_names = iter_to_str(rendered, endsep=_(", and"))
        return f"|w{_('Exits')}:|n {exit_names}" if exit_names else ""

    def get_contextual_action_entries(self, looker, **kwargs):
        if not looker or getattr(looker, "location", None) != self:
            return []

        entries = []
        seen_commands = set()
        exits = self.filter_visible(self.contents_get(content_type="exit"), looker, **kwargs)
        for exit_obj in exits:
            if not bool(getattr(exit_obj.db, "climb_contest", False)):
                continue
            command = str(getattr(exit_obj.db, "climb_action_command", "") or "").strip()
            label = str(getattr(exit_obj.db, "climb_action_label", "") or command).strip()
            if not command or not label:
                continue
            lowered = command.lower()
            if lowered in seen_commands:
                continue
            seen_commands.add(lowered)
            entries.append({"command": command, "label": label})

        if hasattr(looker, "get_ranger_room_action_entries"):
            for entry in list(looker.get_ranger_room_action_entries(self) or []):
                command = str(entry.get("command", "") or "").strip()
                label = str(entry.get("label", "") or command).strip()
                if not command or not label:
                    continue
                lowered = command.lower()
                if lowered in seen_commands:
                    continue
                seen_commands.add(lowered)
                entries.append({"command": command, "label": label})

        vendors = [
            obj for obj in list(self.contents or [])
            if bool(getattr(getattr(obj, "db", None), "is_vendor", False))
        ]
        for vendor in vendors:
            inventory = list(getattr(vendor.db, "inventory", []) or [])
            if inventory:
                browse_command = str(getattr(vendor.db, "browse_action_command", "shop") or "shop").strip()
                browse_label = str(getattr(vendor.db, "browse_action_label", "browse goods") or "browse goods").strip()
                lowered = browse_command.lower()
                if browse_command and browse_label and lowered not in seen_commands:
                    seen_commands.add(lowered)
                    entries.append({"command": browse_command, "label": browse_label})
                for stock_name in inventory:
                    command = f"buy {stock_name}"
                    lowered = command.lower()
                    if lowered in seen_commands:
                        continue
                    seen_commands.add(lowered)
                    entries.append({"command": command, "label": command})
        return entries

    def get_display_actions(self, looker, **kwargs):
        aftermath_entries = []
        try:
            from systems import aftermath

            if looker and getattr(looker, "location", None) == self:
                aftermath_entries = list(aftermath.get_room_action_entries(looker, self) or [])
        except Exception:
            aftermath_entries = []

        try:
            from systems.chargen import mirror as chargen_mirror

            if not looker or getattr(looker, "location", None) != self:
                actions = []
            else:
                actions = list(chargen_mirror.get_available_actions(looker) or [])
        except Exception:
            actions = []

        actions.extend(self.get_contextual_action_entries(looker, **kwargs))
        actions.extend(aftermath_entries)

        if not actions:
            return ""

        rendered = [
            f"|lc__clickmove__ {entry['command']}|lt|y{entry['label']}|n|le"
            for entry in actions
        ]
        action_names = iter_to_str(rendered, endsep=_(", and"))
        return f"|w{_('Actions')}:|n {action_names}" if action_names else ""

    def get_display_footer(self, looker, **kwargs):
        parent_footer = super().get_display_footer(looker, **kwargs)
        aftermath_lines = []
        prestige_lines = []
        ranger_lines = []
        try:
            from systems import aftermath

            if looker and getattr(looker, "location", None) == self:
                aftermath.note_room_look(looker, self)
                aftermath_lines = list(aftermath.get_room_render_lines(looker, self) or [])
        except Exception:
            aftermath_lines = []
        if looker and getattr(looker, "location", None) == self:
            prestige_room = getattr(getattr(self, "db", None), "ranger_prestige_room", None)
            if prestige_room and hasattr(prestige_room, "contents"):
                visible_presence = any(
                    obj != looker and not bool(getattr(getattr(obj, "db", None), "is_npc", False))
                    for obj in list(getattr(prestige_room, "contents", []) or [])
                )
                if visible_presence:
                    signal = str(getattr(self.db, "ranger_prestige_presence_text", "") or "").strip()
                    if signal:
                        prestige_lines.append(signal)
        if looker and getattr(looker, "location", None) == self and hasattr(looker, "get_ranger_room_render_lines"):
            try:
                ranger_lines = list(looker.get_ranger_room_render_lines(self) or [])
            except Exception:
                ranger_lines = []
        ammo_lines = self.get_loose_ammo_display_lines() if looker and getattr(looker, "location", None) == self else []
        actions = self.get_display_actions(looker, **kwargs)
        parts = [part for part in [parent_footer, *aftermath_lines, *prestige_lines, *ranger_lines, *ammo_lines, actions] if part]
        return "\n".join(parts)
