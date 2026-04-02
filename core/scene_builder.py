"""Scene assembly: object generation and placement according to placements."""

import bpy
import math
import random

from core.procedural import import_generator, PROCEDURAL_FURNITURE, PROCEDURAL_DECOR
from core.placement import place_furniture, place_decor
from core.asset_loader import (
    wrap_as_asset, link_group_to_collection,
    load_furniture, load_random_decor,
)


def _generate_procedural(props, ptype, category, index, chosen_subtypes):
    """Calls a procedural generator. Returns (objects, name) or (None, None)."""
    proc_def = PROCEDURAL_FURNITURE.get(ptype) if category == 'furniture' else PROCEDURAL_DECOR.get(ptype)
    if not proc_def:
        return None, None

    item_seed = props.seed + index * 7
    subdir, module, func_name, subtype = proc_def
    (gen_fn,) = import_generator(subdir, module, func_name)

    if subtype and isinstance(subtype, tuple):
        if ptype not in chosen_subtypes:
            chosen_subtypes[ptype] = random.Random(props.seed + hash(ptype)).choice(subtype)
        subtype = chosen_subtypes[ptype]
        kwargs = {'seed': props.seed + hash(ptype)}
    elif subtype and isinstance(subtype, list):
        subtype = random.Random(item_seed).choice(subtype)
        kwargs = {'seed': item_seed}
    else:
        kwargs = {'seed': item_seed}
    if subtype:
        kwargs['subtype'] = subtype

    objects = gen_fn(**kwargs)
    name = f"{ptype.capitalize()}_{index:02d}"
    return objects, name


def generate_object(props, ptype, category, index, chosen_subtypes, placement=None):
    """Generates or loads an asset. Returns root object or None.

    In both modes returns an object with _asset_root=True and metadata.
    """
    item_seed = props.seed + index * 7

    if props.procedural:
        objects, name = _generate_procedural(props, ptype, category, index, chosen_subtypes)
        if not objects:
            return None
        return wrap_as_asset(objects, name)
    else:
        name = f"{ptype.capitalize()}_{index:02d}"
        if category == 'furniture':
            return load_furniture(ptype, name=name, seed=item_seed)
        else:
            asset_cat = (placement or {}).get('asset_category', 'tabletop')
            return load_random_decor(asset_cat, name=name, seed=item_seed)


def place_objects(col, props, width, length, height, wall_thickness, wall_configs):
    """Places furniture and decor in two phases."""

    # ==================== Phase 1: furniture ====================
    furniture_placements = place_furniture(
        width, length, height, wall_thickness,
        props.density, props.seed,
        wall_configs, props.door_width, props.door_height,
        props.window_width, props.window_height, props.window_sill_height,
        room_size=props.room_size)

    chosen_subtypes = {}
    real_tables = []

    for i, p in enumerate(furniture_placements):
        ptype = p['type']
        root = generate_object(props, ptype, 'furniture', i, chosen_subtypes, p)
        if root is None:
            continue

        root.location = (p['x'], p['y'], p.get('z', 0))
        root.rotation_euler = (0, 0, p['rotation'])
        link_group_to_collection(root, col)

        # Table metadata — read from root (same for both modes)
        if ptype in ('table', 'desk') and root.get('surface_z') is not None:
            ts = root.get('table_size', (1.2, 0.7))
            real_tables.append({
                'x': p['x'], 'y': p['y'], 'rotation': p['rotation'],
                'surface_z': root['surface_z'],
                'width': ts[0], 'depth': ts[1],
            })

    # ==================== Phase 2: decor ====================
    decor_placements = place_decor(
        width, length, height, wall_thickness,
        props.density, props.seed,
        wall_configs, props.door_width, props.window_width,
        room_size=props.room_size,
        tables=real_tables,
        furniture_placed=furniture_placements)

    for i, p in enumerate(decor_placements):
        ptype = p['type']
        di = len(furniture_placements) + i
        root = generate_object(props, ptype, 'decor', di, chosen_subtypes, p)
        if root is None:
            continue

        root.location = (p['x'], p['y'], p.get('z', 0))
        root.rotation_euler = (0, 0, p['rotation'])

        if p.get('rug_scale') and hasattr(root, 'dimensions') and root.dimensions.x > 0:
            max_dim = max(root.dimensions.x, root.dimensions.y)
            s = p['rug_scale'] / max_dim if max_dim > 0 else 1.0
            root.scale = (s, s, 1.0)

        link_group_to_collection(root, col)
