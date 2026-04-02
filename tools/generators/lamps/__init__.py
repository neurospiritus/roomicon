"""Lamps generator — светильники всех типов."""

import os
import sys

_dir = os.path.dirname(os.path.realpath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from tabletop import generate_tabletop_lamp, TABLETOP_TYPES
from floor_lamps import generate_floor_lamp, FLOOR_TYPES
from wall_lamps import generate_wall_lamp, WALL_TYPES
from ceiling_lamps import generate_ceiling_lamp, CEILING_TYPES

GENERATOR_INFO = {
    'name': 'Lamps',
    'description': 'Table lamps, floor lamps, sconces, pendants',
    'asset_category': 'mixed',
}

SUBTYPES = {
    'tabletop': list(TABLETOP_TYPES.keys()),
    'floor': list(FLOOR_TYPES.keys()),
    'wall': list(WALL_TYPES.keys()),
    'ceiling': list(CEILING_TYPES.keys()),
}

PARAMS = {
    'obj_type': {
        'type': 'enum',
        'items': ['tabletop', 'floor', 'wall', 'ceiling', 'mixed'],
        'default': 'mixed',
        'label': 'Type',
    },
    'subtype': {
        'type': 'enum',
        'items': ['mixed', 'classic', 'nightlight', 'floor_lamp', 'arc_lamp',
                  'sconce', 'pendant', 'flush'],
        'default': 'mixed',
        'label': 'Subtype',
    },
    'seed': {
        'type': 'int',
        'default': 0,
        'min': 0,
        'max': 99999,
        'label': 'Seed',
    },
}

_TYPE_MAP = {
    'tabletop': generate_tabletop_lamp,
    'floor': generate_floor_lamp,
    'wall': generate_wall_lamp,
    'ceiling': generate_ceiling_lamp,
}

_SUBTYPE_MAP = {
    'tabletop': TABLETOP_TYPES,
    'floor': FLOOR_TYPES,
    'wall': WALL_TYPES,
    'ceiling': CEILING_TYPES,
}


def generate_single(seed=0, obj_type='mixed', subtype='mixed', **kwargs):
    import random
    rng = random.Random(seed)

    if obj_type == 'mixed':
        obj_type = rng.choice(list(_TYPE_MAP.keys()))

    gen_fn = _TYPE_MAP[obj_type]
    type_dict = _SUBTYPE_MAP[obj_type]

    if subtype == 'mixed' or subtype not in type_dict:
        subtype = rng.choice(list(type_dict.keys()))

    return gen_fn(seed, subtype=subtype)


def generate_lamp_ceiling(seed, subtype='mixed'):
    """Потолочная лампа для procedural режима."""
    return generate_single(seed=seed, obj_type='ceiling', subtype=subtype)


def generate_lamp_tabletop(seed, subtype='mixed'):
    """Настольная лампа для procedural режима."""
    return generate_single(seed=seed, obj_type='tabletop', subtype=subtype)


def generate_lamp_floor(seed, subtype='mixed'):
    """Торшер для procedural режима."""
    return generate_single(seed=seed, obj_type='floor', subtype=subtype)


def generate_lamp_wall(seed, subtype='mixed'):
    """Бра для procedural режима."""
    return generate_single(seed=seed, obj_type='wall', subtype=subtype)
