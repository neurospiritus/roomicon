"""Seating & beds generator — кровати и диваны."""

import os, sys
_dir = os.path.dirname(os.path.realpath(__file__))
if _dir not in sys.path: sys.path.insert(0, _dir)
_generators_dir = os.path.dirname(_dir)
if _generators_dir not in sys.path: sys.path.insert(0, _generators_dir)

from common.init_helper import make_generator
_g = make_generator(
    types_module='seating_types', generate_func='generate_seating', types_dict='SEATING_TYPES',
    name='Seating & Beds', description='Beds (single, double, bunk), sofas, corner sofa, daybed', asset_category='furniture',
)
GENERATOR_INFO = _g['info']; PARAMS = _g['params']; generate_single = _g['generate_single']
