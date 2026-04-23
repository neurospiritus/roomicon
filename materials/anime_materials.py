"""Anime/cel-shading material conversion and render setup."""

import bpy


def setup_anime_render():
    """Configure EEVEE for anime-style rendering."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    # Freestyle outlines
    scene.render.use_freestyle = True
    scene.view_layers[0].use_freestyle = True

    # Configure freestyle line set
    vl = scene.view_layers[0]
    if vl.freestyle_settings.linesets:
        ls = vl.freestyle_settings.linesets[0]
    else:
        ls = vl.freestyle_settings.linesets.new("Outline")
    ls.select_silhouette = True
    ls.select_border = True
    ls.select_crease = True
    ls.select_edge_mark = False
    ls.linestyle.thickness = 1.5
    ls.linestyle.color = (0.1, 0.08, 0.06)

    # Bloom for lamp glow effect
    scene.eevee.use_bloom = True
    scene.eevee.bloom_threshold = 1.5
    scene.eevee.bloom_knee = 0.5
    scene.eevee.bloom_radius = 6.0
    scene.eevee.bloom_intensity = 0.3


def setup_realistic_render():
    """Configure EEVEE for realistic rendering with enhanced settings."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    eevee = scene.eevee
    eevee.shadow_cube_size = '2048'
    eevee.shadow_cascade_size = '2048'
    eevee.use_soft_shadows = True

    # Ambient occlusion
    eevee.use_gtao = True
    eevee.gtao_distance = 0.3
    eevee.gtao_factor = 1.0

    # Screen-space reflections
    eevee.use_ssr = True
    eevee.use_ssr_refraction = True

    # Color management
    scene.view_settings.view_transform = 'Filmic'
    scene.view_settings.look = 'Medium Contrast'
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.render.use_freestyle = False

    # Film
    scene.render.film_transparent = False
    scene.cycles.film_exposure = 1.0

    # Color management
    scene.view_settings.view_transform = 'Filmic'
    scene.view_settings.look = 'Medium Contrast'


def _saturate_color(color, factor=1.3):
    """Boost saturation of an RGB color for anime palette."""
    r, g, b = color[0], color[1], color[2]
    gray = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return (
        max(0.0, min(1.0, gray + (r - gray) * factor)),
        max(0.0, min(1.0, gray + (g - gray) * factor)),
        max(0.0, min(1.0, gray + (b - gray) * factor)),
        1.0,
    )


def _make_cel_shader(mat, cel_shading=0.5):
    """Convert a material to cel-shading: Diffuse → Shader to RGB → ColorRamp → Emission.

    cel_shading: 0.0=soft gradients (more tonal variation),
                 1.0=hard flat colors (minimal shading, almost uniform).
    """
    if not mat or not mat.use_nodes:
        return
    # Keep lamp bulbs as emission — they glow regardless of style
    if mat.name.startswith('M_LampBulb'):
        return

    tree = mat.node_tree
    links = tree.links

    # Extract base color from existing Principled BSDF
    base_color = (0.7, 0.7, 0.7, 1.0)
    for node in tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            bc = node.inputs['Base Color']
            if bc.links:
                # Has a texture connected — get from linked node if possible
                linked = bc.links[0].from_node
                if linked.type == 'MIX' and linked.data_type == 'RGBA':
                    # Try to get from mix input
                    pass  # keep default, too complex
                elif linked.type == 'VALTORGB':
                    # ColorRamp — get midpoint color
                    elems = linked.color_ramp.elements
                    if len(elems) >= 2:
                        c = elems[1].color
                        base_color = (c[0], c[1], c[2], 1.0)
                else:
                    base_color = tuple(bc.default_value)
            else:
                base_color = tuple(bc.default_value)
            break

    # Clear all nodes
    output = None
    for node in list(tree.nodes):
        if node.type == 'OUTPUT_MATERIAL':
            output = node
        else:
            tree.nodes.remove(node)
    if not output:
        output = tree.nodes.new('ShaderNodeOutputMaterial')
    output.location = (600, 0)

    # Boost saturation for anime look
    base_color = _saturate_color(base_color, 1.4)

    # Diffuse BSDF
    diffuse = tree.nodes.new('ShaderNodeBsdfDiffuse')
    diffuse.location = (-200, 0)
    diffuse.inputs['Color'].default_value = base_color

    # Shader to RGB
    s2rgb = tree.nodes.new('ShaderNodeShaderToRGB')
    s2rgb.location = (0, 0)

    # ColorRamp for cel-shading steps
    # cel_shading controls:
    # - shadow darkness: high cel = lighter shadow (less visible)
    # - threshold position: high cel = shadow pushed to edges
    # - highlight: high cel = no highlight (flatter)
    shadow_dark = 0.4 + cel_shading * 0.5       # 0.4 (dark) → 0.9 (barely visible)
    shadow_pos = 0.1 + cel_shading * 0.35        # 0.1 (wide shadow) → 0.45 (narrow)
    highlight_boost = 1.3 - cel_shading * 0.25   # 1.3 (bright) → 1.05 (subtle)
    highlight_pos = 0.75 + cel_shading * 0.2     # 0.75 → 0.95 (pushed to edge)

    ramp = tree.nodes.new('ShaderNodeValToRGB')
    ramp.location = (200, 0)
    ramp.color_ramp.interpolation = 'CONSTANT'
    elems = ramp.color_ramp.elements
    elems[0].position = 0.0
    elems[0].color = (
        base_color[0] * shadow_dark,
        base_color[1] * shadow_dark,
        base_color[2] * shadow_dark,
        1.0,
    )
    elems[1].position = shadow_pos
    elems[1].color = base_color

    highlight = ramp.color_ramp.elements.new(highlight_pos)
    highlight.color = (
        min(1.0, base_color[0] * highlight_boost),
        min(1.0, base_color[1] * highlight_boost),
        min(1.0, base_color[2] * highlight_boost),
        1.0,
    )

    # Emission — cel-shading base (flat, ignores scene lights)
    emission = tree.nodes.new('ShaderNodeEmission')
    emission.name = 'CelEmission'
    emission.location = (400, 100)

    # Diffuse for lamp response — same color through ColorRamp,
    # but as Diffuse BSDF it reacts to Point lights
    lamp_diffuse = tree.nodes.new('ShaderNodeBsdfDiffuse')
    lamp_diffuse.location = (400, -100)

    # Mix Shader: Emission (cel) ↔ Diffuse (lamp-reactive)
    # Fac=0 → pure Emission (cel), Fac=1 → pure Diffuse (lit by lamps)
    mix = tree.nodes.new('ShaderNodeMixShader')
    mix.name = 'CelLampMix'
    mix.location = (600, 0)

    # Value node to control mix factor from UI
    mix_val = tree.nodes.new('ShaderNodeValue')
    mix_val.name = 'CelLampFactor'
    mix_val.location = (400, 250)
    mix_val.outputs[0].default_value = 0.0  # default: pure cel

    links.new(diffuse.outputs['BSDF'], s2rgb.inputs['Shader'])
    links.new(s2rgb.outputs['Color'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], emission.inputs['Color'])
    emission.inputs['Strength'].default_value = 1.0
    links.new(ramp.outputs['Color'], lamp_diffuse.inputs['Color'])

    links.new(mix_val.outputs[0], mix.inputs['Fac'])
    links.new(emission.outputs['Emission'], mix.inputs[1])
    links.new(lamp_diffuse.outputs['BSDF'], mix.inputs[2])
    links.new(mix.outputs['Shader'], output.inputs['Surface'])

    output.location = (800, 0)

    mat['cel_shaded'] = True


def convert_scene_to_anime(collection, cel_shading=0.5):
    """Convert all materials in the collection to cel-shading."""
    processed = set()
    for obj in collection.objects:
        if obj.type != 'MESH':
            continue
        for slot in obj.material_slots:
            mat = slot.material
            if mat and mat.name not in processed:
                _make_cel_shader(mat, cel_shading)
                processed.add(mat.name)
        for child in obj.children_recursive:
            if child.type == 'MESH':
                for slot in child.material_slots:
                    mat = slot.material
                    if mat and mat.name not in processed:
                        _make_cel_shader(mat, cel_shading)
                        processed.add(mat.name)
