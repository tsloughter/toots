extends Node3D
## Rocky Mountain locals. They patrol between two x positions; contact is
## resolved with simple box overlap against the player (no physics bodies).

signal defeated(enemy: Node3D)

const PlayerScript := preload("res://scripts/player.gd")

const DEFS := {
	"marmot": {"speed": 1.7, "hw": 0.45, "h": 0.68, "stomp": true, "scale": 1.2},
	"ram": {"speed": 1.4, "hw": 0.68, "h": 1.3, "stomp": true, "scale": 1.0, "charge": 9.0},
	"porcupine": {"speed": 0.9, "hw": 0.5, "h": 0.7, "stomp": false, "scale": 1.15},
	"eagle": {"speed": 4.2, "hw": 0.75, "h": 0.5, "stomp": true, "scale": 1.3, "fly": true},
}

var kind := "marmot"
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
	add_child(_model)
	for n in ["leg_FL", "leg_BR", "leg_FR", "leg_BL"]:
		var leg := _model.find_child(n, true, false) as Node3D
		if leg:
			_legs.append(leg)
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
	elif kind == "marmot":
		# every so often a marmot stops to have a look around
		if _state == "walk" and _state_t > 3.5 and randf() < 0.01:
			_set_state("look")
		elif _state == "look" and _state_t > 1.1:
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
	var phase := _t * maxf(stride, 0.0)
	var amp := 0.0 if absf(speed) < 0.05 else (0.75 if _state == "charge" else 0.5)
	for i in _legs.size():
		var s := sin(phase + (PI if i >= 2 else 0.0))
		_legs[i].rotation.x = lerpf(_legs[i].rotation.x, s * amp, 0.4)
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
			lean = -0.75         # marmot stands up on its hind legs
			hop = 0.12
		_:
			_model.position.x = 0.0
	_model.rotation.x = lerpf(_model.rotation.x, lean, 1.0 - exp(-9.0 * delta))
	_model.position.y = hop
	if kind == "marmot" or kind == "porcupine":
		_model.rotation.z = sin(phase) * 0.07     # waddle


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
