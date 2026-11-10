extends Node3D
## Builds the Rockies: sky, sun, haze, distant ranges, foothills, and the
## level geometry itself from the tables in level.gd.

const Level := preload("res://scripts/level.gd")

var ledges: Array[StaticBody3D] = []     ## one-way platforms, managed by main.gd
var kill_y := -20.0
var min_x := -14.0

var _cache := {}
var _rng := RandomNumberGenerator.new()
var _clouds: Array[Node3D] = []
var _snow: StandardMaterial3D


func model(model_name: String) -> Node3D:
	if not _cache.has(model_name):
		_cache[model_name] = load("res://models/%s.glb" % model_name)
	return _cache[model_name].instantiate()


func place(model_name: String, pos: Vector3, size := Vector3.ONE, yaw := 0.0, parent: Node = self) -> Node3D:
	var m := model(model_name)
	parent.add_child(m)
	m.position = pos
	m.scale = size
	m.rotation.y = yaw
	return m


func build() -> void:
	_rng.seed = 20261109
	_snow = StandardMaterial3D.new()
	_snow.albedo_color = Color("f4f8fc")
	_snow.roughness = 0.6
	_build_environment()
	var x0: float = Level.GROUND[0][0]
	var x1: float = Level.GROUND[-1][1]
	_build_background(x0, x1)
	_build_ground()
	_build_ledges()
	min_x = x0 + 2.0


func floor_near(x: float) -> float:
	## Lowest ground top within a screen or so of x: used to decide how far
	## Toots can fall before he counts as lost down a hole.
	var lowest := 1e9
	for seg in Level.GROUND:
		if seg[1] > x - 16.0 and seg[0] < x + 16.0:
			lowest = minf(lowest, seg[2])
	return lowest if lowest < 1e8 else kill_y + 13.0


func _process(delta: float) -> void:
	for c in _clouds:
		c.position.x += delta * c.get_meta("drift")
		if c.position.x > 900.0:
			c.position.x = -500.0


# ------------------------------------------------------------------ sky
func _build_environment() -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color("2a69c2")
	sky_mat.sky_horizon_color = Color("c2def4")
	sky_mat.sky_curve = 0.12
	sky_mat.ground_horizon_color = Color("c2def4")
	sky_mat.ground_bottom_color = Color("8fb3cf")
	var sky := Sky.new()
	sky.sky_material = sky_mat

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 1.0
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	# blue mountain haze: the further the range, the paler it gets
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_DEPTH
	env.fog_light_color = Color("b3cee8")
	env.fog_depth_begin = 40.0
	env.fog_depth_end = 720.0
	env.fog_density = 0.9
	env.fog_sky_affect = 0.0
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-46, -34, 0)
	sun.light_color = Color("fff2da")
	sun.light_energy = 1.3
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 70.0
	add_child(sun)


# ------------------------------------------------------------------ backdrop
func _build_background(x0: float, x1: float) -> void:
	var back := Node3D.new()
	back.name = "Backdrop"
	add_child(back)
	var peaks := ["mountain_a", "mountain_b", "mountain_c"]

	# valley floor far below
	var plane := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(4000, 1400)
	var floor_mat := StandardMaterial3D.new()
	floor_mat.albedo_color = Color("2c5038")
	floor_mat.roughness = 1.0
	pm.material = floor_mat
	plane.mesh = pm
	plane.position = Vector3((x0 + x1) * 0.5, -46, -640)
	back.add_child(plane)

	# the great snowy wall on the horizon
	var x := x0 - 620.0
	while x < x1 + 620.0:
		var s := _rng.randf_range(78, 118)
		place(peaks[_rng.randi() % 3], Vector3(x, -46, -470 + _rng.randf_range(-45, 45)),
				Vector3(s * 1.2, s, s), _yaw(), back)
		x += s * _rng.randf_range(1.0, 1.5)
	# a nearer, lower range
	x = x0 - 330.0
	while x < x1 + 330.0:
		var s := _rng.randf_range(38, 58)
		place(peaks[_rng.randi() % 3], Vector3(x, -42, -235 + _rng.randf_range(-30, 30)),
				Vector3(s * 1.3, s * 0.85, s), _yaw(), back)
		x += s * _rng.randf_range(1.2, 1.9)
	# forested foothills
	x = x0 - 160.0
	while x < x1 + 160.0:
		var s := _rng.randf_range(28, 44)
		place("hill", Vector3(x, _rng.randf_range(-36, -26), _rng.randf_range(-125, -75)),
				Vector3(s, s * _rng.randf_range(0.8, 1.2), s), _rng.randf() * TAU, back)
		x += s * _rng.randf_range(0.9, 1.4)
	# clouds
	for i in 16:
		var s := _rng.randf_range(14, 30)
		var c := place("cloud_a" if i % 2 == 0 else "cloud_b",
				Vector3(_rng.randf_range(-500, 900), _rng.randf_range(45, 120), _rng.randf_range(-420, -170)),
				Vector3(s, s * 0.7, s), 0.0, back)
		c.set_meta("drift", _rng.randf_range(1.0, 3.0))
		_clouds.append(c)


func _yaw() -> float:
	return (PI if _rng.randf() < 0.5 else 0.0) + _rng.randf_range(-0.5, 0.5)


# ------------------------------------------------------------------ level
func _build_ground() -> void:
	var tiles := ["ground_a", "ground_b", "ground_c"]
	var lowest := 1e9
	for seg in Level.GROUND:
		var a: float = seg[0]
		var b: float = seg[1]
		var top: float = seg[2]
		lowest = minf(lowest, top)
		var snowy := top >= Level.SNOW_LINE
		var x := a
		while x < b - 0.01:
			var t := place(tiles[_rng.randi() % 3], Vector3(x + 1.0, top, 0))
			if snowy:
				_snowify(t)
			x += 2.0
		var body := StaticBody3D.new()
		var shape := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = Vector3(b - a, 24.0, 4.0)
		shape.shape = box
		body.add_child(shape)
		body.position = Vector3((a + b) * 0.5, top - 12.0, 0)
		add_child(body)
		_decorate(a, b, top, snowy)
	kill_y = lowest - 13.0


func _decorate(a: float, b: float, top: float, snowy: bool) -> void:
	var length := b - a
	for i in int(length / 2.4):
		var kind := "pine_snow" if snowy else ("pine_a" if _rng.randf() < 0.6 else "pine_b")
		var s := _rng.randf_range(0.8, 1.5)
		place(kind, Vector3(_rng.randf_range(a + 0.6, b - 0.6), top - 0.05, _rng.randf_range(-6.4, -2.3)),
				Vector3(s, s * _rng.randf_range(0.9, 1.2), s), _rng.randf() * TAU)
	for i in int(length / 5.0):
		var s := _rng.randf_range(0.5, 1.2)
		place("rock_a" if _rng.randf() < 0.5 else "rock_b",
				Vector3(_rng.randf_range(a + 0.8, b - 0.8), top - 0.08, _rng.randf_range(-5.5, -1.3)),
				Vector3(s, s, s), _rng.randf() * TAU)
	for i in int(length / 8.0):
		var s := _rng.randf_range(0.18, 0.32)
		place("rock_a" if _rng.randf() < 0.5 else "rock_b",
				Vector3(_rng.randf_range(a + 0.8, b - 0.8), top - 0.04, _rng.randf_range(1.3, 1.8)),
				Vector3(s, s, s), _rng.randf() * TAU)


func _build_ledges() -> void:
	for l in Level.LEDGES:
		var w: int = l[2]
		var pos := Vector3(l[0], l[1], 0)
		var node := place("ledge_%d" % w, pos)
		if pos.y >= Level.SNOW_LINE:
			_snowify(node)
		var body := StaticBody3D.new()
		var shape := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = Vector3(w, 0.5, 2.5)
		shape.shape = box
		body.add_child(shape)
		body.position = pos + Vector3(0, -0.25, 0)
		body.set_meta("top", pos.y)
		add_child(body)
		ledges.append(body)


func _snowify(node: Node) -> void:
	## Above the snow line the grass turns white.
	if node is MeshInstance3D and node.mesh:
		for i in node.mesh.get_surface_count():
			var m: Material = node.mesh.surface_get_material(i)
			if m and m.resource_name.begins_with("grass"):
				node.set_surface_override_material(i, _snow)
	for c in node.get_children():
		_snowify(c)
