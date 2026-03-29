extends Control


signal hotbar_action(action)


var slots: Array = []
var cooldowns := {}


func _ready() -> void:
	var button_count := $HBoxContainer.get_child_count()
	slots.resize(button_count)
	for index in range(button_count):
		var button = $HBoxContainer.get_child(index)
		button.pressed.connect(func(): _on_button_pressed(index))
	refresh_buttons()


func _process(delta: float) -> void:
	var dirty := false
	for action in cooldowns.keys():
		var next_value = max(0.0, float(cooldowns[action]) - delta)
		if next_value != cooldowns[action]:
			cooldowns[action] = next_value
			dirty = true
	if dirty:
		refresh_buttons()


func set_slot(index: int, action: String) -> void:
	if index < 0 or index >= slots.size():
		return
	slots[index] = action
	refresh_buttons()


func refresh_buttons() -> void:
	for index in range($HBoxContainer.get_child_count()):
		var button = $HBoxContainer.get_child(index)
		var action = slots[index]
		if action == null:
			action = ""
		button.text = _button_text(str(action))
		button.tooltip_text = str(action)


func can_drop_data(_position: Vector2, data) -> bool:
	return data is Dictionary and data.has("item")


func drop_data(position: Vector2, data) -> void:
	set_slot(get_slot_index(position), str(data["item"]))


func get_slot_index(position: Vector2) -> int:
	var local_position := position - $HBoxContainer.position
	for index in range($HBoxContainer.get_child_count()):
		var button = $HBoxContainer.get_child(index)
		var button_rect := Rect2(button.position, button.size)
		if button_rect.has_point(local_position):
			return index
	return 0


func _on_button_pressed(index: int) -> void:
	var action = str(slots[index])
	if action.is_empty():
		return
	if float(cooldowns.get(action, 0.0)) > 0.0:
		return
	var button = $HBoxContainer.get_child(index)
	button.modulate = Color(1.0, 1.0, 0.0)
	emit_signal("hotbar_action", action)


func _button_text(action: String) -> String:
	if action.is_empty():
		return "-"
	var cooldown = float(cooldowns.get(action, 0.0))
	if cooldown > 0.0:
		return "%s (%.0f)" % [action, cooldown]
	return action