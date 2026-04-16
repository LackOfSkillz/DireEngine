extends SceneTree


const OUTPUT_PATH := "user://builder_overlay_debug.txt"
const SCREENSHOT_PATH := "user://builder_overlay_debug.png"


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var packed_scene: PackedScene = load("res://scenes/Main.tscn") as PackedScene
	if packed_scene == null:
		_push_and_quit(["failed: could not load res://scenes/Main.tscn"])
		return

	var main_scene: Control = packed_scene.instantiate() as Control
	get_root().add_child(main_scene)

	await process_frame
	await process_frame

	var builder_controller: Control = main_scene.get_node_or_null("BuilderController") as Control
	if builder_controller == null:
		_push_and_quit(["failed: BuilderController node missing"])
		return

	builder_controller.update_character_context({"is_builder": true, "builder_mode_available": true})
	builder_controller.apply_launch_context({
		"area_id": "new_landing",
		"room_id": "4214",
		"character_name": "Wufgar",
	})

	await process_frame
	await process_frame
	await process_frame

	var lines: Array[String] = []
	lines.append("main_visible=%s" % str(main_scene.visible))
	lines.append("builder_available=%s" % str(builder_controller.builder_available))
	lines.append("builder_mode_enabled=%s" % str(builder_controller.builder_mode_enabled))
	lines.append("builder_root_visible=%s" % str(builder_controller.get_node("BuilderRoot").visible))
	lines.append("status=%s" % str(builder_controller.status_label.text))

	for node_name in ["MapPanel", "TextLog", "CharacterPanel", "InventoryPanel", "CommandInput", "Hotbar"]:
		var node: CanvasItem = main_scene.get_node_or_null(node_name) as CanvasItem
		if node == null:
			lines.append("%s=missing" % node_name)
			continue
		var line := "%s visible=%s in_tree=%s" % [
			node_name,
			str(node.visible),
			str(node.is_visible_in_tree()),
		]
		if node is Control:
			var control := node as Control
			line += " mouse_filter=%d focus_mode=%d size=%s pos=%s" % [
				control.mouse_filter,
				control.focus_mode,
				str(control.size),
				str(control.position),
			]
		lines.append(line)

	for node_path in [
		"BuilderController",
		"BuilderController/BuilderRoot",
		"BuilderController/BuilderRoot/BuilderColumns/LeftPanel",
		"BuilderController/BuilderRoot/BuilderColumns/CenterPanel",
		"BuilderController/BuilderRoot/BuilderColumns/RightPanel",
		"BuilderController/BuilderRoot/BuilderColumns/CenterPanel/Margin/MapGrid",
	]:
		var node: CanvasItem = main_scene.get_node_or_null(node_path) as CanvasItem
		if node == null:
			lines.append("%s=missing" % node_path)
			continue
		lines.append("%s visible=%s in_tree=%s" % [node_path, str(node.visible), str(node.is_visible_in_tree())])

	var file := FileAccess.open(OUTPUT_PATH, FileAccess.WRITE)
	if file != null:
		file.store_string("\n".join(lines))

	var viewport := get_root()
	if viewport != null:
		var image := viewport.get_texture().get_image()
		if image != null and not image.is_empty():
			image.save_png(SCREENSHOT_PATH)
			lines.append("screenshot_saved=%s" % SCREENSHOT_PATH)
		else:
			lines.append("screenshot_saved=no_image")

	_push_and_quit(lines)


func _push_and_quit(lines: Array[String]) -> void:
	for line in lines:
		print(line)
	quit()