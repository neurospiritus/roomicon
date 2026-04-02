"""Kitchenware generator — тела вращения: тарелки, вазы, стаканы, чашки."""

import os
import sys

_dir = os.path.dirname(os.path.realpath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from plates import generate_plate, PLATE_TYPES
from vases import generate_vase, VASE_TYPES
from glasses import generate_glass, GLASS_TYPES
from cups import generate_cup, CUP_TYPES
from bottles import generate_bottle, BOTTLE_TYPES

GENERATOR_INFO = {
    'name': 'Kitchenware',
    'description': 'Plates, vases, glasses, cups, bottles',
    'asset_category': 'tabletop',
}

SUBTYPES = {
    'plates': list(PLATE_TYPES.keys()),
    'vases': list(VASE_TYPES.keys()),
    'glasses': list(GLASS_TYPES.keys()),
    'cups': list(CUP_TYPES.keys()),
    'bottles': list(BOTTLE_TYPES.keys()),
}

PARAMS = {
    'obj_type': {
        'type': 'enum',
        'items': ['plates', 'vases', 'glasses', 'cups', 'mixed','bottles'],
        'default': 'mixed',
        'label': 'Type',
    },
    'subtype': {
        'type': 'enum',
        'items': ['mixed', 'dinner', 'soup', 'dessert', 'classic', 'cylinder',
                  'bottle', 'tumbler', 'highball', 'wine', 'coffee', 'mug'],
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
    'plates': ('plate', generate_plate, PLATE_TYPES),
    'vases': ('vase', generate_vase, VASE_TYPES),
    'glasses': ('glass', generate_glass, GLASS_TYPES),
    'cups': ('cup', generate_cup, CUP_TYPES),
    'bottles': ('bottles', generate_bottle, BOTTLE_TYPES),
}


def generate_single(seed=0, obj_type='mixed', subtype='mixed', **kwargs):
    """Генерирует один объект. Возвращает список Blender-объектов."""
    import random
    rng = random.Random(seed)

    if obj_type == 'mixed':
        obj_type = rng.choice(list(_TYPE_MAP.keys()))

    prefix, gen_fn, type_dict = _TYPE_MAP[obj_type]

    if subtype == 'mixed' or subtype not in type_dict:
        subtype = rng.choice(list(type_dict.keys()))

    if obj_type == 'plates':
        result = gen_fn(seed, plate_type=subtype)
    elif obj_type == 'vases':
        result = gen_fn(seed, vase_type=subtype)
    elif obj_type == 'glasses':
        result = gen_fn(seed, glass_type=subtype)
    elif obj_type == 'cups':
        result = gen_fn(seed, cup_type=subtype)
    elif obj_type == 'bottles':
        result = gen_fn(seed, bottle_type=subtype)



    # cups returns list, others return single object
    if isinstance(result, list):
        return result
    return [result]


def generate_kitchenware(seed, subtype='mixed'):
    """Единый интерфейс: subtype = 'plates','vases','glasses','cups','bottles','mixed'."""
    return generate_single(seed=seed, obj_type=subtype)
