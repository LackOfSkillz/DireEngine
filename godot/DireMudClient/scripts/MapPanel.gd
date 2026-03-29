extends Control


signal room_clicked(room_id)


var rooms: Array = []
var edges: Array = []
var pois: Array = []
var room_positions := {}
var adjacency := {}
var player_room_id = null
var hovered_room_id = null
var offset := Vector2.ZERO
var target_offset := Vector2.ZERO
var zoom := 1.0


func render_map(data: Dictionary) -> void:
	rooms = data.get("rooms", [])
	edges = data.get("edges", [])
	pois = data.get("poi", [])
	player_room_id = data.get("player_room_id")
	build_adjacency()
	center_on_player()
	queue_redraw()


func _draw() -> void:
	room_positions.clear()

	for room in rooms:
		var pos := _room_screen_position(room)
		room_positions[room.get("id")] = pos

	for edge in edges:
		var from_pos = room_positions.get(edge.get("from"))
		var to_pos = room_positions.get(edge.get("to"))
		if from_pos != null and to_pos != null:
			draw_line(from_pos, to_pos, Color(0.45, 0.45, 0.45), 2.0)

	for edge in edges:
		if edge.get("from") == player_room_id:
			var reachable_pos = room_positions.get(edge.get("to"))
			if reachable_pos != null:
				draw_circle(reachable_pos, 10.0, Color(0.95, 0.85, 0.2, 0.25))

	for room in rooms:
		var pos = room_positions.get(room.get("id"), size / 2.0)
		var is_player := bool(room.get("is_player", false))
		var color := _room_color(room, is_player)
		var radius := 6.0 if not is_player else 8.0
		if room.get("id") == hovered_room_id:
			draw_circle(pos, radius + 4.0, Color(1.0, 1.0, 1.0, 0.35))
		draw_circle(pos, radius, color)

	for poi in pois:
		var poi_pos = room_positions.get(poi.get("room_id"))
		if poi_pos != null:
			draw_rect(Rect2(poi_pos - Vector2(4, 4), Vector2(8, 8)), Color(0.2, 0.55, 0.95))


func _process(delta: float) -> void:
	offset = offset.lerp(target_offset, min(1.0, delta * 8.0))
	update_tooltip()
	queue_redraw()


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		hovered_room_id = _room_at_position(event.position)
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var clicked_room = _room_at_position(event.position)
		if clicked_room != null:
			emit_signal("room_clicked", clicked_room)


func _input(event: InputEvent) -> void:
	if not get_global_rect().has_point(get_global_mouse_position()):
		return
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			zoom = clamp(zoom * 1.1, 0.5, 3.0)
			center_on_player()
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			zoom = clamp(zoom * 0.9, 0.5, 3.0)
			center_on_player()


func build_adjacency() -> void:
	adjacency.clear()
	for edge in edges:
		var source = edge.get("from")
		if not adjacency.has(source):
			adjacency[source] = []
		adjacency[source].append(edge)


func get_direction_to(room_id: int):
	if not adjacency.has(player_room_id):
		return null
	for edge in adjacency[player_room_id]:
		if edge.get("to") == room_id:
			return edge.get("dir")
	return null


func center_on_player() -> void:
	var player_room = _room_by_id(player_room_id)
	if player_room.is_empty():
		return
	target_offset = (size / 2.0) - _room_world_position(player_room)


func update_tooltip() -> void:
	var tooltip = $Tooltip
	if hovered_room_id == null:
		tooltip.visible = false
		return
	var room = _room_by_id(hovered_room_id)
	if room.is_empty():
		tooltip.visible = false
		return
	tooltip.text = str(room.get("name", hovered_room_id))
	tooltip.position = room_positions.get(hovered_room_id, Vector2.ZERO) + Vector2(12, -28)
	tooltip.visible = true


func _room_world_position(room: Dictionary) -> Vector2:
	return Vector2(float(room.get("x", 0)), float(room.get("y", 0))) * 40.0 * zoom


func _room_screen_position(room: Dictionary) -> Vector2:
	return _room_world_position(room) + offset


func _room_at_position(position: Vector2):
	for room_id in room_positions:
		if room_positions[room_id].distance_to(position) < 12.0:
			return room_id
	return null


func _room_by_id(room_id) -> Dictionary:
	for room in rooms:
		if room.get("id") == room_id:
			return room
	return {}


func _room_color(room: Dictionary, is_player: bool) -> Color:
	if is_player:
		return Color(0.9, 0.2, 0.2)
	match room.get("type", ""):
		"shop":
			return Color(0.2, 0.55, 0.95)
		"guild":
			return Color(0.7, 0.3, 0.95)
		_:
			return Color(0.2, 0.8, 0.35)


func _get_minimum_size() -> Vector2:
	return Vector2(320, 320)