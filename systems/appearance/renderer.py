import logging

from systems.appearance.normalizer import is_identity_renderable, normalize_identity_data


LOGGER = logging.getLogger(__name__)


def _build_external_text(identity):
    appearance = dict((identity or {}).get("appearance") or {})
    hair = dict(appearance.get("hair") or {})
    eyes = dict(appearance.get("eyes") or {})
    skin = dict(appearance.get("skin") or {})

    race = str(identity.get("race") or "person").strip().lower()
    height = str(appearance.get("height") or "").strip().lower()
    build = str(appearance.get("build") or "average").strip().lower()

    details = []
    if hair.get("color") and hair.get("style"):
        details.append(f"{hair.get('color')} {hair.get('style')} hair")
    elif hair.get("color"):
        details.append(f"{hair.get('color')} hair")
    if eyes.get("color"):
        details.append(f"{eyes.get('color')} eyes")
    if skin.get("tone"):
        details.append(f"{skin.get('tone')} skin")

    subject_text = f"{height} {build} {race}".strip() if height else f"{build} {race}".strip()
    article = "An" if subject_text[:1] in "aeiou" else "A"
    if not details:
        return f"{article} {subject_text}."
    if len(details) == 1:
        detail_text = details[0]
    else:
        detail_text = ", ".join(details[:-1]) + f", and {details[-1]}"
    return f"{article} {subject_text} with {detail_text}."


def render_self_view(character, identity=None, fallback_desc=None):
    resolved = normalize_identity_data(
        identity or character.db.identity,
        fallback_race=character.db.race,
        fallback_gender=character.db.gender,
    )
    if is_identity_renderable(resolved):
        appearance = dict(resolved.get("appearance") or {})
        hair = dict(appearance.get("hair") or {})
        eyes = dict(appearance.get("eyes") or {})
        skin = dict(appearance.get("skin") or {})
        race = str(resolved.get("race") or "person").strip().lower()
        height = str(appearance.get("height") or "").strip().lower()
        build = str(appearance.get("build") or "average").strip().lower()

        details = []
        if hair.get("color") and hair.get("style"):
            details.append(f"{hair.get('color')} {hair.get('style')} hair")
        elif hair.get("color"):
            details.append(f"{hair.get('color')} hair")
        if eyes.get("color"):
            details.append(f"{eyes.get('color')} eyes")
        if skin.get("tone"):
            details.append(f"{skin.get('tone')} skin")
        subject_text = f"{height} {build} {race}".strip() if height else f"{build} {race}".strip()
        if not details:
            return f"You are a {subject_text}."
        if len(details) == 1:
            detail_text = details[0]
        else:
            detail_text = ", ".join(details[:-1]) + f", and {details[-1]}"
        return f"You are a {subject_text} with {detail_text}."

    fallback = str(fallback_desc or "").strip()
    if fallback and getattr(character, "ndb", None) is not None:
        character.ndb._identity_fallback_used = True
        if not getattr(character.ndb, "_identity_fallback_logged", False):
            LOGGER.warning("[IDENTITY FALLBACK] %s missing renderable identity, using desc", getattr(character, "key", character))
            character.ndb._identity_fallback_logged = True
    return fallback or "You are an unremarkable person."


def render_external_view(character, viewer=None, identity=None, fallback_desc=None):
    resolved = normalize_identity_data(
        identity or character.db.identity,
        fallback_race=character.db.race,
        fallback_gender=character.db.gender,
    )
    if is_identity_renderable(resolved):
        return _build_external_text(resolved)
    fallback = str(fallback_desc or "").strip()
    if fallback and getattr(character, "ndb", None) is not None:
        character.ndb._identity_fallback_used = True
        if not getattr(character.ndb, "_identity_fallback_logged", False):
            LOGGER.warning("[IDENTITY FALLBACK] %s missing renderable identity, using desc", getattr(character, "key", character))
            character.ndb._identity_fallback_logged = True
    return fallback or "An unremarkable person."


def render_appearance(character, viewer=None):
    fallback_desc = character.db.desc
    if viewer == character:
        return render_self_view(character, fallback_desc=fallback_desc)
    return render_external_view(character, viewer=viewer, fallback_desc=fallback_desc)