"""Candles generator — свечи и подсвечники."""

import os, sys
_dir = os.path.dirname(os.path.realpath(__file__))
if _dir not in sys.path: sys.path.insert(0, _dir)
_generators_dir = os.path.dirname(_dir)
if _generators_dir not in sys.path: sys.path.insert(0, _generators_dir)

from common.init_helper import make_generator
_g = make_generator(
    types_module='candle_types', generate_func='generate_candle', types_dict='CANDLE_TYPES',
    name='Candles', description='Pillar, candlestick, group on tray, tealight', asset_category='tabletop',
)
GENERATOR_INFO = _g['info']; PARAMS = _g['params']; generate_single = _g['generate_single']
