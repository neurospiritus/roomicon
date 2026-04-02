"""Loading materials from .blend files in assets/materials/."""

import bpy
import os
import random

_addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
MATERIALS_DIR = os.path.join(_addon_dir, "assets", "materials")


def _list_blend_files(category):
    """Return list of .blend files in a category."""
    cat_dir = os.path.join(MATERIALS_DIR, category)
    if not os.path.isdir(cat_dir):
        return []
    return [f for f in os.listdir(cat_dir) if f.endswith('.blend')]


def _load_material_from_blend(blend_path, material_name=None):
    """Load a material from .blend. If name not specified, takes the first one."""
    if not os.path.isfile(blend_path):
        return None

    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        if material_name and material_name in data_from.materials:
            data_to.materials = [material_name]
        elif data_from.materials:
            data_to.materials = [data_from.materials[0]]

    if data_to.materials and data_to.materials[0] is not None:
        return data_to.materials[0]
    return None


def load_material(category, name=None, seed=None):
    """
    Load a material from assets/materials/<category>/.

    category: 'floors', 'walls', 'doors', 'baseboards'
    name: .blend filename (without extension). If None, random choice.
    seed: seed for reproducible random selection.

    Returns bpy.types.Material or None.
    """
    blends = _list_blend_files(category)
    if not blends:
        return None

    if name:
        target = f"{name}.blend"
        if target in blends:
            blend_path = os.path.join(MATERIALS_DIR, category, target)
            return _load_material_from_blend(blend_path)
        return None

    # Random choice
    rng = random.Random(seed) if seed is not None else random
    chosen = rng.choice(blends)
    blend_path = os.path.join(MATERIALS_DIR, category, chosen)
    return _load_material_from_blend(blend_path)


def list_available_materials(category):
    """Return list of available material names (without .blend)."""
    return [f[:-6] for f in _list_blend_files(category)]
