"""Post-generation placement: cushions, books, plush toys, curtains."""

import bpy
import math
import os
import sys
import random

from core.procedural import import_generator
from core.asset_loader import wrap_as_asset, load_random_decor, link_group_to_collection
from core.room_geometry import get_wall_interior, make_window_openings


def place_cushions_on_beds(col, props):
    """Generates cushions and plush toys on beds."""
    cushion_rng = random.Random(props.seed + 555)

    beds = []
    for obj in col.objects:
        if obj.parent is not None:
            continue
        mz = obj.get('mattress_z')
        if mz is not None:
            beds.append(obj)

    if not beds:
        return

    procedural = props.procedural
    gen_fn = None
    toy_fn = None
    if procedural:
        (gen_fn,) = import_generator('cushions', 'cushion_types', 'generate_cushion')

    for bed in beds:
        mattress_z = bed['mattress_z']

        # Bed dimensions from child meshes
        bed_hw, bed_hd = 0.4, 0.9
        bed_objs = bed.children if bed.children else [bed]
        for child in bed_objs:
            if child.data and 'Mattress' in child.name:
                bed_hw = child.dimensions.x / 2
                bed_hd = child.dimensions.y / 2
                break

        rot = bed.rotation_euler.z

        # Cushion
        seed = props.seed + hash(bed.name) + 13
        if procedural:
            objects = gen_fn(seed=seed)
            cobj = wrap_as_asset(objects, f"Cushion_{bed.name}") if objects else None
        else:
            cobj = load_random_decor('bed', name=f"Cushion_{bed.name}", seed=seed)
        if cobj:
            along = cushion_rng.uniform(-bed_hw * 0.2, bed_hw * 0.2)
            depth = -bed_hd * cushion_rng.uniform(0.5, 0.8)
            dx = along * math.cos(rot) - depth * math.sin(rot)
            dy = along * math.sin(rot) + depth * math.cos(rot)
            cobj.location = (bed.location.x + dx, bed.location.y + dy, mattress_z + 0.01)
            cobj.rotation_euler = (0, 0, rot + cushion_rng.uniform(-0.4, 0.4))
            link_group_to_collection(cobj, col)

        # Plush toy (40% chance)
        if cushion_rng.random() < 0.4:
            toy_seed = props.seed + hash(bed.name) + 77
            tobj = None
            if procedural:
                if toy_fn is None:
                    (toy_fn,) = import_generator('plushtoys', 'plushtoy_types', 'generate_plushtoy')
                toy_subtype = cushion_rng.choice(['bear', 'bunny', 'penguin', 'duck'])
                toy_objects = toy_fn(seed=toy_seed, subtype=toy_subtype)
                tobj = wrap_as_asset(toy_objects, f"PlushToy_{bed.name}") if toy_objects else None
            else:
                tobj = load_random_decor('bed', name=f"PlushToy_{bed.name}", seed=toy_seed)
            if tobj:
                t_along = cushion_rng.uniform(-bed_hw * 0.3, bed_hw * 0.3)
                t_depth = -bed_hd * cushion_rng.uniform(0.0, 0.3)
                t_dx = t_along * math.cos(rot) - t_depth * math.sin(rot)
                t_dy = t_along * math.sin(rot) + t_depth * math.cos(rot)
                tobj.location = (bed.location.x + t_dx, bed.location.y + t_dy, mattress_z + 0.01)
                tobj.rotation_euler = (0, 0, rot + math.pi + cushion_rng.uniform(-0.6, 0.6))
                link_group_to_collection(tobj, col)


def place_books_on_shelves(col, props):
    """Generates books on shelves using shelf_surfaces."""
    book_rng = random.Random(props.seed + 333)

    shelves = []
    for obj in col.objects:
        surfaces = obj.get('shelf_surfaces')
        if surfaces is not None and obj.parent is None:
            shelves.append(obj)

    if not shelves:
        return

    (gen_fn,) = import_generator('booksets', 'bookset_types', 'generate_bookset')

    for shelf in shelves:
        surfaces = shelf['shelf_surfaces']
        rot = shelf.rotation_euler.z

        for si, surface in enumerate(surfaces):
            if book_rng.random() > 0.7:
                continue

            surf_z = surface[0]
            surf_w = surface[1]
            max_h = surface[2]
            surf_depth = surface[3] if len(surface) > 3 else 0.18

            inward_x = math.cos(rot + math.pi / 2)
            inward_y = math.sin(rot + math.pi / 2)
            along_x = math.cos(rot)
            along_y = math.sin(rot)
            depth_offset = surf_depth * 0.5

            if surf_w > 0.5:
                n_groups = book_rng.randint(2, 3)
            else:
                n_groups = 1

            for gi in range(n_groups):
                if n_groups == 1:
                    side = book_rng.choice([-1, 1])
                    shift = side * surf_w * book_rng.uniform(0.1, 0.3)
                    group_w = surf_w * 0.7
                else:
                    slot = surf_w / n_groups
                    center = -surf_w / 2 + slot * (gi + 0.5)
                    shift = center + book_rng.uniform(-slot * 0.1, slot * 0.1)
                    group_w = slot * 0.85

                subtype = book_rng.choice(['row', 'leaning'])
                seed = props.seed + hash(shelf.name) + si * 17 + gi * 31
                objects = gen_fn(seed=seed, subtype=subtype,
                                  max_height=max_h, max_width=group_w)
                if not objects:
                    continue

                bobj = wrap_as_asset(objects, f"Books_{shelf.name}_{si}_{gi}")
                bobj.location = (
                    shelf.location.x + inward_x * depth_offset + along_x * shift,
                    shelf.location.y + inward_y * depth_offset + along_y * shift,
                    shelf.location.z + surf_z,
                )
                bobj.rotation_euler = (0, 0, rot + math.pi)
                link_group_to_collection(bobj, col)


def place_curtains(col, rng, wall_configs, width, length, height, wt, props):
    """Generates curtains on all windows."""

    _addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    _generators_dir = os.path.join(_addon_dir, "tools", "generators")
    _curtains_dir = os.path.join(_generators_dir, "curtains")

    if _generators_dir not in sys.path:
        sys.path.insert(0, _generators_dir)
    if _curtains_dir in sys.path:
        sys.path.remove(_curtains_dir)
    sys.path.insert(0, _curtains_dir)
    for _m in ('helpers', 'curtain_types'):
        sys.modules.pop(_m, None)
    from curtains.curtain_types import generate_curtain, CURTAIN_TYPES
    from helpers import mat_curtain, mat_sheer, mat_rod

    curtain_type = rng.choice(list(CURTAIN_TYPES.keys()))
    curtain_seed = rng.randint(0, 999999)

    fabric = mat_sheer() if curtain_type == 'sheer' else mat_curtain(rng)
    rod_material = mat_rod(rng)

    window_top_z = props.window_sill_height + props.window_height
    offset = wt * 0.5
    walls = get_wall_interior(width, length, wt)

    def _link_to_col(obj):
        for c in obj.users_collection:
            c.objects.unlink(obj)
        col.objects.link(obj)

    sides = ['front', 'back', 'left', 'right']

    for (side, wtype, win_count), side_name in zip(wall_configs, sides):
        if wtype != 'WINDOWS' or win_count <= 0:
            continue

        wi = walls[side_name]
        wall_len = wi['wall_len']

        anchor = bpy.data.objects.new(f"CurtainAnchor_{side_name}", None)
        anchor.location = (wi['origin'][0], wi['origin'][1], 0)
        anchor.rotation_euler = (0, 0, wi['rot_hanging'])
        anchor.empty_display_size = 0.01
        anchor.hide_viewport = True
        _link_to_col(anchor)

        openings = make_window_openings(
            wall_len, win_count,
            props.window_width, props.window_height, props.window_sill_height)

        for j, op in enumerate(openings):
            left_edge = openings[j - 1]['x'] + openings[j - 1]['w'] / 2 if j > 0 else 0
            right_edge = openings[j + 1]['x'] - openings[j + 1]['w'] / 2 if j < len(openings) - 1 else wall_len
            max_half = min(op['x'] - left_edge, right_edge - op['x'])

            curtain_w = min(props.window_width * rng.uniform(1.03, 1.08), max_half * 2 * 0.95)

            objs = generate_curtain(curtain_seed + j, subtype=curtain_type,
                                     window_width=curtain_w,
                                     window_top_z=window_top_z,
                                     fabric=fabric, rod_material=rod_material)

            for obj in objs:
                ox, oy, oz = obj.location.x, obj.location.y, obj.location.z
                _link_to_col(obj)
                obj.parent = anchor
                obj.matrix_parent_inverse.identity()
                obj.location = (op['x'] + ox, offset + oy, oz)
