extends RefCounted
## Level layout. Everything lives on the z=0 plane; x is distance along the
## trail, y is altitude. Edit the tables below to reshape the climb.
##
## Rule of thumb for Toots: a plain jump clears ~5 units across or ~2.2 up.
## Anything bigger needs a fart.

## Solid ground: [x_start, x_end, top_y]. Widths should be multiples of 2.
const GROUND := [
	[-16, 24, 0.0],      # meadow
	[28, 52, 0.0],
	[52, 64, 1.5],
	[64, 82, 6.0],       # first cliff: needs a fart
	[92, 122, 6.0],
	[152, 178, 8.0],     # after the ledge chasm
	[178, 188, 9.5],
	[188, 198, 11.0],
	[208, 238, 11.0],
	[238, 252, 16.0],    # snow line
	[266, 286, 18.0],
	[286, 312, 19.8],    # summit
]

## Floating ledges (jump up through them): [x_center, top_y, width 2|3|4]
const LEDGES := [
	[9, 1.9, 3], [15, 3.6, 2],
	[36, 2.0, 3], [43, 3.7, 3],
	[126, 6.8, 3], [132.5, 8.2, 2], [139, 7.2, 3], [145.5, 8.6, 3],
	[170, 10.0, 3],
	[233.5, 13.4, 3],
	[259, 16.5, 2],
	[276, 20.2, 3],
]

## [kind, x, y, patrol_min, patrol_max]  (eagles: y is flight altitude)
const ENEMIES := [
	["beaver", 19, 0.0, 13, 23],
	["beaver", 34, 0.0, 30, 40],
	["beaver", 47, 0.0, 43, 51],
	["beaver", 74, 6.0, 69, 81],
	["ram", 106, 6.0, 98, 112],
	["porcupine", 118, 6.0, 114, 121],
	["eagle", 138, 10.4, 128, 149],
	["porcupine", 159, 8.0, 156, 163],
	["beaver", 170, 8.0, 165, 177],
	["beaver", 193, 11.0, 189, 197],
	["eagle", 203, 13.6, 197, 209],
	["ram", 218, 11.0, 212, 224],
	["porcupine", 229, 11.0, 226, 231],
	["beaver", 245, 16.0, 240, 251],
	["eagle", 259, 19.6, 252, 266],
	["ram", 276, 18.0, 271, 285],      # starts clear of the checkpoint at 268
]

## Cans of beans: instant full tank, even in mid-air.
const BEANS := [
	Vector2(58, 3.0), Vector2(87, 9.2), Vector2(136, 10.2), Vector2(203, 14.5),
	Vector2(235, 15.6), Vector2(255.5, 18.6),
]

const CHECKPOINTS := [Vector2(94, 6.0), Vector2(154, 8.0), Vector2(210, 11.0), Vector2(268, 18.0)]
const START := Vector2(0, 0.0)
const GOAL := Vector2(302, 19.8)
const SNOW_LINE := 15.0

## [x_from, x_to, text]
const HINTS := [
	[-20, 7, "Run with A / D or the arrow keys.  Jump with SPACE."],
	[11, 23, "Bop critters on the head. Don't bump into them!"],
	[52, 64, "Too tall to jump!  Press and HOLD jump again in mid-air to FART-FLY."],
	[72, 82, "Fart across the gap. Your gas refills when you land."],
	[110, 121, "Porcupines are far too spiky to stomp. Fly over!"],
	[226, 238, "Beans = instant refill."],
]


static func berries() -> Array:
	var out: Array = []
	_row(out, 3, 7, 1.0)
	_row(out, 8, 10, 2.9, 1.0)
	_row(out, 14.5, 15.5, 4.6, 1.0)
	_arc(out, 24, 28, 1.2, 2.2, 4)
	_row(out, 35, 37, 3.0, 1.0)
	_row(out, 42, 44, 4.7, 1.0)
	_row(out, 54, 57, 2.5)
	_col(out, 62.6, 3.5, 8.5, 4)
	_row(out, 66, 70, 7.0)
	_arc(out, 82, 92, 8.0, 3.2, 7)
	_row(out, 95, 99, 7.0)
	_row(out, 125, 127, 7.8, 1.0)
	_row(out, 132, 133, 9.2, 1.0)
	_row(out, 138, 140, 8.2, 1.0)
	_row(out, 144.5, 146.5, 9.6, 1.0)
	_row(out, 169, 171, 11.0, 1.0)
	_row(out, 180, 186, 10.5, 2.0)
	_arc(out, 198, 208, 12.6, 3.0, 7)
	_row(out, 214, 222, 12.0, 2.0)
	_row(out, 232.5, 234.5, 14.4, 1.0)
	_col(out, 236.8, 13.0, 18.0, 4)
	_arc(out, 252, 266, 18.4, 2.6, 8)
	_row(out, 275, 277, 21.2, 1.0)
	_row(out, 290, 298, 20.8, 2.0)
	return out


static func _row(out: Array, x0: float, x1: float, y: float, step := 1.5) -> void:
	var x := x0
	while x <= x1 + 0.001:
		out.append(Vector2(x, y))
		x += step


static func _col(out: Array, x: float, y0: float, y1: float, count: int) -> void:
	for i in count:
		out.append(Vector2(x, lerpf(y0, y1, i / float(count - 1))))


static func _arc(out: Array, x0: float, x1: float, y: float, height: float, count: int) -> void:
	for i in count:
		var t := (i + 0.5) / count
		out.append(Vector2(lerpf(x0, x1, t), y + height * 4.0 * t * (1.0 - t)))
