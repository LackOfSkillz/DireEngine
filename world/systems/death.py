import time


DEFAULT_CORPSE_DECAY_SECONDS = 30 * 60


def handle_death(character, cause=None, death_type="vitality"):
    character.ensure_core_defaults()
    if getattr(character.db, "life_state", None) == "dead" or bool(getattr(character.db, "is_dead", False)):
        return character.get_death_corpse() if hasattr(character, "get_death_corpse") else None

    death_type = "spirit" if str(death_type or "vitality").lower() == "spirit" else "vitality"
    death_time = time.time()
    death_location = getattr(getattr(character, "location", None), "id", None)
    had_prior_penalty = character.get_exp_debt() > 0 or bool(getattr(character.db, "death_sting_active", False) or getattr(character.db, "death_sting", False))

    character.db.life_state = "DEAD"
    character.db.is_dead = True
    character.db.death_type = death_type
    character.db.death_timestamp = death_time
    character.db.death_location = death_location
    character.db.recovery_state = "none"
    character.db.last_death_time = death_time
    character.db.death_penalty_applied = False
    character.db.in_combat = False
    character.db.target = None
    character.db.aiming = None

    if hasattr(character, "ndb"):
        for attr_name in ("combat_target", "queued_action", "pending_revive_action"):
            if hasattr(character.ndb, attr_name):
                setattr(character.ndb, attr_name, None)

    if hasattr(character, "capture_exp_debt_on_death"):
        character.capture_exp_debt_on_death(had_prior_penalty=had_prior_penalty)
    if hasattr(character, "handle_favor_death_event"):
        character.handle_favor_death_event()
    snapshot = character.get_favor_death_snapshot() if hasattr(character, "get_favor_death_snapshot") else None
    if snapshot and hasattr(character, "initialize_soul_state"):
        character.initialize_soul_state(snapshot=snapshot)
    if hasattr(character, "apply_death_sting"):
        favor_before = 0
        if isinstance(snapshot, dict):
            favor_before = snapshot.get("favor_before", 0)
        elif hasattr(character, "get_favor"):
            favor_before = character.get_favor()
        character.apply_death_sting(favor=favor_before, had_prior_penalty=had_prior_penalty)

    corpse = character.create_death_corpse() if hasattr(character, "create_death_corpse") else None
    if corpse:
        if hasattr(character, "build_corpse_wound_payload") and hasattr(corpse, "set_corpse_wounds"):
            corpse.set_corpse_wounds(character.build_corpse_wound_payload())
        corpse.db.death_timestamp = death_time
        corpse.db.time_of_death = death_time
        corpse.db.death_type = death_type
        corpse.db.decay_end_time = death_time + DEFAULT_CORPSE_DECAY_SECONDS
        corpse.db.decay_time = corpse.db.decay_end_time
        corpse.db.decay_stage = 0
        corpse.db.location = death_location
        corpse.db.is_valid_for_revive = death_type != "spirit"
        if hasattr(corpse, "refresh_decay_stage"):
            corpse.refresh_decay_stage(now=death_time)
        if death_type == "spirit":
            corpse.db.irrecoverable = True

    if hasattr(character, "move_carried_items_to_corpse"):
        character.move_carried_items_to_corpse(corpse)
    lost_coins = character.move_coins_to_corpse(corpse) if hasattr(character, "move_coins_to_corpse") else 0

    if bool(getattr(character.db, "is_npc", False)) and hasattr(character, "generate_npc_loot"):
        character.generate_npc_loot()
    if getattr(character, "location", None):
        room = character.location
        death_emote = character.get_death_emote() if hasattr(character, "get_death_emote") else f"{character.key} collapses in death."
        room.msg_contents(death_emote, exclude=[character])
    if hasattr(character, "emit_death_event"):
        character.emit_death_event("on_character_death", corpse=corpse, room=character.location, cause=cause, death_type=death_type)
    if hasattr(character, "update_death_analytics"):
        character.update_death_analytics("death")
    if hasattr(character, "msg"):
        character.msg("You have died.")
        character.msg("You feel yourself slipping free from your body.")
        if lost_coins > 0 and not bool(getattr(character.db, "is_npc", False)):
            character.msg("You feel your wealth slip from your grasp as you fall.")
    if hasattr(character, "sync_client_state"):
        character.sync_client_state()
    return corpse