from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GuardDecision:
    action_type: str
    target_id: int | None = None
    destination_id: int | None = None
    message_key: str | None = None
    state_updates: dict[str, Any] = field(default_factory=dict)
    events_to_emit: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class GuardContext:
    guard_id: int
    room_id: int | None
    zone_id: str
    room_player_count: int
    room_guard_count: int
    has_players: bool
    has_active_incident: bool
    warning_count: int = 0
    current_target_id: int | None = None
    target_in_custody: bool = False
    custody_guard_id: int | None = None
    target_is_jailed: bool = False
    confrontation_target_id: int | None = None
    confrontation_state: str = "none"
    warning_stage: int = 0
    target_suspicion_level: int = 0
    pursuit_target_id: int | None = None
    pursuit_last_known_room_id: int | None = None
    pursuit_state: str = "none"
    intercept_room_id: int | None = None
    patrol_index: int = 0
    home_room_id: int | None = None
    behavior_state: str = "idle"
    significance_tier: str = "cold"
    room_npc_count: int = 0
    used_cache: bool = False
    used_direct_room_scan: bool = False
    awareness_due: bool = True
    movement_due: bool = False
    pursuit_due: bool = False
    warning_due: bool = False
    arrest_due: bool = False
    target_present_in_room: bool = False
    escort_due: bool = False
    is_valid_guard: bool = True
    unsupported_reason: str | None = None
