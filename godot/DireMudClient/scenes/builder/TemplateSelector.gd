extends PanelContainer


signal template_chosen(template_id, destination_id, template_type, destination_kind)
signal closed()


var builder_api: Node
var current_type: String = ""
var current_room_id: String = ""
var current_room_object_id: String = ""
var current_npc_object_id: String = ""
var current_npc_name: String = ""
var selected_template_id: String = ""
var selected_destination_kind := "room"
var templates: Array[Dictionary] = []
var filtered_templates: Array[Dictionary] = []
var result_ids: Array[String] = []


@onready var title_label: Label = $Margin/VBoxContainer/Title
@onready var search_input: LineEdit = $Margin/VBoxContainer/Search
@onready var destination_header: Label = $Margin/VBoxContainer/DestinationHeader
@onready var destination_row: HBoxContainer = $Margin/VBoxContainer/DestinationRow
@onready var room_button: Button = $Margin/VBoxContainer/DestinationRow/AddToRoom
@onready var npc_button: Button = $Margin/VBoxContainer/DestinationRow/AddToNpc
@onready var results_list: ItemList = $Margin/VBoxContainer/Results
@onready var select_label: Label = $Margin/VBoxContainer/SelectedDestination
@onready var select_button: Button = $Margin/VBoxContainer/Select
@onready var message_label: Label = $Margin/VBoxContainer/Message


func _ready() -> void:
	search_input.text_changed.connect(_on_search_changed)
	room_button.pressed.connect(_on_room_destination_pressed)
	npc_button.pressed.connect(_on_npc_destination_pressed)
	results_list.item_selected.connect(_on_item_selected)
	select_button.pressed.connect(_on_select_pressed)
	$Margin/VBoxContainer/Close.pressed.connect(_on_close_pressed)
	visible = false
	select_button.disabled = true


func configure_api(api: Node) -> void:
	builder_api = api


func open(template_type: String, room_id: String, room_object_id: String, npc_object_id: String = "", npc_name: String = "") -> void:
	current_type = template_type.strip_edges().to_lower()
	current_room_id = room_id.strip_edges()
	current_room_object_id = room_object_id.strip_edges()
	current_npc_object_id = npc_object_id.strip_edges()
	current_npc_name = npc_name.strip_edges()
	selected_template_id = ""
	templates.clear()
	filtered_templates.clear()
	message_label.text = ""
	search_input.text = ""
	selected_destination_kind = "npc" if current_type == "item" and not current_npc_object_id.is_empty() else "room"
	select_button.disabled = true
	_title_for_mode()
	_update_destination_controls()
	visible = true
	await _load_templates()


func load_results(results: Array) -> void:
	templates.clear()
	for template in results:
		if template is Dictionary:
			templates.append((template as Dictionary).duplicate(true))
	_apply_filter(search_input.text)


func _apply_filter(query: String) -> void:
	results_list.clear()
	filtered_templates.clear()
	result_ids.clear()
	selected_template_id = ""
	select_button.disabled = true
	var normalized_query := query.strip_edges().to_lower()
	for template in templates:
		var template_id := str(template.get("template_id", "")).strip_edges()
		var template_name := str(template.get("name", template_id)).strip_edges()
		var haystack := "%s %s" % [template_name.to_lower(), template_id.to_lower()]
		if not normalized_query.is_empty() and haystack.find(normalized_query) < 0:
			continue
		filtered_templates.append(template.duplicate(true))
		result_ids.append(template_id)
		results_list.add_item(template_name if not template_name.is_empty() else template_id)
	if filtered_templates.is_empty():
		show_message("No templates found")
	else:
		message_label.text = "%d templates" % filtered_templates.size()


func show_message(message: String) -> void:
	message_label.text = message


func _load_templates() -> void:
	if builder_api == null:
		show_message("Builder API unavailable")
		return
	var response: Dictionary = await builder_api.list_npcs() if current_type == "npc" else await builder_api.list_items()
	if not bool(response.get("ok", false)):
		show_message(str(response.get("error", "Template library failed")))
		return
	var templates: Variant = response.get("result", {}).get("templates", response.get("result", []))
	if templates is Array:
		load_results(templates)
	else:
		load_results([])


func _on_search_changed(new_text: String) -> void:
	_apply_filter(new_text)


func _on_item_selected(index: int) -> void:
	if index < 0 or index >= result_ids.size():
		selected_template_id = ""
		select_button.disabled = true
		return
	selected_template_id = result_ids[index]
	select_button.disabled = false


func _on_select_pressed() -> void:
	if selected_template_id.is_empty():
		return
	var destination_id := current_room_object_id
	if selected_destination_kind == "npc" and not current_npc_object_id.is_empty():
		destination_id = current_npc_object_id
	if destination_id.is_empty():
		show_message("Choose a valid destination first")
		return
	emit_signal("template_chosen", selected_template_id, destination_id, current_type, selected_destination_kind)
	visible = false


func _on_close_pressed() -> void:
	visible = false
	emit_signal("closed")


func _title_for_mode() -> void:
	title_label.text = "NPC Library" if current_type == "npc" else "Item Library"
	search_input.placeholder_text = "Search NPC templates" if current_type == "npc" else "Search item templates"
	select_button.text = "Spawn NPC" if current_type == "npc" else "Add Item"


func _update_destination_controls() -> void:
	var item_mode := current_type == "item"
	var has_npc_target := item_mode and not current_npc_object_id.is_empty()
	destination_header.visible = item_mode
	destination_row.visible = item_mode
	room_button.visible = item_mode
	npc_button.visible = has_npc_target
	room_button.button_pressed = selected_destination_kind == "room"
	npc_button.button_pressed = selected_destination_kind == "npc" and has_npc_target
	if not item_mode:
		select_label.text = "Destination: selected room"
		return
	if selected_destination_kind == "npc" and has_npc_target:
		select_label.text = "Destination: %s" % (current_npc_name if not current_npc_name.is_empty() else "selected NPC")
	else:
		selected_destination_kind = "room"
		select_label.text = "Destination: selected room"


func _on_room_destination_pressed() -> void:
	selected_destination_kind = "room"
	_update_destination_controls()


func _on_npc_destination_pressed() -> void:
	if current_npc_object_id.is_empty():
		return
	selected_destination_kind = "npc"
	_update_destination_controls()