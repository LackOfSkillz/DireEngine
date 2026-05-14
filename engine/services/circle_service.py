"""Circle advancement projection and commit flow for LEARN-002b."""

from dataclasses import dataclass
from collections.abc import Mapping

from domain.feats.feat_definitions import Feat
from domain.spells.spell_definitions import SPELL_REGISTRY
from engine.services.feat_training_service import FeatTrainerService
from engine.services.slot_service import SlotService
from engine.services.spell_access_service import SpellAccessService
from engine.services.guildhall_locator import get_guildhall_room_key


@dataclass
class AdvancementResult:
    ok: bool
    message: str
    room_message: str | None = None
    target_message: str | None = None
    new_circle: int = 0
    tdps_granted: int = 0


def get_placeholder_circle_requirements(profession, target_circle):
    circle = max(1, int(target_circle or 1))
    return {
        "skill_rank_total_required": circle * 50,
        "money_coins_required": circle * 100,
        "profession_specific_notes": (
            f"Placeholder requirements for {profession} circle {circle}."
        ),
    }


def calculate_circle_tdp_grant(new_circle):
    circle = int(new_circle or 0)
    if circle > 150:
        return 0
    if circle < 10:
        return 50
    return 100 + circle


def find_guild_leader_for_profession(character, profession):
    if not getattr(character, "location", None):
        return None
    from typeclasses.npcs import GuildLeaderNPC, EmpathGuildleader, ClericGuildmaster, RangerGuildmaster

    leader_types = (GuildLeaderNPC, EmpathGuildleader, ClericGuildmaster, RangerGuildmaster)
    wanted = str(profession or "").strip().lower()
    for obj in list(getattr(character.location, "contents", []) or []):
        if not isinstance(obj, leader_types):
            continue
        leads = str(getattr(obj.db, "leads_profession", None) or getattr(obj.db, "trains_profession", None) or "").strip().lower()
        if leads == wanted:
            return obj
    return None


def _iter_skill_ranks(character):
    exp_store = getattr(character.db, "exp_skill_state", None)
    if isinstance(exp_store, Mapping) and exp_store:
        for entry in exp_store.values():
            if isinstance(entry, Mapping):
                yield max(0, int(entry.get("rank", 0) or 0))
        return
    skills = getattr(character.db, "skills", None)
    if isinstance(skills, Mapping):
        for entry in skills.values():
            if isinstance(entry, Mapping):
                yield max(0, int(entry.get("rank", 0) or 0))


def _display_name(character):
    return getattr(character, "key", None) or getattr(character, "name", None) or "Someone"


def _format_spell_names(spells):
    return ", ".join(spell.name for spell in spells)


def _format_feat_names(feats: list[Feat]):
    return ", ".join(feat.name for feat in feats)


def _get_expiring_apprentice_spells(character, expired_circle):
    profession = SpellAccessService._get_profession(character)
    expired = []
    for spell in SPELL_REGISTRY.values():
        if int(getattr(spell, "apprentice_until_circle", 0) or 0) != int(expired_circle or 0):
            continue
        allowed_professions = {
            SpellAccessService._normalize_profession(entry) for entry in (spell.allowed_professions or [])
        }
        if allowed_professions and profession not in allowed_professions:
            continue
        if SpellAccessService.has_spell(character, spell.id):
            continue
        expired.append(spell)
    return sorted(expired, key=lambda spell: spell.name.lower())


def collect_circle_advancement_private_messages(character, old_circle, new_circle):
    if SlotService._get_magic_placement(character) is None:
        return []

    SlotService.recompute_max(character)
    messages = []
    granted_feats = FeatTrainerService.grant_circle_profession_feats(character, new_circle)
    if granted_feats:
        messages.append(
            f"Your guild grants you the {_format_feat_names(granted_feats)} feat as a benefit of your advancement to circle {int(new_circle or 0)}."
        )

    if int(new_circle or 0) == 10:
        unmemorized = SpellAccessService.get_apprentice_spells(character)
        if unmemorized:
            messages.append(
                "You have reached the 10th circle. At the 11th circle, your apprentice access to "
                f"{_format_spell_names(unmemorized)} will expire unless you permanently memorize the spell. "
                "Use SLOTS to view your available slot allocations."
            )

    if int(old_circle or 0) <= 10 < int(new_circle or 0):
        expired = _get_expiring_apprentice_spells(character, 10)
        if expired:
            messages.append(
                "Your apprentice access has expired with your advancement to the 11th circle. You can no longer cast "
                f"{_format_spell_names(expired)}."
            )

    return messages


def project_advancement(character):
    profession = str(getattr(character.db, "profession", "commoner") or "commoner").strip().lower()
    current_circle = int(getattr(character.db, "circle", 0) or 0)
    target_circle = current_circle + 1
    guildhall_room_key = get_guildhall_room_key(profession)
    leader = find_guild_leader_for_profession(character, profession)
    requirements = get_placeholder_circle_requirements(profession, target_circle)
    total_ranks = sum(_iter_skill_ranks(character))
    coins = int(getattr(character.db, "coins", 0) or 0)
    missing = []
    if total_ranks < int(requirements["skill_rank_total_required"] or 0):
        missing.append(f"Skill ranks: {total_ranks}/{int(requirements['skill_rank_total_required'] or 0)}")
    if coins < int(requirements["money_coins_required"] or 0):
        missing.append(f"Coins: {coins}/{int(requirements['money_coins_required'] or 0)}")
    if not guildhall_room_key:
        missing.append(f"Guildhall: not yet available for {profession.replace('_', ' ').title()}")
    leader_name = getattr(leader, "key", "the guild leader")
    return {
        "profession": profession,
        "current_circle": current_circle,
        "target_circle": target_circle,
        "guildhall_room_key": guildhall_room_key,
        "requirements": requirements,
        "requirements_met": not missing,
        "missing": missing,
        "tdp_grant_preview": calculate_circle_tdp_grant(target_circle),
        "skill_rank_total": total_ranks,
        "coins": coins,
        "room_message": (
            f"{_display_name(character)} stands before {leader_name}, who eventually shakes their head."
            if missing
            else f"{_display_name(character)} stands before {leader_name}, who appraises them in silence."
        ) if leader else None,
    }


def commit_advancement(character):
    profession = str(getattr(character.db, "profession", "commoner") or "commoner").strip().lower()
    leader = find_guild_leader_for_profession(character, profession)
    if not leader:
        return AdvancementResult(False, "You are not with your guild leader.")

    projection = project_advancement(character)
    if not projection["requirements_met"]:
        return AdvancementResult(False, f"{leader.key} shakes their head: {'; '.join(projection['missing'])}")

    new_circle = int(projection["target_circle"] or 0)
    coin_cost = int(projection["requirements"]["money_coins_required"] or 0)
    tdp_grant = int(projection["tdp_grant_preview"] or 0)
    old_circle = int(getattr(character.db, "circle", 0) or 0)
    character.db.coins = max(0, int(getattr(character.db, "coins", 0) or 0) - coin_cost)
    character.db.circle = new_circle
    if hasattr(character, "grant_tdp"):
        character.grant_tdp(tdp_grant, reason=f"circle_{new_circle}")
    private_messages = collect_circle_advancement_private_messages(character, old_circle, new_circle)
    if hasattr(character, "sync_client_state"):
        character.sync_client_state()
    actor_message = (
        f"{leader.key} marks your advancement. You are now Circle {new_circle}, and {tdp_grant} Time Development Points settle into your training."
    )
    if private_messages:
        actor_message = "\n".join([actor_message, *private_messages])
    return AdvancementResult(
        True,
        actor_message,
        room_message=f"{_display_name(character)} has advanced in their guild! {leader.key} marks them as Circle {new_circle}.",
        new_circle=new_circle,
        tdps_granted=tdp_grant,
    )