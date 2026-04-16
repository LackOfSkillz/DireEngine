extends Control


signal item_action(item_name)


func _ready() -> void:
	_apply_item_list_theme()
	$ItemList.item_selected.connect(_on_item_list_item_selected)
	$ItemList.item_activated.connect(_on_item_list_item_activated)


func _apply_item_list_theme() -> void:
	var item_list := $ItemList
	item_list.theme = null
	item_list.focus_mode = Control.FOCUS_ALL

	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color("#2a1e14")
	panel_style.border_color = Color("#8a6a4a")
	panel_style.border_width_left = 1
	panel_style.border_width_top = 1
	panel_style.border_width_right = 1
	panel_style.border_width_bottom = 1
	panel_style.corner_radius_top_left = 8
	panel_style.corner_radius_top_right = 8
	panel_style.corner_radius_bottom_right = 8
	panel_style.corner_radius_bottom_left = 8

	var selected_style := StyleBoxFlat.new()
	selected_style.bg_color = Color("#6c4d31")
	selected_style.border_color = Color("#d9b37a")
	selected_style.border_width_left = 1
	selected_style.border_width_top = 1
	selected_style.border_width_right = 1
	selected_style.border_width_bottom = 1
	selected_style.corner_radius_top_left = 6
	selected_style.corner_radius_top_right = 6
	selected_style.corner_radius_bottom_right = 6
	selected_style.corner_radius_bottom_left = 6

	var unfocused_selected_style := selected_style.duplicate()
	unfocused_selected_style.bg_color = Color("#4b3523")
	unfocused_selected_style.border_color = Color("#a68457")

	item_list.add_theme_stylebox_override("panel", panel_style)
	item_list.add_theme_stylebox_override("cursor", selected_style)
	item_list.add_theme_stylebox_override("cursor_unfocused", unfocused_selected_style)
	item_list.add_theme_color_override("font_color", Color("#f5e6d3"))
	item_list.add_theme_color_override("font_hovered_color", Color("#fff3e6"))
	item_list.add_theme_color_override("font_selected_color", Color("#fff7ef"))
	item_list.add_theme_color_override("guide_color", Color("#8a6a4a"))


func update_inventory(items: Array) -> void:
	$ItemList.clear()
	for item in items:
		$ItemList.add_item(str(item))


func _on_item_list_item_selected(index: int) -> void:
	print("Selected:", $ItemList.get_item_text(index))


func _on_item_list_item_activated(index: int) -> void:
	emit_signal("item_action", $ItemList.get_item_text(index))


func get_drag_data(position: Vector2):
	var local_position: Vector2 = position - $ItemList.position
	var index: int = $ItemList.get_item_at_position(local_position, true)
	if index < 0:
		return null

	var item_name: String = $ItemList.get_item_text(index)
	var preview := Label.new()
	preview.text = item_name
	preview.add_theme_color_override("font_color", Color("#fff7ef"))
	set_drag_preview(preview)
	return {"item": item_name}