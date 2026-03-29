extends Control


signal item_action(item_name)


func _ready() -> void:
	$ItemList.item_selected.connect(_on_item_list_item_selected)
	$ItemList.item_activated.connect(_on_item_list_item_activated)


func update_inventory(items: Array) -> void:
	$ItemList.clear()
	for item in items:
		$ItemList.add_item(str(item))


func _on_item_list_item_selected(index: int) -> void:
	print("Selected:", $ItemList.get_item_text(index))


func _on_item_list_item_activated(index: int) -> void:
	emit_signal("item_action", $ItemList.get_item_text(index))


func get_drag_data(position: Vector2):
	var local_position := position - $ItemList.position
	var index := $ItemList.get_item_at_position(local_position, true)
	if index < 0:
		return null

	var item_name := $ItemList.get_item_text(index)
	var preview := Label.new()
	preview.text = item_name
	set_drag_preview(preview)
	return {"item": item_name}