"""
Реестр генераторов — автоматическое обнаружение и загрузка.
Каждый генератор должен иметь файл __init__.py с:
  - GENERATOR_INFO: dict с name, description
  - PARAMS: dict с описанием параметров
  - generate_single(seed, subtype, **kwargs): функция генерации одного объекта
"""

import os
import sys
import importlib

_generators_dir = os.path.dirname(os.path.realpath(__file__))


def discover_generators():
    """
    Сканирует tools/generators/*/ и возвращает dict:
    { 'kitchenware': module, 'lamps': module, ... }
    """
    if _generators_dir not in sys.path:
        sys.path.insert(0, _generators_dir)

    generators = {}
    for name in sorted(os.listdir(_generators_dir)):
        gen_dir = os.path.join(_generators_dir, name)
        init_file = os.path.join(gen_dir, '__init__.py')
        if os.path.isdir(gen_dir) and os.path.isfile(init_file):
            try:
                # Reload если уже загружен
                mod_name = name
                if mod_name in sys.modules:
                    mod = importlib.reload(sys.modules[mod_name])
                else:
                    mod = importlib.import_module(mod_name)

                if hasattr(mod, 'GENERATOR_INFO') and hasattr(mod, 'generate_single'):
                    generators[name] = mod
            except Exception as e:
                print(f"Warning: failed to load generator '{name}': {e}")

    return generators
