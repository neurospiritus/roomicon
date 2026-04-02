"""Window frames, door frame with panel, door assembly."""

import bpy
import bmesh
import math

from core.material_loader import load_material
from materials.furniture_materials import (
    create_doorframe_material, create_door_material, create_metal_material,
)


def _new_bm():
    return bmesh.new()


def _bm_to_object(bm, name):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return bpy.data.objects.new(name, mesh)


def _add_box(bm, cx, cy, cz, sx, sy, sz):
    """Box in bmesh. (cx,cy,cz) = center, (sx,sy,sz) = half-extents."""
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


# ============================================================
# Window frame
# ============================================================

FRAME_DEPTH = 0.05
FRAME_WIDTH = 0.04
MULLION_WIDTH = 0.03


def create_window_frame(name, opening, wall_thickness, divisions=2, crossbar_pos=0.7, wide_sill=False):
    """
    Window frame in an opening.
    divisions: number of sections (1 = no vertical bars, 2 = one, 3 = two)
    crossbar_pos: relative height of horizontal bar (0.0 = none, 0.7 = 70% height)
    """
    bm = _new_bm()

    ox, oz = opening['x'], opening['z']
    ow, oh = opening['w'], opening['h']
    hw, hh = ow / 2, oh / 2
    fw = FRAME_WIDTH / 2
    fd = FRAME_DEPTH / 2
    fy = -wall_thickness / 2

    # Frame perimeter
    z_top = oz + hh
    z_bot = oz - hh
    # Top
    _add_box(bm, ox, fy, z_top - fw, hw, fd, fw)
    # Bottom (sill)
    if wide_sill:
        sill_depth = fd + 0.08
        _add_box(bm, ox, fy + 0.04, z_bot + fw, hw + 0.03, sill_depth, fw * 1.2)
    else:
        _add_box(bm, ox, fy + 0.01, z_bot + fw, hw + 0.02, fd + 0.01, fw)
    # Left
    _add_box(bm, ox - hw + fw, fy, oz, fw, fd, hh - fw)
    # Right
    _add_box(bm, ox + hw - fw, fy, oz, fw, fd, hh - fw)

    mw = MULLION_WIDTH / 2
    inner_hh = hh - fw  # inner half-height (excluding frame)

    # Horizontal crossbar
    if crossbar_pos > 0.01:
        crossbar_z = z_bot + FRAME_WIDTH + (oh - FRAME_WIDTH * 2) * crossbar_pos
        _add_box(bm, ox, fy, crossbar_z, hw - fw, fd * 0.8, mw)

    # Vertical mullions (divisions - 1 pieces)
    if divisions >= 2:
        inner_w = ow - FRAME_WIDTH * 2  # inner width
        for i in range(1, divisions):
            vx = ox - hw + fw + inner_w * i / divisions
            _add_box(bm, vx, fy, oz, mw, fd * 0.8, inner_hh)

    return _bm_to_object(bm, name)


# ============================================================
# Door frame (separate object)
# ============================================================

DOORFRAME_WIDTH = 0.06
DOORFRAME_OVERHANG = 0.02  # frame overhang into the room


def create_door_frame(name, opening, wall_thickness):
    """Door frame — 3 bars (no threshold)."""
    bm = _new_bm()

    ox, oz = opening['x'], opening['z']
    ow, oh = opening['w'], opening['h']
    hw, hh = ow / 2, oh / 2
    dfw = DOORFRAME_WIDTH / 2
    # Frame depth: full wall thickness + overhang
    depth = wall_thickness + DOORFRAME_OVERHANG
    half_depth = depth / 2
    # Y center: offset so overhang faces inward (-Y)
    fy = -(wall_thickness + DOORFRAME_OVERHANG) / 2

    # Top
    _add_box(bm, ox, fy, oz + hh - dfw, hw + dfw, half_depth, dfw)
    # Left
    _add_box(bm, ox - hw - dfw, fy, oz - dfw, dfw, half_depth, hh + dfw)
    # Right
    _add_box(bm, ox + hw + dfw, fy, oz - dfw, dfw, half_depth, hh + dfw)

    return _bm_to_object(bm, name)


# ============================================================
# Door panel with handle (separate object, origin at hinges)
# ============================================================

DOOR_THICK = 0.04
HANDLE_RADIUS = 0.01
HANDLE_LENGTH = 0.12


def create_door_panel(name, opening, wall_thickness):
    """
    Door panel + handle. Origin at left edge (hinges),
    so rotating around Z opens the door.
    Geometry is built relative to origin on the hinge side.
    """
    bm = _new_bm()

    ow, oh = opening['w'], opening['h']
    gap = 0.01
    panel_w = ow - gap * 2
    panel_h = oh - gap
    dt = DOOR_THICK / 2
    fy = -wall_thickness / 2  # wall thickness center

    # Panel: origin at left (X=0), door extends right (+X)
    # Y = fy, Z from 0 to panel_h
    _add_box(bm, panel_w / 2, fy, panel_h / 2,
             panel_w / 2, dt, panel_h / 2)

    # Handle — on inner side (-Y = into room, Solidify offset=1.0)
    handle_x = panel_w * 0.85
    handle_z = panel_h * 0.48
    handle_y = fy - dt - 0.005  # protrudes from inner side of door

    # Rosette
    _add_box(bm, handle_x, handle_y, handle_z, 0.015, 0.005, 0.015)
    # Lever (horizontal in -X)
    _add_box(bm, handle_x - HANDLE_LENGTH / 2, handle_y - HANDLE_RADIUS,
             handle_z, HANDLE_LENGTH / 2, HANDLE_RADIUS, HANDLE_RADIUS)

    obj = _bm_to_object(bm, name)

    # Origin is already at (0,0,0) — this is the hinge point.
    # Object position will be set by the caller:
    # X = opening['x'] - ow/2 + gap (left edge of opening)
    # Z = 0 (from floor)
    return obj


def create_door_assembly(col, opening, origin, rot, wall_thickness, link_fn=None):
    """Create door frame + panel with handle and add to collection."""
    if link_fn is None:
        def link_fn(obj):
            for c in obj.users_collection:
                c.objects.unlink(obj)
            col.objects.link(obj)

    dframe = create_door_frame("DoorFrame", opening, wall_thickness)
    dframe.location = origin
    dframe.rotation_euler = rot
    dframe.data.materials.append(create_doorframe_material())
    link_fn(dframe)

    panel = create_door_panel("DoorPanel", opening, wall_thickness)
    gap = 0.01
    local_x = opening['x'] - opening['w'] / 2 + gap
    rx, ry, rz = rot
    cos_r = math.cos(rz)
    sin_r = math.sin(rz)
    wx = origin[0] + local_x * cos_r
    wy = origin[1] + local_x * sin_r
    panel.location = (wx, wy, 0)
    panel.rotation_euler = rot
    door_mat = load_material('doors') or create_door_material()
    panel.data.materials.append(door_mat)
    panel.data.materials.append(create_metal_material())
    link_fn(panel)
