import json

from django.http import Http404

from systems.appearance.normalizer import normalize_identity_data
from web.character_builder import normalize_builder_payload
from world.professions import DEFAULT_PROFESSION
from world.races import DEFAULT_RACE, RACE_DEFINITIONS, get_race_display_name, resolve_race_name


def parse_request_data(request):
    if request.content_type and "application/json" in request.content_type.lower():
        try:
            return json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError, UnicodeDecodeError):
            return {}
    return request.POST


def get_owned_characters(account):
    if not getattr(account, "is_authenticated", False):
        return []
    return [character for character in account.characters.all() if character]


def get_character_slot_summary(account):
    characters = get_owned_characters(account)
    max_slots = account.get_character_slots() if getattr(account, "is_authenticated", False) else 0
    available_slots = account.get_available_character_slots() if getattr(account, "is_authenticated", False) else 0
    return {
        "used": len(characters),
        "max": max_slots,
        "available": available_slots,
        "is_unlimited": max_slots is None,
        "is_full": available_slots == 0 if max_slots is not None else False,
    }


def get_slot_limit_message(account):
    slot_summary = get_character_slot_summary(account)
    max_slots = slot_summary["max"]
    if max_slots is None or not slot_summary["is_full"]:
        return ""
    return "You have reached the maximum number of characters."


def normalize_character_creation_error(account, errors):
    message = " ".join(str(error) for error in (errors or ["Character creation failed."]))
    if "maximum of" in message.lower():
        return get_slot_limit_message(account) or message
    return message


def get_selected_character_id(request):
    try:
        return int(request.session.get("puppet") or 0) or None
    except (TypeError, ValueError):
        return None


def serialize_character(character, *, selected_id=None):
    race_name = str(getattr(character.db, "race", DEFAULT_RACE) or DEFAULT_RACE)
    gender = str(getattr(character.db, "gender", "unknown") or "unknown")
    identity = normalize_identity_data(
        getattr(character.db, "identity", None),
        fallback_race=race_name,
        fallback_gender=gender,
    )
    appearance = dict(identity.get("appearance") or {})
    hair = dict(appearance.get("hair") or {})
    eyes = dict(appearance.get("eyes") or {})
    skin = dict(appearance.get("skin") or {})
    summary_parts = []
    if appearance.get("build"):
        summary_parts.append(f"{appearance.get('build')} build")
    if skin.get("tone"):
        summary_parts.append(f"{skin.get('tone')} skin")
    if hair.get("color") and hair.get("style"):
        summary_parts.append(f"{hair.get('color')} {hair.get('style')} hair")
    elif hair.get("color"):
        summary_parts.append(f"{hair.get('color')} hair")
    if eyes.get("color"):
        summary_parts.append(f"{eyes.get('color')} eyes")
    return {
        "id": int(character.id),
        "name": str(character.key),
        "race": race_name,
        "race_display": get_race_display_name(race_name),
        "gender": gender,
        "gender_display": gender.replace("_", " ").title(),
        "identity_summary": " | ".join(summary_parts),
        "selected": bool(selected_id and int(character.id) == int(selected_id)),
    }


def get_owned_character_or_404(account, character_id):
    for character in get_owned_characters(account):
        if int(character.id) == int(character_id):
            return character
    raise Http404("Character not found.")


def set_selected_character(request, character):
    request.session["puppet"] = int(character.id) if character else None
    request.session.modified = True


def clear_selected_character_if_matches(request, character):
    selected_id = get_selected_character_id(request)
    if selected_id and int(selected_id) == int(character.id):
        request.session["puppet"] = None
        request.session.modified = True


def get_race_choices():
    return [(race_name, get_race_display_name(race_name)) for race_name in sorted(RACE_DEFINITIONS.keys())]


def normalize_race_choice(race_name):
    normalized = resolve_race_name(race_name or DEFAULT_RACE)
    if normalized not in RACE_DEFINITIONS:
        raise ValueError("Choose a valid race.")
    return normalized


def create_web_character(account, *, name, race, gender="neutral", appearance=None, identity=None):
    normalized_race = normalize_race_choice(race)
    character, errors = account.create_character(
        key=str(name or "").strip(),
        race=normalized_race,
        gender=str(gender or "neutral").strip().lower() or "neutral",
        profession=DEFAULT_PROFESSION,
        activate_onboarding=False,
        skip_post_create_setup=True,
    )
    if errors or not character:
        raise ValueError(normalize_character_creation_error(account, errors))

    character.db.gender = str(gender or "neutral").strip().lower() or "neutral"
    character.db.identity = normalize_identity_data(
        identity,
        fallback_race=normalized_race,
        fallback_gender=character.db.gender,
        fallback_appearance=appearance,
    )
    if hasattr(character, "get_rendered_desc"):
        character.db.desc = character.get_rendered_desc()

    character.db.new_player = True
    character.db.skip_chargen = True
    character.db.web_char_created = True
    return character


def create_web_character_from_payload(account, payload):
    normalized = normalize_builder_payload(payload)
    character = create_web_character(
        account,
        name=normalized["name"],
        race=normalized["race"],
        gender=normalized["gender"],
        appearance=normalized["appearance"],
        identity=normalized["identity"],
    )
    return character, normalized


def delete_owned_character(request, account, character_id):
    character = get_owned_character_or_404(account, character_id)
    clear_selected_character_if_matches(request, character)
    character.delete()
    return character