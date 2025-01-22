from mathutils import Vector, Matrix
from gpu_extras.batch import batch_for_shader
import gpu

UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')
SMOOTH_COLOR = gpu.shader.from_builtin('SMOOTH_COLOR')

coords = [
	Vector((-0.04584378004074097, -0.04584331065416336, 6.618840142635918e-09)),
	Vector((0.04584331065416336, -0.04584378004074097, 6.618840142635918e-09)),
	Vector((-0.04584331065416336, 0.04584378004074097, 6.618840142635918e-09)),
	Vector((0.04584378004074097, 0.04584331065416336, 6.618840142635918e-09)),
	Vector((-0.04584331065416336, -0.04584378004074097, 0.6532690525054932)),
	Vector((0.04584378004074097, -0.04584331065416336, 0.6532690525054932)),
	Vector((-0.04584378004074097, 0.04584331065416336, 0.6532690525054932)),
	Vector((0.04584331065416336, 0.04584378004074097, 0.6532690525054932)),
	Vector((-0.11727374792098999, -0.11727374792098999, 0.6532690525054932)),
	Vector((0.11727374792098999, -0.11727374792098999, 0.6532690525054932)),
	Vector((-0.11727374792098999, 0.11727374792098999, 0.6532690525054932)),
	Vector((0.11727374792098999, 0.11727374792098999, 0.6532690525054932)),
	Vector((0.0, 0.0, 1.0)),
]

indices = [
	(10, 11, 7),
	(10, 7, 6),
	(11, 9, 5),
	(11, 5, 7),
	(3, 7, 5),
	(3, 5, 1),
	(0, 4, 6),
	(0, 6, 2),
	(2, 6, 7),
	(2, 7, 3),
	(9, 11, 12),
	(2, 3, 1),
	(2, 1, 0),
	(10, 8, 12),
	(11, 10, 12),
	(8, 9, 12),
	(8, 4, 5),
	(8, 5, 9),
	(8, 10, 6),
	(8, 6, 4),
	(1, 5, 4),
	(1, 4, 0),
]

colors = [
	(0.9999688267707825, 0.9999720454216003, 0.9999718070030212, 1.0),
	(0.9999688267707825, 0.9999720454216003, 0.9999718070030212, 1.0),
	(0.9999685883522034, 0.9999719262123108, 0.9999718070030212, 1.0),
	(0.9999688267707825, 0.9999720454216003, 0.9999718070030212, 1.0),
	(0.008243944495916367, 0.008244005031883717, 0.008244005031883717, 1.0),
	(3.9073136544852394e-13, 3.907342114792267e-13, 3.907341843741724e-13, 1.0),
	(2.5758811261766823e-07, 2.575899600287812e-07, 2.575898747636529e-07, 1.0),
	(2.970738618209706e-13, 2.9707589470004403e-13, 2.9707589470004403e-13, 1.0),
	(1.4616641408338182e-07, 1.461675225300496e-07, 1.4616745147577603e-07, 1.0),
	(2.4042890345299384e-06, 2.404307224423974e-06, 2.404306314929272e-06, 1.0),
	(2.3172526653070236e-07, 2.3172682972472103e-07, 2.317268013030116e-07, 1.0),
	(8.92861353349872e-05, 8.928676834329963e-05, 8.928674651542678e-05, 1.0),
	(1.1118159818579443e-05, 0.9999721646308899, 7.520439339714358e-06, 1.0),
]

def gen_poly_batch_flat(center=Vector((0,0,0)), scale=Vector((1,1,1)), direction=Vector((0,0,1))):
	global coords, indices
	mat_loc = Matrix.Translation(center.to_4d())
	mat_sca = Matrix.Diagonal(scale.to_4d())
	mat_rot = direction.to_track_quat('Z', 'Y').to_matrix().to_4x4()
	mat_out = mat_loc @ mat_rot @ mat_sca
	return batch_for_shader(gpu.shader.from_builtin('UNIFORM_COLOR'), 'TRIS', {"pos": [mat_out @ coord for coord in coords]}, indices=indices)

def draw_poly_batch_flat(batch=None, color_front=(0,0,0,1), color_back=(0,0,0,1)):
	if not isinstance(batch, gpu.types.GPUBatch): return
	gpu.state.face_culling_set('FRONT')
	gpu.state.depth_test_set('GREATER')
	gpu.state.depth_mask_set(True)
	gpu.state.blend_set('ALPHA')
	UNIFORM_COLOR.uniform_float("color", color_back)
	batch.draw(UNIFORM_COLOR)
	gpu.state.face_culling_set('BACK')
	gpu.state.depth_test_set('LESS_EQUAL')
	UNIFORM_COLOR.uniform_float("color", color_front)
	batch.draw(UNIFORM_COLOR)
	gpu.state.face_culling_set('NONE')
	gpu.state.depth_test_set('NONE')
	gpu.state.depth_mask_set(False)
	gpu.state.blend_set('NONE')

def gen_poly_batch_smooth(center=Vector((0,0,0)), scale=Vector((1,1,1)), direction=Vector((0,0,1))):
	global coords, indices, colors
	mat_loc = Matrix.Translation(center.to_4d())
	mat_sca = Matrix.Diagonal(scale.to_4d())
	mat_rot = direction.to_track_quat('Z', 'Y').to_matrix().to_4x4()
	mat_out = mat_loc @ mat_rot @ mat_sca
	batch = batch_for_shader(SMOOTH_COLOR, 'TRIS', {'pos': [mat_out @ coord for coord in coords], 'color':colors}, indices=indices)
	if isinstance(batch, gpu.types.GPUBatch): return batch
	return None

def draw_poly_batch_smooth(batch=None):
	if not isinstance(batch, gpu.types.GPUBatch): return
	gpu.state.blend_set('ALPHA')
	gpu.state.depth_mask_set(True)
	gpu.state.face_culling_set('BACK')
	batch.draw(SMOOTH_COLOR)
	gpu.state.face_culling_set('NONE')
	gpu.state.depth_mask_set(False)
	gpu.state.blend_set('NONE')

