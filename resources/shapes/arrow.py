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
	(0.23728635907173157, 0.33217570185661316, 0.8181432485580444, 1.0),
	(0.23728621006011963, 0.33217543363571167, 0.8181424736976624, 1.0),
	(0.23728638887405396, 0.33217570185661316, 0.8181431889533997, 1.0),
	(0.23727098107337952, 0.33215194940567017, 0.818090558052063, 1.0),
	(0.07138421386480331, 1.952982557895666e-07, 0.21021178364753723, 1.0),
	(0.07138421386480331, 1.952982557895666e-07, 0.21021178364753723, 1.0),
	(0.07138421386480331, 1.952982557895666e-07, 0.21021178364753723, 1.0),
	(0.07138419896364212, 1.9529827000042133e-07, 0.21021181344985962, 1.0),
	(0.0, 0.0, 0.0, 1.0),
	(1.5406859787958638e-08, 1.5406859787958638e-08, 1.5406859787958638e-08, 1.0),
	(1.3822043510764467e-15, 1.3822043510764467e-15, 1.3822043510764467e-15, 1.0),
	(3.032701715710573e-05, 3.032701715710573e-05, 3.032701715710573e-05, 1.0),
	(0.9997994303703308, 0.14370232820510864, 0.1827777624130249, 1.0),
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

