"""Генерация ковров: прямоугольные, круглые, овальные с текстурами и процедурными паттернами."""

import bpy
import os
import random

from helpers import (
    create_rect_rug, create_circle_rug, create_oval_rug,
    _get_or_create_mat, RUG_COLORS,
)

TEXTURE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}

RUG_TYPES = {
    'rectangle': {},
    'circle': {},
    'oval': {},
}


def list_textures(pool_dir):
    """Возвращает список путей к текстурам в пуле."""
    if not os.path.isdir(pool_dir):
        return []
    result = []
    for f in os.listdir(pool_dir):
        ext = os.path.splitext(f)[1].lower()
        if ext in TEXTURE_EXTENSIONS:
            result.append(os.path.join(pool_dir, f))
    return sorted(result)


# ============================================================
# Материалы
# ============================================================

def _create_texture_material(texture_path):
    """Материал с изображением-текстурой."""
    img = bpy.data.images.load(texture_path, check_existing=True)
    mat_name = f"M_Rug_{os.path.basename(texture_path)}"
    mat = _get_or_create_mat(mat_name)
    tree = mat.node_tree

    for n in list(tree.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            tree.nodes.remove(n)
    output = [n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    output.location = (600, 0)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (300, 0)
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Specular IOR Level'].default_value = 0.05
    bsdf.inputs['Sheen Weight'].default_value = 0.4

    tex = tree.nodes.new('ShaderNodeTexImage')
    tex.location = (0, 0)
    tex.image = img

    tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat


def _create_solid_material(rng):
    """Однотонный ковёр."""
    color = rng.choice(RUG_COLORS)
    mat = _get_or_create_mat("M_Rug_Solid")
    tree = mat.node_tree

    for n in list(tree.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            tree.nodes.remove(n)
    output = [n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    output.location = (600, 0)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (300, 0)
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Specular IOR Level'].default_value = 0.05
    bsdf.inputs['Sheen Weight'].default_value = 0.4

    # Лёгкий noise bump для текстуры ворса
    noise = tree.nodes.new('ShaderNodeTexNoise')
    noise.location = (-200, -200)
    noise.inputs['Scale'].default_value = 80.0
    noise.inputs['Detail'].default_value = 6.0

    bump = tree.nodes.new('ShaderNodeBump')
    bump.location = (100, -200)
    bump.inputs['Strength'].default_value = 0.03

    tc = tree.nodes.new('ShaderNodeTexCoord')
    tc.location = (-400, -200)

    tree.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat


def _create_stripes_material(rng):
    """Полосатый ковёр."""
    color1 = rng.choice(RUG_COLORS)
    color2 = rng.choice(RUG_COLORS)
    mat = _get_or_create_mat("M_Rug_Stripes")
    tree = mat.node_tree

    for n in list(tree.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            tree.nodes.remove(n)
    output = [n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    output.location = (600, 0)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (300, 0)
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Sheen Weight'].default_value = 0.4

    # Wave для полос
    wave = tree.nodes.new('ShaderNodeTexWave')
    wave.location = (-200, 0)
    wave.inputs['Scale'].default_value = rng.uniform(3, 8)
    wave.wave_type = 'BANDS'
    wave.bands_direction = rng.choice(['X', 'Y'])

    ramp = tree.nodes.new('ShaderNodeValToRGB')
    ramp.location = (0, 0)
    ramp.color_ramp.elements[0].color = color1
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[1].color = color2
    ramp.color_ramp.elements[1].position = 0.55

    tc = tree.nodes.new('ShaderNodeTexCoord')
    tc.location = (-400, 0)

    tree.links.new(tc.outputs['Object'], wave.inputs['Vector'])
    tree.links.new(wave.outputs['Fac'], ramp.inputs['Fac'])
    tree.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat


def _create_border_material(rng):
    """Ковёр с бордюром (центр одного цвета, край другого)."""
    color_center = rng.choice(RUG_COLORS)
    color_border = rng.choice(RUG_COLORS)
    mat = _get_or_create_mat("M_Rug_Border")
    tree = mat.node_tree

    for n in list(tree.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            tree.nodes.remove(n)
    output = [n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    output.location = (800, 0)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (500, 0)
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Sheen Weight'].default_value = 0.4

    # Gradient через UV: расстояние от центра
    tc = tree.nodes.new('ShaderNodeTexCoord')
    tc.location = (-400, 0)

    # Маппинг: UV 0..1 → -0.5..0.5
    mapping = tree.nodes.new('ShaderNodeMapping')
    mapping.location = (-200, 0)
    mapping.inputs['Location'].default_value = (-0.5, -0.5, 0)

    # Расстояние от центра через Vector Math (length)
    vec_math = tree.nodes.new('ShaderNodeVectorMath')
    vec_math.location = (0, 0)
    vec_math.operation = 'LENGTH'

    # Ramp: центр → бордюр
    ramp = tree.nodes.new('ShaderNodeValToRGB')
    ramp.location = (200, 0)
    ramp.color_ramp.elements[0].color = color_center
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[1].color = color_border
    ramp.color_ramp.elements[1].position = 0.35

    tree.links.new(tc.outputs['UV'], mapping.inputs['Vector'])
    tree.links.new(mapping.outputs['Vector'], vec_math.inputs[0])
    tree.links.new(vec_math.outputs['Value'], ramp.inputs['Fac'])
    tree.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat


def _create_checker_material(rng):
    """Шахматный паттерн."""
    color1 = rng.choice(RUG_COLORS)
    color2 = rng.choice(RUG_COLORS)
    mat = _get_or_create_mat("M_Rug_Checker")
    tree = mat.node_tree

    for n in list(tree.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            tree.nodes.remove(n)
    output = [n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    output.location = (600, 0)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (300, 0)
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Sheen Weight'].default_value = 0.4

    checker = tree.nodes.new('ShaderNodeTexChecker')
    checker.location = (-100, 0)
    checker.inputs['Color1'].default_value = color1
    checker.inputs['Color2'].default_value = color2
    checker.inputs['Scale'].default_value = rng.uniform(4, 10)

    tc = tree.nodes.new('ShaderNodeTexCoord')
    tc.location = (-300, 0)

    tree.links.new(tc.outputs['Object'], checker.inputs['Vector'])
    tree.links.new(checker.outputs['Color'], bsdf.inputs['Base Color'])
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat


PATTERN_CREATORS = {
    'solid': _create_solid_material,
    'stripes': _create_stripes_material,
    'border': _create_border_material,
    'checker': _create_checker_material,
}


# ============================================================
# API
# ============================================================

def _get_image_aspect(image_path):
    """Загружает изображение и возвращает aspect ratio (w/h)."""
    img = bpy.data.images.load(image_path, check_existing=True)
    w, h = img.size
    if h == 0:
        return 1.0
    return w / h


def generate_rug(seed, rug_type='rectangle', texture_path=None):
    """Генерирует один ковёр. Возвращает список объектов."""
    rng = random.Random(seed)

    if rug_type == 'rectangle' and texture_path and os.path.isfile(texture_path):
        # С текстурой — всегда прямоугольный, размеры по aspect ratio картинки
        aspect = _get_image_aspect(texture_path)
        width = rng.uniform(1.2, 2.5)
        depth = width / aspect
        # Ограничиваем глубину
        if depth > 2.0:
            depth = 2.0
            width = depth * aspect
        if depth < 0.6:
            depth = 0.6
            width = depth * aspect
        rug = create_rect_rug("Rug", width, depth)
        mat = _create_texture_material(texture_path)

    else:
        # Процедурный — любая форма
        if rug_type == 'rectangle':
            width = rng.uniform(1.2, 2.5)
            depth = rng.uniform(0.8, 1.8)
            rug = create_rect_rug("Rug", width, depth)

        elif rug_type == 'circle':
            radius = rng.uniform(0.6, 1.0)
            rug = create_circle_rug("Rug", radius)

        elif rug_type == 'oval':
            rx = rng.uniform(0.7, 1.25)
            ry = rng.uniform(0.5, 0.9)
            rug = create_oval_rug("Rug", rx, ry)

        else:
            raise ValueError(f"Unknown rug type: {rug_type}")

        pattern = rng.choice(list(PATTERN_CREATORS.keys()))
        mat = PATTERN_CREATORS[pattern](rng)

    # Толщина через Solidify
    mod = rug.modifiers.new("Solidify", 'SOLIDIFY')
    mod.thickness = 0.008
    mod.offset = 1.0

    rug.data.materials.append(mat)
    return [rug]
