"""Helper for creating standard generator __init__.py with minimal boilerplate.

Usage in a generator's __init__.py:

    from common.init_helper import make_generator
    _g = make_generator(
        types_module='bookset_types',
        generate_func='generate_bookset',
        types_dict='BOOKSET_TYPES',
        name='Booksets',
        description='Row, stack, leaning, mixed book arrangements',
        asset_category='tabletop',
        mixed_key='random',  # 'mixed' or 'random', default 'mixed'
    )
    GENERATOR_INFO = _g['info']
    PARAMS = _g['params']
    generate_single = _g['generate_single']
"""

import os
import sys
import importlib


def make_generator(types_module, generate_func, types_dict,
                   name, description, asset_category,
                   mixed_key='mixed', gen_kwarg='subtype'):
    """Create standard generator interface from minimal config.

    Args:
        types_module: Module name to import (e.g. 'bookset_types')
        generate_func: Function name in that module (e.g. 'generate_bookset')
        types_dict: Dict name in that module (e.g. 'BOOKSET_TYPES')
        name: Display name for GENERATOR_INFO
        description: Description for GENERATOR_INFO
        asset_category: Asset category (tabletop, floor, wall, etc.)
        mixed_key: Key for "all types" option ('mixed' or 'random')
        gen_kwarg: Keyword argument name for the type (default 'subtype')

    Returns:
        Dict with 'info', 'params', 'generate_single' keys.
    """
    # Import the types module
    mod = importlib.import_module(types_module)
    gen_fn = getattr(mod, generate_func)
    types = getattr(mod, types_dict)

    info = {
        'name': name,
        'description': description,
        'asset_category': asset_category,
    }

    params = {
        'obj_type': {
            'type': 'enum',
            'items': list(types.keys()) + [mixed_key],
            'default': mixed_key,
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

    def generate_single(seed=0, obj_type=None, **kwargs):
        import random
        if obj_type is None:
            obj_type = mixed_key
        rng = random.Random(seed)
        if obj_type == mixed_key:
            obj_type = rng.choice(list(types.keys()))
        return gen_fn(seed, **{gen_kwarg: obj_type})

    return {
        'info': info,
        'params': params,
        'generate_single': generate_single,
    }
