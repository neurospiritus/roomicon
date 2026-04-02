"""
Скрипт для генерации .blend материалов комнаты.
Запускать из Blender:
    blender --background --python tools/generate_materials.py

Генерирует .blend файлы в assets/materials/
"""

import bpy
import os
import sys
import random

script_dir = os.path.dirname(os.path.realpath(__file__))
project_dir = os.path.dirname(script_dir)
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

OUTPUT_BASE = os.path.join(project_dir, "assets", "materials")


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)


def save_material(mat, category, name):
    """Сохраняет материал как .blend."""
    out_dir = os.path.join(OUTPUT_BASE, category)
    os.makedirs(out_dir, exist_ok=True)
    filepath = os.path.join(out_dir, f"{name}.blend")

    # Создаём плоскость-превью с материалом
    bpy.ops.mesh.primitive_plane_add()
    preview = bpy.context.active_object
    preview.name = f"Preview_{name}"
    preview.data.materials.append(mat)

    bpy.ops.wm.save_as_mainfile(filepath=filepath, copy=True)

    # Убираем превью
    bpy.data.objects.remove(preview, do_unlink=True)
    print(f"  Saved: {filepath}")


# ============================================================
# Утилиты нод
# ============================================================

def _new_mat(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    # Удаляем дефолтный Principled
    for n in list(tree.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            tree.nodes.remove(n)
    output = None
    for n in tree.nodes:
        if n.type == 'OUTPUT_MATERIAL':
            output = n
    if not output:
        output = tree.nodes.new('ShaderNodeOutputMaterial')
    output.location = (800, 0)
    return mat, tree, output


def _add_principled(tree, x=400, y=0):
    n = tree.nodes.new('ShaderNodeBsdfPrincipled')
    n.location = (x, y)
    return n


def _add_texcoord(tree, x=-800, y=0):
    n = tree.nodes.new('ShaderNodeTexCoord')
    n.location = (x, y)
    return n


def _add_mapping(tree, x=-600, y=0, scale=(1, 1, 1)):
    n = tree.nodes.new('ShaderNodeMapping')
    n.location = (x, y)
    n.inputs['Scale'].default_value = scale
    return n


def _add_noise(tree, x=-400, y=-200, scale=10.0, detail=6.0):
    n = tree.nodes.new('ShaderNodeTexNoise')
    n.location = (x, y)
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    return n


def _add_bump(tree, x=200, y=-300, strength=0.1):
    n = tree.nodes.new('ShaderNodeBump')
    n.location = (x, y)
    n.inputs['Strength'].default_value = strength
    n.inputs['Distance'].default_value = 0.01
    return n


def _add_colorramp(tree, x=-100, y=0, positions=None, colors=None):
    n = tree.nodes.new('ShaderNodeValToRGB')
    n.location = (x, y)
    if positions and colors:
        for i, (pos, col) in enumerate(zip(positions, colors)):
            if i < len(n.color_ramp.elements):
                n.color_ramp.elements[i].position = pos
                n.color_ramp.elements[i].color = col
            else:
                elem = n.color_ramp.elements.new(pos)
                elem.color = col
    return n


# ============================================================
# Полы
# ============================================================

def _vary_color(base, rng, spread=0.06):
    """Slightly vary an RGB color, keeping it in 0..1 range."""
    return tuple(max(0.0, min(1.0, c + rng.uniform(-spread, spread))) for c in base)


# Parquet wood tone palettes: (color1, color2, mortar)
_PARQUET_PALETTES = [
    ((0.28, 0.17, 0.08), (0.38, 0.24, 0.12), (0.15, 0.09, 0.04)),  # classic brown
    ((0.45, 0.30, 0.15), (0.55, 0.38, 0.20), (0.25, 0.16, 0.08)),  # honey
    ((0.18, 0.10, 0.05), (0.28, 0.16, 0.08), (0.10, 0.06, 0.03)),  # dark walnut
    ((0.52, 0.40, 0.28), (0.62, 0.48, 0.32), (0.30, 0.22, 0.12)),  # light oak
    ((0.35, 0.18, 0.10), (0.48, 0.28, 0.14), (0.20, 0.10, 0.05)),  # cherry
    ((0.22, 0.20, 0.17), (0.32, 0.28, 0.22), (0.12, 0.10, 0.08)),  # grey ash
]

def make_floor_parquet(seed=0):
    """Паркет — улучшенный с wave + noise."""
    rng = random.Random(seed)
    mat, tree, output = _new_mat("Floor_Parquet")
    L = tree.links

    palette = rng.choice(_PARQUET_PALETTES)
    c1 = _vary_color(palette[0], rng)
    c2 = _vary_color(palette[1], rng)
    cm = _vary_color(palette[2], rng, 0.03)

    bsdf = _add_principled(tree)
    bsdf.inputs['Roughness'].default_value = rng.uniform(0.4, 0.6)
    bsdf.inputs['Specular IOR Level'].default_value = 0.4

    tc = _add_texcoord(tree)
    mapping = _add_mapping(tree, scale=(4, 4, 4))

    brick = tree.nodes.new('ShaderNodeTexBrick')
    brick.location = (-300, 0)
    brick.inputs['Color1'].default_value = (*c1, 1)
    brick.inputs['Color2'].default_value = (*c2, 1)
    brick.inputs['Mortar'].default_value = (*cm, 1)
    brick.inputs['Scale'].default_value = rng.uniform(5.0, 8.0)
    brick.inputs['Mortar Size'].default_value = 0.003
    brick.inputs['Bias'].default_value = -0.5
    brick.inputs['Brick Width'].default_value = 0.85
    brick.inputs['Row Height'].default_value = rng.uniform(0.10, 0.15)

    noise1 = _add_noise(tree, -300, -200, scale=20.0, detail=8.0)
    noise2 = _add_noise(tree, -300, -400, scale=60.0, detail=4.0)

    mix = tree.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.location = (100, 0)
    mix.inputs['Factor'].default_value = 0.2

    bump = _add_bump(tree, strength=0.15)

    L.new(tc.outputs['Object'], mapping.inputs['Vector'])
    L.new(mapping.outputs['Vector'], brick.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise1.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise2.inputs['Vector'])
    L.new(brick.outputs['Color'], mix.inputs[6])
    L.new(noise1.outputs['Color'], mix.inputs[7])
    L.new(mix.outputs[2], bsdf.inputs['Base Color'])
    L.new(noise2.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


# Tile palettes: (color1, color2)
_TILE_PALETTES = [
    ((0.85, 0.83, 0.80), (0.75, 0.73, 0.70)),  # warm grey
    ((0.90, 0.88, 0.85), (0.80, 0.78, 0.75)),  # light beige
    ((0.70, 0.70, 0.72), (0.58, 0.58, 0.60)),  # cool grey
    ((0.92, 0.90, 0.82), (0.82, 0.78, 0.68)),  # sandstone
    ((0.65, 0.62, 0.58), (0.50, 0.47, 0.43)),  # dark stone
    ((0.88, 0.85, 0.80), (0.60, 0.56, 0.50)),  # contrast terracotta
    ((0.95, 0.94, 0.92), (0.88, 0.87, 0.85)),  # white marble
]

def make_floor_tile(seed=0):
    """Керамическая плитка — Voronoi + шахматка."""
    rng = random.Random(seed)
    mat, tree, output = _new_mat("Floor_Tile")
    L = tree.links

    palette = rng.choice(_TILE_PALETTES)
    c1 = _vary_color(palette[0], rng, 0.04)
    c2 = _vary_color(palette[1], rng, 0.04)

    bsdf = _add_principled(tree)
    bsdf.inputs['Roughness'].default_value = rng.uniform(0.10, 0.25)
    bsdf.inputs['Specular IOR Level'].default_value = 0.6

    tc = _add_texcoord(tree)
    mapping = _add_mapping(tree, scale=(3, 3, 3))

    checker = tree.nodes.new('ShaderNodeTexChecker')
    checker.location = (-300, 0)
    checker.inputs['Color1'].default_value = (*c1, 1)
    checker.inputs['Color2'].default_value = (*c2, 1)
    checker.inputs['Scale'].default_value = rng.uniform(6.0, 12.0)

    noise = _add_noise(tree, -300, -200, scale=50.0, detail=4.0)
    bump = _add_bump(tree, strength=0.03)

    voronoi = tree.nodes.new('ShaderNodeTexVoronoi')
    voronoi.location = (-300, -400)
    voronoi.inputs['Scale'].default_value = 8.0
    voronoi.feature = 'F1'

    mix = tree.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.location = (100, 0)
    mix.inputs['Factor'].default_value = 0.05

    L.new(tc.outputs['Object'], mapping.inputs['Vector'])
    L.new(mapping.outputs['Vector'], checker.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise.inputs['Vector'])
    L.new(mapping.outputs['Vector'], voronoi.inputs['Vector'])
    L.new(checker.outputs['Color'], mix.inputs[6])
    L.new(voronoi.outputs['Distance'], mix.inputs[7])
    L.new(mix.outputs[2], bsdf.inputs['Base Color'])
    L.new(noise.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


# Laminate palettes: (dark_color, light_color)
_LAMINATE_PALETTES = [
    ((0.35, 0.22, 0.10), (0.50, 0.33, 0.18)),  # medium brown
    ((0.20, 0.12, 0.06), (0.32, 0.20, 0.10)),  # dark espresso
    ((0.50, 0.38, 0.22), (0.65, 0.50, 0.30)),  # golden oak
    ((0.25, 0.23, 0.20), (0.40, 0.36, 0.30)),  # grey wood
    ((0.58, 0.45, 0.30), (0.72, 0.58, 0.38)),  # light maple
    ((0.40, 0.22, 0.12), (0.55, 0.32, 0.18)),  # cherry
]

def make_floor_laminate(seed=0):
    """Ламинат — длинные доски с wave."""
    rng = random.Random(seed)
    mat, tree, output = _new_mat("Floor_Laminate")
    L = tree.links

    palette = rng.choice(_LAMINATE_PALETTES)
    c1 = _vary_color(palette[0], rng)
    c2 = _vary_color(palette[1], rng)

    bsdf = _add_principled(tree)
    bsdf.inputs['Roughness'].default_value = rng.uniform(0.25, 0.45)
    bsdf.inputs['Specular IOR Level'].default_value = 0.5

    tc = _add_texcoord(tree)
    mapping = _add_mapping(tree, scale=(2, 8, 2))

    wave = tree.nodes.new('ShaderNodeTexWave')
    wave.location = (-400, 0)
    wave.inputs['Scale'].default_value = rng.uniform(1.5, 3.0)
    wave.inputs['Distortion'].default_value = rng.uniform(3.0, 7.0)
    wave.inputs['Detail'].default_value = 4.0
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Y'

    ramp = _add_colorramp(tree, positions=[0.35, 0.65],
                           colors=[(*c1, 1), (*c2, 1)])

    noise = _add_noise(tree, -400, -300, scale=30.0, detail=6.0)
    bump = _add_bump(tree, strength=0.06)

    L.new(tc.outputs['Object'], mapping.inputs['Vector'])
    L.new(mapping.outputs['Vector'], wave.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise.inputs['Vector'])
    L.new(wave.outputs['Fac'], ramp.inputs['Fac'])
    L.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    L.new(noise.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


# ============================================================
# Стены
# ============================================================

# Wall color palettes (base_color)
_WALL_COLORS = [
    (0.70, 0.65, 0.60),  # warm beige
    (0.74, 0.70, 0.64),  # ivory
    (0.60, 0.64, 0.68),  # cool grey-blue
    (0.72, 0.66, 0.57),  # sand
    (0.64, 0.60, 0.56),  # taupe
    (0.67, 0.67, 0.65),  # light grey
    (0.74, 0.64, 0.60),  # peach
    (0.62, 0.68, 0.60),  # sage green
    (0.66, 0.62, 0.70),  # lavender
    (0.74, 0.68, 0.58),  # cream
    (0.57, 0.64, 0.57),  # muted green
    (0.70, 0.60, 0.60),  # dusty rose
    (0.54, 0.60, 0.68),  # steel blue
    (0.72, 0.67, 0.52),  # warm yellow
    (0.62, 0.60, 0.58),  # mushroom
]

def make_wall_plaster(seed=0):
    """Гладкая штукатурка."""
    rng = random.Random(seed)
    mat, tree, output = _new_mat("Wall_Plaster")
    L = tree.links

    color = _vary_color(rng.choice(_WALL_COLORS), rng, 0.04)

    bsdf = _add_principled(tree)
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rng.uniform(0.75, 0.95)
    bsdf.inputs['Specular IOR Level'].default_value = 0.1

    tc = _add_texcoord(tree)
    noise = _add_noise(tree, scale=rng.uniform(30.0, 70.0), detail=10.0)
    noise.inputs['Roughness'].default_value = 0.7
    bump = _add_bump(tree, strength=rng.uniform(0.02, 0.06))

    L.new(tc.outputs['Object'], noise.inputs['Vector'])
    L.new(noise.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


def make_wall_paint(seed=0):
    """Краска — гладкая с едва заметной текстурой."""
    rng = random.Random(seed)
    mat, tree, output = _new_mat("Wall_Paint")
    L = tree.links

    color = _vary_color(rng.choice(_WALL_COLORS), rng, 0.04)

    bsdf = _add_principled(tree)
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rng.uniform(0.4, 0.7)
    bsdf.inputs['Specular IOR Level'].default_value = 0.2

    tc = _add_texcoord(tree)
    noise = _add_noise(tree, scale=100.0, detail=3.0)
    bump = _add_bump(tree, strength=0.01)

    L.new(tc.outputs['Object'], noise.inputs['Vector'])
    L.new(noise.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


# Wallpaper palettes: (pattern_dark, pattern_light)
_WALLPAPER_PALETTES = [
    ((0.57, 0.54, 0.50), (0.67, 0.64, 0.60)),  # classic beige
    ((0.50, 0.54, 0.60), (0.60, 0.64, 0.68)),  # blue-grey
    ((0.56, 0.52, 0.47), (0.66, 0.62, 0.56)),  # warm stone
    ((0.47, 0.54, 0.47), (0.58, 0.64, 0.58)),  # sage
    ((0.60, 0.50, 0.52), (0.70, 0.60, 0.62)),  # dusty pink
    ((0.62, 0.58, 0.47), (0.70, 0.66, 0.54)),  # gold cream
    ((0.44, 0.48, 0.56), (0.56, 0.60, 0.66)),  # steel blue
    ((0.52, 0.50, 0.46), (0.64, 0.62, 0.58)),  # taupe
    ((0.50, 0.56, 0.50), (0.62, 0.68, 0.62)),  # mint
    ((0.60, 0.52, 0.47), (0.70, 0.62, 0.56)),  # terracotta
]

def make_wall_wallpaper(seed=0):
    """Обои — с повторяющимся паттерном."""
    rng = random.Random(seed)
    mat, tree, output = _new_mat("Wall_Wallpaper")
    L = tree.links

    palette = rng.choice(_WALLPAPER_PALETTES)
    c1 = _vary_color(palette[0], rng, 0.03)
    c2 = _vary_color(palette[1], rng, 0.03)

    bsdf = _add_principled(tree)
    bsdf.inputs['Roughness'].default_value = rng.uniform(0.65, 0.85)
    bsdf.inputs['Specular IOR Level'].default_value = 0.1

    tc = _add_texcoord(tree)
    scale = rng.uniform(8.0, 14.0)
    mapping = _add_mapping(tree, scale=(scale, scale, scale))

    voronoi = tree.nodes.new('ShaderNodeTexVoronoi')
    voronoi.location = (-300, 0)
    voronoi.inputs['Scale'].default_value = rng.uniform(10.0, 25.0)
    voronoi.feature = 'F1'

    ramp = _add_colorramp(tree, positions=[0.3, 0.7],
                           colors=[(*c1, 1), (*c2, 1)])

    noise = _add_noise(tree, -300, -300, scale=80.0, detail=4.0)
    bump = _add_bump(tree, strength=0.02)

    L.new(tc.outputs['Object'], mapping.inputs['Vector'])
    L.new(mapping.outputs['Vector'], voronoi.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise.inputs['Vector'])
    L.new(voronoi.outputs['Distance'], ramp.inputs['Fac'])
    L.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    L.new(noise.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


# ============================================================
# Двери
# ============================================================

def make_door_wood(seed=0):
    """Дверь — светлое дерево с выраженной текстурой."""
    mat, tree, output = _new_mat("Door_Wood")
    L = tree.links

    bsdf = _add_principled(tree)
    bsdf.inputs['Roughness'].default_value = 0.45
    bsdf.inputs['Specular IOR Level'].default_value = 0.4

    tc = _add_texcoord(tree)
    mapping = _add_mapping(tree, scale=(1, 3, 1))

    wave = tree.nodes.new('ShaderNodeTexWave')
    wave.location = (-400, 0)
    wave.inputs['Scale'].default_value = 3.0
    wave.inputs['Distortion'].default_value = 6.0
    wave.inputs['Detail'].default_value = 5.0
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Z'

    ramp = _add_colorramp(tree, positions=[0.3, 0.7],
                           colors=[(0.4, 0.26, 0.13, 1), (0.55, 0.38, 0.2, 1)])

    noise = _add_noise(tree, -400, -300, scale=15.0, detail=8.0)
    bump = _add_bump(tree, strength=0.08)

    L.new(tc.outputs['Object'], mapping.inputs['Vector'])
    L.new(mapping.outputs['Vector'], wave.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise.inputs['Vector'])
    L.new(wave.outputs['Fac'], ramp.inputs['Fac'])
    L.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    L.new(noise.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


# ============================================================
# Плинтусы
# ============================================================

def make_baseboard_white(seed=0):
    """Плинтус — белый полуглянцевый."""
    mat, tree, output = _new_mat("Baseboard_White")
    L = tree.links

    bsdf = _add_principled(tree)
    bsdf.inputs['Base Color'].default_value = (0.93, 0.92, 0.9, 1)
    bsdf.inputs['Roughness'].default_value = 0.3
    bsdf.inputs['Specular IOR Level'].default_value = 0.4

    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat


# ============================================================
# Main
# ============================================================

MATERIALS = [
    # (category, name, creator)
    ('floors', 'parquet', make_floor_parquet),
    ('floors', 'tile', make_floor_tile),
    ('floors', 'laminate', make_floor_laminate),
    ('walls', 'plaster', make_wall_plaster),
    ('walls', 'paint', make_wall_paint),
    ('walls', 'wallpaper', make_wall_wallpaper),
    ('doors', 'wood', make_door_wood),
    ('baseboards', 'white', make_baseboard_white),
]


def main():
    print("=" * 50)
    print("Generating material assets...")
    print("=" * 50)

    for category, name, creator in MATERIALS:
        clear_scene()
        print(f"  {category}/{name}")
        mat = creator()
        save_material(mat, category, name)

    print(f"\nDone! Generated {len(MATERIALS)} materials.")


if __name__ == "__main__":
    main()
