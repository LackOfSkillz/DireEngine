extends Control


const WEBSOCKET_URL := "ws://127.0.0.1:4008"

var socket := WebSocketPeer.new()
var command_history: Array[String] = []
var command_history_index := -1
var command_history_draft := ""


func _ready() -> void:
	print("Connecting to server...")
	var result := socket.connect_to_url(WEBSOCKET_URL)
	if result != OK:
		push_error("Unable to connect to %s (code %s)" % [WEBSOCKET_URL, result])
		set_process(false)
		return

	$CommandInput.focus_mode = Control.FOCUS_ALL
	$CommandInput.grab_focus()
	$CommandInput.text_submitted.connect(_on_command_input_text_submitted)
	$CommandInput.gui_input.connect(_on_command_input_gui_input)
	$MapPanel.room_clicked.connect(_on_room_clicked)
	$InventoryPanel.item_action.connect(_on_item_action)
	$CharacterPanel.equip_item.connect(_on_equip_item)
	$Hotbar.hotbar_action.connect(_on_hotbar_action)
	$Hotbar.set_slot(0, "look")
	$Hotbar.set_slot(1, "inventory")
	$Hotbar.set_slot(2, "stats")


func _process(_delta: float) -> void:
	socket.poll()
	match socket.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			while socket.get_available_packet_count() > 0:
				_handle_raw_packet(socket.get_packet().get_string_from_utf8())
		WebSocketPeer.STATE_CONNECTING:
			pass
		WebSocketPeer.STATE_CLOSED:
			print("Disconnected")


func _handle_raw_packet(raw_text: String) -> void:
	print("RAW:", raw_text)
	var packet = JSON.parse_string(raw_text)
	if packet == null:
		push_warning("Failed to parse websocket payload")
		return

	var message := normalize_message(packet)
	if message.is_empty():
		push_warning("Unexpected packet shape: %s" % [str(packet)])
		return

	handle_message(message)


func normalize_message(packet: Variant) -> Dictionary:
	if packet is Array and packet.size() >= 3:
		return {
			"cmd": packet[0],
			"args": packet[1],
			"kwargs": packet[2],
		}
	return {}


func handle_message(message: Dictionary) -> void:
	var cmd = message["cmd"]
	var args = message["args"]

	match cmd:
		"text", "prompt":
			for entry in args:
				if entry:
					$TextLog.add_line(str(entry))
		"map":
			if args.size() > 0:
				$MapPanel.render_map(args[0])
		"character":
			if args.size() > 0:
				$CharacterPanel.update_character(args[0])
				$CharacterPanel.update_equipment(args[0].get("equipment", {}))
				$CharacterPanel.update_status(args[0].get("status", []))
				$InventoryPanel.update_inventory(args[0].get("inventory", []))
		"combat":
			if args.size() > 0:
				handle_combat(args[0])
		"ping":
			$TextLog.add_line("[ping] %s" % [str(args[0] if args.size() > 0 else {})])
		_:
			$TextLog.add_line("[%s] %s" % [cmd, str(args)])


func send_command(command_text: String) -> void:
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		$TextLog.add_line("[system] Not connected.")
		return

	var payload := JSON.stringify(["text", [command_text], {}])
	$TextLog.add_line("> " + command_text)
	socket.send_text(payload)

func _remember_command(command_text: String) -> void:
	var trimmed := command_text.strip_edges()
	if trimmed.is_empty():
		return
	command_history.append(trimmed)
	if command_history.size() > 100:
		command_history = command_history.slice(command_history.size() - 100, command_history.size())
	command_history_index = -1
	command_history_draft = ""


func _set_command_input_text(value: String) -> void:
	$CommandInput.text = value
	$CommandInput.caret_column = value.length()


func _navigate_command_history(direction: int) -> bool:
	if command_history.is_empty():
		return false

	if direction < 0:
		if command_history_index == -1:
			command_history_draft = $CommandInput.text
			command_history_index = command_history.size() - 1
		elif command_history_index > 0:
			command_history_index -= 1
		_set_command_input_text(command_history[command_history_index])
		return true

	if command_history_index == -1:
		return false

	if command_history_index < command_history.size() - 1:
		command_history_index += 1
		_set_command_input_text(command_history[command_history_index])
		return true

	command_history_index = -1
	_set_command_input_text(command_history_draft)
	command_history_draft = ""
	return true


func _on_command_input_text_submitted(new_text: String) -> void:
	var trimmed := new_text.strip_edges()
	if trimmed.is_empty():
		return

	_remember_command(trimmed)
	send_command(trimmed)
	$CommandInput.clear()
	command_history_draft = ""

func _on_command_input_gui_input(event: InputEvent) -> void:
	if not (event is InputEventKey):
		return

	var key_event := event as InputEventKey
	if not key_event.pressed or key_event.echo:
		return

	if key_event.keycode == KEY_UP:
		if _navigate_command_history(-1):
			$CommandInput.accept_event()
		return

	if key_event.keycode == KEY_DOWN:
		if _navigate_command_history(1):
			$CommandInput.accept_event()
		return

	if command_history_index == -1:
		command_history_draft = $CommandInput.text


func _on_room_clicked(room_id: int) -> void:
	var direction = $MapPanel.get_direction_to(room_id)
	if direction:
		send_command(direction)


func _on_item_action(item_name: String) -> void:
	send_command("get " + item_name)


func _on_equip_item(item_name: String) -> void:
	send_command("equip " + item_name)


func _on_hotbar_action(action: String) -> void:
	send_command(action)


func handle_combat(data: Dictionary) -> void:
	var target = str(data.get("target", "target"))
	var damage = int(data.get("damage", 0))
	$TextLog.add_line("You hit %s for %d damage." % [target, damage])
	$CharacterPanel.flash_damage()


func _exit_tree() -> void:
	if socket.get_ready_state() != WebSocketPeer.STATE_CLOSED:
		socket.close()