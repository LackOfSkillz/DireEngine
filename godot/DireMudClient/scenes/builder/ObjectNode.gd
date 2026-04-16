extends Area2D

class_name ObjectNode


const BuilderVisuals = preload("res://scripts/builder_visuals.gd")


signal clicked(object_id)
signal drag_position_changed(object_id, local_position)
signal drop_requested(object_id, local_position)
signal drag_canceled(object_id)


var object_id: String = ""
var object_type: String = "item"
var room_id: String = ""
var object_name: String = ""
var is_surface := false
var dragging := false
var hovered := false
var selected := false
var original_position := Vector2.ZERO
var render_scale := 1.0
var visual_size := Vector2(36.0, 16.0)
var hit_size := Vector2(36.0, 16.0)


@onready var hit_box: ColorRect = $HitBox
@onready var name_label: Label = $Label
@onready var collision_shape: CollisionShape2D = $CollisionShape2D


func _ui_is_ready() -> bool:
	return is_node_ready() and hit_box != null and name_label != null


func _ready() -> void:
	input_pickable = true
	mouse_entered.connect(_on_mouse_entered)
	mouse_exited.connect(_on_mouse_exited)
	set_process(false)
	original_position = position
	_apply_label_state()
	_apply_visual_state()


func configure(data: Dictionary) -> void:
	object_id = str(data.get("object_id", data.get("id", ""))).strip_edges()
	object_type = str(data.get("type", "item")).strip_edges().to_lower()
	object_name = str(data.get("name", object_id))
	is_surface = bool(data.get("is_surface", false))
	z_index = BuilderVisuals.get_object_z_index(object_type)
	original_position = position
	_apply_geometry_state()
	_apply_label_state()
	_apply_visual_state()


func set_render_scale(value: float) -> void:
	render_scale = clampf(value, 0.35, 1.0)
	scale = Vector2.ONE * render_scale


func contains_local_point(point: Vector2) -> bool:
	if hit_box == null:
		return false
	return Rect2(position - (hit_size / 2.0), hit_size).has_point(point)


func set_selected(value: bool) -> void:
	selected = value
	_apply_visual_state()


func reset_position() -> void:
	position = original_position


func _input_event(_viewport: Node, event: InputEvent, _shape_idx: int) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			emit_signal("clicked", object_id)
			dragging = true
			original_position = position
			set_process(true)
			Input.set_default_cursor_shape(Input.CURSOR_MOVE)
		else:
			if not dragging:
				return
			dragging = false
			set_process(false)
			Input.set_default_cursor_shape(Input.CURSOR_ARROW)
			emit_signal("drop_requested", object_id, position)


func _process(_delta: float) -> void:
	if dragging:
		position = get_parent().get_local_mouse_position()
		emit_signal("drag_position_changed", object_id, position)
		if Input.is_action_just_pressed("ui_cancel"):
			dragging = false
			set_process(false)
			Input.set_default_cursor_shape(Input.CURSOR_ARROW)
			reset_position()
			emit_signal("drag_canceled", object_id)


func _on_mouse_entered() -> void:
	hovered = true
	_apply_visual_state()
	Input.set_default_cursor_shape(Input.CURSOR_POINTING_HAND)


func _on_mouse_exited() -> void:
	hovered = false
	_apply_visual_state()
	if not dragging:
		Input.set_default_cursor_shape(Input.CURSOR_ARROW)


func _apply_visual_state() -> void:
	if not _ui_is_ready():
		return
	var color := _get_color()
	if hovered:
		color = color.lightened(0.2)
	if selected:
		color = Color(1.0, 0.9, 0.25, 1.0)
	hit_box.color = color
	name_label.visible = hovered or selected


func _apply_geometry_state() -> void:
	var size_data := _size_profile_for_type()
	visual_size = size_data["visual"]
	hit_size = size_data["hit"]
	if hit_box != null:
		hit_box.position = -(visual_size / 2.0)
		hit_box.size = visual_size
	if collision_shape != null and collision_shape.shape is RectangleShape2D:
		(collision_shape.shape as RectangleShape2D).size = hit_size
	if name_label != null:
		name_label.position = Vector2(-(maxf(visual_size.x, 28.0) / 2.0), -(visual_size.y / 2.0) - 18.0)
		name_label.size.x = maxf(visual_size.x * 2.0, 72.0)


func _apply_label_state() -> void:
	if not _ui_is_ready():
		return
	name_label.text = object_name.substr(0, 10)
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER


func _get_color() -> Color:
	return BuilderVisuals.get_object_color(object_type)


func _size_profile_for_type() -> Dictionary:
	if object_type == "npc":
		return {
			"visual": Vector2(18.0, 18.0),
			"hit": Vector2(28.0, 28.0),
		}
	return {
		"visual": Vector2(32.0, 14.0),
		"hit": Vector2(36.0, 18.0),
	}