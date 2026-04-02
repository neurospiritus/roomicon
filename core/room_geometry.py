"""Room geometry: walls, floor, ceiling, baseboards."""

import bpy
import math

# Wall layout:
#   Front (Y=0)      — long wall (width), camera side
#   Back  (Y=length) — long wall (width), opposite camera
#   Left  (X=0)      — short wall (length)
#   Right (X=width)  — short wall (length)

WALL_DEFS = [
    ("Wall_Front", True,
     lambda w, l: (0, 0, 0),
     lambda w, l: (0, 0, 0)),
    ("Wall_Back", True,
     lambda w, l: (w, l, 0),
     lambda w, l: (0, 0, math.pi)),
    ("Wall_Left", False,
     lambda w, l: (0, 0, 0),
     lambda w, l: (0, 0, math.pi / 2)),
    ("Wall_Right", False,
     lambda w, l: (w, l, 0),
     lambda w, l: (0, 0, -math.pi / 2)),
]


def get_wall_interior(width, length, wt):
    """Return parameters of wall interior surfaces.

    For each wall:
        origin  — point on interior surface (wall start)
        along   — unit vector along wall (local +X)
        inward  — unit vector into room (local +Y)
        rot_hanging — Z rotation for wall-mounted objects (face +Y into room)
        rot_standing — Z rotation for floor furniture (back to wall, face +Y into room)
        wall_len — wall length

    Front/back: Solidify grows inward, inner surface = wall origin (no wt offset).
    Left/right: join with front/back, inner surface offset by wt.
    """
    return {
        'front': {
            'origin': (0, 0),
            'along': (1, 0),
            'inward': (0, 1),
            'rot_hanging': 0,
            'rot_standing': 0,
            'wall_len': width,
        },
        'back': {
            'origin': (width, length),
            'along': (-1, 0),
            'inward': (0, -1),
            'rot_hanging': math.pi,
            'rot_standing': math.pi,
            'wall_len': width,
        },
        'left': {
            'origin': (wt, length),
            'along': (0, -1),
            'inward': (1, 0),
            'rot_hanging': -math.pi / 2,
            'rot_standing': -math.pi / 2,
            'wall_len': length,
        },
        'right': {
            'origin': (width - wt, 0),
            'along': (0, 1),
            'inward': (-1, 0),
            'rot_hanging': math.pi / 2,
            'rot_standing': math.pi / 2,
            'wall_len': length,
        },
    }


# Inner space boundaries (for bounds checks)
def get_inner_bounds(width, length, wt):
    """Return (x_min, x_max, y_min, y_max) of inner space."""
    return wt, width - wt, 0, length


BASEBOARD_HEIGHT = 0.06
BASEBOARD_DEPTH = 0.01


def create_mesh_object(name, verts, faces):
    """Create a mesh object from vertices and faces."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return bpy.data.objects.new(name, mesh)


def create_wall_with_openings(name, width, height, thickness, openings=None):
    """
    Wall as a flat mesh (thickness via Solidify) with rectangular openings.
    Wall along X (0 to width), up Z (0 to height), Y=0.
    """
    if openings is None:
        openings = []

    verts, faces = _build_wall_geometry(width, height, openings)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)

    mod = obj.modifiers.new("Solidify", 'SOLIDIFY')
    mod.thickness = thickness
    mod.offset = 1.0

    return obj


def _build_wall_geometry(width, height, openings):
    """Build a flat wall (XZ, Y=0) with rectangular holes."""
    if not openings:
        verts = [(0, 0, 0), (width, 0, 0), (width, 0, height), (0, 0, height)]
        faces = [(0, 1, 2, 3)]
        return verts, faces

    xs = sorted(set([0, width] + [max(0, o['x'] - o['w']/2) for o in openings]
                     + [min(width, o['x'] + o['w']/2) for o in openings]))
    zs = sorted(set([0, height] + [max(0, o['z'] - o['h']/2) for o in openings]
                     + [min(height, o['z'] + o['h']/2) for o in openings]))

    verts = []
    vert_idx = {}
    for iz, z in enumerate(zs):
        for ix, x in enumerate(xs):
            vert_idx[(ix, iz)] = len(verts)
            verts.append((x, 0, z))

    faces = []
    for iz in range(len(zs) - 1):
        for ix in range(len(xs) - 1):
            cell_cx = (xs[ix] + xs[ix + 1]) / 2
            cell_cz = (zs[iz] + zs[iz + 1]) / 2

            is_opening = False
            for o in openings:
                ox_min = max(0, o['x'] - o['w'] / 2)
                ox_max = min(width, o['x'] + o['w'] / 2)
                oz_min = max(0, o['z'] - o['h'] / 2)
                oz_max = min(height, o['z'] + o['h'] / 2)
                if ox_min <= cell_cx <= ox_max and oz_min <= cell_cz <= oz_max:
                    is_opening = True
                    break

            if not is_opening:
                v0 = vert_idx[(ix, iz)]
                v1 = vert_idx[(ix + 1, iz)]
                v2 = vert_idx[(ix + 1, iz + 1)]
                v3 = vert_idx[(ix, iz + 1)]
                faces.append((v0, v1, v2, v3))

    return verts, faces


def make_window_openings(wall_width, window_count, window_width, window_height, sill_height):
    """Create a list of window openings evenly distributed along the wall."""
    openings = []
    if window_count <= 0:
        return openings
    spacing = wall_width / (window_count + 1)
    for i in range(window_count):
        cx = spacing * (i + 1)
        cz = sill_height + window_height / 2
        openings.append({'x': cx, 'z': cz, 'w': window_width, 'h': window_height})
    return openings


def make_door_opening(wall_width, door_width, door_height):
    """Create a door opening centered on the wall."""
    return {'x': wall_width / 2, 'z': door_height / 2, 'w': door_width, 'h': door_height}


def create_floor(width, length):
    return create_mesh_object("Floor", [
        (0, 0, 0), (width, 0, 0), (width, length, 0), (0, length, 0)
    ], [(0, 1, 2, 3)])


def create_ceiling(width, length, height):
    return create_mesh_object("Ceiling", [
        (0, 0, height), (width, 0, height), (width, length, height), (0, length, height)
    ], [(3, 2, 1, 0)])


def create_baseboards(width, length, wt, wall_configs=None, door_width=0.9):
    """Create baseboards around the room perimeter, with cutout for door opening."""
    import bmesh

    bm = bmesh.new()
    bh = BASEBOARD_HEIGHT
    bd = BASEBOARD_DEPTH

    def add_box(cx, cy, cz, sx, sy, sz):
        if sx < 0.001 or sy < 0.001 or sz < 0.001:
            return
        verts = []
        for dx in (-sx, sx):
            for dy in (-sy, sy):
                for dz in (-sz, sz):
                    verts.append(bm.verts.new((cx + dx, cy + dy, cz + dz)))
        faces = [
            (0, 1, 3, 2), (4, 6, 7, 5),
            (0, 4, 5, 1), (2, 3, 7, 6),
            (0, 2, 6, 4), (1, 5, 7, 3),
        ]
        for f in faces:
            bm.faces.new([verts[i] for i in f])

    door_side = None
    if wall_configs:
        for side, wtype, _ in wall_configs:
            if wtype == 'DOOR':
                door_side = side
                break

    x0, x1 = wt, width - wt
    gap = door_width / 2 + 0.01

    def add_segments(axis_min, axis_max, door_center, perp_pos, is_x_axis):
        if door_center is not None:
            seg1_max = door_center - gap
            seg2_min = door_center + gap
            segments = []
            if seg1_max > axis_min + 0.01:
                segments.append((axis_min, seg1_max))
            if axis_max > seg2_min + 0.01:
                segments.append((seg2_min, axis_max))
        else:
            segments = [(axis_min, axis_max)]

        for s_min, s_max in segments:
            cx = (s_min + s_max) / 2
            hw = (s_max - s_min) / 2
            if is_x_axis:
                add_box(cx, perp_pos, bh / 2, hw, bd / 2, bh / 2)
            else:
                add_box(perp_pos, cx, bh / 2, bd / 2, hw, bh / 2)

    # Front / Back
    door_cx = width / 2 if door_side == 'front' else None
    add_segments(x0, x1, door_cx, bd / 2, is_x_axis=True)
    door_cx = width / 2 if door_side == 'back' else None
    add_segments(x0, x1, door_cx, length - bd / 2, is_x_axis=True)

    # Left / Right
    door_cy = length / 2 if door_side == 'left' else None
    add_segments(0, length, door_cy, wt + bd / 2, is_x_axis=False)
    door_cy = length / 2 if door_side == 'right' else None
    add_segments(0, length, door_cy, width - wt - bd / 2, is_x_axis=False)

    mesh = bpy.data.meshes.new("Baseboard")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return bpy.data.objects.new("Baseboard", mesh)
