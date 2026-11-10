extends Node
## Autoload: one-shot sound effects, the music loop, and a couple of flags
## that need to survive a scene reload.

const NAMES := ["jump", "stomp", "berry", "beans", "hurt", "land", "checkpoint", "lose", "win",
		"toot", "fart_a", "fart_b", "fart_c", "fart_win"]

var streams := {}
var skip_title := false
var _voices: Array[AudioStreamPlayer] = []
var _next := 0
var _music: AudioStreamPlayer
var _quitting := false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	get_tree().auto_accept_quit = false     # we quit ourselves, see quit_cleanly()
	for n in NAMES:
		var path := "res://audio/%s.wav" % n
		if ResourceLoader.exists(path):
			streams[n] = load(path)
	for i in 8:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_voices.append(p)
	_music = AudioStreamPlayer.new()
	_music.volume_db = -15.0
	add_child(_music)
	if ResourceLoader.exists("res://audio/music.wav"):
		var m: AudioStreamWAV = load("res://audio/music.wav")
		m.loop_mode = AudioStreamWAV.LOOP_FORWARD
		m.loop_begin = 0
		m.loop_end = int(m.get_length() * m.mix_rate)
		_music.stream = m


func play(sound: String, volume_db := 0.0, pitch := 1.0) -> void:
	if _quitting or not streams.has(sound):
		return
	var p := _voices[_next]
	_next = (_next + 1) % _voices.size()
	p.stream = streams[sound]
	p.volume_db = volume_db
	p.pitch_scale = pitch
	p.play()


func start_music() -> void:
	if _music.stream and not _music.playing:
		_music.play()


func toggle_music() -> void:
	if _music.playing:
		_music.stop()
	else:
		start_music()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		quit_cleanly()


func quit_cleanly() -> void:
	## Stop every sound, give the audio thread a moment to let go of the
	## streams, then quit. Quitting mid-note makes Godot report leaked
	## resources on the way out.
	if _quitting:
		return
	_quitting = true
	# Freeze the game first, or it can start a new sound (a landing, a pickup,
	# another fart) while we wait and the leak is back. This node keeps running.
	get_tree().paused = true
	_music.stop()
	for v in _voices:
		v.stop()
	for n in get_tree().get_nodes_in_group("game_audio"):
		n.stop()
	await get_tree().create_timer(0.25).timeout
	get_tree().quit()
