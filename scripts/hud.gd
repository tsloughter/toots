extends Control
## Hearts, huckleberry counter and the all-important gas gauge.

var hearts := 3
var max_hearts := 3
var berries := 0
var berries_total := 0
var gas := 1.0
var farting := false

var _time := 0.0
var _bar_bg := StyleBoxFlat.new()
var _bar_fill := StyleBoxFlat.new()


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	_bar_bg.bg_color = Color(0.05, 0.07, 0.1, 0.6)
	_bar_bg.set_corner_radius_all(13)
	_bar_bg.set_border_width_all(3)
	_bar_bg.border_color = Color(1, 1, 1, 0.9)
	_bar_fill.set_corner_radius_all(9)


func _process(delta: float) -> void:
	_time += delta
	queue_redraw()


func _draw() -> void:
	var font := ThemeDB.fallback_font
	for i in max_hearts:
		_heart(Vector2(46 + i * 50, 48), 19.0, i < hearts)

	# huckleberries
	var c := Vector2(44, 104)
	draw_circle(c, 15, Color("241452"))
	draw_circle(c, 12.5, Color("5b3bc0"))
	draw_circle(c + Vector2(-4, -5), 3.5, Color("cfc4ff"))
	var text := "%d / %d" % [berries, berries_total]
	draw_string_outline(font, Vector2(70, 114), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 28, 8, Color(0.05, 0.07, 0.1, 0.8))
	draw_string(font, Vector2(70, 114), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 28, Color.WHITE)

	# gas gauge with a little stink cloud
	var origin := Vector2(30, 140)
	var cloud := Color("c8d64c")
	for puff in [[Vector2(10, 16), 9.0], [Vector2(22, 10), 11.0], [Vector2(34, 17), 9.0], [Vector2(22, 20), 9.0]]:
		draw_circle(origin + puff[0], puff[1] + 2.5, Color(0.05, 0.07, 0.1, 0.75))
	for puff in [[Vector2(10, 16), 9.0], [Vector2(22, 10), 11.0], [Vector2(34, 17), 9.0], [Vector2(22, 20), 9.0]]:
		draw_circle(origin + puff[0], puff[1], cloud)
	var bar := Rect2(origin + Vector2(54, 2), Vector2(210, 27))
	draw_style_box(_bar_bg, bar)
	var empty := gas <= 0.06
	if gas > 0.01:
		var col := Color("b9d13c").lerp(Color("e9a23b"), clampf(1.0 - gas * 1.6, 0.0, 1.0))
		if farting:
			col = col.lightened(0.25 + 0.2 * sin(_time * 30.0))
		_bar_fill.bg_color = col
		var inner := bar.grow(-5)
		inner.size.x = maxf(inner.size.y, inner.size.x * gas)
		draw_style_box(_bar_fill, inner)
	if empty and fmod(_time, 0.4) < 0.2:
		draw_string(font, bar.position + Vector2(62, 21), "EMPTY", HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color("ff6b5a"))


func _heart(c: Vector2, r: float, full: bool) -> void:
	_heart_shape(c, r + 3.5, Color(0.05, 0.07, 0.1, 1.0) if full else Color(0.05, 0.07, 0.1, 0.55))
	if full:
		_heart_shape(c, r, Color("e8413c"))
		draw_circle(c + Vector2(-r * 0.55, -r * 0.45), r * 0.17, Color(1, 1, 1, 0.8))
	else:
		_heart_shape(c, r, Color("4b3b46"))


func _heart_shape(c: Vector2, r: float, col: Color) -> void:
	draw_circle(c + Vector2(-r * 0.5, -r * 0.28), r * 0.56, col)
	draw_circle(c + Vector2(r * 0.5, -r * 0.28), r * 0.56, col)
	draw_colored_polygon(PackedVector2Array([
		c + Vector2(-r * 1.0, -r * 0.02), c + Vector2(0, -r * 0.3),
		c + Vector2(r * 1.0, -r * 0.02), c + Vector2(0, r * 1.05)]), col)
