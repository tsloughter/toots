// Soft cloud puff: fades out towards the silhouette so overlapping spheres
// read as one billowing cloud. Colour and alpha come from the particle.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_back;

void fragment() {
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	// particle colours arrive as sRGB values; bring them into linear space
	vec3 tint = pow(COLOR.rgb, vec3(2.2));
	ALBEDO = tint * mix(0.6, 1.1, facing);
	ALPHA = COLOR.a * smoothstep(0.0, 0.75, facing);
}
