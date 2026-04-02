"""Curtains generator — шторы для окон."""

import os
import sys

_dir = os.path.dirname(os.path.realpath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from curtain_types import generate_curtain, CURTAIN_TYPES

GENERATOR_INFO = {
    'name': 'Curtains',
    'description': 'Straight, gathered, sheer curtains for windows',
    'asset_category': 'wall',
}

PARAMS = {
    'obj_type': {
        'type': 'enum',
        'items': list(CURTAIN_TYPES.keys()) + ['mixed'],
        'default': 'mixed',
        'label': 'Type',
    },
    'seed': {
        'type': 'int',
        'default': 0,
        'min': 0,
        'max': 99999,
        'label': 'Seed',
    },
}


def generate_single(seed=0, obj_type='mixed', **kwargs):
    """Генерирует штору с дефолтными параметрами окна (для Asset Generator)."""
    import random
    rng = random.Random(seed)

    if obj_type == 'mixed':
        obj_type = rng.choice(list(CURTAIN_TYPES.keys()))

    window_width = kwargs.get('window_width', 1.2)
    window_top_z = kwargs.get('window_top_z', 2.2)

    return generate_curtain(seed, subtype=obj_type,
                             window_width=window_width, window_top_z=window_top_z)
