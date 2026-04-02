"""Photoframes generator — фоторамки настольные и настенные."""

import os
import sys

_dir = os.path.dirname(os.path.realpath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)
_generators_dir = os.path.dirname(_dir)
if _generators_dir not in sys.path:
    sys.path.insert(0, _generators_dir)

from photoframe_types import generate_photoframe, PHOTOFRAME_TYPES
from helpers import list_images

_project_dir = os.path.dirname(os.path.dirname(os.path.dirname(_dir)))
_default_pool = os.path.join(_project_dir, "assets", "pool", "photoframes")

GENERATOR_INFO = {
    'name': 'Photo Frames',
    'description': 'Tabletop with stand, wall-mounted, simple/bevel frames',
    'asset_category': 'tabletop',
}

PARAMS = {
    'obj_type': {
        'type': 'enum',
        'items': list(PHOTOFRAME_TYPES.keys()) + ['mixed'],
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
    import random
    import glob
    rng = random.Random(seed)

    if obj_type == 'mixed':
        obj_type = rng.choice(list(PHOTOFRAME_TYPES.keys()))

    pool_dir = kwargs.get('pool', _default_pool)
    images = list_images(pool_dir)
    image_path = rng.choice(images) if images else None

    return generate_photoframe(seed, image_path=image_path, subtype=obj_type)


def generate_photoframe_proc(seed, subtype='mixed'):
    """Единый интерфейс для procedural режима."""
    return generate_single(seed=seed, obj_type=subtype)
