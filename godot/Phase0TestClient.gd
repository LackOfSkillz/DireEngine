extends Node


const WEBSOCKET_URL := "ws://127.0.0.1:4008"

var socket := WebSocketPeer.new()


func _ready() -> void:
	var result := socket.connect_to_url(WEBSOCKET_URL)
	if result != OK:
		push_error("Unable to connect to %s (code %s)" % [WEBSOCKET_URL, result])
		set_process(false)
		return

	print("Connecting to %s" % WEBSOCKET_URL)


func _process(_delta: float) -> void:
	socket.poll()

	match socket.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			while socket.get_available_packet_count() > 0:
				_handle_raw_packet(socket.get_packet().get_string_from_utf8())
		WebSocketPeer.STATE_CLOSED:
			print(
				"WebSocket closed with code %s, reason %s" % [
					socket.get_close_code(),
					socket.get_close_reason(),
				]
			)
			set_process(false)


func _handle_raw_packet(raw_text: String) -> void:
	print("RAW:", raw_text)

	var packet = JSON.parse_string(raw_text)
	if packet == null:
		push_warning("Failed to parse websocket payload as JSON")
		return

	var normalized := normalize_message(packet)
	if normalized.is_empty():
		push_warning("Received unexpected packet shape: %s" % [str(packet)])
		return

	print("NORMALIZED:", normalized)

	match normalized["cmd"]:
		"text", "prompt":
			for entry in normalized["args"]:
				print("TEXT:", entry)
		_:
			print("OOB:", normalized["cmd"], normalized["args"], normalized["kwargs"])


func normalize_message(packet: Variant) -> Dictionary:
	if packet is Array and packet.size() >= 3:
		return {
			"cmd": packet[0],
			"args": packet[1],
			"kwargs": packet[2],
		}
	return {}


func send_command(command_text: String) -> void:
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		push_warning("Socket is not open; command not sent")
		return

	var payload := JSON.stringify(["text", [command_text], {}])
	print("SEND:", payload)
	socket.send_text(payload)


func _input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_accept"):
		send_command("look")


func _exit_tree() -> void:
	if socket.get_ready_state() != WebSocketPeer.STATE_CLOSED:
		socket.close()