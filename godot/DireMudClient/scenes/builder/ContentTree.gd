extends PanelContainer


signal object_selected(object_id, object_data)
signal delete_requested(object_id)


var item_to_object_id := {}
var item_to_payload := {}
var current_room_id := ""


@onready var object_name_label: Label = $Margin/VBoxContainer/ObjectNameLabel
@onready var object_type_label: Label = $Margin/VBoxContainer/ObjectTypeLabel
@onready var object_location_label: Label = $Margin/VBoxContainer/ObjectLocationLabel
@onready var tree: Tree = $Margin/VBoxContainer/Tree
@onready var move_in_button: Button = $Margin/VBoxContainer/Buttons/MoveIn
@onready var move_on_button: Button = $Margin/VBoxContainer/Buttons/MoveOn
@onready var delete_button: Button = $Margin/VBoxContainer/Buttons/Delete


func _ready() -> void:
	tree.hide_root = true
	tree.item_selected.connect(_on_item_selected)
	delete_button.pressed.connect(_on_delete_pressed)
	move_in_button.pressed.connect(_on_move_in_pressed)
	move_on_button.pressed.connect(_on_move_on_pressed)
	_clear_details()
	visible = false


func build_tree(room: Dictionary) -> void:
	visible = true
	current_room_id = str(room.get("id", "")).strip_edges()
	item_to_object_id.clear()
	item_to_payload.clear()
	tree.clear()
	var root := tree.create_item()
	for obj in room.get("contents", []):
		if obj is Dictionary:
			add_node(obj, root)


func rebuild(room: Dictionary) -> void:
	build_tree(room)


func clear_tree() -> void:
	item_to_object_id.clear()
	item_to_payload.clear()
	current_room_id = ""
	tree.clear()
	move_in_button.disabled = true
	move_on_button.disabled = true
	_clear_details()


func add_node(obj: Dictionary, parent = null) -> void:
	var item = tree.create_item(parent)
	item.set_text(0, str(obj.get("name", obj.get("id", "Object"))))
	item_to_object_id[item] = str(obj.get("object_id", obj.get("id", "")))
	item_to_payload[item] = obj.duplicate(true)
	for child in obj.get("contents", []):
		if child is Dictionary:
			add_node(child, item)


func select_object(object_id: String) -> void:
	var normalized_object_id := object_id.strip_edges()
	if normalized_object_id.is_empty():
		_clear_details()
		return
	var item: TreeItem = _find_item_by_object_id(tree.get_root(), normalized_object_id)
	if item != null:
		tree.set_selected(item, 0)
		_on_item_selected()


func _find_item_by_object_id(item: TreeItem, object_id: String):
	if item == null:
		return null
	if str(item_to_object_id.get(item, "")) == object_id:
		return item
	var child: TreeItem = item.get_first_child()
	while child != null:
		var match: TreeItem = _find_item_by_object_id(child, object_id)
		if match != null:
			return match
		child = child.get_next()
	return null


func get_selected_object_id() -> String:
	var selected := tree.get_selected()
	if selected == null:
		return ""
	return str(item_to_object_id.get(selected, ""))


func _get_selected_object_data() -> Dictionary:
	var selected := tree.get_selected()
	if selected == null:
		return {}
	var payload = item_to_payload.get(selected, {})
	return payload.duplicate(true) if payload is Dictionary else {}


func _on_item_selected() -> void:
	var object_id := get_selected_object_id()
	if object_id.is_empty():
		move_in_button.disabled = true
		move_on_button.disabled = true
		_clear_details()
		return
	var object_data := _get_selected_object_data()
	move_in_button.disabled = false
	move_on_button.disabled = not bool(object_data.get("is_surface", false))
	object_name_label.text = "Object: %s" % str(object_data.get("name", object_id))
	object_type_label.text = "Type: %s" % str(object_data.get("type", "item"))
	object_location_label.text = "Location: %s" % str(object_data.get("room_id", current_room_id))
	emit_signal("object_selected", object_id, object_data)


func _clear_details() -> void:
	object_name_label.text = "Object:"
	object_type_label.text = "Type:"
	object_location_label.text = "Location:"


func _on_delete_pressed() -> void:
	var object_id := get_selected_object_id()
	if object_id.is_empty():
		return
	emit_signal("delete_requested", object_id)


func _on_move_in_pressed() -> void:
	var object_id := get_selected_object_id()
	if object_id.is_empty():
		return
	emit_signal("object_selected", object_id, _get_selected_object_data())


func _on_move_on_pressed() -> void:
	var object_id := get_selected_object_id()
	var object_data := _get_selected_object_data()
	if object_id.is_empty():
		return
	if not bool(object_data.get("is_surface", false)):
		return
	emit_signal("object_selected", object_id, object_data)