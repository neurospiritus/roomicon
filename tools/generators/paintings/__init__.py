"""Paintings generator — картины из изображений."""

import os
import sys

_dir = os.path.dirname(os.path.realpath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from painting_types import generate_painting, list_images, PAINTING_TYPES

_project_dir = os.path.dirname(os.path.dirname(os.path.dirname(_dir)))
_default_pool = os.path.join(_project_dir, "assets", "pool", "pictures")

GENERATOR_INFO = {
    'name': 'Paintings',
    'description': 'Paintings from images with frames',
    'asset_category': 'wall',
}

PARAMS = {
    'obj_type': {
        'type': 'enum',
        'items': list(PAINTING_TYPES.keys()) + ['mixed'],
        'default': 'mixed',
        'label': 'Frame Type',
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
    rng = random.Random(seed)

    images = list_images(kwargs.get('pool', _default_pool))
    image_path = rng.choice(images) if images else None

    if obj_type == 'mixed':
        obj_type = rng.choice(list(PAINTING_TYPES.keys()))

    return generate_painting(seed, image_path, frame_type=obj_type)


def generate_painting_proc(seed, subtype='mixed'):
    """Единый интерфейс для procedural режима."""
    return generate_single(seed=seed, obj_type=subtype)
