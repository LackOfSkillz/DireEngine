extends Control

class_name BuilderMapGrid


const ObjectNodeScene = preload("res://scenes/builder/ObjectNode.tscn")
const BuilderVisuals = preload("res://scripts/builder_visuals.gd")


signal empty_cell_clicked(cell)
signal room_selected(room_id)
signal room_dragged(room_id, cell)
signal exit_requested(source_id, direction, target_id)
signal exit_clicked(source_id, direction, target_id)
signal object_selected(object_id, target_id, relation)
signal object_drop_requested(object_id, destination_id, relation)


class RoomNode:
	var room_id := ""
	var object_id := ""
	var x := 0
	var y := 0
	var layer := 0
	var name := ""
	var description := ""
	var room_type := "room"
	var tags: Array[String] = []
	var contents: Array[Dictionary] = []

	func _init(data: Dictionary = {}) -> void:
		room_id = str(data.get("id", ""))
		object_id = str(data.get("object_id", ""))
		x = int(data.get("map_x", 0))
		y = int(data.get("map_y", 0))
		layer = int(data.get("map_layer", 0))
		name = str(data.get("name", room_id))
		description = str(data.get("description", ""))
		room_type = str(data.get("room_type", "room")).strip_edges().to_lower()
		tags = BuilderVisuals.normalize_semantic_tags(data.get("tags", []))
		contents = []
		for entry in data.get("contents", []):
			if entry is Dictionary:
				contents.append((entry as Dictionary).duplicate(true))


const CELL_SIZE := 56.0
const TILE_SIZE := Vector2(44.0, 44.0)
const GRID_PADDING := Vector2(32.0, 32.0)
const MIN_ROOM_PIXEL_SIZE := 10.0
const MAX_ROOM_PIXEL_SIZE := 26.0
const MIN_ZOOM := 0.35
const MAX_ZOOM := 2.4
const ZOOM_STEP := 1.12


var area_id := ""
var rooms: Array[RoomNode] = []
var exits: Array[Dictionary] = []
var room_contents := {}
var room_nodes := {}
var object_nodes := {}
var npc_nodes := {}
var map_min := Vector2.ZERO
var map_max := Vector2.ZERO
var map_scale := CELL_SIZE
var map_offset := GRID_PADDING
var room_draw_size := TILE_SIZE
var object_draw_scale := 1.0
var selected_room_id := ""
var selected_object_id := ""
var hover_object_id := ""
var create_room_mode := false
var draw_exit_mode := false
var hover_room_id := ""
var hover_edge_index := -1
var conflict_room_ids: Array[String] = []
var drop_target_room_id := ""
var pending_exit_source_id := ""
var drag_room_id := ""
var drag_started := false
var drag_start_position := Vector2.ZERO
var drag_preview_cell := {}
var debug_rtsync := false
var builder_enabled := false
var zoom_level := 1.0
var pan_offset := Vector2.ZERO
var panning := false
var last_map_data: Dictionary = {}
var last_transform_signature := ""


@onready var tooltip_label: Label = $Tooltip


func load_builder_map(map_data: Dictionary) -> void:
	apply_map_update(map_data)


func apply_map_update(map_data: Dictionary) -> void:
	last_map_data = map_data.duplicate(true)
	area_id = str(map_data.get("zone_id", map_data.get("area_id", "")))
	update_rooms(map_data)
	update_room_objects(map_data)
	update_npcs(map_data)
	if not selected_room_id.is_empty() and not room_nodes.has(selected_room_id):
		selected_room_id = ""
	if not selected_object_id.is_empty() and not object_nodes.has(selected_object_id):
		selected_object_id = ""
	set_selected_object(selected_object_id)
	queue_redraw()


func set_debug_rtsync(enabled: bool) -> void:
	debug_rtsync = enabled


func set_builder_enabled(enabled: bool) -> void:
	builder_enabled = enabled
	if not builder_enabled:
		panning = false
		hover_room_id = ""
		if tooltip_label != null:
			tooltip_label.visible = false
	_update_cursor_shape()
	queue_redraw()


func get_room_registry() -> Dictionary:
	return room_nodes.duplicate(true)


func get_npc_registry() -> Dictionary:
	return npc_nodes.duplicate()


func update_rooms(map_data: Dictionary) -> void:
	rooms.clear()
	exits.clear()
	room_contents.clear()
	room_nodes.clear()
	drop_target_room_id = ""
	pending_exit_source_id = ""
	conflict_room_ids.clear()
	for room_data in map_data.get("rooms", []):
		if room_data is Dictionary:
			var typed_room_data := room_data as Dictionary
			rooms.append(RoomNode.new(typed_room_data))
			room_contents[str(typed_room_data.get("id", ""))] = typed_room_data.get("contents", [])
			_append_room_exits(typed_room_data)
	_update_view_transform()
	for room_node in rooms:
		room_nodes[room_node.room_id] = {
			"room_id": room_node.room_id,
			"object_id": room_node.object_id,
			"position": _room_position(room_node),
		}


func _parse_exit_target(raw_target: Variant, fallback_zone_id: String) -> Dictionary:
	if raw_target is Dictionary:
		return {
			"zone_id": str((raw_target as Dictionary).get("zone_id", fallback_zone_id)).strip_edges(),
			"room_id": str((raw_target as Dictionary).get("room_id", "")).strip_edges(),
		}
	return {
		"zone_id": fallback_zone_id,
		"room_id": str(raw_target).strip_edges(),
	}


func _append_room_exits(room_data: Dictionary) -> void:
	var source_id := str(room_data.get("id", "")).strip_edges()
	if source_id.is_empty():
		return

	var appended_keys := {}
	var detailed_rows = room_data.get("exit_details", [])
	if detailed_rows is Array and not detailed_rows.is_empty():
		for raw_row in detailed_rows:
			if not raw_row is Dictionary:
				continue
			var row := raw_row as Dictionary
			var direction := str(row.get("direction", "")).strip_edges().to_lower()
			var target_payload := _parse_exit_target(row.get("target", row.get("target_room_id", {})), area_id)
			_append_exit_edge(source_id, direction, target_payload, appended_keys)
		return

	var fallback_exits: Dictionary = (room_data.get("exits", {}) as Dictionary).duplicate(true)
	for direction in fallback_exits.keys():
		var target_payload := _parse_exit_target(fallback_exits.get(direction, {}), area_id)
		_append_exit_edge(source_id, str(direction).strip_edges().to_lower(), target_payload, appended_keys)


func _append_exit_edge(source_id: String, direction: String, target_payload: Dictionary, appended_keys: Dictionary) -> void:
	var target_room_id := str(target_payload.get("room_id", "")).strip_edges()
	var target_zone_id := str(target_payload.get("zone_id", area_id)).strip_edges()
	var normalized_direction := direction.strip_edges().to_lower()
	if target_room_id.is_empty():
		return
	var edge_key := "%s|%s|%s|%s" % [source_id, normalized_direction, target_zone_id, target_room_id]
	if appended_keys.has(edge_key):
		return
	appended_keys[edge_key] = true
	exits.append(
		{
			"source_id": source_id,
			"direction": normalized_direction,
			"target_id": target_room_id,
			"target_zone_id": target_zone_id,
		}
	)


func update_room_objects(_map_data: Dictionary) -> void:
	var seen_static := {}
	for room_node in rooms:
		var contents = room_contents.get(room_node.room_id, [])
		if not contents is Array:
			continue
		for index in range(contents.size()):
			var obj = contents[index]
			if not obj is Dictionary:
				continue
			var object_data := obj as Dictionary
			var object_type := str(object_data.get("type", "item")).strip_edges().to_lower()
			if object_type == "npc":
				continue
			var object_id := str(object_data.get("object_id", object_data.get("id", ""))).strip_edges()
			if object_id.is_empty():
				continue
			seen_static[object_id] = true
			_sync_object_node(object_data, room_node.room_id, _room_position(room_node) + _offset_for_index(index))
	var stale_static: Array[String] = []
	for object_id in object_nodes.keys():
		var normalized_object_id := str(object_id)
		if npc_nodes.has(normalized_object_id):
			continue
		if not seen_static.has(normalized_object_id):
			stale_static.append(normalized_object_id)
	for object_id in stale_static:
		_remove_object_node(object_id)


func update_npcs(map_data: Dictionary) -> void:
	var seen_npcs := {}
	var room_npc_counts := {}
	for raw_npc in _extract_npc_updates(map_data):
		if not raw_npc is Dictionary:
			continue
		var npc := (raw_npc as Dictionary).duplicate(true)
		var npc_id := str(npc.get("id", "")).strip_edges()
		var room_id := str(npc.get("room_id", "")).strip_edges()
		if npc_id.is_empty():
			continue
		seen_npcs[npc_id] = true
		if room_id.is_empty() or not room_nodes.has(room_id):
			continue
		npc["room_index"] = int(room_npc_counts.get(room_id, 0))
		room_npc_counts[room_id] = int(npc["room_index"]) + 1
		if not npc_nodes.has(npc_id):
			spawn_npc(npc)
			continue
		_update_existing_npc(npc)
	var stale_npcs: Array[String] = []
	for npc_id in npc_nodes.keys():
		var normalized_npc_id := str(npc_id)
		if not seen_npcs.has(normalized_npc_id):
			stale_npcs.append(normalized_npc_id)
	for npc_id in stale_npcs:
		_remove_npc_node(npc_id)


func set_create_room_mode(enabled: bool) -> void:
	create_room_mode = enabled
	if enabled:
		pending_exit_source_id = ""
	_update_cursor_shape()
	queue_redraw()


func set_draw_exit_mode(enabled: bool) -> void:
	draw_exit_mode = enabled
	if not enabled:
		pending_exit_source_id = ""
	_update_cursor_shape()
	queue_redraw()


func set_conflict_rooms(room_ids: Array[String]) -> void:
	conflict_room_ids = room_ids.duplicate()
	queue_redraw()


func clear_conflicts() -> void:
	conflict_room_ids.clear()
	queue_redraw()


func set_selected_room(room_id: String) -> void:
	selected_room_id = room_id.strip_edges()
	queue_redraw()


func set_selected_object(object_id: String) -> void:
	selected_object_id = object_id.strip_edges()
	for node in object_nodes.values():
		if node != null:
			node.set_selected(str(node.object_id) == selected_object_id)


func has_object(object_id: String) -> bool:
	return object_nodes.has(object_id.strip_edges())


func get_selected_room() -> Dictionary:
	var room_node := _find_room(selected_room_id)
	if room_node == null:
		return {}
	return _room_to_dictionary(room_node)


func _draw() -> void:
	_update_view_transform()
	_draw_grid()
	_draw_exits()
	_draw_rooms()
	_draw_pending_exit()
	_draw_debug_overlay()


func _gui_input(event: InputEvent) -> void:
	if not builder_enabled:
		return
	if event is InputEventMouseMotion:
		var motion := event as InputEventMouseMotion
		if panning:
			pan_offset += motion.relative
			queue_redraw()
		_update_hover_state(motion.position)
		hover_edge_index = _edge_at_position(motion.position)
		_update_cursor_shape()
		if not drag_room_id.is_empty():
			drag_started = drag_started or motion.position.distance_to(drag_start_position) > 10.0
			if drag_started:
				drag_preview_cell = _cell_from_position(motion.position)
		queue_redraw()
		return

	if event is InputEventMouseButton:
		var mouse_event := event as InputEventMouseButton
		if mouse_event.button_index == MOUSE_BUTTON_WHEEL_UP and mouse_event.pressed:
			_zoom_map(ZOOM_STEP)
			return
		if mouse_event.button_index == MOUSE_BUTTON_WHEEL_DOWN and mouse_event.pressed:
			_zoom_map(1.0 / ZOOM_STEP)
			return
		if mouse_event.button_index == MOUSE_BUTTON_MIDDLE or mouse_event.button_index == MOUSE_BUTTON_RIGHT:
			panning = mouse_event.pressed
			if not panning and tooltip_label != null:
				tooltip_label.visible = not hover_room_id.is_empty()
			_update_cursor_shape()
			return
		if mouse_event.button_index == MOUSE_BUTTON_LEFT:
			if mouse_event.pressed:
				_handle_left_press(mouse_event.position)
			else:
				_handle_left_release(mouse_event.position)


func _handle_left_press(position: Vector2) -> void:
	var clicked_object := _object_at_position(position)
	if not clicked_object.is_empty() and not draw_exit_mode:
		var object_id := str(clicked_object.get("object_id", clicked_object.get("id", ""))).strip_edges()
		if str(clicked_object.get("type", "")).strip_edges().to_lower() == "npc" and debug_rtsync:
			print("Clicked NPC:", object_id)
		selected_object_id = object_id
		set_selected_object(object_id)
		emit_signal("object_selected", object_id, object_id, _default_relation_for_object(clicked_object))
		queue_redraw()
		return

	var clicked_room = _room_at_position(position)
	if draw_exit_mode:
		if clicked_room == null:
			pending_exit_source_id = ""
			queue_redraw()
			return
		if pending_exit_source_id.is_empty():
			pending_exit_source_id = str(clicked_room)
			emit_signal("room_selected", pending_exit_source_id)
			queue_redraw()
			return
		if str(clicked_room) == pending_exit_source_id:
			pending_exit_source_id = ""
			queue_redraw()
			return
		var direction := _direction_between_rooms(pending_exit_source_id, str(clicked_room))
		if direction.is_empty():
			return
		emit_signal("exit_requested", pending_exit_source_id, direction, str(clicked_room))
		pending_exit_source_id = ""
		queue_redraw()
		return

	if clicked_room != null:
		selected_object_id = ""
		drag_room_id = str(clicked_room)
		drag_started = false
		drag_start_position = position
		drag_preview_cell = {}
		emit_signal("room_selected", str(clicked_room))
		queue_redraw()
		return

	var edge_index := _edge_at_position(position)
	if edge_index >= 0 and edge_index < exits.size():
		var edge: Dictionary = exits[edge_index]
		emit_signal("exit_clicked", str(edge.get("source_id", "")), str(edge.get("direction", "")), str(edge.get("target_id", "")))
		return

	selected_object_id = ""
	emit_signal("empty_cell_clicked", _cell_from_position(position))
	queue_redraw()


func _handle_left_release(position: Vector2) -> void:
	if drag_room_id.is_empty():
		return
	if drag_started:
		emit_signal("room_dragged", drag_room_id, _cell_from_position(position))
	drag_room_id = ""
	drag_started = false
	drag_preview_cell = {}
	queue_redraw()


func _draw_grid() -> void:
	var line_color := Color(0.18, 0.18, 0.18, 0.8)
	for x_index in range(0, int(size.x / CELL_SIZE) + 2):
		var x_pos := float(x_index) * CELL_SIZE
		draw_line(Vector2(x_pos, 0.0), Vector2(x_pos, size.y), line_color, 1.0)
	for y_index in range(0, int(size.y / CELL_SIZE) + 2):
		var y_pos := float(y_index) * CELL_SIZE
		draw_line(Vector2(0.0, y_pos), Vector2(size.x, y_pos), line_color, 1.0)


func _draw_rooms() -> void:
	var font = ThemeDB.fallback_font
	var font_size := int(clampf(room_draw_size.x * 0.55, 9.0, 12.0))
	for room_node in rooms:
		var rect := Rect2(_room_position(room_node) - room_draw_size / 2.0, room_draw_size)
		var color := _get_room_color(room_node)
		if room_node.room_id == selected_room_id:
			var glow_rect := rect.grow(6.0)
			draw_rect(glow_rect, Color(0.18, 0.86, 1.0, 0.15))
		draw_rect(rect, color)
		var border_color := Color(0.06, 0.06, 0.08, 1.0)
		var border_width := 2.0
		if room_node.room_id == drop_target_room_id:
			border_color = Color(0.64, 0.92, 0.64, 1.0)
			border_width = 3.0
		elif conflict_room_ids.has(room_node.room_id):
			border_color = Color(0.88, 0.28, 0.28, 1.0)
			border_width = 3.0
		elif room_node.room_id == selected_room_id:
			border_color = Color(0.18, 0.86, 1.0, 1.0)
			border_width = 4.0
		draw_rect(rect, border_color, false, border_width)
		if room_node.room_id == hover_room_id:
			draw_rect(rect.grow(4.0), Color(1.0, 1.0, 1.0, 0.18), false, 2.0)
		if font != null and _should_draw_room_label(room_node):
			draw_string(font, rect.position + Vector2(4.0, rect.size.y + 12.0), room_node.name.substr(0, 18), HORIZONTAL_ALIGNMENT_LEFT, maxf(room_draw_size.x * 6.0, 120.0), font_size, Color.WHITE)


func _draw_exits() -> void:
	var line_width := clampf(room_draw_size.x * 0.22, 2.0, 5.0)
	for index in range(exits.size()):
		var edge: Dictionary = exits[index]
		var source := _find_room(str(edge.get("source_id", "")))
		var target := _find_room(str(edge.get("target_id", "")))
		if source == null or target == null:
			continue
		var color := Color(0.82, 0.84, 0.9, 1.0)
		if index == hover_edge_index:
			color = Color(1.0, 0.54, 0.2, 1.0)
		draw_line(_room_position(source), _room_position(target), color, line_width)
		_draw_arrow(_room_position(source), _room_position(target), color)


func _draw_pending_exit() -> void:
	if pending_exit_source_id.is_empty() or hover_room_id.is_empty():
		return
	var source := _find_room(pending_exit_source_id)
	var target := _find_room(hover_room_id)
	if source == null or target == null:
		return
	draw_line(_room_position(source), _room_position(target), Color(0.92, 0.92, 1.0, 0.55), clampf(room_draw_size.x * 0.12, 1.0, 2.0))


func _draw_arrow(from_pos: Vector2, to_pos: Vector2, color: Color) -> void:
	var direction := (to_pos - from_pos).normalized()
	var arrow_tip := to_pos.lerp(from_pos, 0.18)
	var arrow_size := clampf(room_draw_size.x * 0.35, 4.0, 10.0)
	var left := arrow_tip - direction.rotated(0.6) * arrow_size
	var right := arrow_tip - direction.rotated(-0.6) * arrow_size
	draw_line(arrow_tip, left, color, clampf(room_draw_size.x * 0.12, 1.0, 2.0))
	draw_line(arrow_tip, right, color, clampf(room_draw_size.x * 0.12, 1.0, 2.0))


func _room_position(room_node: RoomNode) -> Vector2:
	return map_offset + Vector2(float(room_node.x) - map_min.x, float(room_node.y) - map_min.y) * map_scale


func _room_at_position(position: Vector2):
	for room_node in rooms:
		var rect := Rect2(_room_position(room_node) - room_draw_size / 2.0, room_draw_size)
		if rect.has_point(position):
			return room_node.room_id
	return null


func _object_at_position(position: Vector2) -> Dictionary:
	var best_match := {}
	var best_priority := -1
	var best_distance: float = INF
	for node in object_nodes.values():
		if node == null or not node.contains_local_point(position):
			continue
		var object_type := str(node.object_type).strip_edges().to_lower()
		var priority := 2 if object_type == "npc" else 1
		var distance: float = node.position.distance_squared_to(position)
		if priority < best_priority:
			continue
		if priority == best_priority and distance >= best_distance:
			continue
		best_priority = priority
		best_distance = distance
		best_match = {
			"object_id": str(node.object_id),
			"type": object_type,
			"is_surface": bool(node.is_surface),
			"room_id": str(node.room_id),
			"name": str(node.object_name),
		}
	return best_match


func _edge_at_position(position: Vector2) -> int:
	for index in range(exits.size()):
		var edge: Dictionary = exits[index]
		var source := _find_room(str(edge.get("source_id", "")))
		var target := _find_room(str(edge.get("target_id", "")))
		if source == null or target == null:
			continue
		var distance: float = Geometry2D.get_closest_point_to_segment(position, _room_position(source), _room_position(target)).distance_to(position)
		if distance <= 8.0:
			return index
	return -1


func _cell_from_position(position: Vector2) -> Dictionary:
	_update_view_transform()
	var grid_space := position - map_offset
	if is_zero_approx(map_scale):
		return {
			"map_x": 0,
			"map_y": 0,
			"map_layer": 0,
		}
	return {
		"map_x": int(round((grid_space.x / map_scale) + map_min.x)),
		"map_y": int(round((grid_space.y / map_scale) + map_min.y)),
		"map_layer": 0,
	}


func _find_room(room_id: String) -> RoomNode:
	for room_node in rooms:
		if room_node.room_id == room_id:
			return room_node
	return null


func _direction_between_rooms(source_id: String, target_id: String) -> String:
	var source := _find_room(source_id)
	var target := _find_room(target_id)
	if source == null or target == null:
		return ""
	var dx := target.x - source.x
	var dy := target.y - source.y
	if dx == 0 and dy == 0:
		return ""
	if abs(dx) > abs(dy):
		return "east" if dx > 0 else "west"
	if abs(dy) > abs(dx):
		return "south" if dy > 0 else "north"
	return ""


func _room_to_dictionary(room_node: RoomNode) -> Dictionary:
	return {
		"id": room_node.room_id,
		"object_id": room_node.object_id,
		"map_x": room_node.x,
		"map_y": room_node.y,
		"map_layer": room_node.layer,
		"name": room_node.name,
		"description": room_node.description,
		"room_type": room_node.room_type,
		"tags": room_node.tags.duplicate(),
		"contents": room_node.contents.duplicate(true),
	}


func spawn_npc(npc: Dictionary) -> void:
	var room_id := str(npc.get("room_id", "")).strip_edges()
	if room_id.is_empty() or not room_nodes.has(room_id):
		return
	var npc_id := str(npc.get("id", "")).strip_edges()
	if npc_id.is_empty() or npc_nodes.has(npc_id):
		return
	var npc_node = _sync_object_node(
		{
			"id": npc_id,
			"object_id": npc_id,
			"name": str(npc.get("name", npc_id)),
			"type": "npc",
		},
		room_id,
		_npc_position_for(npc)
	)
	if npc_node == null:
		return
	npc_nodes[npc_id] = npc_node
	npc_node.scale = Vector2.ONE * maxf(object_draw_scale * 0.5, 0.2)
	var spawn_tween: Tween = npc_node.create_tween()
	spawn_tween.tween_property(npc_node, "scale", Vector2.ONE * object_draw_scale, 0.2)


func _update_existing_npc(npc: Dictionary) -> void:
	var npc_id := str(npc.get("id", "")).strip_edges()
	var room_id := str(npc.get("room_id", "")).strip_edges()
	if npc_id.is_empty() or room_id.is_empty() or not npc_nodes.has(npc_id) or not room_nodes.has(room_id):
		return
	var npc_node = npc_nodes.get(npc_id)
	if npc_node == null:
		return
	npc_node.room_id = room_id
	npc_node.configure(
		{
			"id": npc_id,
			"object_id": npc_id,
			"name": str(npc.get("name", npc_id)),
			"type": "npc",
		}
	)
	npc_node.set_render_scale(object_draw_scale)
	var target_pos := _npc_position_for(npc)
	var distance: float = npc_node.position.distance_to(target_pos)
	if distance <= 1.0:
		npc_node.position = target_pos
		npc_node.original_position = target_pos
		return
	if debug_rtsync:
		print("NPC moved:", npc_id)
	var move_tween: Tween = npc_node.get_meta("move_tween", null)
	if move_tween != null:
		move_tween.kill()
	move_tween = npc_node.create_tween()
	npc_node.set_meta("move_tween", move_tween)
	move_tween.tween_property(npc_node, "position", target_pos, 0.2).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	npc_node.original_position = target_pos


func _npc_position_for(npc: Dictionary) -> Vector2:
	var room_id := str(npc.get("room_id", "")).strip_edges()
	var room_entry: Dictionary = room_nodes.get(room_id, {})
	var room_position := Vector2.ZERO
	var room_position_value = room_entry.get("position", Vector2.ZERO)
	if room_position_value is Vector2:
		room_position = room_position_value
	return room_position + _npc_offset_for_index(int(npc.get("room_index", 0)))


func _npc_offset_for_index(index: int) -> Vector2:
	var step := clampf(room_draw_size.x * 0.32, 4.0, 8.0)
	return Vector2(step * float(index % 2), -clampf(room_draw_size.y * 0.35, 5.0, 10.0) - (step * float(int(index / 2))))


func _sync_object_node(data: Dictionary, room_id: String, target_position: Vector2):
	var object_id := str(data.get("object_id", data.get("id", ""))).strip_edges()
	if object_id.is_empty():
		return null
	var object_node = object_nodes.get(object_id)
	if object_node == null:
		object_node = ObjectNodeScene.instantiate()
		object_node.object_id = object_id
		object_node.object_type = str(data.get("type", "item"))
		object_node.room_id = room_id
		object_node.position = target_position
		add_child(object_node)
		object_node.clicked.connect(_on_object_clicked)
		object_node.drag_position_changed.connect(_on_object_drag_position_changed)
		object_node.drop_requested.connect(_on_object_drop_requested)
		object_node.drag_canceled.connect(_on_object_drag_canceled)
		object_nodes[object_id] = object_node
	else:
		object_node.room_id = room_id
		object_node.position = target_position
	object_node.configure(data)
	object_node.set_render_scale(object_draw_scale)
	object_node.original_position = target_position
	return object_node


func _remove_object_node(object_id: String) -> void:
	var node = object_nodes.get(object_id)
	if node != null:
		node.queue_free()
	object_nodes.erase(object_id)


func _remove_npc_node(npc_id: String) -> void:
	_remove_object_node(npc_id)
	npc_nodes.erase(npc_id)


func _extract_npc_updates(map_data: Dictionary) -> Array[Dictionary]:
	var exported_npcs_value = map_data.get("npcs", [])
	if exported_npcs_value is Array and not exported_npcs_value.is_empty():
		var typed_exported_npcs: Array[Dictionary] = []
		for entry in exported_npcs_value:
			if entry is Dictionary:
				typed_exported_npcs.append((entry as Dictionary).duplicate(true))
		return typed_exported_npcs
	var fallback_npcs: Array[Dictionary] = []
	for room_node in rooms:
		var contents = room_contents.get(room_node.room_id, [])
		if not contents is Array:
			continue
		for obj in contents:
			if not obj is Dictionary:
				continue
			var object_data := obj as Dictionary
			if str(object_data.get("type", "item")).strip_edges().to_lower() != "npc":
				continue
			fallback_npcs.append(
				{
					"id": str(object_data.get("object_id", object_data.get("id", ""))).strip_edges(),
					"room_id": room_node.room_id,
					"name": str(object_data.get("name", "NPC")),
				}
			)
	return fallback_npcs


func _offset_for_index(index: int) -> Vector2:
	var step := clampf(room_draw_size.x * 0.4, 5.0, 10.0)
	var lift := clampf(room_draw_size.y * 0.75, 8.0, 18.0)
	return Vector2(step * float(index % 3), -lift - (step * float(int(index / 3))))


func _clear_object_nodes() -> void:
	for node in object_nodes.values():
		if node != null:
			node.queue_free()
	object_nodes.clear()
	npc_nodes.clear()


func _on_object_clicked(object_id: String) -> void:
	selected_object_id = object_id.strip_edges()
	set_selected_object(selected_object_id)
	emit_signal("object_selected", selected_object_id, selected_object_id, "in")


func _on_object_drag_position_changed(object_id: String, local_position: Vector2) -> void:
	var target = _resolve_drop_target(local_position, object_id)
	drop_target_room_id = str(target.get("room_id", ""))
	queue_redraw()


func _on_object_drop_requested(object_id: String, local_position: Vector2) -> void:
	var target = _resolve_drop_target(local_position, object_id)
	drop_target_room_id = ""
	queue_redraw()
	var destination_id := str(target.get("destination_id", "")).strip_edges()
	if destination_id.is_empty():
		var node = object_nodes.get(object_id)
		if node != null:
			node.reset_position()
		return
	emit_signal("object_drop_requested", object_id, destination_id, str(target.get("relation", "in")))


func _on_object_drag_canceled(object_id: String) -> void:
	drop_target_room_id = ""
	queue_redraw()
	var node = object_nodes.get(object_id)
	if node != null:
		node.reset_position()


func _update_hover_state(position: Vector2) -> void:
	var hovered_object := _object_at_position(position)
	hover_object_id = str(hovered_object.get("object_id", "")).strip_edges()
	if not hover_object_id.is_empty():
		hover_room_id = str(hovered_object.get("room_id", "")).strip_edges()
		if tooltip_label == null:
			_update_cursor_shape()
			return
		if panning:
			tooltip_label.visible = false
			_update_cursor_shape()
			return
		var object_name := str(hovered_object.get("name", hover_object_id)).strip_edges()
		var object_type := str(hovered_object.get("type", "object")).strip_edges().to_upper()
		tooltip_label.text = "%s (%s)\n%s" % [object_name if not object_name.is_empty() else hover_object_id, object_type, hover_object_id]
		tooltip_label.position = position + Vector2(14.0, 14.0)
		tooltip_label.visible = true
		_update_cursor_shape()
		return
	var hovered_room = _room_at_position(position)
	hover_room_id = "" if hovered_room == null else str(hovered_room)
	if tooltip_label == null:
		return
	if hover_room_id.is_empty() or panning:
		tooltip_label.visible = false
		_update_cursor_shape()
		return
	var room_node := _find_room(hover_room_id)
	if room_node == null:
		tooltip_label.visible = false
		_update_cursor_shape()
		return
	tooltip_label.text = "%s\n%s" % [room_node.name, room_node.room_id]
	tooltip_label.position = position + Vector2(14.0, 14.0)
	tooltip_label.visible = true
	_update_cursor_shape()


func _update_cursor_shape() -> void:
	if not builder_enabled:
		mouse_default_cursor_shape = Control.CURSOR_ARROW
		return
	if panning:
		mouse_default_cursor_shape = Control.CURSOR_DRAG
		return
	if draw_exit_mode:
		mouse_default_cursor_shape = Control.CURSOR_CROSS
		return
	if create_room_mode:
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		return
	if not hover_object_id.is_empty():
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		return
	if not hover_room_id.is_empty() or _edge_at_position(get_local_mouse_position()) >= 0:
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		return
	mouse_default_cursor_shape = Control.CURSOR_ARROW


func _zoom_map(multiplier: float) -> void:
	zoom_level = clampf(zoom_level * multiplier, MIN_ZOOM, MAX_ZOOM)
	_update_view_transform()
	queue_redraw()


func reset_zoom() -> void:
	zoom_level = 1.0
	pan_offset = Vector2.ZERO
	_update_view_transform()
	queue_redraw()


func center() -> void:
	pan_offset = Vector2.ZERO
	_update_view_transform()
	queue_redraw()


func _resolve_drop_target(local_position: Vector2, dragged_object_id: String) -> Dictionary:
	for object_id in object_nodes.keys():
		if object_id == dragged_object_id:
			continue
		var node = object_nodes[object_id]
		if node != null and node.contains_local_point(local_position):
			return {
				"destination_id": str(node.object_id),
				"relation": "on" if bool(node.is_surface) else "in",
				"room_id": str(node.room_id),
			}
	var room_id = _room_at_position(local_position)
	if room_id == null:
		return {}
	var room_node := _find_room(str(room_id))
	if room_node == null:
		return {}
	return {
		"destination_id": str(room_node.object_id),
		"relation": "in",
		"room_id": str(room_node.room_id),
	}


func _default_relation_for_object(object_data: Dictionary) -> String:
	if bool(object_data.get("is_surface", false)):
		return "on"
	return "in"


func _get_room_color(room_node: RoomNode) -> Color:
	return BuilderVisuals.get_room_color(room_node.room_type, room_node.tags)


func _should_draw_room_label(room_node: RoomNode) -> bool:
	if rooms.size() <= 40:
		return true
	if room_draw_size.x >= 20.0:
		return true
	return room_node.room_id == selected_room_id or room_node.room_id == hover_room_id or conflict_room_ids.has(room_node.room_id)


func _draw_debug_overlay() -> void:
	var font = ThemeDB.fallback_font
	if font == null:
		return
	var overlay_text := "rooms=%d npcs=%d visible=%s" % [rooms.size(), npc_nodes.size(), str(visible)]
	draw_string(font, Vector2(8.0, 18.0), overlay_text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, 12, Color.WHITE)


func _update_view_transform() -> void:
	if rooms.is_empty():
		map_min = Vector2.ZERO
		map_max = Vector2.ZERO
		map_scale = CELL_SIZE
		map_offset = GRID_PADDING
		last_transform_signature = ""
		return

	var min_x := float(rooms[0].x)
	var max_x := float(rooms[0].x)
	var min_y := float(rooms[0].y)
	var max_y := float(rooms[0].y)
	for room_node in rooms:
		min_x = minf(min_x, float(room_node.x))
		max_x = maxf(max_x, float(room_node.x))
		min_y = minf(min_y, float(room_node.y))
		max_y = maxf(max_y, float(room_node.y))

	map_min = Vector2(min_x, min_y)
	map_max = Vector2(max_x, max_y)

	var available := size - (GRID_PADDING * 2.0)
	var bounds := Vector2(maxf(map_max.x - map_min.x, 1.0), maxf(map_max.y - map_min.y, 1.0))
	if available.x <= 0.0 or available.y <= 0.0:
		map_scale = 1.0
		map_offset = GRID_PADDING
		return

	map_scale = minf(available.x / bounds.x, available.y / bounds.y)
	map_scale = clampf(map_scale, 0.05, CELL_SIZE)
	map_scale *= zoom_level
	var room_pixel_size := clampf(map_scale * 18.0, MIN_ROOM_PIXEL_SIZE, MAX_ROOM_PIXEL_SIZE)
	room_draw_size = Vector2(room_pixel_size, room_pixel_size)
	object_draw_scale = clampf(room_pixel_size / 24.0, 0.4, 0.9)

	var occupied := bounds * map_scale
	map_offset = GRID_PADDING + ((available - occupied) / 2.0) + pan_offset
	var transform_signature := "%s|%s|%s|%s" % [str(map_scale), str(map_offset), str(room_draw_size), str(zoom_level)]
	if transform_signature == last_transform_signature:
		return
	last_transform_signature = transform_signature
	for room_node in rooms:
		room_nodes[room_node.room_id] = {
			"room_id": room_node.room_id,
			"object_id": room_node.object_id,
			"position": _room_position(room_node),
		}
	if not last_map_data.is_empty():
		update_room_objects(last_map_data)
		update_npcs(last_map_data)