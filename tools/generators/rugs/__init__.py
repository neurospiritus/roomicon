"""Rugs generator — прямоугольные, круглые, овальные ковры."""

import os
import sys

_dir = os.path.dirname(os.path.realpath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from rugs_types import generate_rug, RUG_TYPES

_project_dir = os.path.dirname(os.path.dirname(os.path.dirname(_dir)))
_default_pool = os.path.join(_project_dir, "assets", "pool", "rugs")

GENERATOR_INFO = {
    'name': 'Rugs',
    'description': 'Rectangular, circular, and oval rugs',
    'asset_category': 'floor',
}

PARAMS = {
    'obj_type': {
        'type': 'enum',
        'items': list(RUG_TYPES.keys()) + ['mixed'],
        'default': 'mixed',
        'label': 'Rug Type',
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

    # Проверяем путь к текстурам
    pool_dir = kwargs.get('pool', _default_pool)
    textures = []
    if os.path.isdir(pool_dir):
        import glob
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif']:
            textures.extend(glob.glob(os.path.join(pool_dir, ext)))
            textures.extend(glob.glob(os.path.join(pool_dir, ext.upper())))

    texture_path = rng.choice(textures) if textures else None

    if obj_type == 'mixed':
        if texture_path:
            # С текстурой — только прямоугольный (текстура не ложится на круг/овал)
            obj_type = 'rectangle'
        else:
            obj_type = rng.choice(list(RUG_TYPES.keys()))

    return generate_rug(seed, obj_type, texture_path)


def generate_rug_proc(seed, subtype='mixed'):
    """Единый интерфейс для procedural режима (с поиском текстур)."""
    return generate_single(seed=seed, obj_type=subtype)
