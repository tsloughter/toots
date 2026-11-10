extends Node
## Dev helper, only active when the game is launched with user arguments:
##
##   godot --path . -- --shots=/abs/dir [--start-x=60] [--secs=6] [--moves=run,jump,fart] [--every=0.5]
##
## It starts the game, feeds scripted input and saves a screenshot every
## half second (or every --every seconds), then quits. Handy for checking the game without playing it.

var _dir := ""
var _secs := 6.0
var _moves := "run,jump,fart"
var _start_x := NAN
var _t := 0.0
var _shot := 0
var _next_shot := 0.4
var _every := 0.5
var _main: Node
var _drop_on: Node3D
static var _poked := false


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shots="):
			_dir = a.trim_prefix("--shots=")
		elif a.begins_with("--secs="):
			_secs = float(a.trim_prefix("--secs="))
		elif a.begins_with("--start-x="):
			_start_x = float(a.trim_prefix("--start-x="))
		elif a.begins_with("--moves="):
			_moves = a.trim_prefix("--moves=")
		elif a.begins_with("--every="):
			_every = maxf(float(a.trim_prefix("--every=")), 0.02)
	if _dir == "":
		queue_free()
		return
	DirAccess.make_dir_recursive_absolute(_dir)
	process_priority = -10        # run before main.gd so it sees our key presses this frame
	_main = get_parent()


func _process(delta: float) -> void:
	if _dir == "":
		return
	_t += delta
	if _main.state == "title" and _t > 0.9:
		_main._start_play()
		if not is_nan(_start_x):
			var y := 0.0
			for seg in _main.Level.GROUND:
				if _start_x >= seg[0] and _start_x <= seg[1]:
					y = seg[2]
			if _moves.contains("drop"):
				# land on the head of whichever critter is nearest
				var best := 1e9
				for c in _main.get_children():
					if c.get("kind") != null and absf(c.position.x - _start_x) < best:
						best = absf(c.position.x - _start_x)
						y = c.position.y + 3.0
						_drop_on = c
			_main.player.global_position = Vector3(_start_x, y + 0.1, 0)
			_main.player.reset_physics_interpolation()
			_main.camera.position.x = _start_x
			_main.camera.position.y = y + 2.6
	if _main.state != "title":
		var pt := _t - 0.9
		_hold("move_right", _moves.contains("run"))
		_hold("move_left", _moves.contains("left"))
		# jump every 1.6s; hold a mid-air fart from 0.45s to 1.3s of each cycle
		var cyc := fmod(pt, 1.6)
		var want_jump := _moves.contains("jump") and cyc < 0.25
		var want_fart := _moves.contains("fart") and cyc > 0.45 and cyc < 1.3
		_hold("jump", want_jump or want_fart)
	if _drop_on and is_instance_valid(_drop_on) and _drop_on.alive and _main.player.velocity.y > -8.0 \
			and _main.player.global_position.y > _drop_on.position.y + 1.5:
		_main.player.global_position.x = _drop_on.position.x
	if _t >= _next_shot and _t <= _secs:
		_next_shot += _every
		get_viewport().get_texture().get_image().save_png("%s/shot_%02d.png" % [_dir, _shot])
		_shot += 1
		var enemies := 0
		for c in _main.get_children():
			if c.get("kind") != null and c.alive:
				enemies += 1
		print("AUTOPLAY t=%.1f pos=(%.1f, %.1f) hearts=%d gas=%.2f berries=%d enemies=%d state=%s" % [_t,
				_main.player.global_position.x, _main.player.global_position.y, _main.player.hearts,
				_main.player.gas, _main.berries, enemies, _main.state])
	if _t > 2.0 and not _poked:
		_poked = true
		if _moves.contains("restart"):
			Input.action_press("restart")       # same path as pressing R
			Input.action_release.call_deferred("restart")
		elif _moves.contains("close"):
			get_tree().root.propagate_notification(NOTIFICATION_WM_CLOSE_REQUEST)
	if _t > _secs:
		Sfx.quit_cleanly()


func _hold(action: String, on: bool) -> void:
	if on and not Input.is_action_pressed(action):
		Input.action_press(action)
	elif not on and Input.is_action_pressed(action):
		Input.action_release(action)
