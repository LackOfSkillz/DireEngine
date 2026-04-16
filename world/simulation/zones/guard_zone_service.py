import time
from dataclasses import replace

from django.conf import settings
from evennia.objects.models import ObjectDB
from evennia.server.models import ServerConfig
from evennia.utils import logger

from world.simulation.cache.room_facts import get_or_create_room_facts
from world.simulation.cache.zone_facts import get_zone_facts
from world.simulation.custody import JAIL_ROOM_ID, clear_custody, enter_custody, enter_jail, is_in_custody, is_jailed
from world.simulation.events import SimEvent
from world.simulation.guard_messages import get_enter_message, get_exit_message, get_observe_message
from world.simulation.handlers.guard_state import MIN_PURSUIT_THRESHOLD, MIN_TARGET_THRESHOLD, MIN_WARN_THRESHOLD
from world.simulation.patrol_zones import get_patrol_zone_for_room
from world.simulation.resolvers.guard_decision import GuardContext, GuardDecision
from world.simulation.resolvers.guard_resolver import resolve_guard_decision
from world.simulation.significance import COLD, DORMANT, HOT, WARM, normalize_tier
from world.simulation.service import ZoneSimulationService


DEFAULT_MAX_EVENT_WAKE_NPCS = 10
RECENT_WAKE_WINDOW_SECONDS = 15.0
DORMANT_WINDOW_SECONDS = 60.0
PLAYER_ENTER_SUSPICION_GAIN = 2
PLAYER_LEAVE_SUSPICION_GAIN = 0
PLAYER_FLED_SUSPICION_GAIN = 10
PLAYER_COMPLIED_SUSPICION_GAIN = -15
GUARD_WARNED_SUSPICION_GAIN = 5
ADJACENT_SUSPICION_DIVISOR = 2
ADJACENT_PURSUIT_THRESHOLD = 26
TIER_PRIORITY = [HOT, WARM, COLD, DORMANT]
GUARD_RUNTIME_TRACE_CONFIG_KEY = "diresim_guard_runtime_trace"
OBSERVE_EMOTE_COOLDOWN_SECONDS = 8.0
RING_TIER_ELIGIBILITY = {
    "fast": {HOT},
    "normal": {HOT, WARM},
    "slow": {WARM, COLD},
    "deep": {COLD, DORMANT},
}


class GuardZoneService(ZoneSimulationService):
    def __init__(self, service_id, zone_id):
        super().__init__(service_id, zone_id)
        # Significance remains transient service state in this phase. Do not persist it.
        self.last_cycle_metrics = {}
        self.last_ring_metrics = {}
        self.debug_enabled = False
        self.guard_significance = {}
        self.awareness_due_guard_ids = set()
        self.movement_due_guard_ids = set()
        self.recent_wake_timestamps = {}
        self.recent_relevance_timestamps = {}
        self.wake_sources = {}
        self.event_debug_metrics = {"processed": 0, "woken": 0}
        self.zonefacts_feed_metrics = {
            "zonefacts_player_room_updates": 0,
            "zonefacts_hot_room_updates": 0,
            "zonefacts_incident_updates": 0,
        }
        self.suspicion_metrics = {
            "suspicion_added": 0,
            "suspicion_targets_count": 0,
            "suspicion_events_processed": 0,
        }
        self.pending_suspicion_updates = {}
        self.pursuit_metrics = {
            "pursuit_events_processed": 0,
            "pursuit_started": 0,
            "pursuit_refreshed": 0,
            "pursuit_cleared": 0,
        }
        self.pending_pursuit_updates = {}
        self.pending_confrontation_updates = {}
        self.custody_metrics = {
            "arrests_successful": 0,
            "escorts_started": 0,
            "escorts_completed": 0,
            "jail_entries": 0,
        }
        self.queues = self._new_tiered_queues()

    def emit_event(self, event_type, payload=None):
        normalized_event_type = str(event_type or "").strip().upper()
        payload = dict(payload or {})
        if normalized_event_type != "GUARD_MESSAGE":
            return False
        room_id = int(payload.get("room_id", 0) or 0)
        text = str(payload.get("text", "") or "").strip()
        if room_id <= 0 or not text:
            return False
        room = self.get_guard_destination(room_id)
        if room is None or not hasattr(room, "msg_contents"):
            return False
        room.msg_contents(text, exclude=list(payload.get("exclude") or []))
        return True

    def add_guard(self, guard):
        npc_id = int(getattr(guard, "id", 0) or 0)
        self.npc_ids.add(npc_id)
        self.guard_significance.setdefault(npc_id, COLD)
        self.recent_relevance_timestamps.setdefault(npc_id, time.time())

    def _decision_logging_enabled(self):
        return bool(getattr(settings, "ENABLE_DIRESIM_DECISION_LOGGING", False))

    def _get_commit_mode(self):
        normalized = str(getattr(settings, "DIRESIM_COMMIT_MODE", "full") or "full").strip().lower() or "full"
        if normalized not in {"none", "state_only", "full"}:
            return "full"
        return normalized

    def _get_max_active_guards(self):
        return max(0, int(getattr(settings, "MAX_ACTIVE_GUARDS", 0) or 0))

    def _get_max_event_wake_npcs(self):
        return max(1, int(getattr(settings, "MAX_EVENT_WAKE_NPCS", DEFAULT_MAX_EVENT_WAKE_NPCS) or DEFAULT_MAX_EVENT_WAKE_NPCS))

    def _get_active_guard_ids(self):
        active_guard_ids = sorted(self.npc_ids)
        max_active_guards = self._get_max_active_guards()
        if max_active_guards <= 0:
            return active_guard_ids

        capped_guard_ids = active_guard_ids[:max_active_guards]
        now = time.time()
        recent_woken_guard_ids = []
        for guard_id in active_guard_ids[max_active_guards:]:
            recent_wake_at = float(self.recent_wake_timestamps.get(guard_id, 0.0) or 0.0)
            if recent_wake_at <= 0.0:
                continue
            if (now - recent_wake_at) > RECENT_WAKE_WINDOW_SECONDS:
                continue
            recent_woken_guard_ids.append(int(guard_id))
        return capped_guard_ids + recent_woken_guard_ids

    def _log_decision(self, guard, decision, context, ring, significance_tier):
        if not self._decision_logging_enabled():
            return
        self._append_runtime_trace(
            "decision",
            guard_id=int(getattr(guard, "id", 0) or 0),
            ring=str(ring),
            tier=normalize_tier(significance_tier),
            action=str(getattr(decision, "action_type", "NOOP") or "NOOP"),
            reason=str((getattr(decision, "state_updates", {}) or {}).get("decision_reason", "unknown")),
            target_id=getattr(context, "current_target_id", None),
        )
        logger.log_info(
            f"[DECISION] guard={int(getattr(guard, 'id', 0) or 0)} ring={ring} tier={normalize_tier(significance_tier)} action={str(getattr(decision, 'action_type', 'NOOP') or 'NOOP')} reason={str((getattr(decision, 'state_updates', {}) or {}).get('decision_reason', 'unknown'))} target={getattr(context, 'current_target_id', None)}"
        )

    def _append_runtime_trace(self, event_type, **details):
        if not self._decision_logging_enabled():
            return None
        event = {
            "ts": time.time(),
            "service_id": str(self.service_id),
            "zone_id": str(self.zone_id),
            "event_type": str(event_type),
            "details": details,
        }
        trace = list(ServerConfig.objects.conf(key=GUARD_RUNTIME_TRACE_CONFIG_KEY, default=[]) or [])
        trace.append(event)
        if len(trace) > 200:
            trace = trace[-200:]
        ServerConfig.objects.conf(key=GUARD_RUNTIME_TRACE_CONFIG_KEY, value=trace)
        return event

    def _new_tiered_queues(self):
        return {
            "fast": {HOT: [], WARM: [], COLD: [], DORMANT: []},
            "normal": {HOT: [], WARM: [], COLD: [], DORMANT: []},
            "slow": {HOT: [], WARM: [], COLD: [], DORMANT: []},
            "deep": {HOT: [], WARM: [], COLD: [], DORMANT: []},
        }

    def rebuild_queues_if_needed(self):
        self.queues = self._new_tiered_queues()
        for npc_id in self._get_active_guard_ids():
            tier = self._get_queue_tier_for_guard(npc_id)
            self.guard_significance.setdefault(npc_id, COLD)
            for ring, eligible_tiers in RING_TIER_ELIGIBILITY.items():
                if tier in eligible_tiers:
                    self.queues[ring][tier].append(npc_id)

    def _get_queue_tier_for_guard(self, npc_id):
        now = time.time()
        if npc_id in self.awareness_due_guard_ids:
            return HOT
        recent_wake_at = float(self.recent_wake_timestamps.get(npc_id, 0.0) or 0.0)
        if recent_wake_at > 0.0 and (now - recent_wake_at) <= RECENT_WAKE_WINDOW_SECONDS:
            return WARM
        return normalize_tier(self.guard_significance.get(npc_id, COLD))

    def get_queue_debug_snapshot(self):
        snapshot = {}
        for ring, ring_queues in self.queues.items():
            snapshot[ring] = {tier: len(ring_queues.get(tier, [])) for tier in TIER_PRIORITY}
        return snapshot

    def get_zone_debug_snapshot(self):
        zone_facts = get_zone_facts(self.zone_id)
        zone_summary = zone_facts.debug_summary() if zone_facts is not None else {"hot_rooms": 0, "incident_rooms": 0, "active_player_rooms": 0}
        same_room_wakes = sum(1 for source in self.wake_sources.values() if source == "same_room_event")
        adjacent_wakes = sum(1 for source in self.wake_sources.values() if source == "adjacent_room_event")
        return {
            "queues": self.get_queue_debug_snapshot(),
            "hot_room_count": int(zone_summary.get("hot_rooms", 0) or 0),
            "active_player_room_count": int(zone_summary.get("active_player_rooms", 0) or 0),
            "incident_room_count": int(zone_summary.get("incident_rooms", 0) or 0),
            "recent_wake_counts": {
                "same_room_event": same_room_wakes,
                "adjacent_room_event": adjacent_wakes,
            },
        }

    def process_cycle(self, ring, budget):
        self.process_pending_events()
        self.rebuild_queues_if_needed()
        ring_queues = self.queues.get(ring, {})
        ring_metrics = {
            "processed_hot": 0,
            "processed_warm": 0,
            "processed_cold": 0,
            "processed_dormant": 0,
        }

        for tier in TIER_PRIORITY:
            queue = list(ring_queues.get(tier, []))
            for npc_id in queue:
                if budget.exceeded():
                    self.last_ring_metrics[ring] = ring_metrics
                    return

                guard = self.get_guard(npc_id)
                if not guard:
                    continue

                context = self.read_guard_context(guard)
                new_tier = self.evaluate_guard_significance(guard, context)
                old_tier, normalized_tier = self.update_guard_significance(guard, new_tier)
                context = self._shape_context_for_ring(guard, context, ring, normalized_tier)
                decision = self.decide_guard_action(guard, context, ring=ring, significance_tier=normalized_tier)
                commit_metrics = self.commit_guard_decision(guard, decision, context, ring=ring, significance_tier=normalized_tier) or {}
                self.last_cycle_metrics[int(getattr(guard, "id", 0) or 0)] = {
                    "action_type": str(getattr(decision, "action_type", "NOOP") or "NOOP"),
                    "decision_reason": str((getattr(decision, "state_updates", {}) or {}).get("decision_reason", "unknown")),
                    "used_cache": bool(getattr(context, "used_cache", False)),
                    "used_direct_room_scan": bool(getattr(context, "used_direct_room_scan", False)),
                    "tier_old": old_tier,
                    "tier_new": normalized_tier,
                    "tier_changed": old_tier != normalized_tier,
                    "ring": ring,
                    "move_attempted": bool(commit_metrics.get("move_attempted", False)),
                    "move_success": bool(commit_metrics.get("move_success", False)),
                    "move_failed": bool(commit_metrics.get("move_failed", False)),
                    "route_progress": int(commit_metrics.get("route_progress", getattr(context, "patrol_index", 0)) or 0),
                    "suspicion_added": int(commit_metrics.get("suspicion_added", 0) or 0),
                    "suspicion_targets_count": int(commit_metrics.get("suspicion_targets_count", 0) or 0),
                    "suspicion_events_processed": int(commit_metrics.get("suspicion_events_processed", 0) or 0),
                    "current_target_id": commit_metrics.get("current_target_id", getattr(context, "current_target_id", None)),
                    "pursuit_events_processed": int(commit_metrics.get("pursuit_events_processed", 0) or 0),
                    "pursuit_started": int(commit_metrics.get("pursuit_started", 0) or 0),
                    "pursuit_refreshed": int(commit_metrics.get("pursuit_refreshed", 0) or 0),
                    "pursuit_cleared": int(commit_metrics.get("pursuit_cleared", 0) or 0),
                    "pursuit_move_attempted": bool(commit_metrics.get("pursuit_move_attempted", False)),
                    "pursuit_move_success": bool(commit_metrics.get("pursuit_move_success", False)),
                    "pursuit_move_failed": bool(commit_metrics.get("pursuit_move_failed", False)),
                    "pursuit_target_cleared": bool(commit_metrics.get("pursuit_target_cleared", False)),
                    "pursuit_destination_id": commit_metrics.get("pursuit_destination_id", None),
                    "warn_emitted": bool(commit_metrics.get("warn_emitted", False)),
                    "arrest_emitted": bool(commit_metrics.get("arrest_emitted", False)),
                    "warning_stage": int(commit_metrics.get("warning_stage", getattr(context, "warning_stage", 0)) or 0),
                    "arrests_successful": int(commit_metrics.get("arrests_successful", 0) or 0),
                    "escorts_started": int(commit_metrics.get("escorts_started", 0) or 0),
                    "escorts_completed": int(commit_metrics.get("escorts_completed", 0) or 0),
                    "jail_entries": int(commit_metrics.get("jail_entries", 0) or 0),
                }
                ring_metrics[f"processed_{normalized_tier}"] += 1
                self.awareness_due_guard_ids.discard(int(getattr(guard, "id", 0) or 0))
                budget.increment()

        self.last_ring_metrics[ring] = ring_metrics

    def process_pending_events(self):
        if not self.event_queue:
            return

        pending_events = list(self.event_queue)
        self.event_queue = []
        self.event_debug_metrics = {"processed": 0, "woken": 0}
        self.suspicion_metrics = {
            "suspicion_added": 0,
            "suspicion_targets_count": 0,
            "suspicion_events_processed": 0,
        }
        self.pursuit_metrics = {
            "pursuit_events_processed": 0,
            "pursuit_started": 0,
            "pursuit_refreshed": 0,
            "pursuit_cleared": 0,
        }
        for event in pending_events:
            if not isinstance(event, SimEvent):
                continue
            self.event_debug_metrics["processed"] += 1
            impacted_guard_ids = self._wake_guards_for_event(event)
            self._emit_guard_message_for_event(event, impacted_guard_ids)
            self._apply_suspicion_from_event(event, impacted_guard_ids)
            self._apply_pursuit_from_event(event, impacted_guard_ids)
            self._apply_confrontation_from_event(event, impacted_guard_ids)

    def _emit_guard_message_for_event(self, event, impacted_guard_ids):
        event_type = str(getattr(event, "type", "") or "").strip().upper()
        if event_type not in {"PLAYER_ENTER", "PLAYER_LEAVE"}:
            return False

        event_room_id = int(getattr(event, "room_id", 0) or 0)
        if event_room_id <= 0:
            return False

        current_time = time.time()
        selected_guard = None
        for guard_id in list(impacted_guard_ids or []):
            guard = self.get_guard(guard_id)
            guard_room_id = int(getattr(getattr(guard, "location", None), "id", 0) or 0)
            if guard is None or guard_room_id != event_room_id:
                continue
            selected_guard = guard
            break

        if selected_guard is None:
            return False

        sim_state = getattr(selected_guard, "sim_state", None)
        if sim_state is None:
            return False

        if event_type == "PLAYER_ENTER":
            if not sim_state.can_emit_enter(current_time):
                return False
            emitted = self.emit_event(
                "GUARD_MESSAGE",
                {
                    "room_id": event_room_id,
                    "text": get_enter_message(),
                },
            )
            if emitted:
                sim_state.set_enter_cooldown(current_time)
                sim_state.save_if_needed()
                return True
            return False

        if not sim_state.can_emit_exit(current_time):
            return False
        emitted = self.emit_event(
            "GUARD_MESSAGE",
            {
                "room_id": event_room_id,
                "text": get_exit_message(),
            },
        )
        if emitted:
            sim_state.set_exit_cooldown(current_time)
            sim_state.save_if_needed()
            return True
        return False

    def _wake_guards_for_event(self, event):
        event_room_id = int(getattr(event, "room_id", 0) or 0)
        if event_room_id <= 0:
            return []

        zone_owner_guard_ids = []
        same_room_guard_ids = []
        adjacent_guard_ids = []
        adjacent_room_ids = self.get_adjacent_room_ids(self.get_guard_destination(event_room_id))
        max_event_wake_npcs = self._get_max_event_wake_npcs()
        patrol_zone = get_patrol_zone_for_room(event_room_id)
        patrol_zone_owner_guard_id = int((patrol_zone or {}).get("guard_id", 0) or 0) or None
        if patrol_zone_owner_guard_id is not None:
            owner_guard = self.get_guard(patrol_zone_owner_guard_id)
            owner_state = getattr(owner_guard, "sim_state", None)
            if owner_guard is not None and owner_state is not None and bool(getattr(owner_state, "patrol_enabled", False)) and owner_state.is_room_in_patrol_zone(event_room_id):
                zone_owner_guard_ids.append(patrol_zone_owner_guard_id)
        for guard_id in sorted(self.npc_ids):
            guard = self.get_guard(guard_id)
            if not guard:
                continue
            room = getattr(guard, "location", None)
            guard_room_id = int(getattr(room, "id", 0) or 0)
            if int(guard_id or 0) == int(patrol_zone_owner_guard_id or 0):
                continue
            if guard_room_id == event_room_id:
                same_room_guard_ids.append(int(getattr(guard, "id", 0) or 0))
                if len(same_room_guard_ids) >= max_event_wake_npcs:
                    break
                continue
            if guard_room_id in adjacent_room_ids:
                adjacent_guard_ids.append(int(getattr(guard, "id", 0) or 0))

        remaining_capacity = max(0, max_event_wake_npcs - len(same_room_guard_ids))
        adjacent_guard_ids = adjacent_guard_ids[:remaining_capacity]
        woken_guard_ids = list(zone_owner_guard_ids)
        for guard_id in list(same_room_guard_ids) + list(adjacent_guard_ids):
            if guard_id not in woken_guard_ids:
                woken_guard_ids.append(guard_id)
        woken_guard_ids = woken_guard_ids[:max_event_wake_npcs]

        if not woken_guard_ids:
            self._append_runtime_trace(
                "wake",
                source_event_type=str(getattr(event, "type", "") or ""),
                room_id=event_room_id,
                woken_guard_ids=[],
                zone_owner_guard_ids=[],
                same_room_guard_ids=[],
                adjacent_guard_ids=[],
            )
            return []

        now = time.time()
        self.awareness_due_guard_ids.update(woken_guard_ids)
        for guard_id in zone_owner_guard_ids:
            self.recent_wake_timestamps[guard_id] = now
            self.wake_sources[guard_id] = "zone_owned_event"
            self.update_guard_significance(self.get_guard(guard_id), WARM)
        for guard_id in same_room_guard_ids:
            self.recent_wake_timestamps[guard_id] = now
            self.wake_sources[guard_id] = "same_room_event"
            self.update_guard_significance(self.get_guard(guard_id), HOT)
        for guard_id in adjacent_guard_ids:
            self.recent_wake_timestamps[guard_id] = now
            self.wake_sources[guard_id] = "adjacent_room_event"
            self.update_guard_significance(self.get_guard(guard_id), WARM)
        self.event_debug_metrics["woken"] += len(woken_guard_ids)
        self._append_runtime_trace(
            "wake",
            source_event_type=str(getattr(event, "type", "") or ""),
            room_id=event_room_id,
            woken_guard_ids=list(woken_guard_ids),
            zone_owner_guard_ids=list(zone_owner_guard_ids),
            same_room_guard_ids=list(same_room_guard_ids),
            adjacent_guard_ids=list(adjacent_guard_ids),
        )
        return woken_guard_ids

    def _get_suspicion_gain_for_event(self, event_type):
        normalized_type = str(event_type or "").strip().upper()
        suspicion_map = {
            "PLAYER_ENTER": PLAYER_ENTER_SUSPICION_GAIN,
            "PLAYER_LEAVE": PLAYER_LEAVE_SUSPICION_GAIN,
            "PLAYER_FLED": PLAYER_FLED_SUSPICION_GAIN,
            "PLAYER_COMPLIED": PLAYER_COMPLIED_SUSPICION_GAIN,
            "GUARD_WARNED": GUARD_WARNED_SUSPICION_GAIN,
            "CRIME_COMMITTED": CRIME_COMMITTED_SUSPICION_GAIN,
        }
        return int(suspicion_map.get(normalized_type, 0) or 0)

    def _apply_suspicion_from_event(self, event, impacted_guard_ids):
        event_type = str(getattr(event, "type", "") or "").strip().upper()
        target_id = int((getattr(event, "payload", {}) or {}).get("target_id", 0) or 0)
        if target_id <= 0:
            return
        target_obj = self.get_guard_destination(target_id)
        if target_obj is not None and (is_in_custody(target_obj) or is_jailed(target_obj)):
            return
        base_amount = self._get_suspicion_gain_for_event(event_type)
        if base_amount == 0:
            return

        event_room_id = int(getattr(event, "room_id", 0) or 0)
        now = time.time()
        processed_guard_count = 0
        for guard_id in list(impacted_guard_ids or []):
            guard = self.get_guard(guard_id)
            sim_state = getattr(guard, "sim_state", None)
            if guard is None or sim_state is None:
                continue
            guard_room_id = int(getattr(getattr(guard, "location", None), "id", 0) or 0)
            if base_amount >= 0:
                amount = base_amount if guard_room_id == event_room_id else max(1, int(base_amount / ADJACENT_SUSPICION_DIVISOR))
            else:
                amount = base_amount if guard_room_id == event_room_id else min(-1, int(base_amount / ADJACENT_SUSPICION_DIVISOR))
            pending_for_guard = self.pending_suspicion_updates.setdefault(int(guard_id or 0), {})
            target_key = str(int(target_id or 0) or 0)
            pending_entry = dict(pending_for_guard.get(target_key) or {})
            pending_entry["amount"] = int(pending_entry.get("amount", 0) or 0) + amount
            pending_entry["last_seen_at"] = float(now or 0.0)
            pending_entry["event_count"] = int(pending_entry.get("event_count", 0) or 0) + 1
            pending_for_guard[target_key] = pending_entry
            processed_guard_count += 1
            self.suspicion_metrics["suspicion_added"] += amount
            self.suspicion_metrics["suspicion_targets_count"] += len(list((getattr(sim_state, "suspicion_targets", {}) or {}).keys())) + len(list(pending_for_guard.keys()))
        if processed_guard_count > 0:
            self.suspicion_metrics["suspicion_events_processed"] += 1

    def _get_pending_suspicion_for_guard(self, guard_id):
        return dict(self.pending_suspicion_updates.get(int(guard_id or 0), {}) or {})

    def _get_pending_pursuit_for_guard(self, guard_id):
        return dict(self.pending_pursuit_updates.get(int(guard_id or 0), {}) or {})

    def _get_pending_confrontation_for_guard(self, guard_id):
        return dict(self.pending_confrontation_updates.get(int(guard_id or 0), {}) or {})

    def _project_guard_target_state(self, sim_state, guard_id, now):
        current_target_id = getattr(sim_state, "current_target_id", None) if sim_state is not None else None
        current_target_level = 0
        if sim_state is None:
            return current_target_id, current_target_level
        if bool(self._get_pending_confrontation_for_guard(guard_id).get("clear", False)):
            return None, 0
        if current_target_id is not None:
            target_obj = self.get_guard_destination(current_target_id)
            if target_obj is not None and is_in_custody(target_obj) and not is_jailed(target_obj):
                return int(current_target_id or 0) or None, max(0, int(getattr(sim_state, "get_suspicion", lambda target_id: 0)(current_target_id) or 0))

        pending_updates = self._get_pending_suspicion_for_guard(guard_id)
        candidate_target_ids = set(int(target_key or 0) for target_key in list((getattr(sim_state, "suspicion_targets", {}) or {}).keys()))
        candidate_target_ids.update(int(target_key or 0) for target_key in list(pending_updates.keys()))
        best_target_id = None
        best_target_level = 0
        for candidate_target_id in candidate_target_ids:
            if candidate_target_id <= 0:
                continue
            effective_value = int(getattr(sim_state, "get_effective_suspicion", lambda target_id, current_now: 0)(candidate_target_id, now) or 0)
            pending_entry = pending_updates.get(str(int(candidate_target_id or 0) or 0), {})
            effective_value += int(pending_entry.get("amount", 0) or 0)
            if effective_value < 10:
                continue
            if effective_value > best_target_level:
                best_target_id = candidate_target_id
                best_target_level = effective_value
        return best_target_id, best_target_level

    def _stage_pursuit_update(self, guard_id, update):
        if int(guard_id or 0) <= 0:
            return {}
        pending = dict(self.pending_pursuit_updates.get(int(guard_id or 0), {}) or {})
        for key, value in dict(update or {}).items():
            if key == "clear":
                pending["clear"] = bool(value)
                continue
            if value is not None:
                pending[key] = value
        self.pending_pursuit_updates[int(guard_id or 0)] = pending
        return pending

    def _stage_confrontation_update(self, guard_id, update):
        if int(guard_id or 0) <= 0:
            return {}
        pending = dict(self.pending_confrontation_updates.get(int(guard_id or 0), {}) or {})
        for key, value in dict(update or {}).items():
            if key == "clear":
                pending["clear"] = bool(value)
                continue
            if value is not None:
                pending[key] = value
        self.pending_confrontation_updates[int(guard_id or 0)] = pending
        return pending

    def _project_guard_pursuit_state(self, sim_state, guard_id, current_room_id, projected_target_id, projected_target_level, now):
        pending = self._get_pending_pursuit_for_guard(guard_id)
        if bool(pending.get("clear", False)):
            return None, None, "none", None

        pursuit_target_id = int(pending.get("pursuit_target_id", getattr(sim_state, "pursuit_target_id", None)) or 0) or None
        if pursuit_target_id is None and projected_target_id is not None and projected_target_level >= MIN_PURSUIT_THRESHOLD:
            pursuit_target_id = projected_target_id
        pursuit_last_known_room_id = int(pending.get("pursuit_last_known_room_id", getattr(sim_state, "pursuit_last_known_room_id", None)) or 0) or None
        pursuit_state = str(pending.get("pursuit_state", getattr(sim_state, "pursuit_state", "none")) or "none")
        if pursuit_state not in {"none", "tracking", "intercepting"}:
            pursuit_state = "none"
        intercept_room_id = int(pending.get("intercept_room_id", getattr(sim_state, "intercept_room_id", None)) or 0) or None
        if pursuit_last_known_room_id is not None:
            adjacent_room_ids = self.get_adjacent_room_ids(self.get_guard_destination(current_room_id)) if current_room_id is not None else set()
            intercept_room_id = pursuit_last_known_room_id if pursuit_last_known_room_id in adjacent_room_ids else pursuit_last_known_room_id
            if pursuit_state == "none":
                pursuit_state = "intercepting" if intercept_room_id == pursuit_last_known_room_id and current_room_id is not None and pursuit_last_known_room_id in adjacent_room_ids else "tracking"
        return pursuit_target_id, pursuit_last_known_room_id, pursuit_state, intercept_room_id

    def _project_guard_confrontation_state(self, sim_state, guard_id, projected_target_id):
        pending = self._get_pending_confrontation_for_guard(guard_id)
        if bool(pending.get("clear", False)):
            return None, "none", 0
        confrontation_target_id = int(pending.get("confrontation_target_id", getattr(sim_state, "confrontation_target_id", None) or projected_target_id or 0) or 0) or None
        confrontation_state = str(pending.get("confrontation_state", getattr(sim_state, "confrontation_state", "none")) or "none")
        warning_stage = int(pending.get("warning_stage", getattr(sim_state, "warning_stage", 0) or 0) or 0)
        if confrontation_state not in {"none", "warning", "arresting", "cooldown"}:
            confrontation_state = "none"
        warning_stage = max(0, min(2, warning_stage))
        return confrontation_target_id, confrontation_state, warning_stage

    def _apply_confrontation_from_event(self, event, impacted_guard_ids):
        event_type = str(getattr(event, "type", "") or "").strip().upper()
        if event_type != "PLAYER_COMPLIED":
            return
        payload = dict(getattr(event, "payload", {}) or {})
        target_id = int(payload.get("target_id", 0) or 0)
        if target_id <= 0:
            return
        for guard_id in list(impacted_guard_ids or []):
            guard = self.get_guard(guard_id)
            sim_state = getattr(guard, "sim_state", None)
            if guard is None or sim_state is None:
                continue
            tracked_target_ids = {
                int(getattr(sim_state, "current_target_id", 0) or 0),
                int(getattr(sim_state, "pursuit_target_id", 0) or 0),
                int(getattr(sim_state, "confrontation_target_id", 0) or 0),
            }
            if target_id not in tracked_target_ids:
                continue
            self._stage_confrontation_update(guard_id, {"clear": True, "confrontation_target_id": target_id})
            self._stage_pursuit_update(guard_id, {"clear": True})

    def _apply_pursuit_from_event(self, event, impacted_guard_ids):
        event_type = str(getattr(event, "type", "") or "").strip().upper()
        payload = dict(getattr(event, "payload", {}) or {})
        target_id = int(payload.get("target_id", 0) or 0)
        event_room_id = int(getattr(event, "room_id", 0) or 0)
        if target_id <= 0 or event_room_id <= 0:
            return
        target_obj = self.get_guard_destination(target_id)
        if target_obj is not None and (is_in_custody(target_obj) or is_jailed(target_obj)):
            return

        now = time.time()
        processed = False
        for guard_id in list(impacted_guard_ids or []):
            guard = self.get_guard(guard_id)
            sim_state = getattr(guard, "sim_state", None)
            if guard is None or sim_state is None:
                continue
            guard_room_id = int(getattr(getattr(guard, "location", None), "id", 0) or 0)
            same_room_guard = guard_room_id == event_room_id
            pending_suspicion = self._get_pending_suspicion_for_guard(guard_id).get(str(target_id), {})
            projected_suspicion = int(getattr(sim_state, "get_effective_suspicion", lambda current_target_id, current_now: 0)(target_id, now) or 0)
            projected_suspicion += int(pending_suspicion.get("amount", 0) or 0)
            existing_target_id = int(getattr(sim_state, "current_target_id", 0) or 0) or None
            existing_pursuit_target_id = int(getattr(sim_state, "pursuit_target_id", 0) or 0) or None
            threshold = MIN_PURSUIT_THRESHOLD if same_room_guard else ADJACENT_PURSUIT_THRESHOLD
            should_refresh_known_room = existing_target_id == target_id or existing_pursuit_target_id == target_id
            should_start_pursuit = projected_suspicion >= threshold and same_room_guard
            should_allow_adjacent_start = projected_suspicion >= threshold and not same_room_guard and event_type in {"PLAYER_FLED", "CRIME_COMMITTED"}

            if event_type == "PLAYER_ENTER" and should_refresh_known_room:
                self._stage_pursuit_update(
                    guard_id,
                    {
                        "pursuit_target_id": target_id,
                        "pursuit_last_known_room_id": event_room_id,
                        "pursuit_state": "tracking",
                        "pursuit_started_at": float(getattr(sim_state, "pursuit_started_at", 0.0) or now),
                    },
                )
                self.pursuit_metrics["pursuit_refreshed"] += 1
                processed = True
                continue

            if event_type == "PLAYER_LEAVE" and (
                (same_room_guard and projected_suspicion >= MIN_TARGET_THRESHOLD)
                or should_refresh_known_room
            ):
                self._stage_pursuit_update(
                    guard_id,
                    {
                        "pursuit_target_id": target_id,
                        "pursuit_last_known_room_id": event_room_id,
                        "pursuit_state": "tracking",
                        "pursuit_started_at": float(getattr(sim_state, "pursuit_started_at", 0.0) or now),
                    },
                )
                self.pursuit_metrics["pursuit_refreshed"] += 1
                processed = True
                continue

            if event_type in {"PLAYER_FLED", "CRIME_COMMITTED"} and (should_start_pursuit or should_allow_adjacent_start):
                self._stage_pursuit_update(
                    guard_id,
                    {
                        "pursuit_target_id": target_id,
                        "pursuit_last_known_room_id": event_room_id,
                        "pursuit_state": "tracking",
                        "pursuit_started_at": now,
                    },
                )
                self.pursuit_metrics["pursuit_started"] += 1
                processed = True
                continue

            if event_type == "GUARD_WARNED" and should_refresh_known_room:
                self._stage_pursuit_update(
                    guard_id,
                    {
                        "pursuit_target_id": target_id,
                        "pursuit_last_known_room_id": event_room_id,
                        "pursuit_state": "tracking",
                    },
                )
                self.pursuit_metrics["pursuit_refreshed"] += 1
                processed = True

        if processed:
            self.pursuit_metrics["pursuit_events_processed"] += 1

    def _commit_pending_confrontation_for_guard(self, sim_state, guard_id, current_target_id=None):
        pending = self.pending_confrontation_updates.pop(int(guard_id or 0), {})
        metrics = {
            "confrontation_target_id": getattr(sim_state, "confrontation_target_id", None) if sim_state is not None else None,
            "warning_stage": int(getattr(sim_state, "warning_stage", 0) or 0) if sim_state is not None else 0,
            "confrontation_cleared": False,
        }
        if sim_state is None:
            return metrics
        if bool(pending.get("clear", False)) or current_target_id is None:
            had_confrontation = bool(getattr(sim_state, "confrontation_target_id", None) or getattr(sim_state, "confrontation_state", "none") != "none")
            cleared_target_id = int(pending.get("confrontation_target_id", getattr(sim_state, "confrontation_target_id", None) or 0) or 0) or None
            sim_state.clear_confrontation()
            if cleared_target_id is not None:
                sim_state.clear_suspicion(cleared_target_id)
                if getattr(sim_state, "current_target_id", None) == cleared_target_id:
                    sim_state.set_current_target_id(None)
            if had_confrontation:
                metrics["confrontation_cleared"] = True
            metrics["confrontation_target_id"] = None
            metrics["warning_stage"] = 0
            return metrics

        confrontation_target_id = int(pending.get("confrontation_target_id", getattr(sim_state, "confrontation_target_id", None) or current_target_id or 0) or 0) or None
        confrontation_state = str(pending.get("confrontation_state", getattr(sim_state, "confrontation_state", "none")) or "none")
        warning_stage = max(0, min(2, int(pending.get("warning_stage", getattr(sim_state, "warning_stage", 0) or 0) or 0)))
        if confrontation_target_id != getattr(sim_state, "confrontation_target_id", None):
            sim_state.confrontation_target_id = confrontation_target_id
            sim_state.mark_dirty()
        sim_state.set_confrontation_state(confrontation_state)
        if int(getattr(sim_state, "warning_stage", 0) or 0) != warning_stage:
            sim_state.warning_stage = warning_stage
            sim_state.mark_dirty()
        metrics["confrontation_target_id"] = confrontation_target_id
        metrics["warning_stage"] = warning_stage
        return metrics

    def is_target_present_in_room(self, target_id, room_id):
        normalized_target_id = int(target_id or 0) or 0
        normalized_room_id = int(room_id or 0) or 0
        if normalized_target_id <= 0 or normalized_room_id <= 0:
            return False
        try:
            target_obj = ObjectDB.objects.get(id=normalized_target_id)
        except Exception:
            return False
        return int(getattr(getattr(target_obj, "location", None), "id", 0) or 0) == normalized_room_id

    def get_target_custody_state(self, target_id):
        normalized_target_id = int(target_id or 0) or 0
        if normalized_target_id <= 0:
            return None, False, None, False
        target_obj = self.get_guard_destination(normalized_target_id)
        if target_obj is None:
            return None, False, None, False
        return (
            target_obj,
            bool(is_in_custody(target_obj)),
            int(getattr(getattr(target_obj, "db", None), "custody_guard_id", 0) or 0) or None,
            bool(is_jailed(target_obj)),
        )

    def _commit_pending_pursuit_for_guard(self, sim_state, guard_id, now, current_target_id=None):
        pending = self.pending_pursuit_updates.pop(int(guard_id or 0), {})
        metrics = {
            "pursuit_events_processed": 0,
            "pursuit_started": 0,
            "pursuit_refreshed": 0,
            "pursuit_cleared": 0,
            "pursuit_target_id": getattr(sim_state, "pursuit_target_id", None) if sim_state is not None else None,
        }
        if sim_state is None:
            return metrics
        if not pending and current_target_id is not None:
            return metrics

        if bool(pending.get("clear", False)) or (current_target_id is None and getattr(sim_state, "current_target_id", None) is None):
            had_pursuit = bool(getattr(sim_state, "pursuit_target_id", None) or getattr(sim_state, "pursuit_last_known_room_id", None))
            sim_state.clear_pursuit()
            if had_pursuit:
                metrics["pursuit_cleared"] = 1
            return metrics

        pursuit_target_id = int(pending.get("pursuit_target_id", getattr(sim_state, "pursuit_target_id", None) or current_target_id or 0) or 0) or None
        pursuit_last_known_room_id = int(pending.get("pursuit_last_known_room_id", getattr(sim_state, "pursuit_last_known_room_id", None) or 0) or 0) or None
        pursuit_state = str(pending.get("pursuit_state", getattr(sim_state, "pursuit_state", "none")) or "none")
        pursuit_started_at = float(pending.get("pursuit_started_at", getattr(sim_state, "pursuit_started_at", 0.0) or 0.0) or 0.0)
        intercept_room_id = int(pending.get("intercept_room_id", getattr(sim_state, "intercept_room_id", None) or pursuit_last_known_room_id or 0) or 0) or None

        if pursuit_target_id is not None and pursuit_last_known_room_id is not None:
            if getattr(sim_state, "pursuit_target_id", None) != pursuit_target_id or getattr(sim_state, "pursuit_started_at", 0.0) == 0.0:
                metrics["pursuit_started"] = 1
            else:
                metrics["pursuit_refreshed"] = 1
            sim_state.begin_pursuit(pursuit_target_id, pursuit_last_known_room_id, pursuit_started_at or now)
            sim_state.set_pursuit_state(pursuit_state)
            sim_state.set_intercept_room(intercept_room_id)
            metrics["pursuit_target_id"] = pursuit_target_id
        elif getattr(sim_state, "current_target_id", None) is None:
            had_pursuit = bool(getattr(sim_state, "pursuit_target_id", None) or getattr(sim_state, "pursuit_last_known_room_id", None))
            sim_state.clear_pursuit()
            if had_pursuit:
                metrics["pursuit_cleared"] = 1

        metrics["pursuit_events_processed"] = int(self.pursuit_metrics.get("pursuit_events_processed", 0) or 0)
        return metrics

    def _commit_pending_suspicion_for_guard(self, sim_state, guard_id, now):
        applied_amount = 0
        applied_event_count = 0
        pending_updates = self.pending_suspicion_updates.pop(int(guard_id or 0), {})
        if sim_state is None:
            return {
                "suspicion_added": 0,
                "suspicion_targets_count": 0,
                "suspicion_events_processed": 0,
                "current_target_id": None,
            }

        for target_key, pending_entry in list(pending_updates.items()):
            target_id = int(target_key or 0)
            if target_id <= 0:
                continue
            amount = int((pending_entry or {}).get("amount", 0) or 0)
            last_seen_at = float((pending_entry or {}).get("last_seen_at", now) or now)
            if amount != 0:
                sim_state.add_suspicion_from_event(target_id, amount, last_seen_at)
                applied_amount += amount
            else:
                sim_state.touch_target(target_id, last_seen_at)
            applied_event_count += int((pending_entry or {}).get("event_count", 0) or 0)

        primary_target_id = sim_state.update_primary_target(now)
        if applied_amount > 0:
            sim_state.set_last_significant_event_at(now)
        return {
            "suspicion_added": applied_amount,
            "suspicion_targets_count": len(list((getattr(sim_state, "suspicion_targets", {}) or {}).keys())),
            "suspicion_events_processed": applied_event_count,
            "current_target_id": primary_target_id,
        }

    def get_adjacent_room_ids(self, room):
        adjacent_room_ids = set()
        if room is None:
            return adjacent_room_ids
        for obj in list(getattr(room, "contents", None) or []):
            destination = getattr(obj, "destination", None)
            destination_id = int(getattr(destination, "id", 0) or 0)
            if destination_id > 0:
                adjacent_room_ids.add(destination_id)
        return adjacent_room_ids

    def evaluate_guard_significance(self, guard, context):
        guard_id = int(getattr(guard, "id", 0) or 0)
        now = time.time()
        room_id = int(getattr(context, "room_id", 0) or 0)
        room = self.get_guard_destination(room_id) if room_id > 0 else None
        zone_facts = get_zone_facts(self.zone_id)
        recent_wake_at = float(self.recent_wake_timestamps.get(guard_id, 0.0) or 0.0)
        recent_wake_active = recent_wake_at > 0.0 and (now - recent_wake_at) <= RECENT_WAKE_WINDOW_SECONDS
        if not recent_wake_active and recent_wake_at > 0.0:
            self.recent_wake_timestamps.pop(guard_id, None)
            self.wake_sources.pop(guard_id, None)

        if bool(getattr(context, "has_players", False)) or bool(getattr(context, "has_active_incident", False)) or guard_id in self.awareness_due_guard_ids:
            self.recent_relevance_timestamps[guard_id] = now
            return HOT

        hot_room_ids = set(getattr(zone_facts, "hot_room_ids", set()) or set()) if zone_facts is not None else set()
        incident_room_ids = set(getattr(zone_facts, "active_incident_room_ids", set()) or set()) if zone_facts is not None else set()
        active_player_room_ids = set(getattr(zone_facts, "active_player_room_ids", set()) or set()) if zone_facts is not None else set()
        adjacent_room_ids = self.get_adjacent_room_ids(room)
        if room_id in hot_room_ids or room_id in incident_room_ids or bool(adjacent_room_ids & (hot_room_ids | active_player_room_ids)):
            self.recent_relevance_timestamps[guard_id] = now
            return WARM

        if recent_wake_active:
            self.recent_relevance_timestamps[guard_id] = now
            return WARM

        last_relevant_at = float(self.recent_relevance_timestamps.get(guard_id, now) or now)
        if (
            guard_id not in self.awareness_due_guard_ids
            and guard_id not in self.movement_due_guard_ids
            and not bool(getattr(context, "has_players", False))
            and not bool(getattr(context, "has_active_incident", False))
            and (now - last_relevant_at) >= DORMANT_WINDOW_SECONDS
        ):
            return DORMANT

        return COLD

    def update_guard_significance(self, guard, new_tier):
        guard_id = int(getattr(guard, "id", 0) or 0) if guard else 0
        old_tier = normalize_tier(self.guard_significance.get(guard_id, COLD))
        normalized_tier = normalize_tier(new_tier)
        self.guard_significance[guard_id] = normalized_tier
        return old_tier, normalized_tier

    def _shape_context_for_ring(self, guard, context, ring, significance_tier):
        guard_id = int(getattr(guard, "id", 0) or 0)
        movement_due = bool(getattr(context, "movement_due", False) and ring in {"normal", "slow"})
        pursuit_due = bool(getattr(context, "pursuit_due", False) and ring in {"normal", "slow"})
        escort_due = bool(getattr(context, "escort_due", False) and ring in {"normal", "slow"})
        awareness_due = bool(getattr(context, "awareness_due", False))
        if significance_tier == DORMANT:
            movement_due = False
            pursuit_due = False
            escort_due = False
        return replace(context, awareness_due=awareness_due, movement_due=movement_due, pursuit_due=pursuit_due, escort_due=escort_due, significance_tier=normalize_tier(significance_tier))

    def read_guard_context(self, guard):
        """READ PHASE ONLY: no messaging, movement, .db writes, handler writes, or event emission."""
        guard_id = int(getattr(guard, "id", 0) or 0)
        if not guard or not getattr(guard, "pk", None):
            return GuardContext(
                guard_id=guard_id,
                room_id=None,
                zone_id=self.zone_id,
                room_player_count=0,
                room_guard_count=0,
                room_npc_count=0,
                has_players=False,
                has_active_incident=False,
                is_valid_guard=False,
                unsupported_reason="missing_guard",
            )

        if not bool(getattr(getattr(guard, "db", None), "is_guard", False)):
            return GuardContext(
                guard_id=guard_id,
                room_id=None,
                zone_id=self.zone_id,
                room_player_count=0,
                room_guard_count=0,
                room_npc_count=0,
                has_players=False,
                has_active_incident=False,
                is_valid_guard=False,
                unsupported_reason="not_guard",
            )

        guard_zone_id = str(getattr(getattr(guard, "db", None), "zone_id", None) or getattr(getattr(guard, "db", None), "zone", None) or self.zone_id).strip().lower()
        if guard_zone_id != str(self.zone_id or "").strip().lower():
            return GuardContext(
                guard_id=guard_id,
                room_id=None,
                zone_id=guard_zone_id,
                room_player_count=0,
                room_guard_count=0,
                room_npc_count=0,
                has_players=False,
                has_active_incident=False,
                is_valid_guard=False,
                unsupported_reason="wrong_zone",
            )

        room = getattr(guard, "location", None)
        sim_state = getattr(guard, "sim_state", None)
        now = time.time()
        if room is None:
            projected_target_id, projected_target_level = self._project_guard_target_state(sim_state, guard_id, now)
            _, target_in_custody, custody_guard_id, target_is_jailed = self.get_target_custody_state(projected_target_id)
            confrontation_target_id, confrontation_state, warning_stage = self._project_guard_confrontation_state(sim_state, guard_id, projected_target_id)
            pursuit_target_id, pursuit_last_known_room_id, pursuit_state, intercept_room_id = self._project_guard_pursuit_state(
                sim_state,
                guard_id,
                None,
                projected_target_id,
                projected_target_level,
                now,
            )
            return GuardContext(
                guard_id=guard_id,
                room_id=None,
                zone_id=guard_zone_id,
                room_player_count=0,
                room_guard_count=0,
                room_npc_count=0,
                has_players=False,
                has_active_incident=False,
                warning_count=int(getattr(sim_state, "warning_count", 0) or 0),
                current_target_id=projected_target_id,
                target_in_custody=target_in_custody,
                custody_guard_id=custody_guard_id,
                target_is_jailed=target_is_jailed,
                confrontation_target_id=confrontation_target_id,
                confrontation_state=confrontation_state,
                warning_stage=warning_stage,
                target_suspicion_level=projected_target_level,
                pursuit_target_id=pursuit_target_id,
                pursuit_last_known_room_id=pursuit_last_known_room_id,
                pursuit_state=pursuit_state,
                intercept_room_id=intercept_room_id,
                patrol_index=int(getattr(sim_state, "patrol_index", 0) or 0),
                home_room_id=getattr(sim_state, "home_room_id", None),
                behavior_state=str(getattr(sim_state, "behavior_state", "idle") or "idle"),
                movement_due=bool(getattr(sim_state, "is_movement_due", lambda current_now: False)(now)),
                pursuit_due=bool(getattr(sim_state, "is_pursuit_due", lambda current_now: False)(now)),
                warning_due=bool(getattr(sim_state, "is_warning_due", lambda current_now: False)(now)),
                arrest_due=bool(getattr(sim_state, "is_arrest_due", lambda current_now: False)(now)),
                escort_due=bool(getattr(sim_state, "is_movement_due", lambda current_now: False)(now)),
                target_present_in_room=False,
                unsupported_reason="no_location",
            )

        room_id = int(getattr(room, "id", 0) or 0) or None
        facts = get_or_create_room_facts(room_id)
        used_cache = bool(getattr(facts, "last_updated", 0) or 0)
        used_direct_room_scan = False
        room_player_count = int(getattr(facts, "player_count", 0) or 0)
        room_guard_count = int(getattr(facts, "guard_count", 0) or 0)
        room_npc_count = int(getattr(facts, "npc_count", 0) or 0)
        has_active_incident = bool(getattr(facts, "crime_flag", False))

        if not used_cache:
            used_direct_room_scan = True
            room_player_count, room_guard_count, room_npc_count, has_active_incident = self._scan_room_for_facts(room)
            facts.update_from_scan(
                player_count=room_player_count,
                guard_count=room_guard_count,
                npc_count=room_npc_count,
                crime_flag=has_active_incident,
            )

        if self.debug_enabled and used_cache and (time.time() % 20) < 0.1:
            actual_players, actual_guards, actual_npcs, _ = self._scan_room_for_facts(room)
            if actual_players != room_player_count or actual_guards != room_guard_count or actual_npcs != room_npc_count:
                logger.log_trace(
                    f"[DireSim] RoomFacts mismatch room={room_id} cached=({room_player_count},{room_guard_count},{room_npc_count}) actual=({actual_players},{actual_guards},{actual_npcs})"
                )

        projected_target_id, projected_target_level = self._project_guard_target_state(sim_state, guard_id, now)
        _, target_in_custody, custody_guard_id, target_is_jailed = self.get_target_custody_state(projected_target_id)
        confrontation_target_id, confrontation_state, warning_stage = self._project_guard_confrontation_state(sim_state, guard_id, projected_target_id)
        pursuit_target_id, pursuit_last_known_room_id, pursuit_state, intercept_room_id = self._project_guard_pursuit_state(
            sim_state,
            guard_id,
            room_id,
            projected_target_id,
            projected_target_level,
            now,
        )
        target_present_in_room = self.is_target_present_in_room(projected_target_id, room_id)

        return GuardContext(
            guard_id=guard_id,
            room_id=room_id,
            zone_id=guard_zone_id,
            room_player_count=room_player_count,
            room_guard_count=room_guard_count,
            warning_count=int(getattr(sim_state, "warning_count", 0) or 0),
            current_target_id=projected_target_id,
            target_in_custody=target_in_custody,
            custody_guard_id=custody_guard_id,
            target_is_jailed=target_is_jailed,
            confrontation_target_id=confrontation_target_id,
            confrontation_state=confrontation_state,
            warning_stage=warning_stage,
            target_suspicion_level=projected_target_level,
            pursuit_target_id=pursuit_target_id,
            pursuit_last_known_room_id=pursuit_last_known_room_id,
            pursuit_state=pursuit_state,
            intercept_room_id=intercept_room_id,
            patrol_index=int(getattr(sim_state, "patrol_index", 0) or 0),
            home_room_id=getattr(sim_state, "home_room_id", None),
            behavior_state=str(getattr(sim_state, "behavior_state", "idle") or "idle"),
            room_npc_count=room_npc_count,
            has_players=room_player_count > 0,
            has_active_incident=has_active_incident,
            used_cache=used_cache,
            used_direct_room_scan=used_direct_room_scan,
            awareness_due=guard_id in self.awareness_due_guard_ids,
            movement_due=bool(getattr(sim_state, "is_movement_due", lambda current_now: False)(now)),
            pursuit_due=bool(getattr(sim_state, "is_pursuit_due", lambda current_now: False)(now)),
            warning_due=bool(getattr(sim_state, "is_warning_due", lambda current_now: False)(now)),
            arrest_due=bool(getattr(sim_state, "is_arrest_due", lambda current_now: False)(now)),
            escort_due=bool(getattr(sim_state, "is_movement_due", lambda current_now: False)(now)),
            target_present_in_room=target_present_in_room,
        )

    def _scan_room_for_facts(self, room):
        room_player_count = 0
        room_guard_count = 0
        room_npc_count = 0
        for occupant in list(getattr(room, "contents", None) or []):
            if not getattr(occupant, "pk", None):
                continue
            if bool(getattr(getattr(occupant, "db", None), "is_guard", False)):
                room_guard_count += 1
                continue
            if bool(getattr(occupant, "has_account", False)):
                if bool(is_jailed(occupant)) or bool(is_in_custody(occupant)):
                    continue
                room_player_count += 1
                continue
            if bool(getattr(getattr(occupant, "db", None), "is_npc", False)):
                room_npc_count += 1

        has_active_incident = bool(
            getattr(getattr(room, "db", None), "crime_flag", False)
            or bool(getattr(getattr(room, "db", None), "active_incident", False))
            or float(getattr(getattr(room, "db", None), "disturbance_level", 0.0) or 0.0) > 0.0
        )
        return room_player_count, room_guard_count, room_npc_count, has_active_incident

    def decide_guard_action(self, guard, context, ring="normal", significance_tier=COLD):
        """DECIDE PHASE ONLY: pure decision formation, no world mutation or persistent state writes."""
        if not isinstance(context, GuardContext):
            self._log_unsupported_guard_branch(guard, "missing_context")
            return GuardDecision(action_type="NOOP", state_updates={"decision_reason": "missing_context"})

        if not context.is_valid_guard:
            reason = context.unsupported_reason or "invalid_guard"
            self._log_unsupported_guard_branch(guard, reason)
            return GuardDecision(action_type="NOOP", state_updates={"decision_reason": reason})

        if normalize_tier(significance_tier) == DORMANT:
            return GuardDecision(action_type="NOOP", state_updates={"decision_reason": "dormant_noop"})

        decision = resolve_guard_decision(guard, getattr(guard, "sim_state", None), context)
        if str(getattr(decision, "action_type", "NOOP") or "NOOP") not in {"NOOP", "OBSERVE", "WARN", "ARREST", "ESCORT", "MOVE", "PURSUE"}:
            self._log_unsupported_guard_branch(guard, f"unsupported_action:{getattr(decision, 'action_type', 'unknown')}")
            return GuardDecision(action_type="NOOP", state_updates={"decision_reason": "unsupported_action"})
        self._log_decision(guard, decision, context, ring, significance_tier)
        return decision

    def commit_guard_decision(self, guard, decision, context, ring="normal", significance_tier=COLD):
        if not isinstance(decision, GuardDecision):
            return

        action_type = str(getattr(decision, "action_type", "NOOP") or "NOOP")
        sim_state = getattr(guard, "sim_state", None)
        current_room_id = int(getattr(context, "room_id", 0) or 0) or None
        current_time = time.time()
        commit_mode = self._get_commit_mode()
        commit_metrics = {
            "move_attempted": False,
            "move_success": False,
            "move_failed": False,
            "route_progress": int(getattr(sim_state, "movement_progress_index", getattr(context, "patrol_index", 0)) or 0) if sim_state is not None else int(getattr(context, "patrol_index", 0) or 0),
            "suspicion_added": 0,
            "suspicion_targets_count": len(list(getattr(sim_state, "suspicion_targets", {}).keys())) if sim_state is not None else 0,
            "suspicion_events_processed": 0,
            "current_target_id": getattr(context, "current_target_id", None),
            "pursuit_events_processed": 0,
            "pursuit_started": 0,
            "pursuit_refreshed": 0,
            "pursuit_cleared": 0,
            "pursuit_move_attempted": False,
            "pursuit_move_success": False,
            "pursuit_move_failed": False,
            "pursuit_target_cleared": False,
            "pursuit_destination_id": None,
            "warn_emitted": False,
            "arrest_emitted": False,
            "warning_stage": int(getattr(context, "warning_stage", 0) or 0),
            "arrests_successful": 0,
            "escorts_started": 0,
            "escorts_completed": 0,
            "jail_entries": 0,
        }
        if commit_mode == "none":
            self.pending_suspicion_updates.pop(int(getattr(guard, "id", 0) or 0), None)
            self.pending_pursuit_updates.pop(int(getattr(guard, "id", 0) or 0), None)
            self.pending_confrontation_updates.pop(int(getattr(guard, "id", 0) or 0), None)
            return commit_metrics
        if sim_state is not None:
            sim_state.ensure_home_room_id(current_room_id)
            sim_state.last_decision_reason = str((getattr(decision, "state_updates", {}) or {}).get("decision_reason", "unknown"))
            suspicion_commit_metrics = self._commit_pending_suspicion_for_guard(sim_state, int(getattr(guard, "id", 0) or 0), current_time)
            commit_metrics.update(suspicion_commit_metrics)
            confrontation_commit_metrics = self._commit_pending_confrontation_for_guard(
                sim_state,
                int(getattr(guard, "id", 0) or 0),
                current_target_id=commit_metrics.get("current_target_id", getattr(context, "current_target_id", None)),
            )
            commit_metrics.update(confrontation_commit_metrics)
            pursuit_commit_metrics = self._commit_pending_pursuit_for_guard(
                sim_state,
                int(getattr(guard, "id", 0) or 0),
                current_time,
                current_target_id=commit_metrics.get("current_target_id", getattr(context, "current_target_id", None)),
            )
            commit_metrics.update(pursuit_commit_metrics)
            if commit_metrics.get("current_target_id", None) is None and not getattr(sim_state, "has_valid_pursuit", lambda: False)():
                commit_metrics["pursuit_target_cleared"] = True
            commit_metrics["current_target_id"] = getattr(sim_state, "current_target_id", commit_metrics.get("current_target_id", None))
        if action_type == "NOOP":
            if sim_state is not None:
                sim_state.set_behavior_state("idle")
                sim_state.save_if_needed()
                commit_metrics["current_target_id"] = getattr(sim_state, "current_target_id", commit_metrics.get("current_target_id", None))
            return commit_metrics

        guard_ndb = getattr(guard, "ndb", None)
        if action_type == "OBSERVE":
            if guard_ndb is not None:
                guard_ndb.diresim_last_observed_at = current_time
                guard_ndb.diresim_last_action = "OBSERVE"
            should_emit_observe = bool(ring in {"slow", "deep"})
            should_emit_observe = should_emit_observe and sim_state is not None and sim_state.can_emit_observe(current_time)
            should_emit_observe = should_emit_observe and sim_state is not None and not sim_state.is_cooldown_active("msg_enter_until", current_time)
            should_emit_observe = should_emit_observe and sim_state is not None and not sim_state.is_cooldown_active("msg_exit_until", current_time)
            should_emit_observe = should_emit_observe and sim_state is not None and str(getattr(sim_state, "confrontation_state", "none") or "none") == "none"
            should_emit_observe = should_emit_observe and sim_state is not None and not getattr(sim_state, "has_valid_pursuit", lambda: False)()
            if should_emit_observe and current_room_id is not None:
                emitted = self.emit_event(
                    "GUARD_MESSAGE",
                    {
                        "room_id": current_room_id,
                        "text": get_observe_message(),
                    },
                )
                if emitted:
                    sim_state.set_observe_cooldown(current_time)
            if sim_state is not None:
                sim_state.set_behavior_state("observe")
                sim_state.set_current_target_id(getattr(decision, "target_id", None) or getattr(context, "current_target_id", None))
                sim_state.set_last_significant_event_at(current_time)
                sim_state.save_if_needed()
                commit_metrics["current_target_id"] = getattr(sim_state, "current_target_id", commit_metrics.get("current_target_id", None))
            return commit_metrics

        if action_type == "WARN":
            if guard_ndb is not None:
                guard_ndb.diresim_warn_metric = int(getattr(guard_ndb, "diresim_warn_metric", 0) or 0) + 1
                guard_ndb.diresim_last_action = "WARN"
            warning_target_id = int(getattr(decision, "target_id", None) or getattr(context, "current_target_id", None) or 0) or None
            if sim_state is not None:
                sim_state.set_behavior_state("warn")
                sim_state.begin_warning(warning_target_id, current_time)
                sim_state.advance_warning_stage(current_time)
                sim_state.increment_warning_count()
                sim_state.set_current_target_id(warning_target_id)
                sim_state.set_cooldown("warn_until", current_time + 3.0)
                sim_state.set_last_significant_event_at(current_time)
                sim_state.save_if_needed()
                commit_metrics["warning_stage"] = int(getattr(sim_state, "warning_stage", 0) or 0)
                commit_metrics["warn_emitted"] = True
                commit_metrics["current_target_id"] = getattr(sim_state, "current_target_id", commit_metrics.get("current_target_id", None))
            if warning_target_id is not None and current_room_id is not None:
                self.enqueue_event(SimEvent("GUARD_WARNED", current_room_id, payload={"target_id": warning_target_id, "guard_id": int(getattr(guard, "id", 0) or 0)}))
            if self.debug_enabled:
                logger.log_trace(
                    f"[DireSim] WARN placeholder guard={int(getattr(guard, 'id', 0) or 0)} room={getattr(context, 'room_id', None)}"
                )
            return commit_metrics

        if action_type == "ARREST":
            arrest_target_id = int(getattr(decision, "target_id", None) or getattr(context, "current_target_id", None) or 0) or None
            target_obj, target_in_custody, custody_guard_id, target_is_jailed = self.get_target_custody_state(arrest_target_id)
            if guard_ndb is not None:
                guard_ndb.diresim_last_action = "ARREST"
            if sim_state is not None:
                sim_state.set_behavior_state("warn")
                sim_state.begin_arrest(arrest_target_id, current_time)
                sim_state.set_last_significant_event_at(current_time)
            if commit_mode == "state_only":
                if sim_state is not None:
                    sim_state.set_cooldown("arrest_until", current_time + 10.0)
                    sim_state.save_if_needed()
                    commit_metrics["current_target_id"] = getattr(sim_state, "current_target_id", commit_metrics.get("current_target_id", None))
                return commit_metrics
            can_resolve_arrest = bool(
                arrest_target_id is not None
                and current_room_id is not None
                and bool(getattr(context, "target_present_in_room", False))
                and not bool(getattr(context, "target_in_custody", False))
                and not bool(getattr(context, "target_is_jailed", False))
                and target_obj is not None
            )
            if can_resolve_arrest:
                enter_custody(target_obj, int(getattr(guard, "id", 0) or 0), current_room_id, current_time)
                if sim_state is not None:
                    sim_state.set_current_target_id(arrest_target_id)
                    sim_state.set_cooldown("arrest_until", current_time + 10.0)
                    sim_state.clear_confrontation()
                    sim_state.clear_pursuit()
                    sim_state.save_if_needed()
                    commit_metrics["current_target_id"] = getattr(sim_state, "current_target_id", commit_metrics.get("current_target_id", None))
                commit_metrics["warning_stage"] = 0
                commit_metrics["arrest_emitted"] = True
                commit_metrics["arrests_successful"] = 1
                if current_room_id != JAIL_ROOM_ID:
                    commit_metrics["escorts_started"] = 1
                self.custody_metrics["arrests_successful"] += 1
                self.custody_metrics["escorts_started"] += int(commit_metrics["escorts_started"] or 0)
                self.enqueue_event(
                    SimEvent(
                        "PLAYER_ARRESTED",
                        current_room_id,
                        payload={"target_id": arrest_target_id, "guard_id": int(getattr(guard, "id", 0) or 0)},
                    )
                )
            elif sim_state is not None:
                sim_state.set_cooldown("arrest_until", current_time + 10.0)
                sim_state.save_if_needed()
            return commit_metrics

        if action_type == "ESCORT":
            if commit_mode == "state_only":
                return commit_metrics
            escort_target_id = int(getattr(decision, "target_id", None) or getattr(context, "current_target_id", None) or 0) or None
            target_obj, target_in_custody, custody_guard_id, target_is_jailed = self.get_target_custody_state(escort_target_id)
            if guard_ndb is not None:
                guard_ndb.diresim_last_action = "ESCORT"
            if sim_state is not None:
                sim_state.set_behavior_state("escort")
            if escort_target_id is None or target_obj is None or target_is_jailed or not target_in_custody or int(custody_guard_id or 0) != int(getattr(guard, "id", 0) or 0):
                if target_obj is not None and target_in_custody and int(custody_guard_id or 0) == int(getattr(guard, "id", 0) or 0):
                    clear_custody(target_obj)
                if sim_state is not None:
                    sim_state.clear_confrontation()
                    sim_state.clear_pursuit()
                    sim_state.set_current_target_id(None)
                    sim_state.save_if_needed()
                    commit_metrics["current_target_id"] = None
                return commit_metrics

            destination = self.get_guard_destination(JAIL_ROOM_ID)
            if destination is None:
                if sim_state is not None:
                    sim_state.set_cooldown("move_until", current_time + 3.0)
                    sim_state.save_if_needed()
                return commit_metrics

            commit_metrics["move_attempted"] = True
            move_succeeded = False
            if JAIL_ROOM_ID == current_room_id:
                move_succeeded = True
            else:
                move_result = guard.move_to(destination, quiet=True, move_hooks=False)
                move_succeeded = bool(move_result is not False)
            if not move_succeeded:
                commit_metrics["move_failed"] = True
                if sim_state is not None:
                    sim_state.set_cooldown("move_until", current_time + 3.0)
                    sim_state.save_if_needed()
                return commit_metrics

            escort_room_id = int(getattr(getattr(guard, "location", None), "id", 0) or JAIL_ROOM_ID or 0) or None
            target_move_result = target_obj.move_to(getattr(guard, "location", None), quiet=True, move_hooks=False, move_type="custody_escort", allow_custody_transport=True)
            if target_move_result is False:
                clear_custody(target_obj)
                if sim_state is not None:
                    sim_state.clear_confrontation()
                    sim_state.clear_pursuit()
                    sim_state.set_current_target_id(None)
                    sim_state.set_cooldown("move_until", current_time + 3.0)
                    sim_state.save_if_needed()
                commit_metrics["move_failed"] = True
                commit_metrics["current_target_id"] = None
                return commit_metrics

            enter_custody(target_obj, int(getattr(guard, "id", 0) or 0), escort_room_id, current_time)
            if sim_state is not None:
                sim_state.set_current_target_id(escort_target_id)
                sim_state.set_cooldown("move_until", current_time + 3.0)
                sim_state.set_last_significant_event_at(current_time)
                sim_state.save_if_needed()
                commit_metrics["current_target_id"] = getattr(sim_state, "current_target_id", commit_metrics.get("current_target_id", None))
            commit_metrics["move_success"] = True

            if escort_room_id == JAIL_ROOM_ID:
                enter_jail(target_obj, current_time)
                clear_custody(target_obj)
                if sim_state is not None:
                    sim_state.clear_confrontation()
                    sim_state.clear_pursuit()
                    sim_state.clear_suspicion(escort_target_id)
                    sim_state.set_current_target_id(None)
                    sim_state.save_if_needed()
                commit_metrics["escorts_completed"] = 1
                commit_metrics["jail_entries"] = 1
                commit_metrics["current_target_id"] = None
                self.custody_metrics["escorts_completed"] += 1
                self.custody_metrics["jail_entries"] += 1
                self.enqueue_event(
                    SimEvent(
                        "PLAYER_JAILED",
                        escort_room_id,
                        payload={"target_id": escort_target_id, "guard_id": int(getattr(guard, "id", 0) or 0)},
                    )
                )
            return commit_metrics

        if action_type == "MOVE":
            if commit_mode == "state_only":
                return commit_metrics
            commit_metrics["move_attempted"] = True
            if ring not in {"normal", "slow"}:
                commit_metrics["move_failed"] = True
                return commit_metrics
            destination_id = getattr(sim_state, "get_next_patrol_room", lambda: None)() if sim_state is not None else getattr(decision, "destination_id", None)
            if not destination_id:
                if sim_state is not None:
                    sim_state.set_behavior_state("patrol")
                    sim_state.set_movement_target_room_id(None)
                    sim_state.save_if_needed()
                commit_metrics["move_failed"] = True
                return commit_metrics
            destination = self.get_guard_destination(destination_id)
            if destination is None:
                commit_metrics["move_failed"] = True
                return commit_metrics
            if sim_state is not None:
                sim_state.set_behavior_state("patrol")
                sim_state.set_movement_target_room_id(destination_id)
            move_succeeded = False
            if destination_id == current_room_id:
                move_succeeded = True
            else:
                move_result = guard.move_to(destination, quiet=True, move_hooks=False)
                move_succeeded = bool(move_result is not False)
            if not move_succeeded:
                if sim_state is not None:
                    sim_state.save_if_needed()
                commit_metrics["move_failed"] = True
                return commit_metrics
            if guard_ndb is not None:
                guard_ndb.diresim_last_action = "MOVE"
            if sim_state is not None:
                sim_state.set_current_target_id(getattr(decision, "target_id", None) or None)
                sim_state.advance_patrol_index()
                sim_state.set_movement_progress_index(int(getattr(sim_state, "patrol_index", 0) or 0))
                sim_state.set_movement_target_room_id(getattr(sim_state, "get_next_patrol_room", lambda: None)())
                sim_state.set_cooldown("move_until", current_time + 3.0)
                sim_state.set_last_significant_event_at(current_time)
                sim_state.save_if_needed()
                commit_metrics["route_progress"] = int(getattr(sim_state, "movement_progress_index", 0) or 0)
                commit_metrics["current_target_id"] = getattr(sim_state, "current_target_id", commit_metrics.get("current_target_id", None))
            commit_metrics["move_success"] = True
            return commit_metrics

        if action_type == "PURSUE":
            if commit_mode == "state_only":
                return commit_metrics
            commit_metrics["pursuit_move_attempted"] = True
            commit_metrics["pursuit_destination_id"] = int(getattr(decision, "destination_id", None) or getattr(context, "intercept_room_id", None) or getattr(context, "pursuit_last_known_room_id", None) or 0) or None
            if ring not in {"normal", "slow"}:
                commit_metrics["pursuit_move_failed"] = True
                return commit_metrics
            destination_id = commit_metrics["pursuit_destination_id"]
            if not destination_id:
                commit_metrics["pursuit_move_failed"] = True
                return commit_metrics
            destination = self.get_guard_destination(destination_id)
            if destination is None:
                commit_metrics["pursuit_move_failed"] = True
                return commit_metrics
            move_succeeded = False
            if destination_id == current_room_id:
                move_succeeded = True
            else:
                move_result = guard.move_to(destination, quiet=True, move_hooks=False)
                move_succeeded = bool(move_result is not False)
            if not move_succeeded:
                commit_metrics["pursuit_move_failed"] = True
                if sim_state is not None:
                    sim_state.save_if_needed()
                return commit_metrics
            if sim_state is not None:
                sim_state.set_current_target_id(getattr(decision, "target_id", None) or getattr(context, "current_target_id", None))
                sim_state.begin_pursuit(
                    getattr(decision, "target_id", None) or getattr(context, "pursuit_target_id", None) or getattr(context, "current_target_id", None),
                    getattr(context, "pursuit_last_known_room_id", None) or destination_id,
                    float(getattr(sim_state, "pursuit_started_at", 0.0) or current_time),
                )
                sim_state.set_intercept_room(destination_id)
                sim_state.set_pursuit_state("intercepting" if destination_id == getattr(context, "intercept_room_id", None) else "tracking")
                sim_state.set_cooldown("pursuit_until", current_time + 3.0)
                sim_state.set_last_significant_event_at(current_time)
                sim_state.save_if_needed()
                commit_metrics["current_target_id"] = getattr(sim_state, "current_target_id", commit_metrics.get("current_target_id", None))
            if guard_ndb is not None:
                guard_ndb.diresim_last_action = "PURSUE"
            commit_metrics["pursuit_move_success"] = True
            return commit_metrics

        return commit_metrics

    def _log_unsupported_guard_branch(self, guard, reason):
        logger.log_trace(
            f"[DireSim] Unsupported guard branch guard={int(getattr(guard, 'id', 0) or 0)} service={self.service_id} reason={reason}"
        )

    def get_guard_destination(self, destination_id):
        try:
            return ObjectDB.objects.get(id=destination_id)
        except Exception:
            return None

    def message_budget_allows(self, room_id, guard_id):
        return False

    def get_guard(self, npc_id):
        try:
            return ObjectDB.objects.get(id=npc_id)
        except Exception:
            return None
