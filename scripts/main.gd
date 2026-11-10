extends Node3D
## Game flow: builds the world, spawns Toots and the wildlife, runs the
## camera, pickups, checkpoints, HUD and the title / win / game-over states.

const Level := preload("res://scripts/level.gd")
const World := preload("res://scripts/world.gd")
const PlayerScript := preload("res://scripts/player.gd")
const EnemyScript := preload("res://scripts/enemy.gd")
const HudScript := preload("res://scripts/hud.gd")

const CAM_DISTANCE := 17.0

var world: World
var player: PlayerScript
var camera: Camera3D
var hud: HudScript
var state := "title"            # title | play | win | over
var berries := 0
var elapsed := 0.0
var checkpoint := Vector3.ZERO

var _berries: Array[Node3D] = []
var _beans: Array[Node3D] = []
var _checkpoints: Array[Node3D] = []
var _flag: Node3D
var _look_ahead := 0.0
var _time := 0.0                ## drives the idle animations; never reset
var _state_time := 0.0          ## seconds since the win / game-over screen came up
var _title: Label
var _subtitle: Label
var _prompt: Label
var _hint: Label
var _shade: ColorRect
var _poof_mat: ShaderMaterial
var _restarting := false


func _ready() -> void:
	_setup_input()
	# Physics interpolation is on (project settings) so Toots and the critters,
	# which move on the physics tick, stay smooth on displays faster than 60 Hz.
	# The scenery never moves and the pickups, clouds and camera are animated
	# per frame in _process(), so all of those opt out.
	world = World.new()
	world.name = "World"
	world.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	add_child(world)
	world.build()

	player = PlayerScript.new()
	player.name = "Toots"
	add_child(player)
	checkpoint = Vector3(Level.START.x, Level.START.y, 0)
	player.position = checkpoint
	player.get_global_transform_interpolated()     # set up before the first reset, as the docs ask
	player.reset_physics_interpolation()
	player.min_x = world.min_x
	player.hurt_taken.connect(_on_player_hurt)

	camera = Camera3D.new()
	camera.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	camera.fov = 38.0
	camera.far = 2500.0
	camera.rotation_degrees.x = -5.0
	camera.position = Vector3(checkpoint.x + 2.0, checkpoint.y + 2.6, CAM_DISTANCE)
	add_child(camera)
	camera.make_current()

	_poof_mat = ShaderMaterial.new()
	_poof_mat.shader = load("res://shaders/puff.gdshader")
	_spawn_things()
	_build_ui()

	if Sfx.skip_title:
		_start_play()
	else:
		_show_message("TOOTS", "Monster of the Rockies", "Press SPACE to start")
	Sfx.start_music()
	if not OS.get_cmdline_user_args().is_empty():
		add_child(load("res://scripts/autoplay.gd").new())


func _setup_input() -> void:
	_bind("move_left", [KEY_A, KEY_LEFT], [JOY_BUTTON_DPAD_LEFT], JOY_AXIS_LEFT_X, -1.0)
	_bind("move_right", [KEY_D, KEY_RIGHT], [JOY_BUTTON_DPAD_RIGHT], JOY_AXIS_LEFT_X, 1.0)
	_bind("jump", [KEY_SPACE, KEY_W, KEY_UP, KEY_Z], [JOY_BUTTON_A])
	_bind("fart", [KEY_SHIFT, KEY_X, KEY_F], [JOY_BUTTON_X, JOY_BUTTON_RIGHT_SHOULDER])
	_bind("restart", [KEY_R], [JOY_BUTTON_BACK])
	_bind("music", [KEY_M], [])


func _bind(action: String, keys: Array, buttons: Array, axis := -1, axis_value := 0.0) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action, 0.4)
	for k in keys:
		var e := InputEventKey.new()
		e.physical_keycode = k
		InputMap.action_add_event(action, e)
	for b in buttons:
		var e := InputEventJoypadButton.new()
		e.button_index = b
		InputMap.action_add_event(action, e)
	if axis >= 0:
		var e := InputEventJoypadMotion.new()
		e.axis = axis
		e.axis_value = axis_value
		InputMap.action_add_event(action, e)


# ------------------------------------------------------------------ setup
func _spawn_things() -> void:
	for e in Level.ENEMIES:
		var enemy := EnemyScript.new()
		add_child(enemy)
		enemy.setup(e[0], Vector3(e[1], e[2], 0), e[3], e[4], player)
		enemy.defeated.connect(_on_enemy_defeated)
	for b in Level.berries():
		var n := world.place("berry", Vector3(b.x, b.y, 0), Vector3.ONE * 1.35)
		n.set_meta("base_y", b.y)
		n.set_meta("phase", b.x * 0.7)
		_berries.append(n)
	for b in Level.BEANS:
		var n := world.place("beans", Vector3(b.x, b.y, 0), Vector3.ONE * 1.25)
		n.set_meta("base_y", b.y)
		n.set_meta("cooldown", 0.0)
		_beans.append(n)
	for c in Level.CHECKPOINTS:
		var n := world.place("signpost", Vector3(c.x, c.y, -1.1), Vector3.ONE * 1.2)
		n.set_meta("reached", false)
		_checkpoints.append(n)
	var summit := world.place("summit", Vector3(Level.GOAL.x, Level.GOAL.y, -0.9), Vector3.ONE * 1.25)
	_flag = summit.find_child("flag", true, false)


func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	_shade = ColorRect.new()
	_shade.color = Color(0.03, 0.06, 0.12, 0.45)
	_shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(_shade)
	hud = HudScript.new()
	hud.berries_total = _berries.size()
	layer.add_child(hud)
	_title = _label(layer, 120, Color("fff6d8"), 24)
	_title.offset_top = -320
	_title.offset_bottom = -150
	_subtitle = _label(layer, 36, Color.WHITE, 10)
	_subtitle.offset_top = -150
	_subtitle.offset_bottom = -95
	_prompt = _label(layer, 32, Color("ffe9a8"), 10)
	_prompt.offset_top = 150
	_prompt.offset_bottom = 210
	_hint = _label(layer, 27, Color.WHITE, 9)
	_hint.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	_hint.offset_top = -92
	_hint.offset_bottom = -44
	_hint.modulate.a = 0.0


func _label(parent: Node, size: int, color: Color, outline: int) -> Label:
	var l := Label.new()
	var s := LabelSettings.new()
	s.font_size = size
	s.font_color = color
	s.outline_size = outline
	s.outline_color = Color(0.05, 0.07, 0.1)
	s.shadow_size = 6
	s.shadow_color = Color(0, 0, 0, 0.35)
	s.shadow_offset = Vector2(0, 4)
	l.label_settings = s
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.set_anchors_preset(Control.PRESET_HCENTER_WIDE)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l


func _show_message(title: String, subtitle: String, prompt: String) -> void:
	_title.text = title
	_subtitle.text = subtitle
	_prompt.text = prompt
	_title.visible = true
	_subtitle.visible = true
	_prompt.visible = true
	_shade.visible = true


func _start_play() -> void:
	state = "play"
	player.control_enabled = true
	_title.visible = false
	_subtitle.visible = false
	_prompt.visible = false
	_shade.visible = false


# ------------------------------------------------------------------ loop
func _process(delta: float) -> void:
	_time += delta
	_state_time += delta
	if Input.is_action_just_pressed("music"):
		Sfx.toggle_music()
	match state:
		"title":
			if Input.is_action_just_pressed("jump"):
				_start_play()
		"play":
			elapsed += delta
			if Input.is_action_just_pressed("restart"):
				_restart()
		"win", "over":
			if _state_time > 1.2 and (Input.is_action_just_pressed("jump") or Input.is_action_just_pressed("restart")):
				_restart()

	_update_pickups(delta)
	_update_camera(delta)
	_update_hint(delta)
	if _flag:
		_flag.rotation.y = sin(_time * 3.0) * 0.25
	hud.hearts = player.hearts
	hud.berries = berries
	hud.gas = player.gas
	hud.farting = player.farting


func _physics_process(_delta: float) -> void:
	# ledges are one-way: you pass up through them and land on top
	for l in world.ledges:
		var below: bool = player.global_position.y < float(l.get_meta("top")) - 0.08
		var excepted: bool = l.get_meta("excepted", false)
		if below != excepted:
			l.set_meta("excepted", below)
			if below:
				player.add_collision_exception_with(l)
			else:
				player.remove_collision_exception_with(l)
	if state != "play":
		return
	if player.global_position.y < world.floor_near(player.global_position.x) - 9.0:
		_on_fell()
	elif player.global_position.x > Level.GOAL.x - 1.6 and player.global_position.y > Level.GOAL.y - 0.5 \
			and player.is_on_floor():
		# at or past the flag: flying over it and landing beyond still counts
		_win()


func _update_pickups(delta: float) -> void:
	var p := player.global_position + Vector3(0, 0.6, 0)
	for n in _berries:
		if not n.visible:
			continue
		n.rotation.y += delta * 2.5
		n.position.y = n.get_meta("base_y") + sin(_time * 3.0 + n.get_meta("phase")) * 0.12
		if state == "play" and p.distance_to(n.position) < 0.95:
			n.visible = false
			berries += 1
			Sfx.play("berry", -6.0, 1.0 + (berries % 8) * 0.03)
	for n in _beans:
		var cd: float = n.get_meta("cooldown")
		if cd > 0.0:
			cd -= delta
			n.set_meta("cooldown", cd)
			n.visible = cd <= 0.0
			continue
		n.rotation.y += delta * 1.6
		n.rotation.z = sin(_time * 2.0) * 0.15
		n.position.y = n.get_meta("base_y") + sin(_time * 2.4) * 0.15
		if state == "play" and p.distance_to(n.position) < 1.05:
			n.visible = false
			n.set_meta("cooldown", 5.0)
			player.refill()
			Sfx.play("beans", -2.0)
			_poof(n.position, Color(0.85, 0.9, 0.4), 8)
	for n in _checkpoints:
		if not n.get_meta("reached") and state == "play" and player.global_position.x > n.position.x \
				and absf(player.global_position.y - n.position.y) < 4.0:
			n.set_meta("reached", true)
			checkpoint = Vector3(n.position.x, n.position.y, 0)
			Sfx.play("checkpoint", -5.0)
			_light_marker(n)


func _light_marker(post: Node3D) -> void:
	var marker := post.find_child("marker", true, false) as MeshInstance3D
	if marker:
		var gold := StandardMaterial3D.new()
		gold.albedo_color = Color("ffd23f")
		gold.emission_enabled = true
		gold.emission = Color("ffb400")
		gold.emission_energy_multiplier = 1.5
		marker.material_override = gold
	_poof(post.position + Vector3(0, 1.6, 0.4), Color(1.0, 0.9, 0.5), 8)


func _update_camera(delta: float) -> void:
	# follow where Toots is drawn this frame, not where the last physics tick left him
	var pp := player.get_global_transform_interpolated().origin
	_look_ahead = lerpf(_look_ahead, player.facing * 2.2, 1.0 - exp(-2.0 * delta))
	var tx := maxf(pp.x + _look_ahead, world.min_x + 9.0)
	var ty := maxf(pp.y, world.floor_near(pp.x) - 3.0) + 2.6
	camera.position.x = lerpf(camera.position.x, tx, 1.0 - exp(-7.0 * delta))
	camera.position.y = lerpf(camera.position.y, ty, 1.0 - exp(-5.0 * delta))


func _update_hint(delta: float) -> void:
	var text := ""
	if state == "play":
		for h in Level.HINTS:
			if player.global_position.x >= h[0] and player.global_position.x <= h[1]:
				text = h[2]
	if text != "":
		_hint.text = text
	_hint.modulate.a = move_toward(_hint.modulate.a, 1.0 if text != "" else 0.0, delta * 3.0)


# ------------------------------------------------------------------ events
func _on_enemy_defeated(enemy: Node3D) -> void:
	_poof(enemy.position + Vector3(0, 0.4, 0.3), Color(1, 1, 1), 9)


func _on_player_hurt() -> void:
	if player.hearts <= 0:
		_game_over()


func _on_fell() -> void:
	player.hearts -= 1
	if player.hearts <= 0:
		_game_over()
		return
	Sfx.play("hurt", -3.0, 0.8)
	player.respawn(checkpoint + Vector3(0, 0.1, 0))
	camera.position.x = checkpoint.x
	camera.position.y = checkpoint.y + 2.6


func _game_over() -> void:
	state = "over"
	_state_time = 0.0
	player.control_enabled = false
	Sfx.play("lose", -3.0)
	_show_message("PFFFT.", "Toots ran out of puff.", "Press SPACE to try again")


func _win() -> void:
	state = "win"
	_state_time = 0.0
	player.victory_toot()
	Sfx.play("win", -3.0)
	var secs := int(elapsed)
	_show_message("SUMMIT!", "Huckleberries: %d / %d      Time: %d:%02d" % [berries, _berries.size(), secs / 60, secs % 60],
			"Press SPACE to climb again")
	_shade.visible = false


func _restart() -> void:
	# Deferred: reloading on the spot pulls this scene out of the tree while
	# the rest of this frame's _process still wants to read positions from it.
	if _restarting:
		return
	_restarting = true
	Sfx.skip_title = true
	get_tree().reload_current_scene.call_deferred()


func _poof(at: Vector3, color: Color, amount: int) -> void:
	var p := CPUParticles3D.new()
	p.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	p.one_shot = true
	p.explosiveness = 1.0
	p.amount = amount
	p.lifetime = 0.55
	var mesh := SphereMesh.new()
	mesh.radius = 0.3
	mesh.height = 0.6
	mesh.radial_segments = 10
	mesh.rings = 5
	mesh.material = _poof_mat
	p.mesh = mesh
	p.direction = Vector3.UP
	p.spread = 180.0
	p.initial_velocity_min = 1.5
	p.initial_velocity_max = 3.5
	p.gravity = Vector3(0, 1.0, 0)
	p.damping_min = 3.0
	p.damping_max = 4.0
	var ramp := Gradient.new()
	ramp.colors = PackedColorArray([Color(color, 0.9), Color(color, 0.0)])
	p.color_ramp = ramp
	p.position = at
	add_child(p)
	p.emitting = true
	get_tree().create_timer(1.5).timeout.connect(p.queue_free)
