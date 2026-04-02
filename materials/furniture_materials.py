"""Процедурные материалы для мебели и декора (EEVEE)."""

import bpy


def _get_or_create_material(name):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat


def _clear_nodes(node_tree):
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


def _simple_principled(name, color, roughness=0.5, specular=0.3):
    """Создаёт простой Principled BSDF материал."""
    mat = _get_or_create_material(name)
    tree = mat.node_tree
    output = _clear_nodes(tree)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (200, 0)
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Specular IOR Level'].default_value = specular

    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    output.location = (500, 0)
    return mat


# ============================================================
# Дерево (стол, стул, шкаф, рамка картины)
# ============================================================

def create_wood_material():
    """Светлое дерево с текстурой."""
    mat = _get_or_create_material("M_Wood")
    tree = mat.node_tree
    output = _clear_nodes(tree)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (300, 0)
    bsdf.inputs['Roughness'].default_value = 0.55
    bsdf.inputs['Specular IOR Level'].default_value = 0.3

    # Wave texture для волокон дерева
    wave = tree.nodes.new('ShaderNodeTexWave')
    wave.location = (-400, 0)
    wave.inputs['Scale'].default_value = 3.0
    wave.inputs['Distortion'].default_value = 4.0
    wave.inputs['Detail'].default_value = 3.0
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Y'

    # Цвета дерева
    ramp = tree.nodes.new('ShaderNodeValToRGB')
    ramp.location = (-100, 0)
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (0.25, 0.15, 0.07, 1.0)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (0.4, 0.25, 0.12, 1.0)

    texcoord = tree.nodes.new('ShaderNodeTexCoord')
    texcoord.location = (-600, 0)

    # Noise для вариации
    noise = tree.nodes.new('ShaderNodeTexNoise')
    noise.location = (-400, -200)
    noise.inputs['Scale'].default_value = 10.0
    noise.inputs['Detail'].default_value = 4.0

    bump = tree.nodes.new('ShaderNodeBump')
    bump.location = (100, -200)
    bump.inputs['Strength'].default_value = 0.08

    tree.links.new(texcoord.outputs['Object'], wave.inputs['Vector'])
    tree.links.new(texcoord.outputs['Object'], noise.inputs['Vector'])
    tree.links.new(wave.outputs['Fac'], ramp.inputs['Fac'])
    tree.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    output.location = (600, 0)
    return mat


def create_dark_wood_material():
    """Тёмное дерево (шкаф, рамка картины)."""
    mat = _get_or_create_material("M_DarkWood")
    tree = mat.node_tree
    output = _clear_nodes(tree)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (300, 0)
    bsdf.inputs['Roughness'].default_value = 0.45
    bsdf.inputs['Specular IOR Level'].default_value = 0.4

    wave = tree.nodes.new('ShaderNodeTexWave')
    wave.location = (-400, 0)
    wave.inputs['Scale'].default_value = 4.0
    wave.inputs['Distortion'].default_value = 3.0
    wave.inputs['Detail'].default_value = 3.0
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Y'

    ramp = tree.nodes.new('ShaderNodeValToRGB')
    ramp.location = (-100, 0)
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (0.12, 0.06, 0.03, 1.0)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (0.22, 0.12, 0.06, 1.0)

    texcoord = tree.nodes.new('ShaderNodeTexCoord')
    texcoord.location = (-600, 0)

    tree.links.new(texcoord.outputs['Object'], wave.inputs['Vector'])
    tree.links.new(wave.outputs['Fac'], ramp.inputs['Fac'])
    tree.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    output.location = (600, 0)
    return mat


# ============================================================
# Ткань (диван, кровать — матрас)
# ============================================================

def create_fabric_material():
    """Ткань обивки — диван, кресло."""
    mat = _get_or_create_material("M_Fabric")
    tree = mat.node_tree
    output = _clear_nodes(tree)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (300, 0)
    bsdf.inputs['Base Color'].default_value = (0.22, 0.28, 0.38, 1.0)  # тёмно-синяя ткань
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Specular IOR Level'].default_value = 0.1
    bsdf.inputs['Sheen Weight'].default_value = 0.3

    # Noise для текстуры ткани
    noise = tree.nodes.new('ShaderNodeTexNoise')
    noise.location = (-300, -200)
    noise.inputs['Scale'].default_value = 80.0
    noise.inputs['Detail'].default_value = 6.0

    texcoord = tree.nodes.new('ShaderNodeTexCoord')
    texcoord.location = (-500, 0)

    bump = tree.nodes.new('ShaderNodeBump')
    bump.location = (100, -200)
    bump.inputs['Strength'].default_value = 0.03
    bump.inputs['Distance'].default_value = 0.002

    tree.links.new(texcoord.outputs['Object'], noise.inputs['Vector'])
    tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    output.location = (600, 0)
    return mat


def create_mattress_material():
    """Матрас — светлая ткань."""
    return _simple_principled("M_Mattress",
                               (0.9, 0.88, 0.85, 1.0), roughness=0.8, specular=0.1)


def create_bed_frame_material():
    """Каркас кровати — дерево."""
    return create_wood_material()


# ============================================================
# Керамика (горшок)
# ============================================================

def create_ceramic_material():
    """Керамика — горшок для цветов."""
    return _simple_principled("M_Ceramic",
                               (0.65, 0.35, 0.2, 1.0), roughness=0.4, specular=0.5)


# ============================================================
# Растение (листья, земля)
# ============================================================

def create_leaf_material():
    """Зелёные листья."""
    return _simple_principled("M_Leaf",
                               (0.15, 0.35, 0.1, 1.0), roughness=0.6, specular=0.2)


def create_soil_material():
    """Земля в горшке."""
    return _simple_principled("M_Soil",
                               (0.12, 0.08, 0.05, 1.0), roughness=0.95, specular=0.05)


# ============================================================
# Бумага (книги, холст картины)
# ============================================================

def create_book_material():
    """Обложка книги — случайный тёмный цвет."""
    return _simple_principled("M_Book",
                               (0.3, 0.15, 0.12, 1.0), roughness=0.7, specular=0.2)


def create_canvas_material():
    """Холст картины — светлый."""
    return _simple_principled("M_Canvas",
                               (0.85, 0.8, 0.7, 1.0), roughness=0.8, specular=0.1)


# ============================================================
# Плюш (мягкая игрушка)
# ============================================================

def create_plush_material():
    """Мягкая игрушка — ворсистая ткань."""
    mat = _get_or_create_material("M_Plush")
    tree = mat.node_tree
    output = _clear_nodes(tree)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (300, 0)
    bsdf.inputs['Base Color'].default_value = (0.6, 0.45, 0.3, 1.0)  # бежевый мишка
    bsdf.inputs['Roughness'].default_value = 0.95
    bsdf.inputs['Specular IOR Level'].default_value = 0.05
    bsdf.inputs['Sheen Weight'].default_value = 0.8

    noise = tree.nodes.new('ShaderNodeTexNoise')
    noise.location = (-300, -200)
    noise.inputs['Scale'].default_value = 120.0
    noise.inputs['Detail'].default_value = 8.0

    texcoord = tree.nodes.new('ShaderNodeTexCoord')
    texcoord.location = (-500, 0)

    bump = tree.nodes.new('ShaderNodeBump')
    bump.location = (100, -200)
    bump.inputs['Strength'].default_value = 0.05

    tree.links.new(texcoord.outputs['Object'], noise.inputs['Vector'])
    tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    output.location = (600, 0)
    return mat


# ============================================================
# Металл (ручки, фурнитура — для будущего использования)
# ============================================================

def create_metal_material():
    """Матовый металл (ручки, петли)."""
    mat = _get_or_create_material("M_Metal")
    tree = mat.node_tree
    output = _clear_nodes(tree)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (200, 0)
    bsdf.inputs['Base Color'].default_value = (0.6, 0.6, 0.6, 1.0)
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.35
    bsdf.inputs['Specular IOR Level'].default_value = 0.8

    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    output.location = (500, 0)
    return mat


# ============================================================
# Оконная рама, дверь
# ============================================================

def create_window_frame_material():
    """Белый пластик / ПВХ для оконных рам."""
    return _simple_principled("M_WindowFrame",
                               (0.92, 0.92, 0.92, 1.0), roughness=0.3, specular=0.5)


def create_door_material():
    """Дверное полотно — светлое дерево."""
    return _simple_principled("M_Door",
                               (0.55, 0.38, 0.22, 1.0), roughness=0.5, specular=0.3)


def create_doorframe_material():
    """Дверная коробка — белый."""
    return _simple_principled("M_DoorFrame",
                               (0.9, 0.9, 0.88, 1.0), roughness=0.4, specular=0.3)


# ============================================================
# Назначение материалов мебели/декору
# ============================================================

# Маппинг: имя объекта (lowercase startswith) → функция создания материала
FURNITURE_MATERIAL_MAP = {
    'table': create_wood_material,
    'chair': create_wood_material,
    'wardrobe': create_dark_wood_material,
    'bed': create_wood_material,
    'sofa': create_fabric_material,
    'books': create_book_material,
    'pottedplant': create_ceramic_material,
    'plushtoy': create_plush_material,
    'painting': create_dark_wood_material,
}


def assign_furniture_material(obj):
    """Назначает материал объекту мебели/декора по имени."""
    name_lower = obj.name.lower().replace('_', '')

    for key, creator in FURNITURE_MATERIAL_MAP.items():
        if key in name_lower:
            mat = creator()
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            return

    # Fallback — светло-серый
    mat = _simple_principled("M_Default", (0.6, 0.6, 0.6, 1.0), roughness=0.7)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
