extends Control


signal equip_item(item_name)


func _style_dynamic_label(label: Label) -> void:
	label.add_theme_color_override("font_color", Color("#f5e6d3"))


func update_character(data: Dictionary) -> void:
	$NameLabel.text = str(data.get("name", "Unknown"))

	var max_hp = max(1.0, float(data.get("max_hp", 100)))
	var hp = clamp(float(data.get("hp", max_hp)), 0.0, max_hp)
	$HPBar.max_value = max_hp
	$HPBar.value = hp
	$HPBar.modulate = Color(0.9, 0.2, 0.2) if (hp / max_hp) < 0.3 else Color(0.2, 0.85, 0.3)

	var max_stamina = max(1.0, float(data.get("max_stamina", 100)))
	var stamina = clamp(float(data.get("stamina", max_stamina)), 0.0, max_stamina)
	$StaminaBar.max_value = max_stamina
	$StaminaBar.value = stamina
	$StaminaBar.modulate = Color(0.95, 0.8, 0.2)


func update_equipment(data: Dictionary) -> void:
	for child in $EquipmentList.get_children():
		child.queue_free()
	for slot in data.keys():
		var label := Label.new()
		label.text = "%s: %s" % [slot, str(data[slot])]
		_style_dynamic_label(label)
		$EquipmentList.add_child(label)


func update_status(status_list: Array) -> void:
	for child in $StatusList.get_children():
		child.queue_free()
	for status in status_list:
		var label := Label.new()
		label.text = str(status)
		_style_dynamic_label(label)
		$StatusList.add_child(label)


func flash_damage() -> void:
	$HPBar.modulate = Color(1.0, 0.2, 0.2)


func can_drop_data(_position: Vector2, data) -> bool:
	return data is Dictionary and data.has("item")


func drop_data(_position: Vector2, data) -> void:
	emit_signal("equip_item", str(data["item"]))