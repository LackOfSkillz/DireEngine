extends PanelContainer


signal save_requested(object_id, fields)
signal edit_template_requested(template_id, object_type)
signal delete_requested(object_id)
signal back_requested()


const ITEM_KIND_OPTIONS := ["item", "weapon", "container", "vendor"]


var current_object_id := ""
var current_room_id := ""
var current_mode := "item"
var current_template_id := ""


@onready var title_label: Label = $Margin/VBox/Title
@onready var subtitle_label: Label = $Margin/VBox/SubTitle
@onready var name_input: LineEdit = $Margin/VBox/IdentitySection/Margin/VBox/NameInput
@onready var description_input: TextEdit = $Margin/VBox/IdentitySection/Margin/VBox/DescriptionInput
@onready var npc_section: PanelContainer = $Margin/VBox/NpcSection
@onready var str_input: SpinBox = $Margin/VBox/NpcSection/Margin/VBox/StatsGrid/StrInput
@onready var dex_input: SpinBox = $Margin/VBox/NpcSection/Margin/VBox/StatsGrid/DexInput
@onready var con_input: SpinBox = $Margin/VBox/NpcSection/Margin/VBox/StatsGrid/ConInput
@onready var aggressive_toggle: CheckButton = $Margin/VBox/NpcSection/Margin/VBox/FlagsRow/AggressiveToggle
@onready var patrol_toggle: CheckButton = $Margin/VBox/NpcSection/Margin/VBox/FlagsRow/PatrolToggle
@onready var item_section: PanelContainer = $Margin/VBox/ItemSection
@onready var item_kind_input: OptionButton = $Margin/VBox/ItemSection/Margin/VBox/TypeRow/TypeInput
@onready var weight_input: SpinBox = $Margin/VBox/ItemSection/Margin/VBox/PropertiesGrid/WeightInput
@onready var value_input: SpinBox = $Margin/VBox/ItemSection/Margin/VBox/PropertiesGrid/ValueInput
@onready var inventory_list: ItemList = $Margin/VBox/InventorySection/Margin/VBox/InventoryList
@onready var edit_template_button: Button = $Margin/VBox/ButtonRow/EditTemplateButton


func _ready() -> void:
	$Margin/VBox/ButtonRow/SaveButton.pressed.connect(_on_save_pressed)
	edit_template_button.pressed.connect(_on_edit_template_pressed)
	$Margin/VBox/ButtonRow/BackButton.pressed.connect(_on_back_pressed)
	$Margin/VBox/ButtonRow/DeleteButton.pressed.connect(_on_delete_pressed)
	description_input.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	item_kind_input.clear()
	for item_kind in ITEM_KIND_OPTIONS:
		item_kind_input.add_item(item_kind.capitalize())
	clear_editor()


func clear_editor() -> void:
	current_object_id = ""
	current_room_id = ""
	current_mode = "item"
	current_template_id = ""
	title_label.text = "No object selected"
	subtitle_label.text = ""
	name_input.text = ""
	description_input.text = ""
	str_input.value = 10
	dex_input.value = 10
	con_input.value = 10
	aggressive_toggle.button_pressed = false
	patrol_toggle.button_pressed = false
	weight_input.value = 0
	value_input.value = 0
	item_kind_input.select(0)
	inventory_list.clear()
	edit_template_button.disabled = true
	visible = false


func load_object(object_data: Dictionary, room_id: String = "") -> void:
	current_object_id = str(object_data.get("object_id", object_data.get("id", ""))).strip_edges()
	current_room_id = room_id.strip_edges()
	current_mode = "npc" if str(object_data.get("type", "item")).strip_edges().to_lower() == "npc" else "item"
	current_template_id = str(object_data.get("template_id", "")).strip_edges()
	_set_mode(current_mode)
	title_label.text = "Selected %s" % ("NPC" if current_mode == "npc" else "Item")
	subtitle_label.text = str(object_data.get("name", current_object_id)).strip_edges()
	name_input.text = str(object_data.get("name", ""))
	description_input.text = str(object_data.get("description", ""))
	var attributes: Dictionary = (object_data.get("attributes", {}) as Dictionary).duplicate(true)
	str_input.value = float(attributes.get("str", 10))
	dex_input.value = float(attributes.get("dex", 10))
	con_input.value = float(attributes.get("con", 10))
	var flags := {}
	for raw_flag in object_data.get("flags", []):
		flags[str(raw_flag).strip_edges().to_lower()] = true
	aggressive_toggle.button_pressed = bool(flags.get("aggressive", false))
	patrol_toggle.button_pressed = bool(flags.get("patrol", false))
	weight_input.value = float(object_data.get("weight", 0.0))
	value_input.value = float(object_data.get("value", 0.0))
	_select_item_kind(str(object_data.get("item_kind", object_data.get("type", "item"))).strip_edges().to_lower())
	_rebuild_inventory(object_data)
	edit_template_button.disabled = current_template_id.is_empty()
	visible = true


func _set_mode(mode: String) -> void:
	current_mode = mode.strip_edges().to_lower()
	npc_section.visible = current_mode == "npc"
	item_section.visible = current_mode != "npc"


func _select_item_kind(item_kind: String) -> void:
	var normalized_item_kind := item_kind.strip_edges().to_lower()
	var selected_index := 0
	for index in range(ITEM_KIND_OPTIONS.size()):
		if ITEM_KIND_OPTIONS[index] == normalized_item_kind:
			selected_index = index
			break
	item_kind_input.select(selected_index)


func _selected_item_kind() -> String:
	var selected_index := item_kind_input.get_selected_id()
	if selected_index >= 0 and selected_index < ITEM_KIND_OPTIONS.size():
		return ITEM_KIND_OPTIONS[selected_index]
	return "item"


func _rebuild_inventory(object_data: Dictionary) -> void:
	inventory_list.clear()
	for child in object_data.get("contents", []):
		if not child is Dictionary:
			continue
		var child_data := child as Dictionary
		var child_name := str(child_data.get("name", child_data.get("object_id", child_data.get("id", "Object")))).strip_edges()
		inventory_list.add_item(child_name if not child_name.is_empty() else "Object")


func _build_fields() -> Dictionary:
	var fields := {
		"name": name_input.text.strip_edges(),
		"description": description_input.text,
	}
	if current_mode == "npc":
		fields["attributes"] = {
			"str": int(str_input.value),
			"dex": int(dex_input.value),
			"con": int(con_input.value),
		}
		var flags: Array[String] = []
		if aggressive_toggle.button_pressed:
			flags.append("aggressive")
		if patrol_toggle.button_pressed:
			flags.append("patrol")
		fields["flags"] = flags
	else:
		fields["item_kind"] = _selected_item_kind()
		fields["weight"] = float(weight_input.value)
		fields["value"] = float(value_input.value)
	return fields


func _on_save_pressed() -> void:
	if current_object_id.is_empty():
		return
	if name_input.text.strip_edges().is_empty():
		return
	emit_signal("save_requested", current_object_id, _build_fields())


func _on_edit_template_pressed() -> void:
	if current_template_id.is_empty():
		return
	emit_signal("edit_template_requested", current_template_id, current_mode)


func _on_delete_pressed() -> void:
	if current_object_id.is_empty():
		return
	emit_signal("delete_requested", current_object_id)


func _on_back_pressed() -> void:
	emit_signal("back_requested")