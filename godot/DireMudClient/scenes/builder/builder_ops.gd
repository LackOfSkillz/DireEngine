extends RefCounted

class_name BuilderOps


static func make_op(op: String, entity_type: String, entity_id: String, payload: Dictionary, meta: Dictionary = {}) -> Dictionary:
	return {
		"op": op.strip_edges().to_lower(),
		"entity_type": entity_type.strip_edges().to_lower(),
		"entity_id": entity_id.strip_edges(),
		"payload": payload.duplicate(true),
		"meta": meta.duplicate(true),
	}


static func reverse_op(operation: Dictionary) -> Dictionary:
	var normalized_op := str(operation.get("op", "")).strip_edges().to_lower()
	var entity_type := str(operation.get("entity_type", "")).strip_edges().to_lower()
	var entity_id := str(operation.get("entity_id", "")).strip_edges()
	var payload: Dictionary = (operation.get("payload", {}) as Dictionary).duplicate(true)
	var meta: Dictionary = (operation.get("meta", {}) as Dictionary).duplicate(true)
	match normalized_op:
		"create":
			return make_op("delete", entity_type, entity_id, payload, {"before": payload})
		"delete":
			return make_op("create", entity_type, entity_id, payload, meta)
		"update":
			var before_state: Dictionary = (meta.get("before", {}) as Dictionary).duplicate(true)
			return make_op("update", entity_type, entity_id, before_state, {"before": payload})
		_:
			return {}


static func serialize_op(operation: Dictionary) -> Array[Dictionary]:
	var serialized: Array[Dictionary] = []
	var normalized_op := str(operation.get("op", "")).strip_edges().to_lower()
	var entity_type := str(operation.get("entity_type", "")).strip_edges().to_lower()
	var entity_id := str(operation.get("entity_id", "")).strip_edges()
	var payload: Dictionary = (operation.get("payload", {}) as Dictionary).duplicate(true)
	match entity_type:
		"room":
			match normalized_op:
				"create":
					serialized.append({
						"id": "create-%s" % entity_id,
						"op": "create_room",
						"room": (payload.get("room", {}) as Dictionary).duplicate(true),
					})
				"update":
					serialized.append({
						"id": "update-%s" % entity_id,
						"op": "update_room",
						"room_id": entity_id,
						"updates": (payload.get("updates", {}) as Dictionary).duplicate(true),
					})
				"delete":
					serialized.append({
						"id": "delete-%s" % entity_id,
						"op": "delete_room",
						"room_id": entity_id,
					})
		"exit":
			var exit_payload := payload.duplicate(true)
			match normalized_op:
				"create":
					serialized.append({
						"id": "exit-%s" % entity_id,
						"op": "set_exit",
						"source_id": str(exit_payload.get("source_id", "")).strip_edges(),
						"direction": str(exit_payload.get("direction", "")).strip_edges().to_lower(),
						"target_id": str(exit_payload.get("target_id", "")).strip_edges(),
						"target_zone_id": str(exit_payload.get("target_zone_id", "")).strip_edges(),
					})
				"update":
					serialized.append({
						"id": "update-exit-%s" % entity_id,
						"op": "update_exit",
						"exit_id": entity_id,
						"fields": {
							"direction": str(exit_payload.get("direction", "")).strip_edges().to_lower(),
							"target_id": str(exit_payload.get("target_id", "")).strip_edges(),
							"target_zone_id": str(exit_payload.get("target_zone_id", "")).strip_edges(),
							"label": str(exit_payload.get("label", "")).strip_edges(),
							"aliases": (exit_payload.get("aliases", []) as Array).duplicate(true),
						},
					})
				"delete":
					serialized.append({
						"id": "delete-exit-%s" % entity_id,
						"op": "delete_exit",
						"source_id": str(exit_payload.get("source_id", "")).strip_edges(),
						"direction": str(exit_payload.get("direction", "")).strip_edges().to_lower(),
					})
		"npc", "item":
			match normalized_op:
				"create":
					serialized.append(payload.duplicate(true))
				"update":
					if payload.has("destination_id"):
						serialized.append({
							"id": "move-object-%s" % entity_id,
							"op": "move_object",
							"object_id": entity_id,
							"destination_id": str(payload.get("destination_id", "")).strip_edges(),
							"relation": str(payload.get("relation", "in")).strip_edges().to_lower(),
						})
					else:
						serialized.append({
							"id": "update-object-%s" % entity_id,
							"op": "update_object",
							"object_id": entity_id,
							"object": (payload.get("fields", {}) as Dictionary).duplicate(true),
						})
				"delete":
					serialized.append({
						"id": "delete-object-%s" % entity_id,
						"op": "delete_object",
						"object_id": entity_id,
					})
	return serialized