########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gpu
import blf
from bl_math import lerp
from math import cos, sin, radians, pi, ceil, inf
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from mathutils.geometry import intersect_point_quad_2d
from gpu_extras.batch import batch_for_shader
from gpu import state
from .addon import user_prefs
from .screen import screen_factor, pixels_per_unit_at_depth

########################•########################
"""                  DRAWING                  """
########################•########################

UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')
SMOOTH_COLOR = gpu.shader.from_builtin('SMOOTH_COLOR')

class COLORS:
    # --- FLAT --- #
    WHITE  = Vector((1.0, 1.0, 1.0, 1.0))
    BLACK  = Vector((0.0, 0.0, 0.0, 1.0))
    GREY   = Vector((0.5, 0.5, 0.5, 1.0))
    RED    = Vector((1.0, 0.0, 0.0, 1.0))
    GREEN  = Vector((0.0, 1.0, 0.0, 1.0))
    BLUE   = Vector((0.0, 0.0, 1.0, 1.0))
    CYAN   = Vector((0.0, 1.0, 1.0, 1.0))
    YELLOW = Vector((1.0, 1.0, 0.0, 1.0))
    ORANGE = Vector((1.0, 0.2, 0.0, 1.0))
    PURPLE = Vector((1.0, 0.0, 1.0, 1.0))
    # --- DARK --- #
    DARK_RED  = Vector((0.2, 0.0, 0.0, 1.0))
    DARK_GREEN  = Vector((0.0, 0.2, 0.0, 1.0))
    DARK_BLUE  = Vector((0.0, 0.0, 0.2, 1.0))
    DARK_PURPLE  = Vector((0.24335, 0.0, 0.513153, 1.0))
    # --- LIGHT --- #
    LIGHT_RED = Vector((1.0, 0.2, 0.2, 1.0))
    LIGHT_GREEN = Vector((0.2, 1.0, 0.2, 1.0))
    LIGHT_BLUE = Vector((0.4, 0.4, 1.0, 1.0))
    # --- ACTION --- #
    ACT_ONE = Vector((1.0, 0.010329, 0.904661, 1.0))
    ACT_TWO = Vector((0.010329, 1.0, 0.0185, 1.0))
    # --- GEO --- #
    VERT = Vector((0.0, 0.0, 0.2, 6/16))
    EDGE = Vector((0.4, 0.4, 1.0, 4/16))
    FACE = Vector((0.24335, 0.0, 0.513153, 3/16))


def color_from_rgb(r=0, g=0, b=0, a=255):
    return Vector((r/255, g/255, b /255, a/255))


def color_from_axis(axis='X', flip=False):
    color = COLORS.WHITE
    if axis == 'X':
        color = COLORS.DARK_RED if flip else COLORS.RED
    elif axis == 'Y':
        color = COLORS.DARK_GREEN if flip else COLORS.GREEN
    elif axis == 'Z':
        color = COLORS.DARK_BLUE if flip else COLORS.BLUE
    return color

########################•########################
"""                 GENERATORS                """
########################•########################

def gen_triangles_from_sphere(center, radius, segments=32, rings=32):
    vertices = []
    indices = []
    for i in range(rings + 1):
        lat = pi * (i / rings - 0.5)
        for j in range(segments + 1):
            lon = 2 * pi * j / segments
            x = radius * cos(lat) * cos(lon)
            y = radius * cos(lat) * sin(lon)
            z = radius * sin(lat)
            vertices.append(center + Vector((x, y, z)))
    for i in range(rings):
        for j in range(segments):
            p1 = i * (segments + 1) + j
            p2 = p1 + (segments + 1)
            indices.append((p1, p2, p1 + 1))
            indices.append((p2, p2 + 1, p1 + 1))
    triangles = [(vertices[i], vertices[j], vertices[k]) for i, j, k in indices]
    return triangles


def gen_tri_batch_from_triangles(triangles):
    vertices = [v for tri in triangles for v in tri]
    indices = [(i, i+1, i+2) for i in range(0, len(vertices), 3)]
    batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": vertices}, indices=indices)
    return batch


def gen_line_batches_for_wire_sphere(center=Vector((0,0,0)), radius=1, res=32):
    step = (pi * 2) / res
    xy_points = [Vector((cos(step * i), sin(step * i), 0)) * radius + center for i in range(res + 1)]
    xz_points = [Vector((cos(step * i), 0, sin(step * i))) * radius + center for i in range(res + 1)]
    yz_points = [Vector((0, cos(step * i), sin(step * i))) * radius + center for i in range(res + 1)]
    b1 = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": xy_points})
    b2 = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": xz_points})
    b3 = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": yz_points})
    return b1, b2, b3


def gen_points_batch(points=[]):
    return batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": points})


def gen_line_batch(lines=[]):
    return batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": lines})

########################•########################
"""                BATCH DRAW                 """
########################•########################

def draw_points_batch(batch, point_size=3, color=(0,0,0,1)):
    state.blend_set('ALPHA')
    state.point_size_set(point_size)
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)
    state.point_size_set(1)
    state.blend_set('NONE')


def draw_line_batch(batch, width=1, color=(0,0,0,1)):
    state.blend_set('ALPHA')
    state.line_width_set(width)
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')


def draw_line_batches(batches=[], width=1, color=(0,0,0,1)):
    state.blend_set('ALPHA')
    state.line_width_set(width)
    UNIFORM_COLOR.uniform_float("color", color)
    for batch in batches:
        batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')


def draw_triangle_batch(batch, color=(0,0,0,1)):
    state.blend_set('ALPHA')
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')

########################•########################
"""                 STATE SET                 """
########################•########################

def enable_depth_test(test='LESS_EQUAL'):
    state.depth_test_set(test)
    state.depth_mask_set(True)


def disable_depth_test():
    state.depth_test_set('NONE')
    state.depth_mask_set(False)


def enable_scissor(x, y, xsize, ysize):
    state.scissor_test_set(True)
    state.scissor_set(x, y, xsize, ysize)


def disable_scissor():
    state.scissor_test_set(False)

########################•########################
"""                QUICK DRAW                 """
########################•########################

def draw_tris(points=[], indices=[], color=(0,0,0,1), as_quad=True):
    '''Quad Order = TL, BL, TR, BR'''
    if as_quad: indices = [(0, 1, 2), (1, 2, 3)]
    batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": points}, indices=indices)
    state.blend_set('ALPHA')
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')


def draw_triangle(v1=Vector((0,0,0)), v2=Vector((0,0,0)), v3=Vector((0,0,0)), color=(0,0,0,1)):
    batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": [v1, v2, v3]}, indices=[(0,1,2)])
    state.blend_set('ALPHA')
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')


def draw_lines(points=[], width=1, color=(0,0,0,1), as_strip=True):
    line_type = 'LINE_STRIP' if as_strip else 'LINES'
    batch = batch_for_shader(UNIFORM_COLOR, line_type, {"pos": points})
    state.blend_set('ALPHA')
    state.line_width_set(width)
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)
    state.line_width_set(1)
    state.blend_set('NONE')


def draw_line(p1, p2, width=1, color=(0,0,0,1)):
    batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": (p1, p2)})
    state.blend_set('ALPHA')
    state.line_width_set(width)
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')
    state.line_width_set(1)


def draw_line_smooth_colors(p1, p2, width=1, color_1=(0,0,0,1), color_2=(1,1,1,1)):
    batch = batch_for_shader(SMOOTH_COLOR, 'LINES', {"pos": (p1, p2), "color": (color_1, color_2)})
    state.blend_set('ALPHA')
    state.line_width_set(width)
    batch.draw(SMOOTH_COLOR)
    state.blend_set('NONE')


def draw_line_segments_smooth_colors(points=[], width=1, colors=[]):
    batch = batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": points, "color": colors})
    state.blend_set('ALPHA')
    state.line_width_set(width)
    batch.draw(SMOOTH_COLOR)
    state.blend_set('NONE')


def draw_wire_sphere(center=Vector((0,0,0)), radius=1, res=32, width=1, color=(0,0,0,1)):
    state.blend_set('ALPHA')
    state.line_width_set(width)
    UNIFORM_COLOR.uniform_float("color", color)
    step = (pi * 2) / res
    xy_points = [Vector((cos(step * i), sin(step * i), 0)) * radius + center for i in range(res + 1)]
    xz_points = [Vector((cos(step * i), 0, sin(step * i))) * radius + center for i in range(res + 1)]
    yz_points = [Vector((0, cos(step * i), sin(step * i))) * radius + center for i in range(res + 1)]
    batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": xy_points}).draw(UNIFORM_COLOR)
    batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": xz_points}).draw(UNIFORM_COLOR)
    batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": yz_points}).draw(UNIFORM_COLOR)
    state.blend_set('NONE')


def draw_solid_sphere(center, radius, segments=16, rings=16, color=(0,0,0,1)):
    vertices = []
    indices = []
    for i in range(rings + 1):
        lat = pi * (i / rings - 0.5)
        for j in range(segments + 1):
            lon = 2 * pi * j / segments
            x = radius * cos(lat) * cos(lon)
            y = radius * cos(lat) * sin(lon)
            z = radius * sin(lat)
            vertices.append(center + Vector((x, y, z)))
    for i in range(rings):
        for j in range(segments):
            p1 = i * (segments + 1) + j
            p2 = p1 + (segments + 1)
            indices.append((p1, p2, p1 + 1))
            indices.append((p2, p2 + 1, p1 + 1))
    batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": vertices}, indices=indices)
    state.blend_set('ALPHA')
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')


def draw_points(points=[], point_size=3, color=(0,0,0,1)):
    batch = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": points})
    state.blend_set('ALPHA')
    state.point_size_set(point_size)
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')


def draw_point(point=Vector((0,0,0)), point_size=3, color=(0,0,0,1)):
    batch = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": [point]})
    state.blend_set('ALPHA')
    state.point_size_set(point_size)
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')


def draw_matrix(matrix, scale=1.0, with_bounding_box=True, width=1):
    x_p = matrix @ Vector((scale, 0.0, 0.0))
    x_n = matrix @ Vector((-scale, 0.0, 0.0))
    y_p = matrix @ Vector((0.0, scale, 0.0))
    y_n = matrix @ Vector((0.0, -scale, 0.0))
    z_p = matrix @ Vector((0.0, 0.0, scale))
    z_n = matrix @ Vector((0.0, 0.0, -scale))
    coords = [x_n, x_p, y_n, y_p, z_n, z_p]
    colors = [COLORS.DARK_RED, COLORS.LIGHT_RED, COLORS.DARK_GREEN, COLORS.LIGHT_GREEN, COLORS.DARK_BLUE, COLORS.LIGHT_BLUE]
    batch = batch_for_shader(SMOOTH_COLOR, "LINES", {"pos": coords, "color": colors})
    state.line_width_set(width)
    batch.draw(SMOOTH_COLOR)
    if with_bounding_box: draw_bounding_boxes(matrix, scale)
    state.line_width_set(1)


def draw_bounding_boxes(matrix, scale, color=COLORS.GREY):
    boundbox_points = []
    for x in (-scale, scale):
        for y in (-scale, scale):
            for z in (-scale, scale):
                boundbox_points.append(Vector((x, y, z)))
    boundbox_lines = [(0, 1), (1, 3), (3, 2), (2, 0), (0, 4), (4, 5), (5, 7), (7, 6), (6, 4), (1, 5), (2, 6), (3, 7)]
    points = []
    for v1, v2 in boundbox_lines:
        points.append(matrix @ boundbox_points[v1])
        points.append(matrix @ boundbox_points[v2])
    batch = batch_for_shader(UNIFORM_COLOR, "LINES", {"pos": points})
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)


def draw_circle_2d(radius=12, res=32, line_width=1, center=Vector((0,0)), color=(0,0,0,1)):
    step = (pi * 2) / res
    points = [ Vector((cos(step * i), sin(step * i))) * radius + center for i in range(res + 1)]
    batch = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": points})
    state.blend_set('ALPHA')
    state.line_width_set(line_width)
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')


def draw_dot_2d(radius=12, res=32, line_width=1, poly_color=(0,0,0,1), border_color=(0,0,0,1), center=Vector((0,0))):
    step = (pi * 2) / res
    points = [ Vector((cos(step * i), sin(step * i))) * radius + center for i in range(res + 1)]
    state.blend_set('ALPHA')
    indices = [(0, i, i+1) for i in range(res - 1)]
    batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": points}, indices=indices)
    UNIFORM_COLOR.uniform_float("color", poly_color)
    batch.draw(UNIFORM_COLOR)
    batch = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": points})
    UNIFORM_COLOR.uniform_float("color", border_color)
    state.line_width_set(line_width)
    batch.draw(UNIFORM_COLOR)
    state.line_width_set(1)
    state.blend_set('NONE')


def draw_rectangle_2d(width=10, height=10, center=Vector((0,0)), poly_color=(0,0,0,1), line_color=(0,0,0,1), line_width=1):
    half_w = width / 2
    half_h = height / 2
    points = [
        center + Vector((-half_w, -half_h)),
        center + Vector(( half_w, -half_h)),
        center + Vector(( half_w,  half_h)),
        center + Vector((-half_w,  half_h))]
    batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": points}, indices=[(0, 1, 2), (0, 2, 3)])
    state.blend_set('ALPHA')
    UNIFORM_COLOR.uniform_float("color", poly_color)
    batch.draw(UNIFORM_COLOR)
    points.append(center + Vector((-half_w, -half_h)))
    batch = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": points})
    state.line_width_set(line_width)
    UNIFORM_COLOR.uniform_float("color", line_color)
    batch.draw(UNIFORM_COLOR)
    state.line_width_set(1)
    state.blend_set('NONE')


def draw_circle_3d(radius=0.5, res=32, line_width=1, color=(0,0,0,1), center=Vector((0,0,0)), rot=Matrix.Identity(3)):
    step = (pi * 2) / res
    circle = [(rot @ Vector((cos(step * i), sin(step * i), 0)) * radius) + center for i in range(res + 1)]
    batch = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": circle})
    state.blend_set('ALPHA')
    state.line_width_set(line_width)
    UNIFORM_COLOR.uniform_float("color", color)
    batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')


def draw_action_line_3d(context, p1=None, p2=None):
    if not p1 and not p2:
        return
    view_rot = context.region_data.view_rotation
    res = 16
    step = (pi * 2) / 16
    r1 = 0
    r2 = 0
    state.blend_set('ALPHA')
    state.line_width_set(2)
    state.point_size_set(4)
    if isinstance(p1, Vector):
        px_pr_unit = pixels_per_unit_at_depth(context, p1)
        if px_pr_unit == 0:
            return
        r1 = 10 / px_pr_unit
        circle = [(view_rot @ Vector((cos(step * i), sin(step * i), 0)) * r1) + p1 for i in range(res)]
        cir_bat = batch_for_shader(UNIFORM_COLOR, 'LINE_LOOP', {"pos": circle})
        pnt_bat = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": [p1]})
        UNIFORM_COLOR.uniform_float("color", COLORS.ACT_ONE)
        cir_bat.draw(UNIFORM_COLOR)
        pnt_bat.draw(UNIFORM_COLOR)
    if isinstance(p2, Vector):
        px_pr_unit = pixels_per_unit_at_depth(context, p2)
        if px_pr_unit == 0:
            return
        r2 = 10 / px_pr_unit
        circle = [(view_rot @ Vector((cos(step * i), sin(step * i), 0)) * r2) + p2 for i in range(res + 1)]
        cir_bat = batch_for_shader(UNIFORM_COLOR, 'LINE_LOOP', {"pos": circle})
        pnt_bat = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": [p2]})
        UNIFORM_COLOR.uniform_float("color", COLORS.ACT_TWO)
        cir_bat.draw(UNIFORM_COLOR)
        pnt_bat.draw(UNIFORM_COLOR)
    if isinstance(p1, Vector) and isinstance(p2, Vector):
        line_nor = (p2 - p1).normalized()
        line_p1 = p1 + (line_nor * r1)
        line_p2 = p2 - (line_nor * r2)
        lin_bat = batch_for_shader(SMOOTH_COLOR, 'LINES', {"pos": (line_p1, line_p2), "color": (COLORS.ACT_ONE, COLORS.ACT_TWO)})
        lin_bat.draw(SMOOTH_COLOR)


def draw_arrow_3d(context, start, end, fill_color=(0,0,0,1), border_color=(0,0,0,1), border_width=3):
    # Location
    loc = Matrix.Translation(start)
    # Line Rotate
    view_nor = (context.region_data.view_rotation @ Vector((0,0,1))).normalized()
    view_rot = context.region_data.view_rotation
    view_inv = view_rot.inverted()
    user = (view_inv @ (end - start)).normalized().to_2d()
    if user.length == 0:
        user = Vector((0,1))
    terminator = Vector((0,1))
    angle = terminator.angle_signed(user)
    rot_z = Matrix.Rotation(-angle, 4, 'Z')
    # Rotation
    view_quat = context.region_data.view_rotation
    rot = view_quat.to_matrix().to_4x4() @ rot_z
    # Scale
    sca = Matrix.Scale((end - start).length, 4)
    mat = loc @ rot @ sca
    p0 = mat @ Vector(( 0.0000, 1.0, 0)) # Arrow Top
    p1 = mat @ Vector((-0.2500, 0.5, 0)) # Arrow Left
    p2 = mat @ Vector(( 0.2500, 0.5, 0)) # Arrow Right
    p3 = mat @ Vector((-0.0625, 0.5, 0)) # Stem Top Left
    p4 = mat @ Vector(( 0.0625, 0.5, 0)) # Stem Top Right
    p5 = mat @ Vector((-0.0625, 0.0, 0)) # Stem Bot Left
    p6 = mat @ Vector(( 0.0625, 0.0, 0)) # Stem Bot Right
    # Polygons
    points = [p0, p1, p2, p3, p4, p5, p6]
    batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": points}, indices=[(0,1,2), (3,5,6), (3, 6, 4)])
    state.blend_set('ALPHA')
    UNIFORM_COLOR.uniform_float("color", fill_color)
    batch.draw(UNIFORM_COLOR)
    # Outline
    points = [p0, p1, p3, p5, p6, p4, p2, p0]
    batch = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": points})
    state.line_width_set(border_width)
    UNIFORM_COLOR.uniform_float("color", border_color)
    batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')


def draw_label(messages=[], left_x=0, top_y=0):
    props     = user_prefs().drawing
    factor    = screen_factor()
    padding   = props.padding * factor
    font_size = props.font_size
    text_h    = max_text_height(font_size)
    descend_h = text_descender_height(font_size)
    rect_w    = padding * 3
    rect_h    = (padding * (len(messages) + 1)) + (text_h * len(messages))
    delta_width_a = 0
    delta_width_b = 0
    for entry_a, entry_b in messages:
        width_a = text_dims(entry_a, font_size)[0]
        if width_a > delta_width_a:
            delta_width_a = width_a
        width_b = text_dims(entry_b, font_size)[0]
        if width_b > delta_width_b:
            delta_width_b = width_b
    rect_w += delta_width_a + delta_width_b
    rect_bl_x = left_x
    rect_bl_y = top_y - rect_h
    bl = (rect_bl_x         , rect_bl_y)
    br = (rect_bl_x + rect_w, rect_bl_y)
    tl = (rect_bl_x         , rect_bl_y + rect_h)
    tr = (rect_bl_x + rect_w, rect_bl_y + rect_h)
    poly_batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": (tl, bl, tr, br)}, indices=[(0, 1, 2), (1, 2, 3)])
    line_batch = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": (bl, br, tr, tl, bl)})
    state.blend_set('ALPHA')
    UNIFORM_COLOR.uniform_float("color", props.background_color)
    poly_batch.draw(UNIFORM_COLOR)
    state.line_width_set(1)
    UNIFORM_COLOR.uniform_float("color", props.border_primary_color)
    line_batch.draw(UNIFORM_COLOR)
    entry_a_x = rect_bl_x + padding
    entry_b_x = rect_bl_x + (padding * 2) + delta_width_a
    delta_y   = rect_bl_y + rect_h - padding
    blf.size(0, int(props.font_size * factor))
    for entry_a, entry_b in messages:
        delta_y -= text_h
        text_y = delta_y + padding - descend_h
        blf.position(0, entry_a_x, text_y, 0)
        blf.color(0, *props.font_primary_color)
        blf.draw(0, entry_a)
        blf.position(0, entry_b_x, text_y, 0)
        blf.color(0, *props.font_secondary_color)
        blf.draw(0, entry_b)
        delta_y -= padding
    state.blend_set('NONE')
    return delta_y


def label_dims(messages=[], font_size=12):
    pad = round(user_prefs().drawing.padding * screen_factor())
    width = 0
    for entry_a, entry_b in messages:
        entry_a_w = text_dims(entry_a, font_size)[0]
        entry_b_w = text_dims(entry_b, font_size)[0]
        delta_w = pad + entry_a_w + pad + entry_b_w + pad
        if delta_w > width:
            width = delta_w
    height = round((text_dims("j`", font_size)[1] + pad) * len(messages) + pad)
    return width, height

########################•########################
"""                  FONTS                    """
########################•########################

def text_dims(text, size):
    blf.size(0, size)
    factor = screen_factor()
    w, h = blf.dimensions(0, text)
    return round(w * factor), round(h * factor)


def max_text_height(size):
    blf.size(0, size)
    return round(blf.dimensions(0, "Klgjy`")[1] * screen_factor())


def text_descender_height(size):
    blf.size(0, size)
    return round((blf.dimensions(0, "Klgjy`")[1] * screen_factor()) / 4)


def draw_text(text, x, y, size=12, color=(1,1,1,1)):
    blf.position(0, x, y, 0)
    blf.size(0, int(size * screen_factor()))
    blf.color(0, *color)
    blf.draw(0, text)


def draw_text_extra_feat(text, x, y, size=12, color=(1,1,1,1), angle=0):
    
    blf.enable(0, blf.ROTATION)
    blf.enable(0, blf.SHADOW)
    
    blf.position(0, x, y, 0)
    blf.rotation(0, angle)
    blf.shadow(0, 3, 0, 0, 0, 1)
    blf.shadow_offset(0, 2, 2)

    blf.size(0, int(size * screen_factor()))
    blf.color(0, *color)
    blf.draw(0, text)

    blf.disable(0, blf.ROTATION)
    blf.disable(0, blf.SHADOW)


def fitted_text_to_width(text="", max_w=0, left_to_right=True, overage_text="..."):
    # Not string
    if type(text) != str:
        text = str(text)
    # Font Size
    font_size = user_prefs().drawing.font_size
    # Already fits
    if text_dims(text, font_size)[0] <= max_w:
        return text
    # Overage width
    overage_w = text_dims(overage_text, font_size)[0]
    # Slice until it fits
    fitted_text = text
    for i in range(1, len(text)):
        if left_to_right:
            fitted_text = text[:len(text) - i]
        else:
            fitted_text = text[i:]
        fitted_w = text_dims(fitted_text, font_size)[0]
        if fitted_w + overage_w <= max_w:
            if left_to_right:
                return fitted_text + overage_text
            else:
                return overage_text + fitted_text
    if left_to_right:
        return fitted_text + overage_text
    return overage_text + fitted_text


def text_maps_from_entry(text="", separator="", x=0, y=0, font_size=12, color_a=(0,0,0,1), color_b=(0,0,0,1)):
    phrases = []
    temp = ''
    in_split = False
    for char in text:
        if char == separator:
            if temp:
                phrases.append(temp)
                temp = ''
            in_split = True
        elif char.isspace() and in_split:
            if temp:
                phrases.append(temp)
                temp = ''
            in_split = False
        temp += char
    if temp:
        phrases.append(temp)
    splits = []
    color = color_a
    for phrase in phrases:
        if separator in phrase:
            phrase = phrase.replace(separator, "")
            color = color_b
        else:
            color = color_a
        splits.append(TextMap(text=phrase, font_size=font_size, color=color, location=Vector((x, y))))
        x += text_dims(phrase, font_size)[0]
    return splits

########################•########################
"""                   UTILS                   """
########################•########################

def copied_color(color):
    return Vector((color[0], color[1], color[2], color[3]))

########################•########################
"""                   TYPES                   """
########################•########################

class TextMap:
    def __init__(self, text="", font_size=12, color=(1,1,1,1), location=None):
        self.text = text
        self.font_size = font_size
        self.color = color
        self.location = location if type(location) == Vector else Vector((0,0))
        # Misc
        self.user_data = {}
        self.alpha_a = 0
        self.alpha_b = 0


    def calc_dims(self):
        return text_dims(self.text, self.font_size)


    def draw(self):
        state.blend_set('ALPHA')
        draw_text(self.text, x=self.location.x, y=self.location.y, size=self.font_size, color=self.color)
        state.blend_set('NONE')


class Rect2D:
    def __init__(self, poly_color=(0,0,0,1), line_color=(0,0,0,1), line_width=1):
        self.poly_color = poly_color
        self.line_color = line_color
        self.line_width = line_width
        self.poly_batch  = None
        self.lines_batch = None
        self.bl = Vector((0,0))
        self.br = Vector((0,0))
        self.tl = Vector((0,0))
        self.tr = Vector((0,0))
        self.center = Vector((0,0))
        self.width = 0
        self.height = 0
        # Misc
        self.user_data = {}
        self.alpha_a = 0
        self.alpha_b = 0
        # Text
        self.text_maps = []


    def build(self, left_x=0, bottom_y=0, w=0, h=0, text_maps=[]):
        self.text_maps = text_maps
        self.bl = Vector((left_x    , bottom_y))
        self.br = Vector((left_x + w, bottom_y))
        self.tl = Vector((left_x    , bottom_y + h))
        self.tr = Vector((left_x + w, bottom_y + h))
        self.center = (self.bl + self.br + self.tl + self.tr) / 4
        self.width = self.br.x - self.bl.x
        self.height = self.tl.y - self.bl.y
        self.build_batches()


    def offset(self, x_offset=0, lx_limit=inf, rx_limit=inf, y_offset=0, by_limit=inf, ty_limit=inf):
        # X Offset
        self.bl.x += x_offset
        self.br.x += x_offset
        self.tl.x += x_offset
        self.tr.x += x_offset
        # Y Offset
        self.bl.y += y_offset
        self.br.y += y_offset
        self.tl.y += y_offset
        self.tr.y += y_offset
        # Text Maps
        for text_map in self.text_maps:
            text_map.location.x += x_offset
            text_map.location.y += y_offset
        # Clamps
        clamped_ty = False
        clamped_by = False
        clamped_lx = False
        clamped_rx = False
        # TY Limit
        if ty_limit != inf:
            if self.tl.y > ty_limit:
                clamped_ty = True
                delta = self.tl.y - ty_limit
                self.tl.y -= delta
                self.tr.y -= delta
                self.bl.y -= delta
                self.br.y -= delta
                # Text Maps
                for text_map in self.text_maps:
                    text_map.location.y -= delta
        # BY Limit
        if by_limit != inf:
            if self.bl.y < by_limit:
                clamped_by = True
                delta = by_limit - self.bl.y
                self.tl.y += delta
                self.tr.y += delta
                self.bl.y += delta
                self.br.y += delta
                # Text Maps
                for text_map in self.text_maps:
                    text_map.location.y += delta
        # LX Limit
        if lx_limit != inf:
            if self.tl.x < lx_limit:
                clamped_lx = True
                delta = lx_limit - self.tl.x
                self.tl.x += delta
                self.tr.x += delta
                self.bl.x += delta
                self.br.x += delta
                # Text Maps
                for text_map in self.text_maps:
                    text_map.location.x += delta
        # RX Limit
        if rx_limit != inf:
            if self.tr.x > rx_limit:
                clamped_rx = True
                delta = self.tr.x - rx_limit
                self.tl.x -= delta
                self.tr.x -= delta
                self.bl.x -= delta
                self.br.x -= delta
                # Text Maps
                for text_map in self.text_maps:
                    text_map.location.x -= delta
        # Calc
        self.center = (self.bl + self.br + self.tl + self.tr) / 4
        self.width = self.br.x - self.bl.x
        self.height = self.tl.y - self.bl.y
        # Batches
        self.build_batches()
        return clamped_ty, clamped_by, clamped_lx, clamped_rx


    def other_rect_within_bounds(self, rect2d=None):
        if type(rect2d) != Rect2D:
            return False
        return all([intersect_point_quad_2d(point, self.bl, self.br, self.tr, self.tl) for point in [rect2d.bl, rect2d.br, rect2d.tr, rect2d.tl]])


    def point_within_bounds(self, point=Vector((0,0))):
        return intersect_point_quad_2d(point, self.bl, self.br, self.tr, self.tl)


    def build_batches(self):
        self.poly_batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": (self.tl, self.bl, self.tr, self.br)}, indices=[(0, 1, 2), (1, 2, 3)])
        self.lines_batch = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": (self.bl, self.br, self.tr, self.tl, self.bl)})


    def get_corners(self):
        return self.bl, self.br, self.tl, self.tr


    def draw(self):
        state.blend_set('ALPHA')
        if self.poly_batch:
            UNIFORM_COLOR.uniform_float("color", self.poly_color)
            self.poly_batch.draw(UNIFORM_COLOR)
        if self.lines_batch:
            state.line_width_set(self.line_width)
            UNIFORM_COLOR.uniform_float("color", self.line_color)
            self.lines_batch.draw(UNIFORM_COLOR)
        state.line_width_set(1)
        state.blend_set('NONE')

        for text_map in self.text_maps:
            text_map.draw()


class Label2D:
    def __init__(self):
        self.bounds = Rect2D()
        self.messages = []

    @staticmethod
    def padded_bottom_right_screen_position(context):
        screen_padding = round(user_prefs().drawing.screen_padding * screen_factor())
        return Vector((context.area.width - screen_padding, screen_padding))

    @staticmethod
    def padded_bottom_center_screen_position(context):
        screen_padding = user_prefs().drawing.screen_padding * screen_factor()
        return Vector((round(context.area.width / 2), screen_padding))

    @staticmethod
    def label_dimensions_from_msgs(messages=[]):
        # Build Data
        prefs = user_prefs().drawing
        font_size = prefs.font_size
        pad = round(prefs.padding * screen_factor())
        text_h = max_text_height(font_size)
        descend_h = text_descender_height(font_size)
        # Widths & Heights
        label_w = 0
        label_h = 0
        column_one_w = 0
        column_two_w = 0
        for entry in messages[:]:
            # Sanitize
            if not isinstance(entry, tuple) or len(entry) == 0:
                messages.remove(entry)
                continue
            # Label Height
            label_h += text_h
            # Column One
            if len(entry) == 1:
                delta_w = text_dims(entry[0].replace("$", ""), font_size)[0]
                if delta_w > column_one_w:
                    column_one_w = delta_w
            # Column One & Column Two
            elif len(entry) == 2:
                delta_w = text_dims(entry[0].replace("$", ""), font_size)[0]
                if delta_w > column_one_w:
                    column_one_w = delta_w
                delta_w = text_dims(entry[1].replace("$", ""), font_size)[0]
                if delta_w > column_two_w:
                    column_two_w = delta_w
        # Label Width
        if column_one_w > 0 and column_two_w > 0:
            label_w = column_one_w + column_two_w + pad * 3
        elif column_one_w > 0 and column_two_w == 0:
            label_w = column_one_w + pad * 2
        elif column_one_w == 0 and column_two_w > 0:
            label_w = column_two_w + pad * 2
        # Label Height        
        label_h += pad * (len(messages) + 1)
        # Completed
        return label_w, label_h, column_one_w, column_two_w

    @staticmethod
    def label_pos(pos_x, pos_y, label_w, label_h, pos='BOTTOM_LEFT'):
        if pos == 'BOTTOM_LEFT':
            return pos_x, pos_y
        elif pos == 'BOTTOM_CENTER':
            return round(pos_x - (label_w / 2)), pos_y
        elif pos == 'BOTTOM_RIGHT':
            return pos_x - label_w, pos_y
        elif pos == 'TOP_LEFT':
            return pos_x, pos_y - label_h
        elif pos == 'TOP_RIGHT':
            return pos_x - label_w, pos_y - label_h
        elif pos == 'CENTER':
            return pos_x - round(label_w / 2), pos_y - round(label_h / 2)
        return 0, 0

    @staticmethod
    def text_pos(label_lx, label_by, label_w, label_h, text_w, orientation='CENTER'):
        # Build Data
        prefs = user_prefs().drawing
        font_size = prefs.font_size
        pad = round(prefs.padding * screen_factor())
        text_h = max_text_height(font_size)
        descend_h = text_descender_height(font_size)
        # Locate Text
        text_x = 0
        text_y = label_by + label_h - (pad + (text_h - descend_h))
        if orientation == 'LEFT':
            text_x = label_lx + pad
        elif orientation == 'CENTER':
            text_x = label_lx + round((label_w - text_w) / 2)
        elif orientation == 'RIGHT':
            text_x = label_lx + label_w - (pad + text_w)
        return text_x, text_y


    def build_from_msgs(self, pos_x=0, pos_y=0, messages=[], pos='BOTTOM_LEFT', special="$"):
        # Build Data
        prefs = user_prefs().drawing
        font_size = prefs.font_size
        pad = round(prefs.padding * screen_factor())
        text_h = max_text_height(font_size)
        descend_h = text_descender_height(font_size)
        # Overall Dimensions
        label_w, label_h, column_one_w, column_two_w = Label2D.label_dimensions_from_msgs(messages)
        # Label Position
        label_lx, label_by = Label2D.label_pos(pos_x, pos_y, label_w, label_h, pos)
        # Text Maps
        text_maps = []
        # Text Positions
        column_one_x = label_lx + pad
        column_two_x = label_lx + pad + column_one_w + pad if column_one_w > 0 else label_lx + pad
        text_y = label_by + label_h
        # Colors
        font_primary_color = copied_color(prefs.font_primary_color)
        font_secondary_color = copied_color(prefs.font_secondary_color)
        font_tertiary_color = copied_color(prefs.font_tertiary_color)
        background_color = copied_color(prefs.background_color)
        border_primary_color = copied_color(prefs.border_primary_color)
        # Top Down
        for entry in messages:
            # Text Offset
            text_y -= pad + (text_h - descend_h)
            # Columns
            if len(entry) == 1:
                text_maps.extend(text_maps_from_entry(text=entry[0], separator=special, x=column_one_x, y=text_y, font_size=font_size, color_a=font_primary_color, color_b=font_tertiary_color))
            elif len(entry) == 2:
                text_maps.extend(text_maps_from_entry(text=entry[0], separator=special, x=column_one_x, y=text_y, font_size=font_size, color_a=font_primary_color, color_b=font_tertiary_color))
                text_maps.extend(text_maps_from_entry(text=entry[1], separator=special, x=column_two_x, y=text_y, font_size=font_size, color_a=font_secondary_color, color_b=font_tertiary_color))
            # Finish Offset
            text_y -= descend_h
        # Bounds
        self.bounds.poly_color = background_color
        self.bounds.line_color = border_primary_color
        self.bounds.build(left_x=label_lx, bottom_y=label_by, w=label_w, h=label_h, text_maps=text_maps)
        # Keep Ref
        self.messages = messages


    def build_from_single(self, pos_x=0, pos_y=0, preferred_width=0, message="", orientation='CENTER', pos='BOTTOM_LEFT', special="$"):
        # Build Data
        prefs = user_prefs().drawing
        font_size = prefs.font_size
        pad = round(prefs.padding * screen_factor())
        text_h = max_text_height(font_size)
        descend_h = text_descender_height(font_size)
        # Widths & Heights
        text_w = text_dims(message, font_size)[0]
        label_w = preferred_width if (preferred_width > 0) else (text_w + pad * 2)
        label_h = text_h + pad * 2
        # Label Position
        label_lx, label_by = Label2D.label_pos(pos_x, pos_y, label_w, label_h, pos)
        # Colors
        font_primary_color = copied_color(prefs.font_primary_color)
        font_tertiary_color = copied_color(prefs.font_tertiary_color)
        background_color = copied_color(prefs.background_color)
        border_primary_color = copied_color(prefs.border_primary_color)
        # Text Position
        text_x, text_y = Label2D.text_pos(label_lx, label_by, label_w, label_h, text_w, orientation)
        text_maps = text_maps_from_entry(text=message, separator=special, x=text_x, y=text_y, font_size=font_size, color_a=font_primary_color, color_b=font_tertiary_color)
        # Bounds
        self.bounds.poly_color = background_color
        self.bounds.line_color = border_primary_color
        self.bounds.build(left_x=label_lx, bottom_y=label_by, w=label_w, h=label_h, text_maps=text_maps)
        # Keep Ref
        self.messages = [message]
    

    def add_text_maps(self, text_maps=[]):
        self.bounds.text_maps.extend([text_map for text_map in text_maps if isinstance(text_map, TextMap)])


    def mouse_within_label(self, event):
        return self.bounds.point_within_bounds(point=Vector((event.mouse_region_x, event.mouse_region_y)))


    def store_transparency(self):
        # Poly
        self.bounds.poly_color = copied_color(self.bounds.poly_color)
        self.bounds.alpha_a = self.bounds.poly_color[3]
        # Line
        self.bounds.line_color = copied_color(self.bounds.line_color)
        self.bounds.alpha_b = self.bounds.line_color[3]
        # Text Maps
        for text_map in self.bounds.text_maps:
            text_map.color = copied_color(text_map.color)
            text_map.alpha_a = text_map.color[3]


    def restore_transparency(self):
        # Poly
        color = self.bounds.poly_color
        self.bounds.poly_color = (color[0], color[1], color[2], self.bounds.alpha_a)
        # Line
        color = self.bounds.line_color
        self.bounds.line_color = (color[0], color[1], color[2], self.bounds.alpha_b)
        # Text Maps
        for text_map in self.bounds.text_maps:
            color = text_map.color
            text_map.color = (color[0], color[1], color[2], text_map.alpha_a)


    def lerp_transparency(self, factor=1.0):
        # Poly
        color = self.bounds.poly_color
        alpha = lerp(self.bounds.alpha_a, 0, factor)
        self.bounds.poly_color = (color[0], color[1], color[2], alpha)
        # Line
        color = self.bounds.line_color
        alpha = lerp(self.bounds.alpha_b, 0, factor)
        self.bounds.line_color = (color[0], color[1], color[2], alpha)
        # Text Maps
        for text_map in self.bounds.text_maps:
            color = text_map.color
            alpha = lerp(text_map.alpha_a, 0, factor)
            text_map.color = (color[0], color[1], color[2], alpha)


    def draw(self):
        self.bounds.draw()


class Graphics:
    def __init__(self):
        self.setup()


    def setup(self):
        # 2D
        self.point_batches_2D = []
        self.line_batches_2D = []
        self.poly_batches_2D = []
        # 3D
        self.point_batches_3D = []
        self.line_batches_3D = []
        self.poly_batches_3D = []


    def clear(self, opt='ALL'):
        if opt == 'ALL':
            self.setup()
        elif opt == '2D':
            self.point_batches_2D = []
            self.line_batches_2D = []
            self.poly_batches_2D = []
        elif opt == '3D':
            self.point_batches_3D = []
            self.line_batches_3D = []
            self.poly_batches_3D = []


    def gen_point_batch(self, space='2D', clear=True, points=[], color=(1,1,1,1), size=1):
        if not points: return
        if space == '2D':
            if clear: self.point_batches_2D.clear()
            batch = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": points})
            if not isinstance(batch, gpu.types.GPUBatch): return
            self.point_batches_2D.append((batch, color, size))
        elif space == '3D':
            if clear: self.point_batches_3D.clear()
            batch = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": points})
            if not isinstance(batch, gpu.types.GPUBatch): return
            self.point_batches_3D.append((batch, color, size))


    def gen_line_batch(self, space='2D', clear=True, points=[], color=(1,1,1,1), width=1, line='LINES'):
        if not points: return
        if space == '2D':
            if clear: self.line_batches_2D.clear()
            batch = batch_for_shader(UNIFORM_COLOR, line, {"pos": points})
            if not isinstance(batch, gpu.types.GPUBatch): return
            self.line_batches_2D.append((batch, color, width))
        elif space == '3D':
            if clear: self.line_batches_3D.clear()
            batch = batch_for_shader(UNIFORM_COLOR, line, {"pos": points})
            if not isinstance(batch, gpu.types.GPUBatch): return
            self.line_batches_3D.append((batch, color, width))


    def gen_poly_batch(self, space='2D', clear=True, triangles=[], color=(1,1,1,1)):
        if not triangles: return
        if space == '2D':
            if clear: self.poly_batches_2D.clear()
            vertices = [v for tri in triangles for v in tri]
            indices = [(i, i+1, i+2) for i in range(0, len(vertices), 3)]
            batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": vertices}, indices=indices)
            if not isinstance(batch, gpu.types.GPUBatch): return
            self.poly_batches_2D.append((batch, color))
        elif space == '3D':
            if clear: self.point_batches_3D.clear()
            vertices = [v for tri in triangles for v in tri]
            indices = [(i, i+1, i+2) for i in range(0, len(vertices), 3)]
            batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": vertices}, indices=indices)
            if not isinstance(batch, gpu.types.GPUBatch): return
            self.poly_batches_3D.append((batch, color))


    def draw_2D(self):
        if not self.point_batches_2D and not self.line_batches_2D and not self.poly_batches_2D: return
        state.blend_set('ALPHA')
        for batch, color in self.poly_batches_2D:
            UNIFORM_COLOR.uniform_float("color", color)
            batch.draw(UNIFORM_COLOR)
        for batch, color, width in self.line_batches_2D:
            state.line_width_set(width)
            UNIFORM_COLOR.uniform_float("color", color)
            batch.draw(UNIFORM_COLOR)
        for batch, color, size in self.point_batches_2D:
            state.point_size_set(size)
            UNIFORM_COLOR.uniform_float("color", color)
            batch.draw(UNIFORM_COLOR)
        state.line_width_set(1)
        state.point_size_set(1)
        state.blend_set('NONE')


    def draw_3D(self):
        if not self.point_batches_3D and not self.line_batches_3D and not self.poly_batches_3D: return
        state.blend_set('ALPHA')
        for batch, color in self.poly_batches_3D:
            UNIFORM_COLOR.uniform_float("color", color)
            batch.draw(UNIFORM_COLOR)
        for batch, color, width in self.line_batches_3D:
            state.line_width_set(width)
            UNIFORM_COLOR.uniform_float("color", color)
            batch.draw(UNIFORM_COLOR)
        for batch, color, size in self.point_batches_3D:
            state.point_size_set(size)
            UNIFORM_COLOR.uniform_float("color", color)
            batch.draw(UNIFORM_COLOR)
        state.line_width_set(1)
        state.point_size_set(1)
        state.blend_set('NONE')

