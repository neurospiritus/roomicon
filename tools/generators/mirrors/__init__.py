"""Mirrors generator — настенные зеркала."""

import os, sys
_dir = os.path.dirname(os.path.realpath(__file__))
if _dir not in sys.path: sys.path.insert(0, _dir)
_generators_dir = os.path.dirname(_dir)
if _generators_dir not in sys.path: sys.path.insert(0, _generators_dir)

from common.init_helper import make_generator
_g = make_generator(
    types_module='mirror_types', generate_func='generate_mirror', types_dict='MIRROR_TYPES',
    name='Mirrors', description='Rectangle, round, oval, arched, with shelf', asset_category='wall',
)
GENERATOR_INFO = _g['info']; PARAMS = _g['params']; generate_single = _g['generate_single']
