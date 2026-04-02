"""Процедурные материалы для комнаты (EEVEE)."""

import bpy


def _get_or_create_material(name):
    """Возвращает материал по имени или создаёт новый с нодами."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat


def _clear_nodes(node_tree):
    """Удаляет все ноды кроме Material Output."""
    for node in list(node_tree.nodes):
        if node.type != 'OUTPUT_MATERIAL':
            node_tree.nodes.remove(node)
    output = None
    for node in node_tree.nodes:
        if node.type == 'OUTPUT_MATERIAL':
            output = node
            break
    if output is None:
        output = node_tree.nodes.new('ShaderNodeOutputMaterial')
    return output


def create_ceiling_material():
    """Потолок — белый матовый."""
    mat = _get_or_create_material("M_Ceiling")
    tree = mat.node_tree
    output = _clear_nodes(tree)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (200, 0)
    bsdf.inputs['Base Color'].default_value = (0.95, 0.95, 0.95, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.95
    bsdf.inputs['Specular IOR Level'].default_value = 0.05

    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    output.location = (500, 0)
    return mat


def _pick_procedural_material(category, seed):
    """Выбирает процедурный материал по категории и seed."""
    import random
    import os, sys, importlib
    rng = random.Random(seed)

    # Импортируем функции из tools/generate_materials.py
    _addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    tools_dir = os.path.join(_addon_dir, 'tools')
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    if 'generate_materials' in sys.modules:
        importlib.reload(sys.modules['generate_materials'])
    else:
        importlib.import_module('generate_materials')
    gm = sys.modules['generate_materials']

    creators = {
        'floors': [gm.make_floor_parquet, gm.make_floor_tile, gm.make_floor_laminate],
        'walls': [gm.make_wall_plaster, gm.make_wall_paint, gm.make_wall_wallpaper],
        'doors': [gm.make_door_wood],
        'baseboards': [gm.make_baseboard_white],
    }
    options = creators.get(category, [])
    if not options:
        return None
    return rng.choice(options)(seed=seed)


def assign_room_materials(collection, seed=0):
    """Назначает материалы объектам комнаты. Сначала пробует .blend, затем процедурные."""
    from core.material_loader import load_material

    # Пробуем загрузить из .blend, иначе процедурные (разные по seed)
    floor_mat = load_material('floors', seed=seed) or _pick_procedural_material('floors', seed)
    wall_mat = load_material('walls', seed=seed) or _pick_procedural_material('walls', seed + 1)
    baseboard_mat = load_material('baseboards', seed=seed) or _pick_procedural_material('baseboards', seed + 2)
    ceiling_mat = create_ceiling_material()

    for obj in collection.objects:
        if obj.type != 'MESH':
            continue

        name = obj.name.lower()
        if 'floor' in name:
            mat = floor_mat
        elif 'ceiling' in name:
            mat = ceiling_mat
        elif 'baseboard' in name:
            mat = baseboard_mat
        elif 'wall' in name:
            mat = wall_mat
        else:
            continue

        obj.data.materials.clear()
        obj.data.materials.append(mat)
