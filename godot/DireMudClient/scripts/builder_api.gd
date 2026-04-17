extends Node

class_name BuilderApi


const API_BASE_URL := "http://127.0.0.1:4001/api/builder"
const LAUNCHER_API_BASE_URL := "http://127.0.0.1:7777/builder-api"
const REQUEST_TIMEOUT_SECONDS := 8.0


var csrf_token := ""
var session_cookie := ""
var default_headers: Array[String] = []


func set_csrf_token(token: String) -> void:
	csrf_token = token.strip_edges()


func set_session_cookie(cookie_value: String) -> void:
	session_cookie = cookie_value.strip_edges()


func set_default_headers(headers: Array[String]) -> void:
	default_headers = headers.duplicate()


func apply_diff(diff: Dictionary, preview: bool = false, group_id: String = "", session_id: String = "") -> Dictionary:
	var payload := {
		"diff": diff,
		"preview": preview,
	}
	if not group_id.strip_edges().is_empty():
		payload["group_id"] = group_id.strip_edges()
	if not session_id.strip_edges().is_empty():
		payload["session_id"] = session_id.strip_edges()
	return await _request_json_with_fallback("POST", "/map/diff/", payload)


func save_all(diff: Dictionary, session_id: String = "") -> Dictionary:
	var payload := {
		"diff": diff,
		"preview": false,
	}
	if not session_id.strip_edges().is_empty():
		payload["session_id"] = session_id.strip_edges()
	return await _request_json_with_fallback("POST", "/map/save-all/", payload)


func apply_undo(undo_diff: Dictionary) -> Dictionary:
	return await _request_json_with_fallback("POST", "/map/undo/", {"undo_diff": undo_diff})


func apply_redo(diff: Dictionary) -> Dictionary:
	return await _request_json_with_fallback("POST", "/map/redo/", {"diff": diff})


func get_history(area_id: String = "", limit: int = 20) -> Dictionary:
	var query_parts: Array[String] = []
	if not area_id.strip_edges().is_empty():
		query_parts.append("area_id=%s" % area_id.uri_encode())
	if limit >= 0:
		query_parts.append("limit=%d" % limit)
	var suffix := ""
	if not query_parts.is_empty():
		suffix = "?%s" % "&".join(query_parts)
	return await _request_json("GET", "/map/history/%s" % suffix)


func export_map(area_id: String) -> Dictionary:
	var normalized_area_id := area_id.strip_edges()
	print("CALLING EXPORT MAP:", normalized_area_id)
	if normalized_area_id.is_empty():
		return {
			"ok": false,
			"status": 400,
			"error": "area_id_required",
		}
	var web_result := await _request_json("GET", "/map/export/%s/" % normalized_area_id.uri_encode())
	if web_result.get("ok", false):
		return web_result
	print("Web Builder export failed, falling back to launcher export:", web_result)
	return await _request_json_with_base("GET", LAUNCHER_API_BASE_URL, "/map/export/%s/" % normalized_area_id.uri_encode())


func load_zone(zone_id: String) -> Dictionary:
	return await export_map(zone_id)


func list_zones() -> Dictionary:
	return await _request_json_with_fallback("GET", "/zones/")


func create_zone(zone_id: String, name: String) -> Dictionary:
	return await _request_json_with_fallback("POST", "/zones/create/", {
		"zone_id": zone_id.strip_edges(),
		"name": name.strip_edges(),
	})


func update_room(room_id: String, updates: Dictionary) -> Dictionary:
	var normalized_room_id := room_id.strip_edges()
	if normalized_room_id.is_empty():
		return {
			"ok": false,
			"status": 400,
			"error": "room_id_required",
		}
	return await _request_json("POST", "/room/update/%s/" % normalized_room_id.uri_encode(), updates)


func search_templates(query: String, template_type: String = "") -> Dictionary:
	var query_parts := ["q=%s" % query.uri_encode()]
	if not template_type.strip_edges().is_empty():
		query_parts.append("type=%s" % template_type.strip_edges().uri_encode())
	return await _request_json("GET", "/templates/search/?%s" % "&".join(query_parts))


func list_npcs() -> Dictionary:
	return await _request_template_list_with_fallback("/npcs/")


func list_items() -> Dictionary:
	return await _request_template_list_with_fallback("/items/")


func list_templates(template_type: String = "") -> Dictionary:
	var normalized_type := template_type.strip_edges().to_lower()
	if normalized_type == "npc":
		return await list_npcs()
	if normalized_type == "item":
		return await list_items()
	return await _request_json("GET", "/templates/")


func get_template(template_id: String) -> Dictionary:
	var normalized_template_id := template_id.strip_edges()
	if normalized_template_id.is_empty():
		return {
			"ok": false,
			"status": 400,
			"error": "template_id_required",
		}
	return await _request_json("GET", "/templates/%s/" % normalized_template_id.uri_encode())


func create_template(payload: Dictionary) -> Dictionary:
	return await _request_json("POST", "/templates/create/", payload)


func update_template(template_id: String, payload: Dictionary) -> Dictionary:
	var normalized_template_id := template_id.strip_edges()
	if normalized_template_id.is_empty():
		return {
			"ok": false,
			"status": 400,
			"error": "template_id_required",
		}
	return await _request_json("POST", "/templates/%s/update/" % normalized_template_id.uri_encode(), payload)


func spawn(payload: Dictionary) -> Dictionary:
	return await _request_json("POST", "/spawn/", payload)


func move(payload: Dictionary) -> Dictionary:
	return await _request_json("POST", "/move/", payload)


func delete_instance(payload: Dictionary) -> Dictionary:
	return await _request_json("POST", "/delete/", payload)


func _request_json(method: String, path: String, payload: Dictionary = {}) -> Dictionary:
	return await _request_json_with_base(method, API_BASE_URL, path, payload)


func _request_json_with_fallback(method: String, path: String, payload: Dictionary = {}) -> Dictionary:
	var web_result := await _request_json_with_base(method, API_BASE_URL, path, payload)
	if web_result.get("ok", false):
		return web_result
	var status_code := int(web_result.get("status", 0))
	if status_code != 404 and status_code != 403 and status_code != 0:
		return web_result
	print("Web Builder request failed, falling back to launcher:", method, path, web_result)
	return await _request_json_with_base(method, LAUNCHER_API_BASE_URL, path, payload)


func _request_template_list_with_fallback(path: String) -> Dictionary:
	var web_result := await _request_json_with_base("GET", API_BASE_URL, path)
	if web_result.get("ok", false):
		var result_payload: Variant = web_result.get("result", {})
		var templates: Variant = result_payload.get("templates", []) if result_payload is Dictionary else []
		if templates is Array and not templates.is_empty():
			return web_result
		print("Web Builder template list was empty, falling back to launcher:", path, web_result)
	else:
		var status_code := int(web_result.get("status", 0))
		if status_code != 404 and status_code != 0:
			return web_result
		print("Web Builder template request failed, falling back to launcher:", path, web_result)
	return await _request_json_with_base("GET", LAUNCHER_API_BASE_URL, path)


func _request_json_with_base(method: String, base_url: String, path: String, payload: Dictionary = {}) -> Dictionary:
	var http_request := HTTPRequest.new()
	http_request.timeout = REQUEST_TIMEOUT_SECONDS
	add_child(http_request)
	var headers := _build_headers()
	var url := "%s%s" % [base_url, path]
	var body := ""
	if method != "GET":
		body = JSON.stringify(payload)
	var request_error := http_request.request(url, headers, HTTPClient.METHOD_GET if method == "GET" else HTTPClient.METHOD_POST, body)
	if request_error != OK:
		http_request.queue_free()
		return {
			"ok": false,
			"status": 0,
			"error": "request_failed",
			"transport_error": request_error,
		}

	var result = await http_request.request_completed
	http_request.queue_free()
	var response_code: int = int(result[1])
	var body_bytes: PackedByteArray = result[3]
	var raw_text := body_bytes.get_string_from_utf8()
	print("BUILDER API RESPONSE:", method, path, response_code, raw_text.left(800))
	var parsed = JSON.parse_string(raw_text)
	return _normalize_response(response_code, parsed)


func _build_headers() -> Array[String]:
	var headers := default_headers.duplicate()
	headers.append("Content-Type: application/json")
	headers.append("X-Builder-Local: 1")
	if not csrf_token.is_empty():
		headers.append("X-CSRFToken: %s" % csrf_token)
	if not session_cookie.is_empty():
		headers.append("Cookie: %s" % session_cookie)
	return headers


func _normalize_response(status_code: int, payload) -> Dictionary:
	if payload is Dictionary:
		var body: Dictionary = payload
		if bool(body.get("ok", false)):
			return {
				"ok": true,
				"status": status_code,
				"result": body.get("data", {}).get("result", body.get("data", body)),
				"history": body.get("history", []),
				"raw": body,
			}
		return {
			"ok": false,
			"status": status_code,
			"error": str(body.get("error", "request_failed")),
			"failed_operation_id": body.get("failed_operation_id"),
			"failed_operation": body.get("failed_operation"),
			"conflicts": body.get("conflicts", []),
			"raw": body,
		}
	return {
		"ok": false,
		"status": status_code,
		"error": "invalid_response",
		"raw": payload,
	}