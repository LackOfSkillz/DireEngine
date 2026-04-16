extends PanelContainer


signal close_requested()


@export var template_type := "npc"


var builder_api: Node
var templates: Array[Dictionary] = []
var filtered_templates: Array[Dictionary] = []
var result_ids: Array[String] = []
var selected_template_id := ""
var create_mode := false


@onready var title_label: Label = $Margin/VBox/Title
@onready var search_input: LineEdit = $Margin/VBox/Search
@onready var results_list: ItemList = $Margin/VBox/ResultsSection/Margin/VBox/Results
@onready var empty_state_label: Label = $Margin/VBox/ResultsSection/Margin/VBox/EmptyState
@onready var template_id_input: LineEdit = $Margin/VBox/EditorSection/Scroll/Margin/VBox/TemplateIdInput
@onready var name_input: LineEdit = $Margin/VBox/EditorSection/Scroll/Margin/VBox/NameInput
@onready var description_input: TextEdit = $Margin/VBox/EditorSection/Scroll/Margin/VBox/DescriptionInput
@onready var tags_input: LineEdit = $Margin/VBox/EditorSection/Scroll/Margin/VBox/TagsInput
@onready var npc_section: PanelContainer = $Margin/VBox/EditorSection/Scroll/Margin/VBox/NpcSection
@onready var str_input: SpinBox = $Margin/VBox/EditorSection/Scroll/Margin/VBox/NpcSection/Margin/VBox/StatsGrid/StrInput
@onready var dex_input: SpinBox = $Margin/VBox/EditorSection/Scroll/Margin/VBox/NpcSection/Margin/VBox/StatsGrid/DexInput
@onready var con_input: SpinBox = $Margin/VBox/EditorSection/Scroll/Margin/VBox/NpcSection/Margin/VBox/StatsGrid/ConInput
@onready var aggressive_toggle: CheckButton = $Margin/VBox/EditorSection/Scroll/Margin/VBox/NpcSection/Margin/VBox/FlagsRow/AggressiveToggle
@onready var patrol_toggle: CheckButton = $Margin/VBox/EditorSection/Scroll/Margin/VBox/NpcSection/Margin/VBox/FlagsRow/PatrolToggle
@onready var item_section: PanelContainer = $Margin/VBox/EditorSection/Scroll/Margin/VBox/ItemSection
@onready var item_kind_input: OptionButton = $Margin/VBox/EditorSection/Scroll/Margin/VBox/ItemSection/Margin/VBox/TypeRow/TypeInput
@onready var weight_input: SpinBox = $Margin/VBox/EditorSection/Scroll/Margin/VBox/ItemSection/Margin/VBox/PropertiesGrid/WeightInput
@onready var value_input: SpinBox = $Margin/VBox/EditorSection/Scroll/Margin/VBox/ItemSection/Margin/VBox/PropertiesGrid/ValueInput
@onready var message_label: Label = $Margin/VBox/Message


func _ready() -> void:
	search_input.text_changed.connect(_on_search_changed)
	results_list.item_selected.connect(_on_result_selected)
	$FloatingBackButton.pressed.connect(_on_close_pressed)
	$Margin/VBox/TopButtonRow/BackButton.pressed.connect(_on_close_pressed)
	$Margin/VBox/ButtonRow/NewButton.pressed.connect(_on_new_pressed)
	$Margin/VBox/ButtonRow/SaveButton.pressed.connect(_on_save_pressed)
	$Margin/VBox/ButtonRow/CloseButton.pressed.connect(_on_close_pressed)
	description_input.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	item_kind_input.clear()
	for item_kind in ["item", "weapon", "container", "vendor"]:
		item_kind_input.add_item(item_kind.capitalize())
	_clear_form(true)
	visible = false


func configure_api(api: Node) -> void:
	builder_api = api


func open_workspace(preferred_template_id: String = "") -> void:
	visible = true
	await refresh_workspace(preferred_template_id)


func refresh_workspace(preferred_template_id: String = "") -> void:
	_title_for_mode()
	_set_mode(template_type)
	if builder_api == null:
		message_label.text = "Builder API unavailable"
		_empty_library_state(true)
		return
	var response: Dictionary = await builder_api.list_templates(template_type)
	if not bool(response.get("ok", false)):
		message_label.text = str(response.get("error", "Template library failed"))
		_empty_library_state(true)
		return
	var payload: Variant = response.get("result", {}).get("templates", response.get("result", []))
	templates.clear()
	if payload is Array:
		for template in payload:
			if template is Dictionary:
				templates.append((template as Dictionary).duplicate(true))
	_apply_filter(search_input.text)
	if not preferred_template_id.strip_edges().is_empty():
		_select_template_by_id(preferred_template_id)
	elif not create_mode and not result_ids.is_empty():
		_select_template_by_id(result_ids[0])


func _title_for_mode() -> void:
	var normalized_type := template_type.strip_edges().to_lower()
	title_label.text = "NPC Templates" if normalized_type == "npc" else "Item Templates"
	search_input.placeholder_text = "Search %s templates" % normalized_type


func _set_mode(mode: String) -> void:
	var normalized_mode := mode.strip_edges().to_lower()
	npc_section.visible = normalized_mode == "npc"
	item_section.visible = normalized_mode != "npc"


func _apply_filter(query: String) -> void:
	results_list.clear()
	filtered_templates.clear()
	result_ids.clear()
	var normalized_query := query.strip_edges().to_lower()
	for template in templates:
		var template_id := str(template.get("template_id", "")).strip_edges()
		var template_name := str(template.get("name", template_id)).strip_edges()
		var tag_text := " ".join(_normalized_tags(template.get("tags", []))).to_lower()
		var haystack := "%s %s %s" % [template_name.to_lower(), template_id.to_lower(), tag_text]
		if not normalized_query.is_empty() and haystack.find(normalized_query) < 0:
			continue
		filtered_templates.append(template.duplicate(true))
		result_ids.append(template_id)
		results_list.add_item(_library_row_label(template))
	_empty_library_state(filtered_templates.is_empty())
	message_label.text = "%d templates" % filtered_templates.size() if not filtered_templates.is_empty() else "No templates found"
	if filtered_templates.is_empty():
		_clear_form(true)


func _select_template_by_id(template_id: String) -> void:
	var normalized_template_id := template_id.strip_edges()
	for index in range(result_ids.size()):
		if result_ids[index] != normalized_template_id:
			continue
		results_list.select(index)
		_on_result_selected(index)
		return


func _on_search_changed(new_text: String) -> void:
	_apply_filter(new_text)


func _on_result_selected(index: int) -> void:
	if index < 0 or index >= filtered_templates.size():
		return
	create_mode = false
	var template_data: Dictionary = (filtered_templates[index] as Dictionary).duplicate(true)
	selected_template_id = str(template_data.get("template_id", "")).strip_edges()
	_populate_form(template_data)


func _populate_form(template_data: Dictionary) -> void:
	template_id_input.editable = false
	template_id_input.text = str(template_data.get("template_id", ""))
	name_input.text = str(template_data.get("name", ""))
	var attributes: Dictionary = (template_data.get("attributes", {}) as Dictionary).duplicate(true)
	var flags := {}
	for raw_flag in template_data.get("flags", []):
		flags[str(raw_flag).strip_edges().to_lower()] = true
	var description_text := str(template_data.get("description", ""))
	var guard_placeholder_description := description_text == "A watchful civic guard on regular patrol." and bool(flags.get("guard", false)) and attributes.is_empty()
	var has_explicit_description := bool(template_data.get("has_explicit_description", not description_text.is_empty() and not guard_placeholder_description))
	description_input.text = description_text if has_explicit_description else ""
	var normalized_tags: Array[String] = _normalized_tags(template_data.get("tags", []))
	tags_input.text = ", ".join(normalized_tags)
	str_input.value = float(attributes.get("str", attributes.get("strength", 0)))
	dex_input.value = float(attributes.get("dex", attributes.get("agility", 0)))
	con_input.value = float(attributes.get("con", attributes.get("stamina", 0)))
	aggressive_toggle.button_pressed = bool(flags.get("aggressive", false))
	patrol_toggle.button_pressed = bool(flags.get("patrol", false))
	_select_item_kind(str(template_data.get("item_kind", "item")).strip_edges().to_lower())
	weight_input.value = float(template_data.get("weight", 0.0))
	value_input.value = float(template_data.get("value", 0.0))
	if template_type == "npc" and (not has_explicit_description or attributes.is_empty()):
		var missing_parts: Array[String] = []
		if not has_explicit_description:
			missing_parts.append("description")
		if attributes.is_empty():
			missing_parts.append("stats")
		message_label.text = "Editing %s (%s unavailable in source data)" % [selected_template_id, ", ".join(missing_parts)]
	else:
		message_label.text = "Editing %s" % selected_template_id


func _clear_form(new_mode: bool = false) -> void:
	create_mode = new_mode
	selected_template_id = ""
	template_id_input.editable = true
	template_id_input.text = ""
	name_input.text = ""
	description_input.text = ""
	tags_input.text = ""
	str_input.value = 10
	dex_input.value = 10
	con_input.value = 10
	aggressive_toggle.button_pressed = false
	patrol_toggle.button_pressed = false
	_select_item_kind("item")
	weight_input.value = 0
	value_input.value = 0
	message_label.text = "New template" if new_mode else ""


func _library_row_label(template_data: Dictionary) -> String:
	var template_id := str(template_data.get("template_id", "")).strip_edges()
	var template_name := str(template_data.get("name", template_id)).strip_edges()
	var normalized_tags := _normalized_tags(template_data.get("tags", []))
	if normalized_tags.is_empty():
		return template_name if not template_name.is_empty() else template_id
	return "%s [%s]" % [template_name if not template_name.is_empty() else template_id, ", ".join(normalized_tags)]


func _normalized_tags(raw_tags: Variant) -> Array[String]:
	var normalized_tags: Array[String] = []
	if raw_tags is Array:
		for raw_tag in raw_tags:
			var normalized_tag := str(raw_tag).strip_edges()
			if not normalized_tag.is_empty():
				normalized_tags.append(normalized_tag)
	return normalized_tags


func _empty_library_state(show_empty: bool) -> void:
	empty_state_label.visible = show_empty
	results_list.visible = not show_empty


func _select_item_kind(item_kind: String) -> void:
	var normalized_item_kind := item_kind.strip_edges().to_lower()
	var item_kinds := ["item", "weapon", "container", "vendor"]
	var selected_index := 0
	for index in range(item_kinds.size()):
		if item_kinds[index] == normalized_item_kind:
			selected_index = index
			break
	item_kind_input.select(selected_index)


func _selected_item_kind() -> String:
	var item_kinds := ["item", "weapon", "container", "vendor"]
	var selected_index := item_kind_input.get_selected_id()
	if selected_index >= 0 and selected_index < item_kinds.size():
		return item_kinds[selected_index]
	return "item"


func _build_payload() -> Dictionary:
	var tags: Array[String] = []
	for raw_tag in tags_input.text.split(","):
		var normalized_tag := raw_tag.strip_edges()
		if not normalized_tag.is_empty() and not tags.has(normalized_tag):
			tags.append(normalized_tag)
	var payload := {
		"template_id": template_id_input.text.strip_edges(),
		"type": template_type,
		"name": name_input.text.strip_edges(),
		"description": description_input.text,
		"tags": tags,
	}
	if template_type == "npc":
		payload["attributes"] = {
			"str": int(str_input.value),
			"dex": int(dex_input.value),
			"con": int(con_input.value),
		}
		var flags: Array[String] = []
		if aggressive_toggle.button_pressed:
			flags.append("aggressive")
		if patrol_toggle.button_pressed:
			flags.append("patrol")
		payload["flags"] = flags
	else:
		payload["item_kind"] = _selected_item_kind()
		payload["weight"] = float(weight_input.value)
		payload["value"] = float(value_input.value)
	return payload


func _on_new_pressed() -> void:
	results_list.deselect_all()
	_clear_form(true)


func _on_save_pressed() -> void:
	if builder_api == null:
		message_label.text = "Builder API unavailable"
		return
	var payload := _build_payload()
	if str(payload.get("template_id", "")).strip_edges().is_empty() or str(payload.get("name", "")).strip_edges().is_empty():
		message_label.text = "Template id and name are required"
		return
	var response: Dictionary = {}
	if create_mode or selected_template_id.is_empty():
		response = await builder_api.create_template(payload)
	else:
		var update_payload := payload.duplicate(true)
		update_payload.erase("template_id")
		update_payload.erase("type")
		response = await builder_api.update_template(selected_template_id, update_payload)
	if not bool(response.get("ok", false)):
		message_label.text = str(response.get("error", "Template save failed"))
		return
	var resolved_template_id := str(payload.get("template_id", selected_template_id)).strip_edges()
	create_mode = false
	await refresh_workspace(resolved_template_id)
	message_label.text = "Template saved"


func _on_close_pressed() -> void:
	visible = false
	emit_signal("close_requested")