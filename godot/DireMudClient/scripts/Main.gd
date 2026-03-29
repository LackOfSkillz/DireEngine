extends Control


const WEBSOCKET_URL := "ws://127.0.0.1:4008"

var socket := WebSocketPeer.new()


func _ready() -> void:
	print("Connecting to server...")
	var result := socket.connect_to_url(WEBSOCKET_URL)
	if result != OK:
		push_error("Unable to connect to %s (code %s)" % [WEBSOCKET_URL, result])
		set_process(false)
		return

	$CommandInput.text_submitted.connect(_on_command_input_text_submitted)
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


func _on_command_input_text_submitted(new_text: String) -> void:
	var trimmed := new_text.strip_edges()
	if trimmed.is_empty():
		return

	send_command(trimmed)
	$CommandInput.clear()


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