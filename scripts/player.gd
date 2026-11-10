extends CharacterBody3D
## Toots. Runs, jumps, and - his one real talent - flies briefly by farting.

signal hurt_taken
signal fart_started

const SPEED := 7.5
const ACCEL := 55.0
const AIR_ACCEL := 34.0
const FRICTION := 60.0
const JUMP_VELOCITY := 12.0
const GRAVITY := 32.0
const MAX_FALL := 22.0
const COYOTE_TIME := 0.1
const JUMP_BUFFER := 0.12

const FART_TIME := 1.15          ## seconds of thrust in a full tank
const FART_RISE := 6.5           ## climb speed while farting
const FART_ACCEL := 75.0
const GAS_REFILL_TIME := 0.45    ## seconds on the ground to refill
const MAX_HEARTS := 3
const HEIGHT := 1.2
const HALF_WIDTH := 0.38
const MODEL_SCALE := 1.12

var gas := 1.0
var hearts := MAX_HEARTS
var facing := 1.0
var farting := false
var control_enabled := false
var invuln := 0.0
var min_x := -1000.0

var _coyote := 0.0
var _buffer := 0.0
var _jumping := false
var _fart_request := false
var _empty_tooted := false
var _refill_delay := 0.0
var _hurt_lock := 0.0
var _was_on_floor := true
var _walk_phase := 0.0
var _squash := 1.0
var _time := 0.0

var _pivot: Node3D
var _tilt: Node3D
var _model: Node3D
var _arm_l: Node3D
var _arm_r: Node3D
var _leg_l: Node3D
var _leg_r: Node3D
var _cloud: CPUParticles3D
var _burst: CPUParticles3D
var _fart_audio: AudioStreamPlayer
var _fart_fade: Tween


func _ready() -> void:
	axis_lock_linear_z = true
	floor_snap_length = 0.2
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = HALF_WIDTH
	capsule.height = HEIGHT
	shape.shape = capsule
	shape.position.y = HEIGHT / 2.0
	add_child(shape)

	# Everything under the pivot is posed in _process(), so it opts out of
	# physics interpolation; it still rides on the body's interpolated position.
	_pivot = Node3D.new()
	_pivot.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	add_child(_pivot)
	_tilt = Node3D.new()
	_pivot.add_child(_tilt)
	_model = load("res://models/hero.glb").instantiate()
	_model.scale = Vector3.ONE * MODEL_SCALE
	_tilt.add_child(_model)
	_arm_l = _model.find_child("arm_L", true, false)
	_arm_r = _model.find_child("arm_R", true, false)
	_leg_l = _model.find_child("leg_L", true, false)
	_leg_r = _model.find_child("leg_R", true, false)
	_add_fur_rim(_model)

	# the business end
	var butt := Node3D.new()
	butt.position = Vector3(0, 0.32, -0.38)
	_tilt.add_child(butt)
	_cloud = _make_cloud(46, 1.25, false)
	butt.add_child(_cloud)
	_burst = _make_cloud(18, 0.9, true)
	butt.add_child(_burst)

	_fart_audio = AudioStreamPlayer.new()
	_fart_audio.add_to_group("game_audio")
	add_child(_fart_audio)
	_pivot.rotation.y = deg_to_rad(35.0)


func _add_fur_rim(node: Node) -> void:
	# a soft rim light keeps a black monster readable against dark rock
	if node is MeshInstance3D and node.mesh:
		for i in node.mesh.get_surface_count():
			var m := node.mesh.surface_get_material(i) as BaseMaterial3D
			if m and m.resource_name.begins_with("fur"):
				m.rim_enabled = true
				m.rim = 0.55
				m.rim_tint = 0.25
	for c in node.get_children():
		_add_fur_rim(c)


func _make_cloud(amount: int, lifetime: float, burst: bool) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.emitting = false
	p.amount = amount
	p.lifetime = lifetime
	p.local_coords = false
	p.one_shot = burst
	p.explosiveness = 0.95 if burst else 0.0
	p.randomness = 0.4
	var mesh := SphereMesh.new()
	mesh.radius = 0.5
	mesh.height = 1.0
	mesh.radial_segments = 14
	mesh.rings = 7
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/puff.gdshader")
	mesh.material = mat
	p.mesh = mesh
	p.direction = Vector3(0, -0.55, -1.0)
	p.spread = 55.0 if burst else 24.0
	p.initial_velocity_min = 2.0 if burst else 3.0
	p.initial_velocity_max = 5.0 if burst else 5.5
	p.gravity = Vector3(0, 1.6, 0)
	p.damping_min = 3.5
	p.damping_max = 5.0
	p.scale_amount_min = 0.55 if burst else 0.4
	p.scale_amount_max = 1.0 if burst else 0.8
	var grow := Curve.new()
	grow.add_point(Vector2(0.0, 0.3))
	grow.add_point(Vector2(0.25, 0.95))
	grow.add_point(Vector2(1.0, 1.35))
	p.scale_amount_curve = grow
	var ramp := Gradient.new()
	ramp.offsets = PackedFloat32Array([0.0, 0.15, 0.6, 1.0])
	ramp.colors = PackedColorArray([
		Color(0.62, 0.74, 0.16, 0.0), Color(0.55, 0.68, 0.13, 0.92),
		Color(0.42, 0.52, 0.12, 0.65), Color(0.33, 0.36, 0.14, 0.0)])
	p.color_ramp = ramp
	return p


# ------------------------------------------------------------------ physics
func _physics_process(delta: float) -> void:
	var dir := 0.0
	var jump_pressed := false
	var jump_held := false
	var fart_held := false
	var fart_pressed := false
	if control_enabled and _hurt_lock <= 0.0:
		dir = Input.get_axis("move_left", "move_right")
		jump_pressed = Input.is_action_just_pressed("jump")
		jump_held = Input.is_action_pressed("jump")
		fart_held = Input.is_action_pressed("fart")
		fart_pressed = Input.is_action_just_pressed("fart")
	_hurt_lock = maxf(0.0, _hurt_lock - delta)
	invuln = maxf(0.0, invuln - delta)

	var on_floor := is_on_floor()
	_coyote = COYOTE_TIME if on_floor else _coyote - delta
	_buffer = JUMP_BUFFER if jump_pressed else _buffer - delta

	# run
	if _hurt_lock <= 0.0:
		var accel := AIR_ACCEL
		if on_floor:
			accel = ACCEL if absf(dir) > 0.01 else FRICTION
		elif absf(dir) < 0.01:
			accel = AIR_ACCEL * 0.35
		velocity.x = move_toward(velocity.x, dir * SPEED * (1.1 if farting else 1.0), accel * delta)
		if absf(dir) > 0.01:
			facing = signf(dir)

	# jump (or, when already airborne, ask for a fart)
	if _buffer > 0.0 and _coyote > 0.0:
		velocity.y = JUMP_VELOCITY
		_buffer = 0.0
		_coyote = 0.0
		_jumping = true
		_squash = 1.25
		Sfx.play("jump", -4.0, randf_range(0.95, 1.08))
	elif jump_pressed and not on_floor:
		_fart_request = true
	if fart_pressed:
		_fart_request = true
	if not (jump_held or fart_held):
		_fart_request = false
		_empty_tooted = false
	if _jumping and not jump_held and velocity.y > 4.0:
		velocity.y *= 0.45
		_jumping = false
	if velocity.y <= 0.0:
		_jumping = false

	# fart-fly
	if _fart_request and gas > 0.0 and (farting or gas > 0.06):
		if not farting:
			_start_fart()
		if velocity.y > FART_RISE:
			# still rising faster than a fart can push (fresh off a jump or a
			# stomp): let that play out rather than braking it, and save the gas
			velocity.y = maxf(velocity.y - GRAVITY * delta, FART_RISE)
		else:
			gas = maxf(0.0, gas - delta / FART_TIME)
			velocity.y = move_toward(velocity.y, FART_RISE, FART_ACCEL * delta)
		_jumping = false
		if gas <= 0.0:
			_stop_fart()
			_fart_request = false
	else:
		if farting:
			_stop_fart()
		if _fart_request and not _empty_tooted and gas <= 0.06:
			_empty_tooted = true          # running on empty: a sad little squeak
			Sfx.play("toot", -6.0, randf_range(1.1, 1.4))
			_burst.amount = 5
			_burst.restart()

	if not farting and not on_floor:
		velocity.y = maxf(velocity.y - GRAVITY * delta, -MAX_FALL)

	# gas comes back on solid ground
	if on_floor and not farting:
		_refill_delay -= delta
		if _refill_delay <= 0.0:
			gas = minf(1.0, gas + delta / GAS_REFILL_TIME)

	move_and_slide()
	position.z = 0.0
	if position.x < min_x:
		position.x = min_x
		velocity.x = maxf(velocity.x, 0.0)

	if is_on_floor() and not _was_on_floor:
		_squash = 0.72
		Sfx.play("land", -10.0)
	_was_on_floor = is_on_floor()


func _start_fart() -> void:
	farting = true
	if _fart_fade:
		_fart_fade.kill()
	_fart_audio.stream = Sfx.streams.get(["fart_a", "fart_b", "fart_c"].pick_random())
	_fart_audio.volume_db = 0.0
	_fart_audio.pitch_scale = randf_range(0.9, 1.22)
	_fart_audio.play()
	_cloud.emitting = true
	_burst.amount = 18
	_burst.restart()
	_squash = 1.2
	fart_started.emit()


func _stop_fart() -> void:
	farting = false
	_cloud.emitting = false
	_refill_delay = 0.2
	if _fart_fade:
		_fart_fade.kill()
	_fart_fade = create_tween()
	_fart_fade.tween_property(_fart_audio, "volume_db", -45.0, 0.09)
	_fart_fade.tween_callback(_fart_audio.stop)


# ------------------------------------------------------------------ events
func bounce() -> void:
	## Called when we stomp something: hop off it and get a puff of gas back.
	velocity.y = 13.0 if Input.is_action_pressed("jump") and control_enabled else 9.0
	_jumping = false
	_squash = 1.25
	gas = minf(1.0, gas + 0.4)


func hurt(from_x: float) -> bool:
	if invuln > 0.0 or hearts <= 0:
		return false
	hearts -= 1
	invuln = 1.6
	_hurt_lock = 0.35
	if farting:
		_stop_fart()
	_fart_request = false
	velocity = Vector3((1.0 if global_position.x >= from_x else -1.0) * 6.5, 8.5, 0)
	_squash = 0.75
	Sfx.play("hurt", -3.0)
	hurt_taken.emit()
	return true


func refill() -> void:
	gas = 1.0
	_empty_tooted = false


func respawn(at: Vector3) -> void:
	global_position = at
	reset_physics_interpolation()     # a teleport, not a very fast move
	velocity = Vector3.ZERO
	gas = 1.0
	invuln = 2.0
	_hurt_lock = 0.0
	if farting:
		_stop_fart()
	_fart_request = false


func victory_toot() -> void:
	control_enabled = false
	if farting:
		_stop_fart()
	_fart_request = false
	velocity.x = 0.0
	_fart_audio.stream = Sfx.streams.get("fart_win")
	_fart_audio.volume_db = 0.0
	_fart_audio.pitch_scale = 1.0
	_fart_audio.play()
	_cloud.emitting = true
	_burst.amount = 18
	_burst.restart()
	get_tree().create_timer(2.2).timeout.connect(func() -> void: _cloud.emitting = false)


# ------------------------------------------------------------------ looks
func _process(delta: float) -> void:
	_time += delta
	var on_floor := is_on_floor()
	var run := clampf(absf(velocity.x) / SPEED, 0.0, 1.0)

	# turn to face where we're going, but never fully side-on: the teeth must show
	var yaw := facing * deg_to_rad(52.0 if run > 0.1 or not on_floor else 28.0)
	_pivot.rotation.y = lerp_angle(_pivot.rotation.y, yaw, 1.0 - exp(-14.0 * delta))

	var lean := 0.0
	var arm_raise := 0.0
	var arm_swing := 0.0
	var leg_swing := 0.0
	var bob := 0.0
	if farting:
		lean = 0.55
		arm_raise = 0.55 + sin(_time * 34.0) * 0.3
		leg_swing = -0.5
		_model.position = Vector3(randf_range(-1, 1), randf_range(-1, 1), 0) * 0.018
	else:
		_model.position = Vector3.ZERO
		if on_floor:
			_walk_phase += delta * (5.0 + 11.0 * run) * (1.0 if run > 0.05 else 0.0)
			leg_swing = sin(_walk_phase) * 0.95 * run
			arm_swing = -sin(_walk_phase) * 0.6 * run     # opposite to the leg on the same side
			bob = absf(sin(_walk_phase)) * 0.07 * run + sin(_time * 2.4) * 0.012
			lean = 0.14 * run
		else:
			arm_raise = 0.75 if velocity.y > 0.0 else 0.35 + sin(_time * 22.0) * 0.25
			leg_swing = 0.35
			lean = -0.1 if velocity.y > 0.0 else 0.12

	var k := 1.0 - exp(-18.0 * delta)
	_tilt.rotation.x = lerpf(_tilt.rotation.x, lean, k)
	_tilt.position.y = bob
	if _arm_l and _arm_r:
		_arm_l.rotation.z = lerpf(_arm_l.rotation.z, arm_raise, k)
		_arm_r.rotation.z = lerpf(_arm_r.rotation.z, -arm_raise, k)
		_arm_l.rotation.y = lerpf(_arm_l.rotation.y, arm_swing, k)
		_arm_r.rotation.y = lerpf(_arm_r.rotation.y, arm_swing, k)
	if _leg_l and _leg_r:
		var both := farting or not on_floor
		_leg_l.rotation.x = lerpf(_leg_l.rotation.x, leg_swing, k)
		_leg_r.rotation.x = lerpf(_leg_r.rotation.x, leg_swing if both else -leg_swing, k)

	# squash and stretch
	_squash = lerpf(_squash, 1.0, 1.0 - exp(-10.0 * delta))
	var wide := 1.0 / sqrt(_squash)
	_tilt.scale = Vector3(wide, _squash, wide)

	# blink while invulnerable
	_pivot.visible = invuln <= 0.0 or fmod(invuln, 0.16) < 0.09 or hearts <= 0
