extends Control


const BuilderApiScript = preload("res://scripts/builder_api.gd")
const BuilderOpsScript = preload("res://scenes/builder/builder_ops.gd")
enum ToolMode {
	SELECT,
	CREATE_ROOM,
	DRAW_EXIT,
	DELETE,
}
const BUILDER_LEFT_COLUMN_WIDTH := 240.0
const BUILDER_RIGHT_COLUMN_WIDTH := 360.0
const DBV2_LEFT_DOCK_WIDTH := 176.0
const DBV2_RIGHT_DOCK_WIDTH := 320.0
const DBV2_RIGHT_TOP_DOCK_HEIGHT := 218.0
const DBV2_BOTTOM_DOCK_HEIGHT := 148.0
const POLL_INTERVAL := 1.0
const MAX_LOG_LINES := 40
const SHELL_NODES_TO_HIDE := [
	"MapPanel",
	"TextLog",
	"CharacterPanel",
	"InventoryPanel",
	"CommandInput",
	"Hotbar",
]


signal feedback(message)


var builder_api: Node
var builder_available := false
var builder_mode_enabled := false
var is_builder := false
var is_dirty := false
var current_area_id := ""
var current_session_id := ""
var selected_room_id: String = ""
var selected_exit_id: String = ""
var selected_object_id: String = ""
var operation_journal: Array[Dictionary] = []
var redo_stack: Array[Dictionary] = []
var move_mode := false
var saved_map_data: Dictionary = {}
var current_map_data: Dictionary = {}
var available_zones: Dictionary = {}
var zone_dropdown_ids: Array[String] = []
var launch_context: Dictionary = {}
var launch_context_applied := false
var is_polling := false
var is_refreshing := false
var refresh_pending := false
var pending_delete_room_id := ""
var builder_log_lines: Array[String] = []
var npc_nodes := {}
var room_nodes := {}
var seen_npcs := {}
var selected_palette_room_type := "forest"
var active_tool := ToolMode.SELECT
var active_workspace := "inspector"
var active_context := {"type": "", "id": ""}
var pending_context_switch: Callable = Callable()
var operation_debug_panel: PanelContainer
var operation_debug_label: RichTextLabel
var DEBUG_RTSYNC := true
var exit_start_room_id := ""


@onready var left_panel: PanelContainer = $BuilderRoot/BuilderColumns/LeftPanel
@onready var center_panel: PanelContainer = $BuilderRoot/BuilderColumns/CenterPanel
@onready var builder_root: MarginContainer = $BuilderRoot
@onready var mode_toggle: CheckButton = $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/BuilderModeToggle
@onready var tools_panel: PanelContainer = $BuilderRoot/BuilderColumns/RightPanel
@onready var zone_dropdown: OptionButton = $BuilderRoot/RootVBox/TopBar/ZoneDropdown
@onready var top_save_button: Button = $BuilderRoot/RootVBox/TopBar/SaveButton
@onready var top_undo_button: Button = $BuilderRoot/RootVBox/TopBar/UndoButton
@onready var top_redo_button: Button = $BuilderRoot/RootVBox/TopBar/RedoButton
@onready var active_tool_value_label: Label = $BuilderRoot/RootVBox/TopBar/ActiveToolValue
@onready var work_split: VSplitContainer = $BuilderRoot/RootVBox/WorkSplit
@onready var outer_split: HSplitContainer = $BuilderRoot/RootVBox/WorkSplit/OuterSplit
@onready var inner_split: HSplitContainer = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/InnerSplit
@onready var left_dock: PanelContainer = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/LeftDock
@onready var zone_stub_value_label: Label = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/LeftDock/Margin/VBox/ZoneStubValue
@onready var right_split: VSplitContainer = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/InnerSplit/RightDock/RightSplit
@onready var select_tool_button: BaseButton = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/LeftDock/Margin/VBox/SelectToolButton
@onready var create_zone_button: Button = $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/ToolsSection/Margin/VBox/ZoneRow/CreateZoneButton
@onready var area_input: LineEdit = $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/ToolsSection/Margin/VBox/AreaIdInput
@onready var load_button: Button = $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/ToolsSection/Margin/VBox/Buttons/LoadMapButton
@onready var save_map_button: Button = $BuilderRoot/RootVBox/WorkSplit/BottomDock/Margin/VBox/SaveBar/Margin/HBox/SaveMapButton
@onready var create_room_button: BaseButton = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/LeftDock/Margin/VBox/CreateRoomToolButton
@onready var draw_exit_button: BaseButton = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/LeftDock/Margin/VBox/DrawExitToolButton
@onready var delete_room_button: Button = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/LeftDock/Margin/VBox/DeleteToolButton
@onready var undo_button: Button = $BuilderRoot/RootVBox/TopBar/UndoButton
@onready var redo_button: Button = $BuilderRoot/RootVBox/TopBar/RedoButton
@onready var status_label: Label = $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/ToolsSection/Margin/VBox/StatusLabel
@onready var dirty_label: Label = $BuilderRoot/RootVBox/WorkSplit/BottomDock/Margin/VBox/SaveBar/Margin/HBox/DirtyLabel
@onready var inspector_tab_button: Button = $BuilderRoot/BuilderColumns/RightPanel/Margin/VBox/WorkspaceTabs/InspectorTabButton
@onready var npc_templates_tab_button: Button = $BuilderRoot/BuilderColumns/RightPanel/Margin/VBox/WorkspaceTabs/NpcTemplatesTabButton
@onready var item_templates_tab_button: Button = $BuilderRoot/BuilderColumns/RightPanel/Margin/VBox/WorkspaceTabs/ItemTemplatesTabButton
@onready var inspector_title_label: Label = $BuilderRoot/BuilderColumns/RightPanel/Margin/VBox/InspectorHeader/Margin/HBox/Title
@onready var inspector_state_label: Label = $BuilderRoot/BuilderColumns/RightPanel/Margin/VBox/InspectorHeader/Margin/HBox/State
@onready var inspector_scroll: ScrollContainer = $BuilderRoot/BuilderColumns/RightPanel/Margin/VBox/InspectorScroll
@onready var builder_log: RichTextLabel = $BuilderRoot/RootVBox/WorkSplit/BottomDock/Margin/VBox/BuilderLogSection/Margin/VBox/LogScroll/BuilderLog
@onready var center_canvas: PanelContainer = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/InnerSplit/CenterCanvas
@onready var right_dock: PanelContainer = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/InnerSplit/RightDock
@onready var bottom_dock: PanelContainer = $BuilderRoot/RootVBox/WorkSplit/BottomDock
@onready var right_panel_vbox: VBoxContainer = $BuilderRoot/BuilderColumns/RightPanel/Margin/VBox
@onready var map_grid = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/InnerSplit/CenterCanvas/MapGrid
@onready var room_editor: Control = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/InnerSplit/RightDock/RightSplit/InspectorDock/VBox/Scroll/InspectorContent/RoomEditor
@onready var instance_editor: Control = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/InnerSplit/RightDock/RightSplit/InspectorDock/VBox/Scroll/InspectorContent/InstanceEditor
@onready var template_selector: Control = $BuilderRoot/BuilderColumns/RightPanel/Margin/VBox/InspectorScroll/InspectorSections/TemplateSelector
@onready var content_tree: Control = $BuilderRoot/RootVBox/WorkSplit/OuterSplit/InnerSplit/RightDock/RightSplit/ContentTree
@onready var npc_template_workspace: Control = $BuilderRoot/BuilderColumns/RightPanel/Margin/VBox/NpcTemplateWorkspace
@onready var item_template_workspace: Control = $BuilderRoot/BuilderColumns/RightPanel/Margin/VBox/ItemTemplateWorkspace
@onready var delete_room_confirm: ConfirmationDialog = $DeleteRoomConfirm
@onready var create_zone_dialog: ConfirmationDialog = $CreateZoneDialog
@onready var zone_name_input: LineEdit = $CreateZoneDialog/Margin/VBox/ZoneNameInput
@onready var zone_id_input: LineEdit = $CreateZoneDialog/Margin/VBox/ZoneIdInput
@onready var add_item_button: Button = $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/ObjectsSection/Margin/VBox/Buttons/AddItemButton
@onready var add_npc_button: Button = $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/ObjectsSection/Margin/VBox/Buttons/AddNpcButton
@onready var room_type_buttons := {
	"forest": $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/RoomTypesSection/Margin/VBox/Grid/TypeForest,
	"river": $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/RoomTypesSection/Margin/VBox/Grid/TypeRiver,
	"city": $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/RoomTypesSection/Margin/VBox/Grid/TypeCity,
	"home": $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/RoomTypesSection/Margin/VBox/Grid/TypeHome,
	"coast": $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/RoomTypesSection/Margin/VBox/Grid/TypeCoast,
	"guild": $BuilderRoot/BuilderColumns/LeftPanel/Margin/VBox/RoomTypesSection/Margin/VBox/Grid/TypeGuild,
}


func _ready() -> void:
	left_panel.custom_minimum_size.x = BUILDER_LEFT_COLUMN_WIDTH
	tools_panel.custom_minimum_size.x = BUILDER_RIGHT_COLUMN_WIDTH
	builder_api = BuilderApiScript.new()
	add_child(builder_api)
	map_grid.set_debug_rtsync(DEBUG_RTSYNC)
	template_selector.configure_api(builder_api)
	npc_template_workspace.configure_api(builder_api)
	item_template_workspace.configure_api(builder_api)
	npc_template_workspace.template_type = "npc"
	item_template_workspace.template_type = "item"
	template_selector.visible = false
	npc_template_workspace.visible = false
	item_template_workspace.visible = false
	delete_room_button.toggle_mode = true
	mode_toggle.toggled.connect(_on_mode_toggled)
	zone_dropdown.item_selected.connect(_on_zone_dropdown_selected)
	select_tool_button.pressed.connect(_on_select_tool_pressed)
	top_save_button.pressed.connect(_on_save_map_pressed)
	top_undo_button.pressed.connect(_on_undo_pressed)
	top_redo_button.pressed.connect(_on_redo_pressed)
	inspector_tab_button.pressed.connect(_on_workspace_tab_pressed.bind("inspector"))
	npc_templates_tab_button.pressed.connect(_on_workspace_tab_pressed.bind("npc_templates"))
	item_templates_tab_button.pressed.connect(_on_workspace_tab_pressed.bind("item_templates"))
	create_zone_button.pressed.connect(_on_create_zone_pressed)
	load_button.pressed.connect(_on_load_map_pressed)
	save_map_button.pressed.connect(_on_save_map_pressed)
	create_room_button.toggled.connect(_on_create_room_toggled)
	draw_exit_button.toggled.connect(_on_draw_exit_toggled)
	delete_room_button.toggled.connect(_on_delete_tool_toggled)
	add_item_button.pressed.connect(_on_room_editor_add_item_requested)
	add_npc_button.pressed.connect(_on_room_editor_add_npc_requested)
	delete_room_confirm.confirmed.connect(_on_delete_room_confirmed)
	create_zone_dialog.confirmed.connect(_on_create_zone_confirmed)
	zone_name_input.text_changed.connect(_on_zone_name_changed)
	map_grid.empty_cell_clicked.connect(_on_empty_cell_clicked)
	map_grid.room_selected.connect(_on_room_selected)
	map_grid.room_dragged.connect(_on_room_dragged)
	map_grid.exit_requested.connect(_on_exit_requested)
	map_grid.exit_clicked.connect(_on_exit_clicked)
	map_grid.object_selected.connect(_on_map_object_selected)
	map_grid.object_drop_requested.connect(_on_map_object_drop_requested)
	room_editor.draft_changed.connect(_on_room_editor_draft_changed)
	room_editor.save_requested.connect(_on_room_editor_save_requested)
	room_editor.close_requested.connect(_on_room_editor_close_requested)
	room_editor.add_npc_requested.connect(_on_room_editor_add_npc_requested)
	room_editor.add_item_requested.connect(_on_room_editor_add_item_requested)
	room_editor.exit_selected.connect(_on_room_editor_exit_selected)
	room_editor.exit_save_requested.connect(_on_room_editor_exit_save_requested)
	room_editor.exit_delete_requested.connect(_on_room_editor_exit_delete_requested)
	instance_editor.save_requested.connect(_on_instance_editor_save_requested)
	instance_editor.edit_template_requested.connect(_on_instance_editor_edit_template_requested)
	instance_editor.delete_requested.connect(_on_instance_editor_delete_requested)
	instance_editor.back_requested.connect(_on_instance_editor_back_requested)
	template_selector.template_chosen.connect(_on_template_chosen)
	template_selector.closed.connect(_on_template_selector_closed)
	content_tree.object_selected.connect(_on_content_tree_object_selected)
	content_tree.delete_requested.connect(_on_content_tree_delete_requested)
	npc_template_workspace.close_requested.connect(_on_template_workspace_closed)
	item_template_workspace.close_requested.connect(_on_template_workspace_closed)
	for room_type in room_type_buttons.keys():
		(room_type_buttons[room_type] as BaseButton).toggled.connect(_on_room_type_button_toggled.bind(room_type))
	_setup_context_switch_dialog()
	_setup_operation_debug_view()
	_set_builder_visible(false)
	_set_palette_room_type(selected_palette_room_type)
	set_active_tool(ToolMode.SELECT)
	_set_dirty(false)
	_log_builder("Builder controller ready.")
	_set_workspace("inspector")
	_apply_builder_layout()
	_update_action_buttons()
	resized.connect(_on_resized)


func apply_launch_context(context: Dictionary) -> void:
	launch_context = context.duplicate(true)
	var area_id := str(context.get("area_id", "")).strip_edges()
	var room_id := str(context.get("room_id", "")).strip_edges()
	var character_name := str(context.get("character_name", "")).strip_edges()
	print("BuilderController launch context: %s" % [str(context)])
	if not area_id.is_empty():
		current_area_id = area_id
		area_input.text = area_id
		_sync_zone_dropdown(area_id)
	if not room_id.is_empty():
		select_room(room_id)
	if not character_name.is_empty():
		print("Builder launch character context: %s" % character_name)
	_set_status("Launch context received.%s%s" % [
		" Area: %s." % area_id if not area_id.is_empty() else "",
		" Room: %s." % room_id if not room_id.is_empty() else "",
	])
	if not area_id.is_empty():
		_activate_builder_from_launch_context()


func _has_builder_launch_context() -> bool:
	return not str(launch_context.get("area_id", "")).strip_edges().is_empty()


func update_character_context(data: Dictionary) -> void:
	var permission_flag := bool(
		data.get("is_builder", false)
		or data.get("builder_mode_available", false)
		or _has_builder_launch_context()
	)
	builder_available = permission_flag
	mode_toggle.visible = builder_available
	if not builder_available:
		mode_toggle.button_pressed = false
		_set_builder_visible(false)
	current_session_id = str(data.get("builder_session_id", current_session_id)).strip_edges()
	if builder_available and not launch_context.is_empty() and not launch_context_applied:
		_activate_builder_from_launch_context()


func ingest_live_map(data: Dictionary) -> void:
	if current_area_id.is_empty() and not str(data.get("area_id", "")).strip_edges().is_empty():
		current_area_id = str(data.get("area_id", "")).strip_edges()
		area_input.text = current_area_id
		_sync_zone_dropdown(current_area_id)
	if builder_mode_enabled and not launch_context.is_empty() and not launch_context_applied:
		_activate_builder_from_launch_context()


func _activate_builder_from_launch_context() -> void:
	var area_id := str(launch_context.get("area_id", current_area_id)).strip_edges()
	if area_id.is_empty():
		return
	launch_context_applied = true
	builder_available = true
	mode_toggle.visible = true
	mode_toggle.button_pressed = true
	_set_builder_visible(true)
	print("BUILDER MODE ENABLED")
	print("Requesting map for area:", area_id)
	call_deferred("_deferred_refresh_map", area_id)


func _deferred_refresh_map(area_id: String) -> void:
	await _reload_zone_registry(area_id)
	await _refresh_map(area_id, true)


func _set_builder_visible(enabled: bool) -> void:
	builder_mode_enabled = enabled and builder_available
	is_builder = builder_mode_enabled
	mouse_filter = Control.MOUSE_FILTER_STOP if builder_mode_enabled else Control.MOUSE_FILTER_IGNORE
	_apply_builder_layout()
	builder_root.visible = builder_mode_enabled
	builder_root.mouse_filter = Control.MOUSE_FILTER_STOP if builder_mode_enabled else Control.MOUSE_FILTER_IGNORE
	left_panel.visible = builder_mode_enabled
	center_panel.visible = builder_mode_enabled
	tools_panel.visible = builder_mode_enabled
	map_grid.visible = builder_mode_enabled
	map_grid.set_builder_enabled(is_builder)
	_set_shell_visibility(not builder_mode_enabled)
	if builder_mode_enabled:
		move_to_front()
		builder_root.move_to_front()
	if builder_mode_enabled:
		start_polling()
	else:
		stop_polling()
	if not builder_mode_enabled:
		_set_workspace("inspector")
		select_room("")
		select_object("")
		room_editor.clear_room()
		instance_editor.clear_editor()
		set_active_tool(ToolMode.SELECT)
		template_selector.visible = false
		content_tree.visible = false
		delete_room_confirm.hide()
	_update_action_buttons()


func _setup_context_switch_dialog() -> void:
	var confirm_dialog := ConfirmationDialog.new()
	confirm_dialog.title = "Unsaved Changes"
	confirm_dialog.dialog_text = "You have unsaved staged changes. Continue and keep them staged?"
	confirm_dialog.confirmed.connect(_on_context_switch_confirmed)
	add_child(confirm_dialog)
	confirm_dialog.name = "ContextSwitchConfirm"


func _setup_operation_debug_view() -> void:
	operation_debug_panel = PanelContainer.new()
	operation_debug_panel.name = "OperationDebugPanel"
	operation_debug_panel.custom_minimum_size = Vector2(0, 120)
	operation_debug_panel.visible = true
	var margin := MarginContainer.new()
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 6)
	var header := Label.new()
	header.text = "Operations"
	operation_debug_label = RichTextLabel.new()
	operation_debug_label.fit_content = true
	operation_debug_label.scroll_active = true
	operation_debug_label.custom_minimum_size = Vector2(0, 84)
	vbox.add_child(header)
	vbox.add_child(operation_debug_label)
	margin.add_child(vbox)
	operation_debug_panel.add_child(margin)
	right_panel_vbox.add_child(operation_debug_panel)
	right_panel_vbox.move_child(operation_debug_panel, right_panel_vbox.get_child_count() - 2)
	_update_operation_debug_view()


func _on_context_switch_confirmed() -> void:
	if pending_context_switch.is_valid():
		var callback := pending_context_switch
		pending_context_switch = Callable()
		callback.call()


func _has_unsaved_changes() -> bool:
	return not operation_journal.is_empty()


func _context_would_change(context_type: String, context_id: String) -> bool:
	return str(active_context.get("type", "")) != context_type.strip_edges().to_lower() or str(active_context.get("id", "")) != context_id.strip_edges()


func _request_context_switch(context_type: String, context_id: String, callback: Callable) -> void:
	if not _context_would_change(context_type, context_id):
		callback.call()
		return
	if _has_unsaved_changes():
		pending_context_switch = callback
		var confirm_dialog := get_node_or_null("ContextSwitchConfirm") as ConfirmationDialog
		if confirm_dialog != null:
			confirm_dialog.popup_centered()
		return
	callback.call()


func _update_operation_debug_view() -> void:
	if operation_debug_label == null:
		return
	if operation_journal.is_empty():
		operation_debug_label.text = "No staged operations."
		return
	var lines: Array[String] = []
	var index := 1
	for entry in operation_journal:
		for operation in entry.get("ops", []):
			if not operation is Dictionary:
				continue
			var op_dict := operation as Dictionary
			lines.append("%d. %s %s %s" % [index, str(op_dict.get("op", "")).strip_edges(), str(op_dict.get("entity_type", "")).strip_edges(), str(op_dict.get("entity_id", "")).strip_edges()])
			index += 1
	operation_debug_label.text = "\n".join(lines)


func _set_workspace(workspace_id: String) -> void:
	# TODO: DBV2 replace with library system
	active_workspace = "inspector"
	inspector_scroll.visible = false
	npc_template_workspace.visible = false
	item_template_workspace.visible = false
	inspector_tab_button.set_pressed_no_signal(true)
	npc_templates_tab_button.set_pressed_no_signal(false)
	item_templates_tab_button.set_pressed_no_signal(false)
	_update_inspector_header()


func _on_workspace_tab_pressed(workspace_id: String) -> void:
	if not is_builder:
		return
	_set_status("DBV2 TODO: library system not wired yet.")


func _on_resized() -> void:
	_apply_builder_layout()


func _unhandled_input(event: InputEvent) -> void:
	if not is_builder:
		return
	if not (event is InputEventKey):
		return
	var key_event := event as InputEventKey
	if not key_event.pressed or key_event.echo:
		return
	if key_event.ctrl_pressed and key_event.keycode == KEY_Z:
		get_viewport().set_input_as_handled()
		call_deferred("_on_undo_pressed")
		return
	if key_event.ctrl_pressed and key_event.keycode == KEY_Y:
		get_viewport().set_input_as_handled()
		call_deferred("_on_redo_pressed")
		return
	if key_event.keycode == KEY_DELETE:
		get_viewport().set_input_as_handled()
		if not selected_object_id.is_empty():
			call_deferred("_on_content_tree_delete_requested", selected_object_id)
		elif not selected_room_id.is_empty():
			call_deferred("_on_delete_room_pressed")
		return
	if key_event.keycode == KEY_E:
		get_viewport().set_input_as_handled()
		draw_exit_button.button_pressed = not draw_exit_button.button_pressed
		_on_draw_exit_toggled(draw_exit_button.button_pressed)
		return
	if key_event.keycode == KEY_C:
		get_viewport().set_input_as_handled()
		create_room_button.button_pressed = not create_room_button.button_pressed
		_on_create_room_toggled(create_room_button.button_pressed)


func _apply_builder_layout() -> void:
	left_panel.custom_minimum_size.x = BUILDER_LEFT_COLUMN_WIDTH
	tools_panel.custom_minimum_size.x = BUILDER_RIGHT_COLUMN_WIDTH
	left_dock.custom_minimum_size.x = DBV2_LEFT_DOCK_WIDTH
	right_dock.custom_minimum_size.x = DBV2_RIGHT_DOCK_WIDTH
	bottom_dock.custom_minimum_size.y = DBV2_BOTTOM_DOCK_HEIGHT
	left_dock.size_flags_horizontal = Control.SIZE_FILL
	right_dock.size_flags_horizontal = Control.SIZE_FILL
	center_canvas.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	center_canvas.size_flags_vertical = Control.SIZE_EXPAND_FILL
	if outer_split.size.x > 0:
		outer_split.split_offset = int(DBV2_LEFT_DOCK_WIDTH)
	if inner_split.size.x > 0:
		inner_split.split_offset = max(0, int(inner_split.size.x - DBV2_RIGHT_DOCK_WIDTH - 4.0))
	if right_split.size.y > 0:
		right_split.split_offset = int(DBV2_RIGHT_TOP_DOCK_HEIGHT)
	if work_split.size.y > 0:
		work_split.split_offset = max(0, int(work_split.size.y - DBV2_BOTTOM_DOCK_HEIGHT - 4.0))


func _set_shell_visibility(visible: bool) -> void:
	var parent := get_parent()
	if parent == null:
		return
	for node_name in SHELL_NODES_TO_HIDE:
		var node := parent.get_node_or_null(node_name)
		if node != null:
			node.visible = visible
			if node is Control:
				var control := node as Control
				if not control.has_meta("builder_original_mouse_filter"):
					control.set_meta("builder_original_mouse_filter", control.mouse_filter)
				if not control.has_meta("builder_original_focus_mode"):
					control.set_meta("builder_original_focus_mode", control.focus_mode)
				control.mouse_filter = int(control.get_meta("builder_original_mouse_filter")) if visible else Control.MOUSE_FILTER_IGNORE
				control.focus_mode = int(control.get_meta("builder_original_focus_mode")) if visible else Control.FOCUS_NONE
				if control is LineEdit:
					var line_edit := control as LineEdit
					if not line_edit.has_meta("builder_original_editable"):
						line_edit.set_meta("builder_original_editable", line_edit.editable)
					line_edit.editable = bool(line_edit.get_meta("builder_original_editable")) if visible else false


func _update_action_buttons() -> void:
	select_tool_button.disabled = not is_builder
	delete_room_button.disabled = not is_builder
	create_room_button.disabled = not is_builder or current_area_id.is_empty()
	draw_exit_button.disabled = not is_builder
	add_item_button.disabled = not is_builder or selected_room_id.is_empty()
	add_npc_button.disabled = not is_builder or selected_room_id.is_empty()
	save_map_button.disabled = not is_builder or operation_journal.is_empty()
	top_save_button.disabled = save_map_button.disabled
	undo_button.disabled = not is_builder or operation_journal.is_empty()
	top_undo_button.disabled = undo_button.disabled
	redo_button.disabled = not is_builder or redo_stack.is_empty()
	top_redo_button.disabled = redo_button.disabled
	zone_dropdown.disabled = not is_builder
	_update_zone_stub_label()
	_refresh_active_tool_ui()


func set_active_tool(mode: int) -> void:
	var normalized_mode := clampi(mode, ToolMode.SELECT, ToolMode.DELETE)
	var changed := active_tool != normalized_mode
	active_tool = normalized_mode
	if active_tool != ToolMode.DRAW_EXIT:
		_clear_draw_exit_state()
	map_grid.set_active_tool(_tool_mode_key(active_tool))
	_refresh_active_tool_ui()
	if changed:
		_log_builder("Tool changed to: %s" % _active_tool_label(active_tool))


func _refresh_active_tool_ui() -> void:
	if active_tool_value_label != null:
		active_tool_value_label.text = _active_tool_label(active_tool)
	if select_tool_button != null:
		select_tool_button.set_pressed_no_signal(active_tool == ToolMode.SELECT)
	if create_room_button != null:
		create_room_button.set_pressed_no_signal(active_tool == ToolMode.CREATE_ROOM)
	if draw_exit_button != null:
		draw_exit_button.set_pressed_no_signal(active_tool == ToolMode.DRAW_EXIT)
	if delete_room_button != null:
		delete_room_button.set_pressed_no_signal(active_tool == ToolMode.DELETE)


func _active_tool_label(tool_mode: int) -> String:
	match tool_mode:
		ToolMode.CREATE_ROOM:
			return "Create Room"
		ToolMode.DRAW_EXIT:
			return "Draw Exit"
		ToolMode.DELETE:
			return "Delete"
		_:
			return "Select"


func _tool_mode_key(tool_mode: int) -> String:
	match tool_mode:
		ToolMode.CREATE_ROOM:
			return "create_room"
		ToolMode.DRAW_EXIT:
			return "draw_exit"
		ToolMode.DELETE:
			return "delete"
		_:
			return "select"


func _clear_draw_exit_state() -> void:
	exit_start_room_id = ""
	if map_grid != null:
		map_grid.set_pending_exit_source("")


func _update_zone_stub_label() -> void:
	if zone_stub_value_label == null:
		return
	var zone_id := _selected_zone_id()
	if zone_id.is_empty():
		zone_id = current_area_id.strip_edges()
	zone_stub_value_label.text = "Current Zone: %s" % (zone_id if not zone_id.is_empty() else "none")


func _set_status(message: String) -> void:
	status_label.text = message
	emit_signal("feedback", message)


func _set_dirty(value: bool) -> void:
	is_dirty = value
	dirty_label.text = "● Unsaved changes" if is_dirty else "✓ Saved"
	inspector_state_label.text = dirty_label.text
	_update_inspector_header()
	_update_action_buttons()
	_update_operation_debug_view()


func _log_builder(message: String, kind: String = "info") -> void:
	var normalized_message := str(message).strip_edges()
	if normalized_message.is_empty():
		return
	var prefix := kind.to_upper()
	builder_log_lines.append("[%s] %s" % [prefix, normalized_message])
	while builder_log_lines.size() > MAX_LOG_LINES:
		builder_log_lines.remove_at(0)
	if builder_log != null:
		builder_log.clear()
		builder_log.text = "\n".join(builder_log_lines)


func _on_mode_toggled(enabled: bool) -> void:
	if enabled and not builder_available:
		mode_toggle.button_pressed = false
		return
	_set_builder_visible(enabled)
	if builder_mode_enabled:
		await _reload_zone_registry(current_area_id)
		var selected_zone_id := _selected_zone_id()
		if not selected_zone_id.is_empty():
			await _refresh_map(selected_zone_id, true)


func _on_load_map_pressed() -> void:
	if not is_builder:
		return
	var selected_zone_id := _selected_zone_id()
	if selected_zone_id.is_empty():
		_set_status("Select a zone before loading Builder.")
		return
	if is_dirty and selected_zone_id != current_area_id:
		_set_status("Save Map before switching zones.")
		return
	await _refresh_map(selected_zone_id, true)


func _on_save_map_pressed() -> void:
	if not is_builder or operation_journal.is_empty():
		return
	var diff := _build_combined_diff()
	if diff.is_empty():
		return
	_log_builder("Saving %d staged operations." % int((diff.get("operations", []) as Array).size()))
	var response: Dictionary = await builder_api.save_all(diff, current_session_id)
	if not bool(response.get("ok", false)):
		_handle_api_error(response)
		return
	operation_journal.clear()
	redo_stack.clear()
	_set_dirty(false)
	await _refresh_map(current_area_id)
	_set_status("Map saved.")
	_log_builder("Save completed.")


func _on_create_room_pressed() -> void:
	if not is_builder:
		return
	var area_id := _require_area_id()
	if area_id.is_empty():
		return
	create_room_button.button_pressed = not create_room_button.button_pressed
	_on_create_room_toggled(create_room_button.button_pressed)


func _on_create_room_toggled(enabled: bool) -> void:
	if not is_builder and enabled:
		create_room_button.set_pressed_no_signal(false)
		return
	if enabled:
		set_active_tool(ToolMode.CREATE_ROOM)
		_set_status("Create room mode enabled. Click the map to place a room.")
	else:
		if active_tool == ToolMode.CREATE_ROOM:
			set_active_tool(ToolMode.SELECT)
		_set_status("Create room mode disabled.")


func _on_draw_exit_toggled(enabled: bool) -> void:
	if not is_builder:
		draw_exit_button.set_pressed_no_signal(false)
		return
	set_active_tool(ToolMode.DRAW_EXIT if enabled else ToolMode.SELECT)
	_set_status("Draw exit mode enabled." if enabled else "Draw exit mode disabled.")


func _on_select_tool_pressed() -> void:
	if not is_builder:
		return
	set_active_tool(ToolMode.SELECT)
	_set_status("Select tool enabled.")


func _on_delete_tool_toggled(enabled: bool) -> void:
	if not is_builder and enabled:
		delete_room_button.set_pressed_no_signal(false)
		return
	set_active_tool(ToolMode.DELETE if enabled else ToolMode.SELECT)
	_set_status("Delete tool enabled. Click a room to delete it." if enabled else "Delete tool disabled.")


func _handle_select_room(room_id: String) -> void:
	_request_context_switch("room", room_id, func() -> void:
		select_room(room_id)
		var room_data_for_type := _get_room_from_cache(selected_room_id)
		_set_palette_room_type(_normalize_palette_room_type(str(room_data_for_type.get("room_type", "room"))), false)
		var room_data := _get_room_from_cache(selected_room_id)
		if move_mode and not selected_object_id.is_empty() and not room_data.is_empty():
			var destination_id := str(room_data.get("object_id", "")).strip_edges()
			if not destination_id.is_empty() and destination_id != selected_object_id:
				move_selected_object(destination_id, "in")
				return
		map_grid.clear_conflicts()
	)


func _on_room_selected(_room_id: String) -> void:
	var room_id := str(_room_id).strip_edges()
	if room_id.is_empty():
		return
	await handle_canvas_click(room_id, {}, Vector2.ZERO)


func select_room(room_id: String) -> void:
	var normalized_room_id := room_id.strip_edges()
	if normalized_room_id != selected_room_id:
		selected_exit_id = ""
	selected_room_id = normalized_room_id
	selected_object_id = ""
	move_mode = false
	_set_active_context("room" if not selected_room_id.is_empty() else "", selected_room_id)
	map_grid.set_selected_room(selected_room_id)
	map_grid.set_selected_object("")
	content_tree.select_object("")
	if selected_room_id.is_empty():
		selected_exit_id = ""
		room_editor.clear_room()
		instance_editor.clear_editor()
		content_tree.clear_tree()
		_show_inspector_context()
		_update_inspector_header()
		map_grid.clear_conflicts()
		_update_action_buttons()
		return
	_open_room_editor(selected_room_id)
	_update_inspector_header()
	_update_action_buttons()


func select_object(object_id: String) -> void:
	selected_object_id = object_id.strip_edges()
	move_mode = not selected_object_id.is_empty()
	if selected_object_id.is_empty():
		_set_active_context("room" if not selected_room_id.is_empty() else "", selected_room_id)
		map_grid.set_selected_object("")
		content_tree.select_object("")
		_show_inspector_context()
		if not selected_room_id.is_empty():
			_open_room_editor(selected_room_id)
		return
	var object_data := _find_selected_object_data()
	var object_type := str(object_data.get("type", "item")).strip_edges().to_lower()
	_set_active_context("npc" if object_type == "npc" else "item", selected_object_id)
	_open_instance_editor(selected_object_id)


func handle_canvas_click(room_id: String, cell: Dictionary, position: Vector2 = Vector2.ZERO, object_id: String = "") -> void:
	if not is_builder:
		return
	match active_tool:
		ToolMode.SELECT:
			if not object_id.strip_edges().is_empty():
				_on_canvas_object_selected(object_id)
			elif not room_id.strip_edges().is_empty():
				_handle_select_room(room_id)
			else:
				select_room("")
		ToolMode.CREATE_ROOM:
			await _handle_create_room_click(cell, room_id, object_id)
		ToolMode.DRAW_EXIT:
			await _handle_draw_exit_click(room_id)
		ToolMode.DELETE:
			await _handle_delete_click(room_id)


func _handle_create_room_click(cell: Dictionary, clicked_room_id: String, object_id: String) -> void:
	if not clicked_room_id.strip_edges().is_empty() or not object_id.strip_edges().is_empty():
		return
	var area_id := _require_area_id()
	if area_id.is_empty():
		return
	var new_room_id := _generate_room_id()
	var diff := {
		"area_id": area_id,
		"operations": [
			{
				"id": "create-%s" % new_room_id,
				"op": "create_room",
				"room": {
					"id": new_room_id,
					"object_id": new_room_id,
					"name": "New Room",
					"description": "An unfinished room.",
					"zone_id": area_id,
					"room_type": selected_palette_room_type,
					"map_x": int(cell.get("map_x", 0)),
					"map_y": int(cell.get("map_y", 0)),
					"map_layer": int(cell.get("map_layer", 0)),
					"exits": {},
					"contents": [],
				}
			}
		]
	}
	var staged := await _stage_previewable_diff(diff, "Room created.")
	if staged:
		select_room(new_room_id)


func _handle_draw_exit_click(room_id: String) -> void:
	var normalized_room_id := room_id.strip_edges()
	if normalized_room_id.is_empty():
		return
	if exit_start_room_id.is_empty():
		exit_start_room_id = normalized_room_id
		map_grid.set_pending_exit_source(exit_start_room_id)
		_handle_select_room(normalized_room_id)
		_set_status("Draw exit: select destination room.")
		return
	if normalized_room_id == exit_start_room_id:
		_clear_draw_exit_state()
		_set_status("Draw exit cancelled.")
		return
	var direction: String = map_grid.get_direction_between_rooms(exit_start_room_id, normalized_room_id)
	if direction.is_empty():
		_set_status("Rooms must be adjacent to draw an exit.")
		return
	await _on_exit_requested(exit_start_room_id, direction, normalized_room_id)
	_clear_draw_exit_state()
	_handle_select_room(normalized_room_id)


func _handle_delete_click(room_id: String) -> void:
	var normalized_room_id := room_id.strip_edges()
	if normalized_room_id.is_empty():
		return
	await _delete_room_by_id(normalized_room_id)


func _delete_room_by_id(room_id: String) -> void:
	var area_id := _require_area_id()
	if area_id.is_empty():
		return
	var normalized_room_id := room_id.strip_edges()
	if normalized_room_id.is_empty():
		return
	if exit_start_room_id == normalized_room_id:
		_clear_draw_exit_state()
	var diff := {
		"area_id": area_id,
		"operations": [
			{
				"id": "delete-%s" % normalized_room_id,
				"op": "delete_room",
				"room_id": normalized_room_id,
			}
		]
	}
	var staged := await _stage_previewable_diff(diff, "Room deleted.")
	if staged:
		_sync_selection_after_map_update()


func _on_empty_cell_clicked(cell: Dictionary) -> void:
	await handle_canvas_click("", cell, Vector2.ZERO)


func _on_room_dragged(room_id: String, cell: Dictionary) -> void:
	if not is_builder:
		return
	if room_id.is_empty():
		return
	var area_id := _require_area_id()
	if area_id.is_empty():
		return
	var group_id := "move-room-%d" % Time.get_unix_time_from_system()
	var diff := {
		"area_id": area_id,
		"operations": [
			{
				"id": "move-%s" % room_id,
				"op": "update_room",
				"room_id": room_id,
				"updates": {
					"map_x": int(cell.get("map_x", 0)),
					"map_y": int(cell.get("map_y", 0)),
				}
			}
		]
	}
	await _stage_previewable_diff(diff, "Room moved.", group_id)


func _on_delete_room_confirmed() -> void:
	if not is_builder or pending_delete_room_id.is_empty():
		return
	var room_id := pending_delete_room_id
	pending_delete_room_id = ""
	await _delete_room_by_id(room_id)


func _on_exit_requested(source_id: String, direction: String, target_id: String) -> void:
	if not is_builder:
		return
	var area_id := _require_area_id()
	if area_id.is_empty():
		return
	var reverse_direction := _opposite_direction(direction)
	var operations: Array[Dictionary] = [
		{
			"id": "exit-%s-%s" % [source_id, direction],
			"op": "set_exit",
			"source_id": source_id,
			"direction": direction,
			"target_id": target_id,
			"target_zone_id": current_area_id,
		}
	]
	if not reverse_direction.is_empty():
		operations.append(
			{
				"id": "exit-%s-%s" % [target_id, reverse_direction],
				"op": "set_exit",
				"source_id": target_id,
				"direction": reverse_direction,
				"target_id": source_id,
				"target_zone_id": current_area_id,
			}
		)
	var diff := {
		"area_id": area_id,
		"operations": operations,
	}
	await _stage_previewable_diff(diff, "Exit updated.", "draw-exit-%d" % Time.get_unix_time_from_system())


func _on_exit_clicked(source_id: String, direction: String, target_id: String) -> void:
	if not is_builder:
		return
	var area_id := _require_area_id()
	if area_id.is_empty():
		return
	var reverse_direction := _opposite_direction(direction)
	var operations: Array[Dictionary] = [
		{
			"id": "delete-exit-%s-%s" % [source_id, direction],
			"op": "delete_exit",
			"source_id": source_id,
			"direction": direction,
		}
	]
	if not reverse_direction.is_empty():
		operations.append(
			{
				"id": "delete-exit-%s-%s" % [target_id, reverse_direction],
				"op": "delete_exit",
				"source_id": target_id,
				"direction": reverse_direction,
			}
		)
	var diff := {
		"area_id": area_id,
		"operations": operations,
	}
	await _stage_previewable_diff(diff, "Exit deleted.")


func _on_undo_pressed() -> void:
	if not is_builder:
		return
	if operation_journal.is_empty():
		return
	redo_stack.append(operation_journal.pop_back())
	_rebuild_current_map_from_saved()
	_set_dirty(not operation_journal.is_empty())
	_set_status("Undo staged.")
	_log_builder("Undo staged change.")


func _on_redo_pressed() -> void:
	if not is_builder:
		return
	if redo_stack.is_empty():
		return
	operation_journal.append(redo_stack.pop_back())
	_rebuild_current_map_from_saved()
	_set_dirty(true)
	_set_status("Redo staged.")
	_log_builder("Redo staged change.")


func _stage_previewable_diff(diff: Dictionary, success_message: String, group_id: String = "") -> bool:
	return await _stage_previewable_diff_entry(diff, success_message, group_id)


func _stage_previewable_diff_entry(diff: Dictionary, success_message: String, group_id: String = "", entry_metadata: Dictionary = {}, replace_last: bool = false) -> bool:
	if not is_builder:
		return false
	map_grid.clear_conflicts()
	var preview_response: Dictionary = await builder_api.apply_diff(diff, true, group_id, current_session_id)
	if not bool(preview_response.get("ok", false)):
		_handle_api_error(preview_response)
		return false
	var canonical_ops := _canonicalize_diff(diff)
	var validation_error := _validate_op_sequence(canonical_ops)
	if not validation_error.is_empty():
		_set_status(validation_error)
		return false
	var entry := {
		"ops": canonical_ops,
		"message": success_message,
		"group_id": group_id,
	}
	for key in entry_metadata.keys():
		entry[key] = entry_metadata.get(key)
	if replace_last and not operation_journal.is_empty():
		operation_journal[operation_journal.size() - 1] = entry
	else:
		operation_journal.append(entry)
	redo_stack.clear()
	_set_dirty(true)
	_rebuild_current_map_from_saved()
	_set_status("%s Save Map to persist." % success_message)
	_log_builder(success_message)
	return true


func _validate_op_sequence(operations: Array[Dictionary]) -> String:
	var candidate_map := rebuild_from_journal().duplicate(true)
	for operation in operations:
		var error := validate_op(candidate_map, operation)
		if not error.is_empty():
			return error
		apply_op(candidate_map, operation)
	return ""


func _build_combined_diff() -> Dictionary:
	if operation_journal.is_empty():
		return {}
	var operations: Array[Dictionary] = []
	for entry in operation_journal:
		for operation in entry.get("ops", []):
			if operation is Dictionary:
				for serialized_operation in BuilderOpsScript.serialize_op(operation as Dictionary):
					operations.append(serialized_operation)
	return {
		"area_id": current_area_id,
		"operations": operations,
	}


func _refresh_map(area_id: String, reset_view: bool = false) -> void:
	if not is_builder:
		return
	var normalized_area_id := area_id.strip_edges()
	if normalized_area_id.is_empty():
		_set_status("Zone id is required.")
		return
	var switching_zone := current_area_id != normalized_area_id
	if switching_zone and is_dirty:
		_set_status("Save Map before switching zones.")
		return
	current_area_id = normalized_area_id
	area_input.text = current_area_id
	_sync_zone_dropdown(current_area_id)
	if switching_zone or reset_view:
		operation_journal.clear()
		redo_stack.clear()
		selected_exit_id = ""
		select_room("")
		select_object("")
		map_grid.reset_zoom()
		map_grid.center()
		_set_dirty(false)
	await refresh_map()


func start_polling() -> void:
	if is_polling:
		return
	is_polling = true
	_poll_loop()


func stop_polling() -> void:
	is_polling = false
	refresh_pending = false


func _poll_loop() -> void:
	while is_polling:
		await get_tree().create_timer(POLL_INTERVAL).timeout
		if not is_polling or not builder_mode_enabled:
			continue
		await refresh_map()


func refresh_map() -> void:
	if not is_builder:
		return
	var normalized_area_id := current_area_id.strip_edges()
	if normalized_area_id.is_empty():
		normalized_area_id = _selected_zone_id()
	if normalized_area_id.is_empty():
		return
	current_area_id = normalized_area_id
	area_input.text = current_area_id
	_sync_zone_dropdown(current_area_id)
	if is_refreshing:
		refresh_pending = true
		return
	is_refreshing = true
	if DEBUG_RTSYNC:
		print("Polling map update...")
	var response: Dictionary = await builder_api.load_zone(current_area_id)
	if not bool(response.get("ok", false)):
		_handle_api_error(response)
		is_refreshing = false
		_call_pending_refresh_if_needed()
		return
	var map_data: Variant = response.get("result", {}).get("map", response.get("result", {}))
	if not (map_data is Dictionary):
		_handle_api_error({"error": "invalid_map_payload"})
		is_refreshing = false
		_call_pending_refresh_if_needed()
		return
	saved_map_data = (map_data as Dictionary).duplicate(true)
	available_zones = _merge_zone_snapshot(available_zones, saved_map_data)
	_sync_zone_dropdown(current_area_id)
	_rebuild_current_map_from_saved()
	_set_status("Zone loaded: %d rooms, %d NPCs." % [
		int(current_map_data.get("rooms", []).size()),
		int(current_map_data.get("npcs", []).size()),
	])
	is_refreshing = false
	_update_action_buttons()
	_call_pending_refresh_if_needed()


func _call_pending_refresh_if_needed() -> void:
	if refresh_pending and builder_mode_enabled and not current_area_id.is_empty():
		refresh_pending = false
		call_deferred("refresh_map")


func _selected_zone_id() -> String:
	var selected_index := zone_dropdown.get_selected_id()
	if selected_index >= 0 and selected_index < zone_dropdown_ids.size():
		return zone_dropdown_ids[selected_index]
	return area_input.text.strip_edges()


func _reload_zone_registry(preferred_zone_id: String = "") -> void:
	if builder_api == null:
		return
	var response: Dictionary = await builder_api.list_zones()
	if bool(response.get("ok", false)):
		var zones_payload = response.get("result", {}).get("zones", {})
		if zones_payload is Dictionary:
			available_zones = _merge_zone_registry_payload(available_zones, zones_payload as Dictionary)
	else:
		var status_code := int(response.get("status", 0))
		var error_code := str(response.get("error", "")).strip_edges().to_lower()
		if status_code != 404 and status_code != 0 and error_code != "invalid_response":
			_handle_api_error(response)
	if not preferred_zone_id.strip_edges().is_empty() and not available_zones.has(preferred_zone_id):
		available_zones[preferred_zone_id] = {
			"name": preferred_zone_id.replace("_", " ").capitalize(),
			"rooms": {},
		}
	_sync_zone_dropdown(preferred_zone_id)
	_update_zone_stub_label()


func _sync_zone_dropdown(preferred_zone_id: String = "") -> void:
	zone_dropdown_ids.clear()
	zone_dropdown.clear()
	var sorted_zone_ids: Array[String] = []
	for zone_id in available_zones.keys():
		sorted_zone_ids.append(str(zone_id))
	sorted_zone_ids.sort()
	for zone_id in sorted_zone_ids:
		zone_dropdown_ids.append(zone_id)
		var zone_payload: Dictionary = (available_zones.get(zone_id, {}) as Dictionary).duplicate(true)
		var zone_name := str(zone_payload.get("name", zone_id)).strip_edges()
		zone_dropdown.add_item("%s (%s)" % [zone_name if not zone_name.is_empty() else zone_id, zone_id])
	zone_dropdown.add_item("+ Create New Zone")
	var selected_zone_id := preferred_zone_id.strip_edges()
	if selected_zone_id.is_empty():
		selected_zone_id = current_area_id
	var selected_index := -1
	for index in range(zone_dropdown_ids.size()):
		if zone_dropdown_ids[index] == selected_zone_id:
			selected_index = index
			break
	if selected_index >= 0:
		zone_dropdown.select(selected_index)
	elif zone_dropdown.item_count > 1:
		zone_dropdown.select(0)
	_update_zone_stub_label()


func _merge_zone_registry_payload(base_zones: Dictionary, incoming_zones: Dictionary) -> Dictionary:
	var merged := base_zones.duplicate(true)
	for zone_id_variant in incoming_zones.keys():
		var zone_id := str(zone_id_variant).strip_edges()
		if zone_id.is_empty():
			continue
		var existing_zone: Dictionary = (merged.get(zone_id, {}) as Dictionary).duplicate(true)
		var incoming_zone: Dictionary = (incoming_zones.get(zone_id, {}) as Dictionary).duplicate(true)
		existing_zone["name"] = str(incoming_zone.get("name", existing_zone.get("name", zone_id))).strip_edges()
		var rooms_payload: Dictionary = (existing_zone.get("rooms", {}) as Dictionary).duplicate(true)
		var incoming_rooms: Dictionary = (incoming_zone.get("rooms", {}) as Dictionary).duplicate(true)
		for room_id_variant in incoming_rooms.keys():
			var room_id := str(room_id_variant).strip_edges()
			if room_id.is_empty():
				continue
			rooms_payload[room_id] = ((incoming_rooms.get(room_id_variant, {}) as Dictionary)).duplicate(true)
		existing_zone["rooms"] = rooms_payload
		merged[zone_id] = existing_zone
	return merged


func _merge_zone_snapshot(base_zones: Dictionary, map_data: Dictionary) -> Dictionary:
	var merged := base_zones.duplicate(true)
	var zone_id := str(map_data.get("zone_id", map_data.get("area_id", current_area_id))).strip_edges()
	if zone_id.is_empty():
		return merged
	var zone_entry: Dictionary = (merged.get(zone_id, {}) as Dictionary).duplicate(true)
	zone_entry["name"] = str(zone_entry.get("name", zone_id.replace("_", " ").capitalize())).strip_edges()
	var rooms_payload: Dictionary = (zone_entry.get("rooms", {}) as Dictionary).duplicate(true)
	for room_variant in map_data.get("rooms", []):
		if not room_variant is Dictionary:
			continue
		var room_data := room_variant as Dictionary
		var room_id := str(room_data.get("id", "")).strip_edges()
		if room_id.is_empty():
			continue
		rooms_payload[room_id] = {
			"id": room_id,
			"name": str(room_data.get("name", room_id)).strip_edges(),
		}
	zone_entry["rooms"] = rooms_payload
	merged[zone_id] = zone_entry
	return merged


func _on_zone_dropdown_selected(index: int) -> void:
	if index < 0:
		return
	if index >= zone_dropdown_ids.size():
		if is_dirty:
			_set_status("Save Map before creating a new zone.")
			_sync_zone_dropdown(current_area_id)
			return
		_open_create_zone_dialog()
		return
	var selected_zone_id := zone_dropdown_ids[index]
	area_input.text = selected_zone_id
	if not builder_mode_enabled or selected_zone_id == current_area_id:
		return
	if is_dirty:
		_set_status("Save Map before switching zones.")
		_sync_zone_dropdown(current_area_id)
		return
	call_deferred("_deferred_refresh_map", selected_zone_id)


func _on_create_zone_pressed() -> void:
	if is_dirty:
		_set_status("Save Map before creating a new zone.")
		return
	_open_create_zone_dialog()


func _open_create_zone_dialog() -> void:
	create_zone_dialog.title = "Create Zone"
	create_zone_dialog.dialog_text = ""
	zone_name_input.text = ""
	zone_id_input.text = ""
	create_zone_dialog.popup_centered()


func _on_zone_name_changed(new_text: String) -> void:
	if not zone_id_input.text.strip_edges().is_empty():
		return
	var slug := new_text.strip_edges().to_lower().replace(" ", "_")
	zone_id_input.text = slug


func _on_create_zone_confirmed() -> void:
	var zone_name := zone_name_input.text.strip_edges()
	var zone_id := zone_id_input.text.strip_edges().to_lower().replace(" ", "_")
	if zone_name.is_empty() or zone_id.is_empty():
		_set_status("Zone name and zone id are required.")
		create_zone_dialog.dialog_text = ""
		create_zone_dialog.popup_centered()
		return
	var response: Dictionary = await builder_api.create_zone(zone_id, zone_name)
	if not bool(response.get("ok", false)):
		_set_status("Create zone failed: %s" % str(response.get("error", "request_failed")))
		create_zone_dialog.dialog_text = ""
		create_zone_dialog.popup_centered()
		_handle_api_error(response)
		return
	create_zone_dialog.title = "Create Zone"
	create_zone_dialog.dialog_text = ""
	await _reload_zone_registry(zone_id)
	await _refresh_map(zone_id, true)


func _sync_live_registries() -> void:
	room_nodes = map_grid.get_room_registry()
	npc_nodes = map_grid.get_npc_registry()
	seen_npcs = npc_nodes.duplicate()


func _handle_api_error(response: Dictionary) -> void:
	print("BUILDER API ERROR:", response)
	_log_builder(str(response), "error")
	if str(response.get("error", "")) == "permission_denied":
		mode_toggle.button_pressed = false
		_set_builder_visible(false)
		_set_status("Builder mode disabled: permission denied.")
		return
	var conflicts = response.get("conflicts", [])
	if conflicts is Array and not conflicts.is_empty():
		var highlighted: Array[String] = []
		var failed_operation = response.get("failed_operation", {})
		if failed_operation is Dictionary:
			for key in ["room_id", "source_id", "target_id"]:
				var room_id := str(failed_operation.get(key, ""))
				if not room_id.is_empty() and not highlighted.has(room_id):
					highlighted.append(room_id)
		map_grid.set_conflict_rooms(highlighted)
		_set_status("Preview failed: %s" % str(conflicts[0].get("message", response.get("error", "request_failed"))))
		return
	var failed_operation_id := str(response.get("failed_operation_id", "")).strip_edges()
	if not failed_operation_id.is_empty():
		_set_status("Preview failed at %s: %s" % [failed_operation_id, str(response.get("error", "request_failed"))])
	else:
		_set_status(str(response.get("error", "request_failed")))


func _set_palette_room_type(room_type: String, apply_to_selected_room: bool = false) -> void:
	selected_palette_room_type = _normalize_palette_room_type(room_type)
	for key in room_type_buttons.keys():
		var button := room_type_buttons[key] as BaseButton
		button.button_pressed = key == selected_palette_room_type
	room_editor.set_room_type(selected_palette_room_type)
	if apply_to_selected_room and not selected_room_id.is_empty():
		_apply_room_type_to_selected_room(selected_palette_room_type)


func _normalize_palette_room_type(room_type: String) -> String:
	var normalized := room_type.strip_edges().to_lower()
	match normalized:
		"forest", "river", "city", "home", "coast", "guild":
			return normalized
		"wilderness":
			return "forest"
		"coastal":
			return "coast"
		"room", "shop", "training":
			return "city"
		_:
			return "forest"


func _on_room_type_button_toggled(enabled: bool, room_type: String) -> void:
	if not enabled:
		return
	_set_palette_room_type(room_type, true)


func _apply_room_type_to_selected_room(room_type: String) -> void:
	if selected_room_id.is_empty():
		return
	var normalized_room_type := _normalize_palette_room_type(room_type)
	var current_room := _get_room_from_cache(selected_room_id)
	if str(current_room.get("room_type", "")).strip_edges().to_lower() == normalized_room_type:
		return
	var diff := {
		"area_id": current_area_id,
		"operations": [
			{
				"id": "type-%s" % selected_room_id,
				"op": "update_room",
				"room_id": selected_room_id,
				"updates": {
					"room_type": normalized_room_type,
				}
			}
		]
	}
	await _stage_previewable_diff_entry(
		diff,
		"Room type updated.",
		"room-type-%s" % selected_room_id,
		{
			"kind": "room_type",
			"room_id": selected_room_id,
		},
	)


func _set_active_context(context_type: String, context_id: String) -> void:
	active_context = {
		"type": context_type.strip_edges().to_lower(),
		"id": context_id.strip_edges(),
	}


func _update_inspector_header() -> void:
	if active_workspace == "npc_templates":
		inspector_title_label.text = "NPC Templates"
		return
	if active_workspace == "item_templates":
		inspector_title_label.text = "Item Templates"
		return
	if not selected_object_id.is_empty():
		var object_data := _find_selected_object_data()
		var object_type := str(object_data.get("type", "item")).strip_edges().to_lower()
		var object_name := str(object_data.get("name", selected_object_id)).strip_edges()
		inspector_title_label.text = "Selected %s %s" % ["NPC" if object_type == "npc" else "Item", object_name if not object_name.is_empty() else selected_object_id]
		return
	if selected_room_id.is_empty():
		inspector_title_label.text = "No room selected"
		return
	inspector_title_label.text = "Selected Room %s" % selected_room_id


func _require_area_id() -> String:
	var normalized_area_id := _selected_zone_id()
	if normalized_area_id.is_empty():
		_set_status("Select a zone before using Builder Mode.")
		return ""
	current_area_id = normalized_area_id
	area_input.text = current_area_id
	return current_area_id


func _generate_room_id() -> String:
	return "room-%d-%d" % [Time.get_unix_time_from_system(), randi() % 100000]


func _get_room_from_cache(room_id: String) -> Dictionary:
	var normalized_room_id := room_id.strip_edges()
	if normalized_room_id.is_empty():
		return {}
	for room_data in current_map_data.get("rooms", []):
		if room_data is Dictionary and str(room_data.get("id", "")) == normalized_room_id:
			return (room_data as Dictionary).duplicate(true)
	return {}


func _get_room_from_zone_cache(zone_id: String, room_id: String) -> Dictionary:
	var normalized_zone_id := zone_id.strip_edges()
	var normalized_room_id := room_id.strip_edges()
	if normalized_zone_id.is_empty() or normalized_room_id.is_empty():
		return {}
	if normalized_zone_id == current_area_id:
		return _get_room_from_cache(normalized_room_id)
	var zone_payload: Dictionary = (available_zones.get(normalized_zone_id, {}) as Dictionary).duplicate(true)
	var room_payload: Dictionary = ((zone_payload.get("rooms", {}) as Dictionary).get(normalized_room_id, {}) as Dictionary).duplicate(true)
	if room_payload.is_empty():
		return {}
	return room_payload


func _normalize_exit_target(raw_target: Variant, fallback_zone_id: String) -> Dictionary:
	if raw_target is Dictionary:
		return {
			"zone_id": str((raw_target as Dictionary).get("zone_id", fallback_zone_id)).strip_edges(),
			"room_id": str((raw_target as Dictionary).get("room_id", "")).strip_edges(),
		}
	return {
		"zone_id": fallback_zone_id,
		"room_id": str(raw_target).strip_edges(),
	}


func _get_selected_npc_target(room_data: Dictionary) -> Dictionary:
	if selected_object_id.is_empty():
		return {}
	return _find_object_in_contents((room_data.get("contents", []) as Array), selected_object_id, "npc")


func _find_selected_object_data() -> Dictionary:
	if selected_object_id.is_empty():
		return {}
	var room_id := _find_room_id_for_object(selected_object_id)
	if room_id.is_empty():
		return {}
	var room_data := _get_room_from_cache(room_id)
	if room_data.is_empty():
		return {}
	return _find_object_in_contents((room_data.get("contents", []) as Array), selected_object_id)


func _find_room_id_for_object(object_id: String) -> String:
	var normalized_object_id := object_id.strip_edges()
	if normalized_object_id.is_empty():
		return ""
	for room_variant in current_map_data.get("rooms", []):
		if not room_variant is Dictionary:
			continue
		var room_data := room_variant as Dictionary
		if not _find_object_in_contents((room_data.get("contents", []) as Array), normalized_object_id).is_empty():
			return str(room_data.get("id", "")).strip_edges()
	return ""


func _find_object_in_contents(contents: Array, object_id: String, expected_type: String = "") -> Dictionary:
	for entry in contents:
		if not entry is Dictionary:
			continue
		var object_data := (entry as Dictionary).duplicate(true)
		var entry_id := str(object_data.get("object_id", object_data.get("id", ""))).strip_edges()
		if entry_id == object_id:
			var object_type := str(object_data.get("type", "item")).strip_edges().to_lower()
			if expected_type.is_empty() or object_type == expected_type:
				return object_data
		var nested_match := _find_object_in_contents((object_data.get("contents", []) as Array), object_id, expected_type)
		if not nested_match.is_empty():
			return nested_match
	return {}


func _open_room_editor(room_id: String) -> void:
	var room_data := _get_room_from_cache(room_id)
	if room_data.is_empty():
		room_editor.clear_room()
		instance_editor.clear_editor()
		content_tree.clear_tree()
		return
	_set_workspace("inspector")
	map_grid.set_selected_room(room_id)
	room_editor.load_room(room_data, current_area_id, selected_exit_id, _get_zone_options_for_editor())
	room_editor.set_room_type(_normalize_palette_room_type(str(room_data.get("room_type", "room"))))
	_show_inspector_context()
	content_tree.rebuild(room_data)
	content_tree.visible = true


func _show_inspector_context() -> void:
	var showing_object := not selected_object_id.is_empty()
	room_editor.visible = not showing_object
	instance_editor.visible = showing_object
	template_selector.visible = false
	content_tree.visible = true
	if not showing_object:
		instance_editor.clear_editor()
	_update_inspector_header()


func _show_template_selector_context(title: String) -> void:
	room_editor.visible = false
	instance_editor.visible = false
	content_tree.visible = false
	template_selector.visible = false
	inspector_title_label.text = title
	inspector_state_label.text = "DBV2 TODO: replace with library system."


func _open_instance_editor(object_id: String) -> void:
	selected_object_id = object_id.strip_edges()
	if selected_object_id.is_empty():
		_show_inspector_context()
		if not selected_room_id.is_empty():
			_open_room_editor(selected_room_id)
		return
	var room_id := _find_room_id_for_object(selected_object_id)
	if room_id.is_empty():
		instance_editor.clear_editor()
		return
	selected_room_id = room_id
	selected_exit_id = ""
	map_grid.set_selected_room(selected_room_id)
	map_grid.set_selected_object(selected_object_id)
	var room_data := _get_room_from_cache(selected_room_id)
	if room_data.is_empty():
		instance_editor.clear_editor()
		return
	content_tree.rebuild(room_data)
	content_tree.select_object(selected_object_id)
	var object_data := _find_selected_object_data()
	if object_data.is_empty():
		instance_editor.clear_editor()
		return
	_set_workspace("inspector")
	_show_inspector_context()
	instance_editor.load_object(object_data, selected_room_id)


func _get_zone_options_for_editor() -> Dictionary:
	return _merge_zone_snapshot(available_zones, current_map_data)


func _get_exit_detail_from_room(room_data: Dictionary, exit_id: String) -> Dictionary:
	var normalized_exit_id := exit_id.strip_edges()
	if normalized_exit_id.is_empty():
		return {}
	for raw_exit in room_data.get("exit_details", []):
		if raw_exit is Dictionary and str(raw_exit.get("id", "")).strip_edges() == normalized_exit_id:
			return (raw_exit as Dictionary).duplicate(true)
	var fallback_exits: Dictionary = (room_data.get("exits", {}) as Dictionary).duplicate(true)
	for direction in fallback_exits.keys():
		var synthetic_id := "legacy:%s:%s" % [str(room_data.get("id", "")).strip_edges(), str(direction).strip_edges().to_lower()]
		if synthetic_id == normalized_exit_id:
			var target := _normalize_exit_target(fallback_exits.get(direction, ""), current_area_id)
			return {
				"id": synthetic_id,
				"direction": str(direction).strip_edges().to_lower(),
				"target": target,
				"label": "",
				"aliases": [],
			}
	return {}


func _on_room_editor_exit_selected(exit_id: String) -> void:
	selected_exit_id = exit_id.strip_edges()
	if selected_exit_id.is_empty():
		_set_active_context("room" if not selected_room_id.is_empty() else "", selected_room_id)
	else:
		_set_active_context("exit", selected_exit_id)


func _on_room_editor_draft_changed(room_id: String, updates: Dictionary) -> void:
	if not is_builder:
		return
	var normalized_room_id := room_id.strip_edges()
	if normalized_room_id.is_empty():
		return
	var diff := {
		"area_id": current_area_id,
		"operations": [
			{
				"id": "update-%s" % normalized_room_id,
				"op": "update_room",
				"room_id": normalized_room_id,
				"updates": updates.duplicate(true),
			}
		]
	}
	var replace_last := false
	if not operation_journal.is_empty():
		var last_entry: Dictionary = operation_journal[operation_journal.size() - 1]
		replace_last = str(last_entry.get("kind", "")) == "room_update" and str(last_entry.get("room_id", "")) == normalized_room_id
	await _stage_previewable_diff_entry(
		diff,
		"Room updated.",
		"room-update-%s" % normalized_room_id,
		{
			"kind": "room_update",
			"room_id": normalized_room_id,
		},
		replace_last,
	)


func _on_room_editor_save_requested(room_id: String, updates: Dictionary) -> void:
	if not is_builder:
		return
	_on_room_editor_draft_changed(room_id, updates)
	_set_status("Room update staged. Save Map to persist.")


func _on_room_editor_close_requested() -> void:
	if not is_builder:
		return
	room_editor.visible = false


func _on_room_editor_add_npc_requested() -> void:
	if not is_builder:
		return
	if selected_room_id.is_empty():
		_set_status("Select a room before adding an NPC.")
		return
	_set_status("DBV2 TODO: NPC library system not wired yet.")


func _on_room_editor_add_item_requested() -> void:
	if not is_builder:
		return
	if selected_room_id.is_empty():
		_set_status("Select a room before adding an item.")
		return
	_set_status("DBV2 TODO: Item library system not wired yet.")


func _on_room_editor_exit_save_requested(room_id: String, exit_id: String, fields: Dictionary) -> void:
	if not is_builder:
		return
	var area_id := _require_area_id()
	if area_id.is_empty():
		return
	var normalized_room_id := room_id.strip_edges()
	var normalized_exit_id := exit_id.strip_edges()
	var source_room := _get_room_from_cache(normalized_room_id)
	if normalized_room_id.is_empty() or normalized_exit_id.is_empty() or source_room.is_empty():
		_set_status("Exit update requires a selected exit.")
		return
	var existing_exit := _get_exit_detail_from_room(source_room, normalized_exit_id)
	if existing_exit.is_empty():
		_set_status("Selected exit could not be found.")
		return
	var previous_direction := str(existing_exit.get("direction", "")).strip_edges().to_lower()
	var previous_target := _normalize_exit_target(existing_exit.get("target", {}), current_area_id)
	var previous_target_zone_id := str(previous_target.get("zone_id", current_area_id)).strip_edges()
	var previous_target_room_id := str(previous_target.get("room_id", "")).strip_edges()
	var normalized_direction := str(fields.get("direction", previous_direction)).strip_edges().to_lower()
	var normalized_target_zone_id := str(fields.get("target_zone_id", previous_target_zone_id)).strip_edges()
	var normalized_target_room_id := str(fields.get("target_room_id", previous_target_room_id)).strip_edges()
	if normalized_direction.is_empty() or normalized_target_room_id.is_empty():
		_set_status("Exit update requires a direction and target room.")
		return
	if normalized_target_zone_id == current_area_id and normalized_target_room_id == normalized_room_id:
		_set_status("Exit target cannot be the same room.")
		return
	var target_room := _get_room_from_zone_cache(normalized_target_zone_id, normalized_target_room_id)
	if source_room.is_empty() or target_room.is_empty():
		_set_status("Exit target room was not found in the selected zone.")
		return
	var reverse_direction := _opposite_direction(normalized_direction)
	var previous_reverse_direction := _opposite_direction(previous_direction)
	var normalized_label := str(fields.get("label", existing_exit.get("label", ""))).strip_edges()
	var normalized_aliases: Array[String] = []
	for raw_alias in fields.get("aliases", []):
		var alias := str(raw_alias).strip_edges()
		if not alias.is_empty() and not normalized_aliases.has(alias):
			normalized_aliases.append(alias)
	var operations: Array[Dictionary] = []
	var exit_changed := previous_direction != normalized_direction or previous_target_room_id != normalized_target_room_id or previous_target_zone_id != normalized_target_zone_id
	if exit_changed and previous_target_zone_id == current_area_id and not previous_reverse_direction.is_empty() and not previous_target_room_id.is_empty():
		operations.append(
			{
				"id": "delete-exit-%s-%s" % [previous_target_room_id, previous_reverse_direction],
				"op": "delete_exit",
				"source_id": previous_target_room_id,
				"direction": previous_reverse_direction,
			}
		)
	if normalized_exit_id.begins_with("pending:") or normalized_exit_id.begins_with("legacy:"):
		if not normalized_label.is_empty() or not normalized_aliases.is_empty():
			_set_status("Save Map before editing labels or aliases on newly staged exits.")
			return
		operations.append(
			{
				"id": "exit-%s-%s" % [normalized_room_id, normalized_direction],
				"op": "set_exit",
				"source_id": normalized_room_id,
				"direction": normalized_direction,
				"target_id": normalized_target_room_id,
				"target_zone_id": normalized_target_zone_id,
			}
		)
	else:
		operations.append(
			{
				"id": "update-exit-%s" % normalized_exit_id,
				"op": "update_exit",
				"exit_id": normalized_exit_id,
				"fields": {
					"direction": normalized_direction,
					"target_id": normalized_target_room_id,
					"target_zone_id": normalized_target_zone_id,
					"label": normalized_label,
					"aliases": normalized_aliases,
				},
			}
		)
	if exit_changed and normalized_target_zone_id == current_area_id and not reverse_direction.is_empty():
		operations.append(
			{
				"id": "exit-%s-%s" % [normalized_target_room_id, reverse_direction],
				"op": "set_exit",
				"source_id": normalized_target_room_id,
				"direction": reverse_direction,
				"target_id": normalized_room_id,
			}
		)
	var diff := {
		"area_id": area_id,
		"operations": operations,
	}
	var staged := await _stage_previewable_diff(diff, "Exit updated.", "edit-exit-%d" % Time.get_unix_time_from_system())
	if staged:
		selected_exit_id = normalized_exit_id
		select_room(normalized_room_id)


func _on_room_editor_exit_delete_requested(room_id: String, exit_id: String) -> void:
	if not is_builder:
		return
	var normalized_room_id := room_id.strip_edges()
	var normalized_exit_id := exit_id.strip_edges()
	if normalized_room_id.is_empty() or normalized_exit_id.is_empty():
		return
	var source_room := _get_room_from_cache(normalized_room_id)
	if source_room.is_empty():
		_set_status("Selected room is unavailable.")
		return
	var exit_detail := _get_exit_detail_from_room(source_room, normalized_exit_id)
	if exit_detail.is_empty():
		_set_status("Selected exit is unavailable.")
		return
	var normalized_direction := str(exit_detail.get("direction", "")).strip_edges().to_lower()
	var target := _normalize_exit_target(exit_detail.get("target", {}), current_area_id)
	var target_zone_id := str(target.get("zone_id", current_area_id)).strip_edges()
	var target_room_id := str(target.get("room_id", "")).strip_edges()
	if target_zone_id == current_area_id:
		await _on_exit_clicked(normalized_room_id, normalized_direction, target_room_id)
	else:
		var diff := {
			"area_id": current_area_id,
			"operations": [
				{
					"id": "delete-exit-%s-%s" % [normalized_room_id, normalized_direction],
					"op": "delete_exit",
					"source_id": normalized_room_id,
					"direction": normalized_direction,
				}
			]
		}
		await _stage_previewable_diff(diff, "Exit deleted.")
	selected_exit_id = ""
	select_room(normalized_room_id)


func _on_template_selector_closed() -> void:
	template_selector.visible = false
	_show_inspector_context()


func _on_template_chosen(template_id: String, destination_id: String, template_type: String, _destination_kind: String) -> void:
	if destination_id.strip_edges().is_empty():
		_set_status("Selected destination is unavailable.")
		return
	var preview_template := await _resolve_template_preview(template_id, template_type)
	var preview_object_id := "preview-spawn-%d-%d" % [Time.get_unix_time_from_system(), randi() % 100000]
	var diff := {
		"area_id": current_area_id,
		"operations": [
			{
				"id": "spawn-template-%s" % preview_object_id,
				"op": "spawn_template",
				"template_id": template_id,
				"location_id": destination_id,
				"template_type": str(preview_template.get("type", template_type)).strip_edges().to_lower(),
				"template_name": str(preview_template.get("name", template_id)),
				"preview_object_id": preview_object_id,
			}
		]
	}
	var staged := await _stage_previewable_diff(diff, "Template staged.", "spawn-template-%d" % Time.get_unix_time_from_system())
	if not staged:
		return
	select_room(selected_room_id)
	select_object(preview_object_id)


func _on_content_tree_object_selected(object_id: String, object_data: Dictionary) -> void:
	if not is_builder:
		return
	var normalized_object_id := object_id.strip_edges()
	if normalized_object_id.is_empty():
		return
	if move_mode and not selected_object_id.is_empty() and normalized_object_id != selected_object_id:
		var relation := "on" if bool(object_data.get("is_surface", false)) else "in"
		await move_selected_object(normalized_object_id, relation)
		return
	var object_type := str(object_data.get("type", "item")).strip_edges().to_lower()
	_request_context_switch("npc" if object_type == "npc" else "item", normalized_object_id, func() -> void:
		select_object(normalized_object_id)
	)


func _on_map_object_selected(object_id: String, _target_id: String, _relation: String) -> void:
	if not is_builder or active_tool != ToolMode.SELECT:
		return
	await handle_canvas_click("", {}, Vector2.ZERO, object_id)


func _on_canvas_object_selected(object_id: String) -> void:
	var object_data := _find_object_anywhere(object_id)
	var object_type := str(object_data.get("type", "item")).strip_edges().to_lower()
	_request_context_switch("npc" if object_type == "npc" else "item", object_id, func() -> void:
		select_object(object_id)
	)


func _on_map_object_drop_requested(object_id: String, destination_id: String, relation: String) -> void:
	if not is_builder:
		return
	var normalized_object_id := object_id.strip_edges()
	if normalized_object_id.is_empty():
		return
	if selected_object_id != normalized_object_id:
		select_object(normalized_object_id)
	await move_selected_object(destination_id, relation)


func _on_content_tree_delete_requested(object_id: String) -> void:
	if not is_builder:
		return
	var normalized_object_id := object_id.strip_edges()
	if normalized_object_id.is_empty():
		return
	var diff := {
		"area_id": current_area_id,
		"operations": [
			{
				"id": "delete-object-%s" % normalized_object_id,
				"op": "delete_object",
				"object_id": normalized_object_id,
			}
		]
	}
	var staged := await _stage_previewable_diff(diff, "Object delete staged.", "delete-object-%d" % Time.get_unix_time_from_system())
	if not staged:
		return
	if selected_object_id == normalized_object_id:
		select_object("")


func _on_instance_editor_save_requested(object_id: String, updates: Dictionary) -> void:
	if not is_builder:
		return
	var normalized_object_id := object_id.strip_edges()
	if normalized_object_id.is_empty():
		return
	var area_id := _require_area_id()
	if area_id.is_empty():
		return
	var diff := {
		"area_id": area_id,
		"operations": [
			{
				"id": "update-object-%s" % normalized_object_id,
				"op": "update_object",
				"object_id": normalized_object_id,
				"object": updates,
			}
		]
	}
	var staged := await _stage_previewable_diff(diff, "Object update staged.", "update-object-%d" % Time.get_unix_time_from_system())
	if staged:
		select_object(normalized_object_id)


func _on_instance_editor_edit_template_requested(template_id: String, object_type: String) -> void:
	var _unused_template_id := template_id
	var _unused_object_type := object_type
	_set_status("DBV2 TODO: template editor replaced by library system.")


func _on_instance_editor_delete_requested(object_id: String) -> void:
	await _on_content_tree_delete_requested(object_id)


func _on_instance_editor_back_requested() -> void:
	select_object("")


func _open_template_workspace(object_type: String, template_id: String = "") -> void:
	# TODO: DBV2 replace with library system
	var _unused_object_type := object_type
	var _unused_template_id := template_id
	_set_status("DBV2 TODO: template workspaces disabled during shell refactor.")


func _on_template_workspace_closed() -> void:
	_set_active_context("room" if not selected_room_id.is_empty() else "", selected_room_id)
	_set_workspace("inspector")
	_show_inspector_context()


func move_selected_object(destination_id: String, relation: String = "in") -> void:
	if not is_builder:
		return
	if selected_object_id.is_empty():
		return
	var area_id := _require_area_id()
	if area_id.is_empty():
		return
	var diff := {
		"area_id": area_id,
		"operations": [
			{
				"id": "move-object-%s" % selected_object_id,
				"op": "move_object",
				"object_id": selected_object_id,
				"destination_id": destination_id.strip_edges(),
				"relation": relation.strip_edges().to_lower(),
			}
		]
	}
	var staged := await _stage_previewable_diff(diff, "Object moved.", "move-object-%d" % Time.get_unix_time_from_system())
	if not staged:
		return
	select_object("")


func _rebuild_current_map_from_saved() -> void:
	current_map_data = rebuild_from_journal()
	map_grid.apply_map_update(current_map_data)
	_sync_live_registries()
	_sync_selection_after_map_update()


func rebuild_from_journal() -> Dictionary:
	var rebuilt_map := saved_map_data.duplicate(true)
	for entry in operation_journal:
		for operation in entry.get("ops", []):
			if not operation is Dictionary:
				continue
			var op_dict := operation as Dictionary
			var validation_error := validate_op(rebuilt_map, op_dict)
			if not validation_error.is_empty():
				_log_builder("Journal rebuild skipped invalid op: %s" % validation_error, "warn")
				continue
			apply_op(rebuilt_map, op_dict)
	return rebuilt_map


func _canonicalize_diff(diff: Dictionary) -> Array[Dictionary]:
	var operations: Array[Dictionary] = []
	for raw_operation in diff.get("operations", []):
		if raw_operation is Dictionary:
			operations.append(_canonicalize_operation(raw_operation as Dictionary))
	return operations


func _canonicalize_operation(operation: Dictionary) -> Dictionary:
	var op_type := str(operation.get("op", "")).strip_edges().to_lower()
	match op_type:
		"create_room":
			var room_payload: Dictionary = (operation.get("room", {}) as Dictionary).duplicate(true)
			return BuilderOpsScript.make_op("create", "room", str(room_payload.get("id", "")).strip_edges(), {"room": room_payload}, {"before": {}})
		"update_room":
			var room_id := str(operation.get("room_id", "")).strip_edges()
			var updates: Dictionary = (operation.get("updates", {}) as Dictionary).duplicate(true)
			var before_room := _snapshot_room_state(room_id)
			var before_updates := {}
			for key in updates.keys():
				before_updates[key] = before_room.get(key)
			return BuilderOpsScript.make_op("update", "room", room_id, {"updates": updates}, {"before": {"updates": before_updates, "room": before_room}})
		"delete_room":
			var delete_room_id := str(operation.get("room_id", "")).strip_edges()
			return BuilderOpsScript.make_op("delete", "room", delete_room_id, {"room": _snapshot_room_state(delete_room_id)}, {"before": {"room": _snapshot_room_state(delete_room_id)}})
		"set_exit":
			var source_id := str(operation.get("source_id", "")).strip_edges()
			var direction := str(operation.get("direction", "")).strip_edges().to_lower()
			var existing_exit := _snapshot_exit_state(source_id, direction)
			var op_name := "create" if existing_exit.is_empty() else "update"
			return BuilderOpsScript.make_op(op_name, "exit", "%s:%s" % [source_id, direction], {
				"source_id": source_id,
				"direction": direction,
				"target_id": str(operation.get("target_id", "")).strip_edges(),
				"target_zone_id": str(operation.get("target_zone_id", current_area_id)).strip_edges(),
				"label": str(operation.get("label", existing_exit.get("label", ""))).strip_edges(),
				"aliases": (operation.get("aliases", existing_exit.get("aliases", [])) as Array).duplicate(true),
			}, {"before": existing_exit})
		"update_exit":
			var exit_id := str(operation.get("exit_id", "")).strip_edges()
			var before_exit := _find_exit_by_id(exit_id)
			return BuilderOpsScript.make_op("update", "exit", exit_id, {
				"source_id": str(before_exit.get("source_id", "")).strip_edges(),
				"direction": str((operation.get("fields", {}) as Dictionary).get("direction", before_exit.get("direction", ""))).strip_edges().to_lower(),
				"target_id": str((operation.get("fields", {}) as Dictionary).get("target_id", before_exit.get("target", {}).get("room_id", ""))).strip_edges(),
				"target_zone_id": str((operation.get("fields", {}) as Dictionary).get("target_zone_id", before_exit.get("target", {}).get("zone_id", current_area_id))).strip_edges(),
				"label": str((operation.get("fields", {}) as Dictionary).get("label", before_exit.get("label", ""))).strip_edges(),
				"aliases": (((operation.get("fields", {}) as Dictionary).get("aliases", before_exit.get("aliases", []))) as Array).duplicate(true),
			}, {"before": before_exit})
		"delete_exit":
			var delete_source_id := str(operation.get("source_id", "")).strip_edges()
			var delete_direction := str(operation.get("direction", "")).strip_edges().to_lower()
			var delete_exit := _snapshot_exit_state(delete_source_id, delete_direction)
			return BuilderOpsScript.make_op("delete", "exit", str(delete_exit.get("id", "%s:%s" % [delete_source_id, delete_direction])).strip_edges(), delete_exit, {"before": delete_exit})
		"update_object":
			var update_object_id := str(operation.get("object_id", "")).strip_edges()
			var existing_object := _snapshot_object_state(update_object_id)
			var entity_type := str(existing_object.get("object", {}).get("type", "item")).strip_edges().to_lower()
			var object_fields: Dictionary = (operation.get("object", {}) as Dictionary).duplicate(true)
			var before_fields := {}
			for key in object_fields.keys():
				before_fields[key] = (existing_object.get("object", {}) as Dictionary).get(key)
			return BuilderOpsScript.make_op("update", entity_type if entity_type == "npc" else "item", update_object_id, {"fields": object_fields}, {"before": {"fields": before_fields, "object_state": existing_object}})
		"delete_object":
			var delete_object_id := str(operation.get("object_id", "")).strip_edges()
			var deleted_object := _snapshot_object_state(delete_object_id)
			var deleted_type := str((deleted_object.get("object", {}) as Dictionary).get("type", "item")).strip_edges().to_lower()
			return BuilderOpsScript.make_op("delete", deleted_type if deleted_type == "npc" else "item", delete_object_id, deleted_object, {"before": deleted_object})
		"move_object":
			var move_object_id := str(operation.get("object_id", "")).strip_edges()
			var moved_object := _snapshot_object_state(move_object_id)
			var moved_type := str((moved_object.get("object", {}) as Dictionary).get("type", "item")).strip_edges().to_lower()
			return BuilderOpsScript.make_op("update", moved_type if moved_type == "npc" else "item", move_object_id, {
				"destination_id": str(operation.get("destination_id", "")).strip_edges(),
				"relation": str(operation.get("relation", "in")).strip_edges().to_lower(),
			}, {"before": {"object_state": moved_object}})
		"spawn_template":
			var preview_object_id := str(operation.get("preview_object_id", "")).strip_edges()
			var template_type := str(operation.get("template_type", "item")).strip_edges().to_lower()
			return BuilderOpsScript.make_op("create", template_type if template_type == "npc" else "item", preview_object_id, operation.duplicate(true), {"before": {}})
		_:
			return BuilderOpsScript.make_op("update", "zone", str(operation.get("id", "")).strip_edges(), operation.duplicate(true), {"before": {}})


func _snapshot_room_state(room_id: String) -> Dictionary:
	return _get_room_from_cache(room_id)


func _snapshot_exit_state(source_id: String, direction: String = "", exit_id: String = "") -> Dictionary:
	var room_data := _get_room_from_cache(source_id)
	if room_data.is_empty():
		return {}
	if not exit_id.strip_edges().is_empty():
		var exit_detail := _get_exit_detail_from_room(room_data, exit_id)
		if not exit_detail.is_empty():
			exit_detail["source_id"] = source_id
			return exit_detail
	var normalized_direction := direction.strip_edges().to_lower()
	if normalized_direction.is_empty():
		return {}
	for exit_detail_variant in _get_local_exit_details(room_data):
		if not exit_detail_variant is Dictionary:
			continue
		var exit_detail := (exit_detail_variant as Dictionary).duplicate(true)
		if str(exit_detail.get("direction", "")).strip_edges().to_lower() != normalized_direction:
			continue
		exit_detail["source_id"] = source_id
		return exit_detail
	return {}


func _snapshot_object_state(object_id: String) -> Dictionary:
	var normalized_object_id := object_id.strip_edges()
	if normalized_object_id.is_empty():
		return {}
	var room_id := _find_room_id_for_object(normalized_object_id)
	if room_id.is_empty():
		return {}
	var room_data := _get_room_from_cache(room_id)
	var object_data := _find_object_in_contents((room_data.get("contents", []) as Array), normalized_object_id)
	if object_data.is_empty():
		return {}
	return {
		"room_id": room_id,
		"object": object_data,
	}


func apply_op(map_data: Dictionary, operation: Dictionary) -> void:
	match str(operation.get("entity_type", "")).strip_edges().to_lower():
		"room":
			_apply_room_op(map_data, operation)
		"exit":
			_apply_exit_op(map_data, operation)
		"npc":
			_apply_npc_op(map_data, operation)
		"item":
			_apply_item_op(map_data, operation)
		"zone":
			_apply_zone_op(map_data, operation)


func _apply_room_op(map_data: Dictionary, operation: Dictionary) -> void:
	var normalized_op := str(operation.get("op", "")).strip_edges().to_lower()
	var room_id := str(operation.get("entity_id", "")).strip_edges()
	var payload: Dictionary = (operation.get("payload", {}) as Dictionary).duplicate(true)
	match normalized_op:
		"create":
			var rooms_value = map_data.get("rooms", [])
			if rooms_value is Array:
				var room_payload: Dictionary = (payload.get("room", {}) as Dictionary).duplicate(true)
				room_payload["exits"] = (room_payload.get("exits", {}) as Dictionary).duplicate(true)
				room_payload["contents"] = (room_payload.get("contents", []) as Array).duplicate(true)
				room_payload["exit_details"] = _get_local_exit_details(room_payload)
				rooms_value.append(room_payload)
				map_data["rooms"] = rooms_value
		"update":
			var room_index := _find_room_index_in_map(map_data, room_id)
			if room_index < 0:
				return
			var rooms_array = map_data.get("rooms", [])
			var room_data: Dictionary = (rooms_array[room_index] as Dictionary).duplicate(true)
			for key in (payload.get("updates", {}) as Dictionary).keys():
				room_data[key] = (payload.get("updates", {}) as Dictionary).get(key)
			rooms_array[room_index] = room_data
			map_data["rooms"] = rooms_array
		"delete":
			var updated_rooms: Array = []
			for room_variant in map_data.get("rooms", []):
				if not room_variant is Dictionary:
					continue
				var room_dict: Dictionary = (room_variant as Dictionary).duplicate(true)
				if str(room_dict.get("id", "")).strip_edges() == room_id:
					continue
				var exits_dict: Dictionary = (room_dict.get("exits", {}) as Dictionary).duplicate(true)
				for exit_direction in exits_dict.keys():
					var delete_target := _normalize_exit_target(exits_dict.get(exit_direction, ""), current_area_id)
					if str(delete_target.get("zone_id", current_area_id)).strip_edges() == current_area_id and str(delete_target.get("room_id", "")).strip_edges() == room_id:
						exits_dict.erase(exit_direction)
				room_dict["exits"] = exits_dict
				updated_rooms.append(room_dict)
			map_data["rooms"] = updated_rooms


func _apply_exit_op(map_data: Dictionary, operation: Dictionary) -> void:
	var normalized_op := str(operation.get("op", "")).strip_edges().to_lower()
	var exit_id := str(operation.get("entity_id", "")).strip_edges()
	var payload: Dictionary = (operation.get("payload", {}) as Dictionary).duplicate(true)
	match normalized_op:
		"create":
			_upsert_exit_in_map(map_data, payload, "pending:%s:%s" % [str(payload.get("source_id", "")).strip_edges(), str(payload.get("direction", "")).strip_edges().to_lower()])
		"update":
			_upsert_exit_in_map(map_data, payload, exit_id)
		"delete":
			var source_id := str(payload.get("source_id", operation.get("meta", {}).get("before", {}).get("source_id", ""))).strip_edges()
			var direction := str(payload.get("direction", operation.get("meta", {}).get("before", {}).get("direction", ""))).strip_edges().to_lower()
			_delete_exit_from_map(map_data, source_id, direction)


func _apply_npc_op(map_data: Dictionary, operation: Dictionary) -> void:
	_apply_object_entity_op(map_data, operation, "npc")


func _apply_item_op(map_data: Dictionary, operation: Dictionary) -> void:
	_apply_object_entity_op(map_data, operation, "item")


func _apply_zone_op(map_data: Dictionary, operation: Dictionary) -> void:
	var _unused := map_data
	var _unused_operation := operation


func _apply_object_entity_op(map_data: Dictionary, operation: Dictionary, entity_type: String) -> void:
	var normalized_op := str(operation.get("op", "")).strip_edges().to_lower()
	var object_id := str(operation.get("entity_id", "")).strip_edges()
	var payload: Dictionary = (operation.get("payload", {}) as Dictionary).duplicate(true)
	match normalized_op:
		"create":
			_apply_spawn_payload(map_data, payload)
		"update":
			if payload.has("destination_id"):
				var object_payload := _remove_object_from_rooms(map_data, object_id)
				if object_payload.is_empty():
					return
				_insert_object_into_destination(map_data, object_payload, str(payload.get("destination_id", "")).strip_edges())
			else:
				_apply_object_updates_by_fields(map_data, object_id, (payload.get("fields", {}) as Dictionary).duplicate(true))
		"delete":
			_remove_object_from_rooms(map_data, object_id)
			if entity_type == "npc":
				var npcs = map_data.get("npcs", [])
				if npcs is Array:
					var filtered_npcs: Array = []
					for npc in npcs:
						if npc is Dictionary and str((npc as Dictionary).get("id", "")).strip_edges() == object_id:
							continue
						filtered_npcs.append(npc)
					map_data["npcs"] = filtered_npcs


func validate_op(map_data: Dictionary, operation: Dictionary) -> String:
	var normalized_op := str(operation.get("op", "")).strip_edges().to_lower()
	var entity_type := str(operation.get("entity_type", "")).strip_edges().to_lower()
	var entity_id := str(operation.get("entity_id", "")).strip_edges()
	var payload: Dictionary = (operation.get("payload", {}) as Dictionary).duplicate(true)
	match entity_type:
		"room":
			if normalized_op == "create" and _find_room_index_in_map(map_data, entity_id) >= 0:
				return "Room already exists."
			if normalized_op != "create" and _find_room_index_in_map(map_data, entity_id) < 0:
				return "Room is unavailable."
		"exit":
			var source_id := str(payload.get("source_id", operation.get("meta", {}).get("before", {}).get("source_id", ""))).strip_edges()
			var direction := str(payload.get("direction", operation.get("meta", {}).get("before", {}).get("direction", ""))).strip_edges().to_lower()
			if source_id.is_empty() or _find_room_index_in_map(map_data, source_id) < 0:
				return "Exit source room is unavailable."
			if normalized_op != "delete":
				var target_zone_id := str(payload.get("target_zone_id", current_area_id)).strip_edges()
				var target_id := str(payload.get("target_id", "")).strip_edges()
				if target_id.is_empty():
					return "Exit target room is required."
				if target_zone_id == current_area_id and _find_room_index_in_map(map_data, target_id) < 0:
					return "Exit target room was not found."
				if direction.is_empty():
					return "Exit direction is required."
		"npc", "item":
			if normalized_op != "create" and _find_object_anywhere_in_map(map_data, entity_id).is_empty():
				return "%s is unavailable." % ("NPC" if entity_type == "npc" else "Item")
			if normalized_op == "update" and payload.has("destination_id"):
				var destination_id := str(payload.get("destination_id", "")).strip_edges()
				if destination_id.is_empty() or _find_room_id_for_destination(map_data, destination_id).is_empty():
					return "Move destination is unavailable."
			if normalized_op == "create":
				var location_id := str(payload.get("location_id", "")).strip_edges()
				if location_id.is_empty() or _find_room_id_for_destination(map_data, location_id).is_empty():
					return "Spawn destination is unavailable."
	return ""


func _find_exit_by_id(exit_id: String) -> Dictionary:
	var normalized_exit_id := exit_id.strip_edges()
	if normalized_exit_id.is_empty():
		return {}
	for room_variant in current_map_data.get("rooms", []):
		if not room_variant is Dictionary:
			continue
		var exit_detail := _get_exit_detail_from_room(room_variant as Dictionary, normalized_exit_id)
		if not exit_detail.is_empty():
			exit_detail["source_id"] = str((room_variant as Dictionary).get("id", "")).strip_edges()
			return exit_detail
	return {}


func _find_object_anywhere(object_id: String) -> Dictionary:
	return _find_object_anywhere_in_map(current_map_data, object_id)


func _find_object_anywhere_in_map(map_data: Dictionary, object_id: String) -> Dictionary:
	var normalized_object_id := object_id.strip_edges()
	if normalized_object_id.is_empty():
		return {}
	for room_variant in map_data.get("rooms", []):
		if not room_variant is Dictionary:
			continue
		var room_data := room_variant as Dictionary
		var object_data := _find_object_in_contents((room_data.get("contents", []) as Array), normalized_object_id)
		if not object_data.is_empty():
			return object_data
	return {}


func _find_room_index_in_map(map_data: Dictionary, room_id: String) -> int:
	var normalized_room_id := room_id.strip_edges()
	for index in range((map_data.get("rooms", []) as Array).size()):
		var room_variant = map_data.get("rooms", [])[index]
		if room_variant is Dictionary and str(room_variant.get("id", "")).strip_edges() == normalized_room_id:
			return index
	return -1


func _get_local_exit_details(room_data: Dictionary) -> Array:
	var raw_exit_details = room_data.get("exit_details", [])
	if raw_exit_details is Array and not raw_exit_details.is_empty():
		var details: Array = []
		for raw_exit_detail in raw_exit_details:
			if raw_exit_detail is Dictionary:
				details.append((raw_exit_detail as Dictionary).duplicate(true))
		return details
	var fallback_details: Array = []
	var fallback_exits: Dictionary = (room_data.get("exits", {}) as Dictionary).duplicate(true)
	for direction in fallback_exits.keys():
		var target := _normalize_exit_target(fallback_exits.get(direction, ""), current_area_id)
		fallback_details.append(
			{
				"id": "legacy:%s:%s" % [str(room_data.get("id", "")).strip_edges(), str(direction).strip_edges().to_lower()],
				"direction": str(direction).strip_edges().to_lower(),
				"target": target,
				"label": "",
				"aliases": [],
			}
		)
	return fallback_details


func _upsert_exit_in_map(map_data: Dictionary, payload: Dictionary, exit_id: String) -> void:
	var normalized_exit_id := exit_id.strip_edges()
	if normalized_exit_id.is_empty():
		return
	var source_id := str(payload.get("source_id", "")).strip_edges()
	var source_room_index := _find_room_index_in_map(map_data, source_id)
	if source_room_index < 0:
		return
	var rooms_array = map_data.get("rooms", [])
	var room_data: Dictionary = (rooms_array[source_room_index] as Dictionary).duplicate(true)
	var exit_details: Array = _get_local_exit_details(room_data)
	var old_direction := ""
	var detail_index := -1
	for candidate_index in range(exit_details.size()):
		var candidate: Dictionary = (exit_details[candidate_index] as Dictionary).duplicate(true)
		if str(candidate.get("id", "")).strip_edges() == normalized_exit_id or str(candidate.get("direction", "")).strip_edges().to_lower() == str(payload.get("direction", "")).strip_edges().to_lower():
			old_direction = str(candidate.get("direction", "")).strip_edges().to_lower()
			detail_index = candidate_index
			break
	var new_direction := str(payload.get("direction", old_direction)).strip_edges().to_lower()
	var new_target_room_id := str(payload.get("target_id", "")).strip_edges()
	var new_target_zone_id := str(payload.get("target_zone_id", current_area_id)).strip_edges()
	var exit_detail := {}
	if detail_index >= 0:
		exit_detail = (exit_details[detail_index] as Dictionary).duplicate(true)
	else:
		exit_detail = {
			"id": normalized_exit_id,
			"label": "",
			"aliases": [],
		}
	exit_detail["id"] = normalized_exit_id
	exit_detail["direction"] = new_direction
	exit_detail["target"] = {
		"zone_id": new_target_zone_id,
		"room_id": new_target_room_id,
	}
	exit_detail["label"] = str(payload.get("label", exit_detail.get("label", ""))).strip_edges()
	exit_detail["aliases"] = (payload.get("aliases", exit_detail.get("aliases", [])) as Array).duplicate(true)
	if detail_index >= 0:
		exit_details[detail_index] = exit_detail
	else:
		exit_details.append(exit_detail)
	var exits_dict: Dictionary = (room_data.get("exits", {}) as Dictionary).duplicate(true)
	if not old_direction.is_empty() and old_direction != new_direction:
		exits_dict.erase(old_direction)
	exits_dict[new_direction] = {
		"zone_id": new_target_zone_id,
		"room_id": new_target_room_id,
	}
	room_data["exits"] = exits_dict
	room_data["exit_details"] = exit_details
	rooms_array[source_room_index] = room_data
	map_data["rooms"] = rooms_array


func _delete_exit_from_map(map_data: Dictionary, source_id: String, direction: String) -> void:
	var delete_source_index := _find_room_index_in_map(map_data, source_id)
	if delete_source_index < 0:
		return
	var rooms_array = map_data.get("rooms", [])
	var room_data: Dictionary = (rooms_array[delete_source_index] as Dictionary).duplicate(true)
	var exits_dict: Dictionary = (room_data.get("exits", {}) as Dictionary).duplicate(true)
	var delete_direction := direction.strip_edges().to_lower()
	exits_dict.erase(delete_direction)
	var updated_exit_details: Array = []
	for raw_exit_detail in _get_local_exit_details(room_data):
		if not raw_exit_detail is Dictionary:
			continue
		if str(raw_exit_detail.get("direction", "")).strip_edges().to_lower() == delete_direction:
			continue
		updated_exit_details.append((raw_exit_detail as Dictionary).duplicate(true))
	room_data["exits"] = exits_dict
	room_data["exit_details"] = updated_exit_details
	rooms_array[delete_source_index] = room_data
	map_data["rooms"] = rooms_array


func _apply_object_updates_by_fields(map_data: Dictionary, object_id: String, object_updates: Dictionary) -> void:
	var normalized_object_id := object_id.strip_edges()
	if normalized_object_id.is_empty():
		return
	if object_updates.is_empty():
		return
	var rooms_array: Array = map_data.get("rooms", []) as Array
	for room_index in range((rooms_array as Array).size()):
		var room_data: Dictionary = (rooms_array[room_index] as Dictionary).duplicate(true)
		var updated_contents: Variant = _apply_object_updates_to_contents((room_data.get("contents", []) as Array), normalized_object_id, object_updates)
		if updated_contents == null:
			continue
		room_data["contents"] = updated_contents
		rooms_array[room_index] = room_data
		map_data["rooms"] = rooms_array
		return


func _apply_spawn_payload(map_data: Dictionary, payload: Dictionary) -> void:
	var destination_id := str(payload.get("location_id", "")).strip_edges()
	var preview_object_id := str(payload.get("preview_object_id", "")).strip_edges()
	if destination_id.is_empty() or preview_object_id.is_empty():
		return
	var template_type := str(payload.get("template_type", "item")).strip_edges().to_lower()
	var template_name := str(payload.get("template_name", payload.get("template_id", "Object")))
	var object_payload := {
		"id": preview_object_id,
		"object_id": preview_object_id,
		"name": template_name,
		"type": template_type,
		"template_id": str(payload.get("template_id", "")),
		"contents": [],
	}
	_insert_object_into_destination(map_data, object_payload, destination_id)
	if template_type == "npc":
		var room_id := _find_room_id_for_destination(map_data, destination_id)
		if not room_id.is_empty():
			var npcs = map_data.get("npcs", [])
			if npcs is Array:
				npcs.append({
					"id": preview_object_id,
					"room_id": room_id,
					"name": template_name,
				})
				map_data["npcs"] = npcs


func _apply_object_updates_to_contents(contents: Array, object_id: String, object_updates: Dictionary) -> Variant:
	var updated_contents: Array = []
	var found := false
	for entry in contents:
		if not entry is Dictionary:
			updated_contents.append(entry)
			continue
		var object_data: Dictionary = (entry as Dictionary).duplicate(true)
		if str(object_data.get("object_id", "")).strip_edges() == object_id:
			for key in object_updates.keys():
				object_data[key] = object_updates.get(key)
			updated_contents.append(object_data)
			found = true
			continue
		var nested_result: Variant = _apply_object_updates_to_contents((object_data.get("contents", []) as Array), object_id, object_updates)
		if nested_result != null:
			object_data["contents"] = nested_result
			found = true
		updated_contents.append(object_data)
	if found:
		return updated_contents
	return null


func _remove_object_from_rooms(map_data: Dictionary, object_id: String) -> Dictionary:
	var normalized_object_id := object_id.strip_edges()
	if normalized_object_id.is_empty():
		return {}
	var rooms_array = map_data.get("rooms", [])
	for index in range((rooms_array as Array).size()):
		var room_data: Dictionary = (rooms_array[index] as Dictionary).duplicate(true)
		var contents: Array = (room_data.get("contents", []) as Array).duplicate(true)
		var removed := _remove_object_recursive(contents, normalized_object_id)
		if removed.is_empty():
			continue
		room_data["contents"] = contents
		rooms_array[index] = room_data
		map_data["rooms"] = rooms_array
		return removed
	return {}


func _remove_object_recursive(contents: Array, object_id: String) -> Dictionary:
	for index in range(contents.size()):
		var entry = contents[index]
		if not entry is Dictionary:
			continue
		var object_data: Dictionary = (entry as Dictionary).duplicate(true)
		var normalized_entry_id := str(object_data.get("object_id", object_data.get("id", ""))).strip_edges()
		if normalized_entry_id == object_id:
			contents.remove_at(index)
			return object_data
		var nested_contents: Array = (object_data.get("contents", []) as Array).duplicate(true)
		var removed := _remove_object_recursive(nested_contents, object_id)
		if removed.is_empty():
			continue
		object_data["contents"] = nested_contents
		contents[index] = object_data
		return removed
	return {}


func _insert_object_into_destination(map_data: Dictionary, object_payload: Dictionary, destination_id: String) -> void:
	var normalized_destination_id := destination_id.strip_edges()
	var rooms_array = map_data.get("rooms", [])
	for index in range((rooms_array as Array).size()):
		var room_data: Dictionary = (rooms_array[index] as Dictionary).duplicate(true)
		if str(room_data.get("object_id", room_data.get("id", ""))).strip_edges() == normalized_destination_id:
			var room_contents: Array = (room_data.get("contents", []) as Array).duplicate(true)
			room_contents.append(object_payload.duplicate(true))
			room_data["contents"] = room_contents
			rooms_array[index] = room_data
			map_data["rooms"] = rooms_array
			return
		var room_contents: Array = (room_data.get("contents", []) as Array).duplicate(true)
		if _insert_object_recursive(room_contents, object_payload, normalized_destination_id):
			room_data["contents"] = room_contents
			rooms_array[index] = room_data
			map_data["rooms"] = rooms_array
			return


func _insert_object_recursive(contents: Array, object_payload: Dictionary, destination_id: String) -> bool:
	for index in range(contents.size()):
		var entry = contents[index]
		if not entry is Dictionary:
			continue
		var object_data: Dictionary = (entry as Dictionary).duplicate(true)
		var normalized_entry_id := str(object_data.get("object_id", object_data.get("id", ""))).strip_edges()
		if normalized_entry_id == destination_id:
			var nested_contents: Array = (object_data.get("contents", []) as Array).duplicate(true)
			nested_contents.append(object_payload.duplicate(true))
			object_data["contents"] = nested_contents
			contents[index] = object_data
			return true
		var nested_contents: Array = (object_data.get("contents", []) as Array).duplicate(true)
		if _insert_object_recursive(nested_contents, object_payload, destination_id):
			object_data["contents"] = nested_contents
			contents[index] = object_data
			return true
	return false


func _find_room_id_for_destination(map_data: Dictionary, destination_id: String) -> String:
	var normalized_destination_id := destination_id.strip_edges()
	if normalized_destination_id.is_empty():
		return ""
	for room_variant in map_data.get("rooms", []):
		if not room_variant is Dictionary:
			continue
		var room_data := room_variant as Dictionary
		if str(room_data.get("object_id", room_data.get("id", ""))).strip_edges() == normalized_destination_id:
			return str(room_data.get("id", "")).strip_edges()
		if _contains_destination((room_data.get("contents", []) as Array), normalized_destination_id):
			return str(room_data.get("id", "")).strip_edges()
	return ""


func _contains_destination(contents: Array, destination_id: String) -> bool:
	for entry in contents:
		if not entry is Dictionary:
			continue
		var object_data := entry as Dictionary
		if str(object_data.get("object_id", object_data.get("id", ""))).strip_edges() == destination_id:
			return true
		if _contains_destination((object_data.get("contents", []) as Array), destination_id):
			return true
	return false


func _resolve_template_preview(template_id: String, template_type: String) -> Dictionary:
	var response: Dictionary = await builder_api.search_templates(template_id, template_type)
	if not bool(response.get("ok", false)):
		return {
			"template_id": template_id,
			"type": template_type,
			"name": template_id,
		}
	var templates: Variant = response.get("result", {}).get("templates", response.get("result", []))
	if templates is Array:
		for template in templates:
			if template is Dictionary and str((template as Dictionary).get("template_id", "")).strip_edges() == template_id:
				return (template as Dictionary).duplicate(true)
	return {
		"template_id": template_id,
		"type": template_type,
		"name": template_id,
	}


func _sync_selection_after_map_update() -> void:
	if current_map_data.get("rooms", []).is_empty():
		select_room("")
		select_object("")
		return
	var preserve_workspace := active_workspace == "npc_templates" or active_workspace == "item_templates"
	if not selected_object_id.is_empty():
		if _find_room_id_for_object(selected_object_id).is_empty():
			select_object("")
		elif map_grid.has_object(selected_object_id):
			if not preserve_workspace:
				_open_instance_editor(selected_object_id)
			return
	if selected_room_id.is_empty() or _get_room_from_cache(selected_room_id).is_empty():
		select_room(_first_room_id())
	else:
		if not preserve_workspace:
			_open_room_editor(selected_room_id)


func _first_room_id() -> String:
	for room_data in current_map_data.get("rooms", []):
		if room_data is Dictionary:
			return str(room_data.get("id", "")).strip_edges()
	return ""


func _next_adjacent_cell(room_data: Dictionary) -> Dictionary:
	var candidates: Array[Dictionary] = [
		{"map_x": int(room_data.get("map_x", 0)) + 1, "map_y": int(room_data.get("map_y", 0)), "map_layer": int(room_data.get("map_layer", 0))},
		{"map_x": int(room_data.get("map_x", 0)) - 1, "map_y": int(room_data.get("map_y", 0)), "map_layer": int(room_data.get("map_layer", 0))},
		{"map_x": int(room_data.get("map_x", 0)), "map_y": int(room_data.get("map_y", 0)) + 1, "map_layer": int(room_data.get("map_layer", 0))},
		{"map_x": int(room_data.get("map_x", 0)), "map_y": int(room_data.get("map_y", 0)) - 1, "map_layer": int(room_data.get("map_layer", 0))},
	]
	for candidate in candidates:
		var occupied := false
		for existing_room in current_map_data.get("rooms", []):
			if not existing_room is Dictionary:
				continue
			occupied = int(existing_room.get("map_x", 0)) == int(candidate.get("map_x", 0)) and int(existing_room.get("map_y", 0)) == int(candidate.get("map_y", 0)) and int(existing_room.get("map_layer", 0)) == int(candidate.get("map_layer", 0))
			if occupied:
				break
		if not occupied:
			return candidate
	return candidates[0]


func _opposite_direction(direction: String) -> String:
	match direction.strip_edges().to_lower():
		"north":
			return "south"
		"south":
			return "north"
		"east":
			return "west"
		"west":
			return "east"
		_:
			return ""