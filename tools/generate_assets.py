"""
Generate .blend assets using procedural generators from tools/generators/.

Usage:
    blender --background --python tools/generate_assets.py
    blender --background --python tools/generate_assets.py -- --count 10
    blender --background --python tools/generate_assets.py -- --type table --count 20

Generates .blend files in assets/furniture/ and assets/decor/<category>/.
Each file contains one object group with seed in the filename.
"""

import bpy
import os
import sys

script_dir = os.path.dirname(os.path.realpath(__file__))
project_dir = os.path.dirname(script_dir)
generators_dir = os.path.join(script_dir, "generators")

if project_dir not in sys.path:
    sys.path.insert(0, project_dir)
if generators_dir not in sys.path:
    sys.path.insert(0, generators_dir)

ASSETS_DIR = os.path.join(project_dir, "assets")

# (type_name, subdir, module, func, subtypes, output_subpath)
# output_subpath: 'furniture' or 'decor/<category>'
ASSET_DEFS = [
    # Furniture → assets/furniture/
    ('table',    'tables',    'table_types',    'generate_table',    ['dining', 'coffee', 'round', 'radial', 'tea'], 'furniture'),
    ('desk',     'tables',    'table_types',    'generate_table',    ['desk'], 'furniture'),
    ('chair',    'chairs',    'chair_types',    'generate_chair',    ['dining', 'normal', 'stool'], 'furniture'),
    ('armchair', 'chairs',    'chair_types',    'generate_chair',    ['armchair'], 'furniture'),
    ('bed',      'seating',   'seating_types',  'generate_seating',  ['single_bed', 'panel_bed', 'double_bed'], 'furniture'),
    ('sofa',     'seating',   'seating_types',  'generate_seating',  ['sofa', 'daybed'], 'furniture'),
    ('wardrobe',   'wardrobes', 'wardrobe_types', 'generate_wardrobe', ['single', 'double', 'with_drawers'], 'furniture'),
    ('nightstand', 'wardrobes', 'wardrobe_types', 'generate_wardrobe', ['nightstand'], 'furniture'),
    ('dresser',    'wardrobes', 'wardrobe_types', 'generate_wardrobe', ['dresser'], 'furniture'),
    # Decor tabletop → assets/decor/tabletop/
    ('candle',      'candles',     'candle_types',  'generate_candle',       ['single', 'candlestick', 'tealight'], 'decor/tabletop'),
    ('kitchenware', 'kitchenware', 'kitchenware',   'generate_kitchenware',  [None], 'decor/tabletop'),
    ('plant',       'plants',      'plant_types',   'generate_plant',        ['succulent', 'cactus', 'fern', 'ficus'], 'decor/tabletop'),
    ('photoframe_tabletop', 'photoframes', 'photoframes', 'generate_photoframe_proc', ['tabletop_simple', 'tabletop_bevel'], 'decor/tabletop'),
    ('bookset',     'booksets',    'bookset_types', 'generate_bookset',      ['single', 'row', 'stack'], 'decor/tabletop'),
    ('cushion',     'cushions',    'cushion_types', 'generate_cushion',      ['square', 'rectangle', 'round', 'bolster'], 'decor/bed'),
    ('plushtoy',    'plushtoys',   'plushtoy_types', 'generate_plushtoy',     ['bear', 'bunny', 'penguin', 'duck'], 'decor/bed'),
    # Decor wall → assets/decor/wall/
    ('shelf',       'shelves',     'shelf_types',   'generate_shelf',        ['single', 'multi', 'bracket', 'box'], 'decor/wall'),
    ('painting',    'paintings',   'paintings',     'generate_painting_proc', ['simple', 'bevel'], 'decor/wall'),
    ('mirror',      'mirrors',     'mirror_types',  'generate_mirror',       ['rectangle', 'round', 'oval', 'arched'], 'decor/wall'),
    ('clock_wall',  'clocks',      'clock_types',   'generate_clock',        ['round', 'square'], 'decor/wall'),
    ('photoframe_wall', 'photoframes', 'photoframes', 'generate_photoframe_proc', ['wall_simple', 'wall_bevel'], 'decor/wall'),
    ('lamp_wall',   'lamps',       'lamps',         'generate_lamp_wall',    ['sconce'], 'decor/wall'),
    # Decor floor → assets/decor/floor/
    ('lamp_floor',  'lamps',       'lamps',         'generate_lamp_floor',   ['floor_lamp', 'arc_lamp'], 'decor/floor'),
    # Decor wall_floor → assets/decor/wall_floor/
    ('clock_floor', 'clocks',      'clock_types',   'generate_clock',        ['grandfather'], 'decor/wall_floor'),
    # Decor ceiling → assets/decor/ceiling/
    ('lamp_ceiling', 'lamps',      'lamps',         'generate_lamp_ceiling', ['pendant', 'flush'], 'decor/ceiling'),
    # Rugs, cushions, curtains
    ('rug',         'rugs',        'rugs',          'generate_rug_proc',     ['rectangle', 'circle', 'oval'], 'decor/floor'),
    # Tabletop decor
    ('clock_tabletop', 'clocks',   'clock_types',   'generate_clock',        ['alarm'], 'decor/tabletop'),
    ('lamp_tabletop',  'lamps',    'lamps',         'generate_lamp_tabletop', ['classic', 'nightlight'], 'decor/tabletop'),
]


def _import_gen(subdir, module_name, func_name):
    """Import generator function from tools/generators/."""
    gen_dir = os.path.join(generators_dir, subdir)
    if gen_dir in sys.path:
        sys.path.remove(gen_dir)
    sys.path.insert(0, gen_dir)
    for m in ('helpers', module_name):
        sys.modules.pop(m, None)
    mod = __import__(module_name)
    return getattr(mod, func_name)


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)


def save_asset(objects, name, filepath):
    """Wrap objects as asset with Empty root, link to scene, save as .blend."""
    # Добавляем корень проекта для импорта core.asset_loader
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)
    from core.asset_loader import wrap_as_asset

    root = wrap_as_asset(objects, name)
    if root is None:
        return

    # Линкуем root и все children в сцену
    if root.name not in [o.name for o in bpy.context.collection.objects]:
        bpy.context.collection.objects.link(root)
    for child in root.children_recursive:
        if child.name not in [o.name for o in bpy.context.collection.objects]:
            bpy.context.collection.objects.link(child)

    bpy.ops.wm.save_as_mainfile(filepath=filepath, copy=True)


def generate_all(count=5, only_type=None):
    total = 0

    for type_name, subdir, module, func, subtypes, output_subpath in ASSET_DEFS:
        if only_type and type_name != only_type:
            continue

        out_dir = os.path.join(ASSETS_DIR, output_subpath)
        os.makedirs(out_dir, exist_ok=True)

        gen_fn = _import_gen(subdir, module, func)

        for i in range(count):
            clear_scene()
            seed = i * 137 + hash(type_name) % 10000

            subtype = subtypes[i % len(subtypes)]
            kwargs = {'seed': seed}
            if subtype is not None:
                kwargs['subtype'] = subtype

            try:
                objects = gen_fn(**kwargs)
            except Exception as e:
                print(f"  ERROR: {type_name} seed={seed}: {e}")
                continue

            if not objects:
                continue

            sub_label = f"_{subtype}" if subtype else ""
            asset_name = f"{type_name}{sub_label}_{seed:05d}"
            filename = f"{asset_name}.blend"
            filepath = os.path.join(out_dir, filename)

            save_asset(objects, asset_name, filepath)
            total += 1
            print(f"  {output_subpath}/{filename}")

    return total


def parse_args():
    import argparse
    argv = sys.argv
    if '--' in argv:
        argv = argv[argv.index('--') + 1:]
    else:
        argv = []

    types = sorted(set(d[0] for d in ASSET_DEFS))
    parser = argparse.ArgumentParser(
        description="Generate .blend assets from procedural generators")
    parser.add_argument('--count', type=int, default=5,
                        help='Variants per type (default: 5)')
    parser.add_argument('--type', type=str, default=None, choices=types,
                        help='Generate only this type')
    args = parser.parse_args(argv)
    return args.count, args.type


def main():
    count, only_type = parse_args()

    print("=" * 50)
    print(f"Generating assets: {count} per type" +
          (f", type={only_type}" if only_type else ""))
    print("=" * 50)

    total = generate_all(count, only_type)

    print(f"\nDone! Generated {total} assets.")
    types = sorted(set(d[0] for d in ASSET_DEFS))
    print(f"Available types: {', '.join(types)}")


if __name__ == "__main__":
    main()
