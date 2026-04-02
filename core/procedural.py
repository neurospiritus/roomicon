"""Procedural generator mapping and import from tools/generators/."""

import os
import sys

_addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
_generators_dir = os.path.join(_addon_dir, "tools", "generators")


def import_generator(subdir, module_name, *names):
    """Import from tools/generators/<subdir>/<module_name> with cache cleanup.

    If module_name == subdir, imports as package (from __init__.py).
    Otherwise, imports as a module inside subdir/.
    """
    gen_dir = os.path.join(_generators_dir, subdir)

    if _generators_dir not in sys.path:
        sys.path.insert(0, _generators_dir)

    if gen_dir in sys.path:
        sys.path.remove(gen_dir)
    sys.path.insert(0, gen_dir)

    for m in ('helpers', module_name):
        sys.modules.pop(m, None)
    mod = __import__(module_name)
    return tuple(getattr(mod, n) for n in names)


# Furniture type mapping -> (subdir, module, func, subtype)
# tuple = uniform subtype (same for all instances)
PROCEDURAL_FURNITURE = {
    'bed':      ('seating',   'seating_types',   'generate_seating',  ('single_bed', 'panel_bed', 'double_bed')),
    'sofa':     ('seating',   'seating_types',   'generate_seating',  ('sofa', 'daybed')),
    'table':    ('tables',    'table_types',     'generate_table',    ('dining', 'coffee', 'round', 'radial', 'tea')),
    'desk':     ('tables',    'table_types',     'generate_table',    ('desk',)),
    'armchair': ('chairs',    'chair_types',     'generate_chair',    ('armchair',)),
    'chair':    ('chairs',    'chair_types',     'generate_chair',    ('dining', 'normal', 'stool')),
    'wardrobe':   ('wardrobes', 'wardrobe_types',  'generate_wardrobe', ('single', 'double', 'with_drawers')),
    'nightstand': ('wardrobes', 'wardrobe_types',  'generate_wardrobe', ('nightstand',)),
    'dresser':    ('wardrobes', 'wardrobe_types',  'generate_wardrobe', ('dresser',)),
}

# Decor type mapping -> (subdir, module, func, subtype)
# list = varied subtype (random for each instance)
PROCEDURAL_DECOR = {
    'rug':         ('rugs',     'rugs',          'generate_rug_proc', None),
    'book_single': ('booksets', 'bookset_types', 'generate_bookset', 'single'),
    'book_stack':  ('booksets', 'bookset_types', 'generate_bookset', 'stack'),
    'candle':      ('candles',      'candle_types',  'generate_candle',      ['single', 'candlestick', 'tealight']),
    'kitchenware': ('kitchenware', 'kitchenware',   'generate_kitchenware', None),
    'shelf':       ('shelves',     'shelf_types',   'generate_shelf',       ('single', 'multi', 'bracket', 'box')),
    'painting':    ('paintings',   'paintings',     'generate_painting_proc', ['simple', 'bevel']),
    'mirror':      ('mirrors',     'mirror_types',  'generate_mirror',        ('rectangle', 'round', 'oval', 'arched')),
    'clock_wall':     ('clocks', 'clock_types', 'generate_clock', ('round', 'square')),
    'clock_tabletop': ('clocks', 'clock_types', 'generate_clock', ('alarm',)),
    'clock_floor':    ('clocks', 'clock_types', 'generate_clock', ('grandfather',)),
    'photoframe_wall':    ('photoframes', 'photoframes', 'generate_photoframe_proc', ['wall_simple', 'wall_bevel']),
    'photoframe_tabletop': ('photoframes', 'photoframes', 'generate_photoframe_proc', ['tabletop_simple', 'tabletop_bevel']),
    'plant_tabletop': ('plants', 'plant_types', 'generate_plant', ['succulent', 'cactus', 'fern', 'ficus']),
    'lamp_ceiling':   ('lamps', 'lamps', 'generate_lamp_ceiling', ('pendant', 'flush')),
    'lamp_tabletop':  ('lamps', 'lamps', 'generate_lamp_tabletop', ('classic', 'nightlight')),
    'lamp_floor':     ('lamps', 'lamps', 'generate_lamp_floor', ('floor_lamp', 'arc_lamp')),
    'lamp_wall':      ('lamps', 'lamps', 'generate_lamp_wall', ('sconce',)),
}
