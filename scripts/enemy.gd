extends Node3D
## Rocky Mountain locals. They patrol between two x positions; contact is
## resolved with simple box overlap against the player (no physics bodies).

signal defeated(enemy: Node3D)

const PlayerScript := preload("res://scripts/player.gd")

const DEFS := {
	"beaver": {"speed": 1.7, "hw": 0.5, "h": 0.68, "stomp": true, "scale": 1.1},
	"ram": {"speed": 1.4, "hw": 0.68, "h": 1.3, "stomp": true, "scale": 1.0, "charge": 9.0},
	"porcupine": {"speed": 0.9, "hw": 0.5, "h": 0.75, "stomp": false, "scale": 1.15},
	"eagle": {"speed": 4.2, "hw": 0.75, "h": 0.5, "stomp": true, "scale": 1.3, "fly": true},
}

## Beaver joints in model space (see blender/critters.py): the hips it rocks
## back on when it sits up, and how far the toes reach ahead of each leg.
const BEAVER_HIP := Vector3(0.0, 0.17, -0.2)
const BEAVER_SIT := 0.8
const BEAVER_TOE_FRONT := 0.1
const BEAVER_TOE_HIND := 0.2
## How close Toots gets before a porcupine puts its quills up.
const PORCUPINE_ALARM := 4.5
const PORCUPINE_HIP := 0.14

var kind := "beaver"
var x_min := 0.0
var x_max := 0.0
var player: PlayerScript
var alive := true

var _def: Dictionary
var _dir := -1.0
var _base_y := 0.0
var _t := 0.0
var _state := "walk"
var _state_t := 0.0
var _model: Node3D
var _legs: Array[Node3D] = []
var _swing: Array[float] = []   ## walk-cycle angle of each leg
var _shins: Array[Node3D] = []  ## lower leg of each leg, or null if it has no knee
var _ears: Array[Node3D] = []
var _quills: Node3D
var _bristle := 0.0             ## 0 = quills flat, 1 = fully raised
var _body: Node3D
var _head: Node3D
var _tail: Node3D
var _eyes: Array[Node3D] = []
var _rest := {}                 ## Node3D -> position it was modelled at
var _look := 0.0
var _nod := 0.0
var _blink := 2.0
var _twitch := 1.0              ## counts down to the next ear twitch
var _twitch_ear := 0
var _wing_l: Node3D
var _wing_r: Node3D
var _fall := Vector3.ZERO
var _was_above := false         ## Toots's feet were above our head last tick


func setup(p_kind: String, pos: Vector3, p_min: float, p_max: float, p_player: PlayerScript) -> void:
	kind = p_kind
	_def = DEFS[kind]
	position = pos
	_base_y = pos.y
	x_min = p_min
	x_max = p_max
	player = p_player
	_t = randf() * 6.0
	_model = load("res://models/%s.glb" % kind).instantiate()
	_model.scale = Vector3.ONE * _def.scale
	_use_paint(_model)
	add_child(_model)
	for n in ["leg_FL", "leg_BR", "leg_FR", "leg_BL"]:
		var leg := _model.find_child(n, true, false) as Node3D
		if leg:
			_legs.append(leg)
			_swing.append(0.0)
			_rest[leg] = leg.position
			_shins.append(_model.find_child(n.replace("leg_", "shin_"), true, false) as Node3D)
	_body = _model.find_child("body", true, false)
	_head = _model.find_child("head", true, false)
	_tail = _model.find_child("tail", true, false)
	_quills = _model.find_child("quills", true, false)
	if _tail:
		_rest[_tail] = _tail.position
	for n in ["eye_L", "eye_R"]:
		var eye := _model.find_child(n, true, false) as Node3D
		if eye:
			_eyes.append(eye)
	for n in ["ear_L", "ear_R"]:
		var ear := _model.find_child(n, true, false) as Node3D
		if ear:
			_ears.append(ear)
	_blink = randf_range(0.5, 3.0)
	_wing_l = _model.find_child("wing_L", true, false)
	_wing_r = _model.find_child("wing_R", true, false)
	_model.rotation.y = _dir * deg_to_rad(70.0)
	reset_physics_interpolation()     # we were placed, we didn't travel here


func _physics_process(delta: float) -> void:
	_t += delta
	if not alive:
		_fall.y -= 30.0 * delta
		position += _fall * delta
		_model.rotation.z += 9.0 * delta
		if position.y < _base_y - 25.0:
			queue_free()
		return

	_state_t += delta
	var speed: float = _def.speed
	if kind == "ram":
		speed = _ram_brain(speed)
	elif kind == "beaver":
		# every so often a beaver stops and sits up to have a look around
		if _state == "walk" and _state_t > 3.5 and randf() < 0.01:
			_set_state("look")
		elif _state == "look" and _state_t > 1.7:
			_set_state("walk")
		if _state == "look":
			speed = 0.0

	position.x += _dir * speed * delta
	if position.x > x_max:
		position.x = x_max
		_dir = -1.0
		if _state == "charge":
			_set_state("rest")
	elif position.x < x_min:
		position.x = x_min
		_dir = 1.0
		if _state == "charge":
			_set_state("rest")

	_animate(delta, speed)
	_check_player()


func _ram_brain(walk_speed: float) -> float:
	var dx := player.global_position.x - position.x
	var dy := player.global_position.y - position.y
	match _state:
		"walk":
			var in_lane := player.global_position.x > x_min - 1.0 and player.global_position.x < x_max + 1.0
			if in_lane and absf(dx) < 8.5 and absf(dx) > 1.0 and absf(dy) < 1.6 and _state_t > 0.6:
				_dir = signf(dx)
				_set_state("windup")
			return walk_speed
		"windup":
			if _state_t > 0.6:
				_set_state("charge")
			return -0.8          # shuffle backwards before the charge
		"charge":
			if _state_t > 2.2:
				_set_state("rest")
			return _def.charge
		"rest":
			if _state_t > 1.0:
				_set_state("walk")
			return 0.0
	return walk_speed


func _set_state(s: String) -> void:
	_state = s
	_state_t = 0.0


func _animate(delta: float, speed: float) -> void:
	var yaw := _dir * deg_to_rad(62.0 if _def.has("fly") else 72.0)
	_model.rotation.y = lerp_angle(_model.rotation.y, yaw, 1.0 - exp(-10.0 * delta))
	if _def.has("fly"):
		position.y = _base_y + sin(_t * 1.7) * 1.1
		var flap := sin(_t * 9.0)
		if _wing_l and _wing_r:
			_wing_l.rotation.z = flap * 0.7 + 0.1
			_wing_r.rotation.z = -flap * 0.7 - 0.1
		_model.position.y = -flap * 0.06
		_model.rotation.x = 0.15 + cos(_t * 1.7) * 0.2
		return
	var stride := absf(speed) * (5.0 if kind == "ram" else 9.0)
	if kind == "ram":
		stride = minf(stride, 20.0)       # a gallop you can still read
	var phase := _t * maxf(stride, 0.0)
	var amp := 0.0 if absf(speed) < 0.05 else (0.75 if _state == "charge" else 0.5)
	for i in _legs.size():
		var s := sin(phase + _gait(i))
		_swing[i] = lerpf(_swing[i], s * amp, 0.4)
		_legs[i].rotation.x = _swing[i]
	var lean := 0.0
	var hop := absf(sin(phase)) * 0.04
	match _state:
		"windup":
			lean = -0.22
			_model.position.x = sin(_t * 50.0) * 0.02
		"charge":
			lean = 0.28
			hop = absf(sin(phase)) * 0.1
		"look":
			lean = -BEAVER_SIT   # beaver sits up on its haunches
			hop = 0.0
		_:
			_model.position.x = 0.0
	_model.rotation.x = lerpf(_model.rotation.x, lean, 1.0 - exp(-9.0 * delta))
	_model.position.y = hop
	if kind == "beaver" or kind == "porcupine":
		_model.rotation.z = sin(phase) * 0.07     # waddle
	if kind == "beaver":
		_animate_beaver(delta, phase, hop)
	elif kind == "ram":
		_animate_ram(delta, phase, amp)
	elif kind == "porcupine":
		_animate_porcupine(delta, phase)


## Where leg i is in the stride: diagonal pairs together at a walk, and the
## ram bounds off both front legs and then both hind legs when it charges.
func _gait(i: int) -> float:
	if _state == "charge":
		return 0.0 if i % 2 == 0 else 2.2
	return PI if i >= 2 else 0.0


## The beaver has more joints than the other critters: it rocks back on its
## hips with its feet and tail still on the ground, tucks its paws in, looks
## about, slaps its tail, blinks and breathes.
func _animate_beaver(delta: float, phase: float, hop: float) -> void:
	var lean := _model.rotation.x
	var sit := clampf(-lean / BEAVER_SIT, 0.0, 1.0)
	var hip: Vector3 = BEAVER_HIP * float(_def.scale)
	var off := hip - hip.rotated(Vector3.RIGHT, lean)
	_model.position = off.rotated(Vector3.UP, _model.rotation.y) + Vector3(0.0, hop, 0.0)

	for i in _legs.size():
		var leg := _legs[i]
		var nm := String(leg.name)
		var a := _swing[i]
		var rest: Vector3 = _rest[leg]
		if nm.begins_with("leg_B"):
			# hind feet stay planted, and push off from the toes
			leg.rotation.x = a - lean
			leg.position = rest + Vector3(0.0, _toe_lift(a, BEAVER_TOE_HIND, BEAVER_HIP.y), 0.0)
		else:
			var side := 1.0 if nm.ends_with("L") else -1.0
			leg.rotation.x = a + 0.25 * sit
			leg.rotation.z = -side * 0.6 * sit        # paws together against the chest
			leg.position = rest + Vector3(0.0, _toe_lift(a, BEAVER_TOE_FRONT, BEAVER_HIP.y), 0.0)

	if _tail:
		# keep the paddle flat on the ground while the rump tips down onto it
		var rest: Vector3 = _rest[_tail]
		var now := BEAVER_HIP + (rest - BEAVER_HIP).rotated(Vector3.RIGHT, lean)
		_tail.position = rest + Vector3(0.0, rest.y - now.y, 0.0).rotated(Vector3.RIGHT, -lean)
		var slap := 0.0
		if _state == "look" and _state_t > 0.8 and _state_t < 1.1:
			slap = sin((_state_t - 0.8) / 0.3 * PI) * 0.5
		_tail.rotation = Vector3(-lean + slap, sin(phase) * 0.16 * (1.0 - sit), 0.0)

	if _head:
		# level the head when sitting up, and have a look towards the camera
		var look := 0.0
		if _state == "look":
			look = -_dir * 0.55 + sin(_state_t * 4.2) * 0.5
		_look = lerpf(_look, look, 1.0 - exp(-7.0 * delta))
		var nod := sin(phase * 2.0) * 0.05 * (1.0 - sit) + sin(_t * 1.3) * 0.03
		_head.basis = Basis(Vector3.RIGHT, -lean * 0.8 + nod) * Basis(Vector3.UP, _look)

	_breathe(3.0 + 2.0 * sit, 0.02)
	_blink_eyes(delta)


## The ram folds its knees and hocks as it walks, nods along, and telegraphs
## the charge: it paws the ground with its horns down, then gallops with its
## ears pinned back and stands there panting afterwards.
func _animate_ram(delta: float, phase: float, amp: float) -> void:
	var paw_leg := 2 if _dir > 0.0 else 0          # the front leg nearer the camera
	for i in _legs.size():
		var shin := _shins[i]
		if shin == null:
			continue
		# fold the joint while the leg swings forward, so the hoof clears the ground
		var flex := maxf(0.0, -cos(phase + _gait(i))) * amp * 1.5
		if _state == "windup" and i == paw_leg:
			var paw := sin(_state_t * 17.0)
			_legs[i].rotation.x = -0.35 + paw * 0.3
			flex = 0.55 - paw * 0.45
		# knees fold backwards, hocks forwards
		var front := String(_legs[i].name).begins_with("leg_F")
		shin.rotation.x = lerpf(shin.rotation.x, flex if front else -flex * 0.8, 0.5)

	if _head:
		var nod := sin(phase * 2.0) * 0.04
		var look := -_dir * (0.22 + 0.14 * sin(_t * 0.9))     # half an eye on the camera
		match _state:
			"windup":
				nod = 0.85 + sin(_state_t * 17.0) * 0.05
				look = 0.0
			"charge":
				nod = 0.5
				look = 0.0
			"rest":
				nod = -0.1 + sin(_t * 9.0) * 0.03
		_nod = lerpf(_nod, nod, 1.0 - exp(-10.0 * delta))
		_look = lerpf(_look, look, 1.0 - exp(-6.0 * delta))
		_head.basis = Basis(Vector3.UP, _look) * Basis(Vector3.RIGHT, _nod)

	_twitch -= delta
	if _twitch < -0.35:
		_twitch = randf_range(1.0, 3.5)
		_twitch_ear = randi() % 2
	for i in _ears.size():
		var side := 1.0 if String(_ears[i].name).ends_with("L") else -1.0
		var back := 0.0
		if _state == "charge" or _state == "windup":
			back = 0.6
		elif _twitch < 0.0 and i == _twitch_ear:
			back = sin(-_twitch / 0.35 * TAU * 2.0) * 0.45
		_ears[i].rotation.y = lerpf(_ears[i].rotation.y, side * back, 0.5)

	if _tail:
		# a flick every few seconds; straight up when charging
		var burst := pow(maxf(0.0, sin(_t * 1.3)), 6.0)
		var up := 1.0 if _state == "charge" else 0.0
		_tail.rotation.z = sin(_t * 22.0) * 0.6 * burst
		_tail.rotation.x = lerpf(_tail.rotation.x, up, 1.0 - exp(-10.0 * delta))

	if _state == "rest":
		_breathe(9.0, 0.03)       # panting
	else:
		_breathe(2.6, 0.012)
	_blink_eyes(delta)


## The porcupine snuffles along nose down until Toots gets close, then tucks
## its head in, raises its quills with a rattle and lashes its tail.
func _animate_porcupine(delta: float, phase: float) -> void:
	var gap := player.global_position - position
	var alarmed := player.control_enabled and absf(gap.x) < PORCUPINE_ALARM and absf(gap.y) < 3.0
	_bristle = lerpf(_bristle, 1.0 if alarmed else 0.0, 1.0 - exp(-(9.0 if alarmed else 2.5) * delta))
	if _quills:
		# the quills are rooted deep in the body, so growing them pushes them out
		var puff := 1.0 + 0.24 * _bristle + sin(_t * 46.0) * 0.018 * _bristle
		_quills.scale = Vector3(puff, puff, puff)

	for i in _legs.size():
		var leg := _legs[i]
		var reach := 0.1 if String(leg.name).begins_with("leg_F") else 0.13
		var rest: Vector3 = _rest[leg]
		leg.position = rest + Vector3(0.0, _toe_lift(_swing[i], reach, PORCUPINE_HIP), 0.0)

	if _tail:
		_tail.rotation.y = sin(phase) * 0.22 * (1.0 - _bristle) + sin(_t * 15.0) * 0.55 * _bristle
		_tail.rotation.x = 0.35 * _bristle

	if _head:
		var nod := 0.08 + sin(phase * 2.0) * 0.05 + sin(_t * 6.0) * 0.02
		_nod = lerpf(_nod, lerpf(nod, 0.4, _bristle), 1.0 - exp(-10.0 * delta))
		_head.basis = Basis(Vector3.UP, -sin(phase) * 0.1) * Basis(Vector3.RIGHT, _nod)

	_breathe(3.2 + 4.0 * _bristle, 0.018)
	_blink_eyes(delta)


func _breathe(rate: float, depth: float) -> void:
	if _body:
		var breath := sin(_t * rate) * depth
		_body.scale = Vector3(1.0 + breath, 1.0 + breath * 0.6, 1.0)


func _blink_eyes(delta: float) -> void:
	_blink -= delta
	if _blink < -0.12:
		_blink = randf_range(1.2, 4.0)
	for eye in _eyes:
		eye.scale.y = 0.1 if _blink < 0.0 else 1.0


## How far to raise a leg swung back by angle a so its toes stay on the
## ground. reach is how far the toes are ahead of the hip, hip its height.
func _toe_lift(a: float, reach: float, hip: float) -> float:
	return maxf(0.0, reach * sin(a) - hip * (1.0 - cos(a)))


func _check_player() -> void:
	var pp := player.global_position
	var bottom: float = position.y - (_def.h * 0.5 if _def.has("fly") else 0.0)
	var top: float = bottom + _def.h
	var was_above := _was_above
	_was_above = pp.y >= top
	# no contact on the title screen, after the summit, or once he's out of hearts
	if player.hearts <= 0 or not player.control_enabled:
		return
	if absf(pp.x - position.x) > _def.hw + player.HALF_WIDTH:
		return
	if pp.y > top or pp.y + player.HEIGHT < bottom:
		return
	# A fast fall can cover more than the top of a small critter in one tick, so
	# also count it as a stomp if he was clear above us on the previous tick.
	var from_above: bool = player.velocity.y < -0.5 and (was_above or pp.y > bottom + _def.h * 0.4)
	if from_above and _def.stomp:
		_die()
		player.bounce()
	elif from_above:
		# spiky: ouch, and get thrown clear
		if player.hurt(position.x):
			player.velocity.y = 10.0
	else:
		player.hurt(position.x)


func _die() -> void:
	alive = false
	_fall = Vector3(-_dir * 2.0, 7.0, 0.6)
	_model.scale = Vector3(1.25, 0.45, 1.25) * _def.scale
	Sfx.play("stomp", -2.0, randf_range(0.92, 1.1))
	defeated.emit(self)


func _use_paint(node: Node) -> void:
	# the fur colours are painted on the models' vertices (see vertex_colours
	# in blender/lib.py); the importer only switches that on for some surfaces
	if node is MeshInstance3D and node.mesh:
		for i in node.mesh.get_surface_count():
			var m := node.mesh.surface_get_material(i) as BaseMaterial3D
			if m and m.resource_name.begins_with("paint"):
				m.vertex_color_use_as_albedo = true
	for c in node.get_children():
		_use_paint(c)
