"""Booksets generator — наборы книг для полок и столов."""

import os
import sys

_dir = os.path.dirname(os.path.realpath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)
_generators_dir = os.path.dirname(_dir)
if _generators_dir not in sys.path:
    sys.path.insert(0, _generators_dir)

from common.init_helper import make_generator

_g = make_generator(
    types_module='bookset_types',
    generate_func='generate_bookset',
    types_dict='BOOKSET_TYPES',
    name='Booksets',
    description='Row, stack, leaning, mixed book arrangements',
    asset_category='tabletop',
    mixed_key='random',
)
GENERATOR_INFO = _g['info']
PARAMS = _g['params']
generate_single = _g['generate_single']
