"""Shared material utilities for generators."""

import bpy


def get_or_create_mat(name):
    """Get existing material or create a new one with nodes enabled."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat


def clear_and_get_output(tree):
    """Clear all nodes except Material Output, return it."""
    for n in list(tree.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            tree.nodes.remove(n)
    output = [n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL']
    if output:
        return output[0]
    return tree.nodes.new('ShaderNodeOutputMaterial')


def setup_principled(mat, color, roughness=0.5, specular=0.3, metallic=0.0,
                     sheen=0.0, sheen_roughness=0.0,
                     transmission=0.0, alpha=1.0, ior=1.45):
    """Set up a Principled BSDF material with common parameters.

    Returns the material.
    """
    tree = mat.node_tree
    output = clear_and_get_output(tree)
    output.location = (500, 0)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (200, 0)
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Specular IOR Level'].default_value = specular
    bsdf.inputs['Metallic'].default_value = metallic

    if sheen > 0:
        bsdf.inputs['Sheen Weight'].default_value = sheen
        bsdf.inputs['Sheen Roughness'].default_value = sheen_roughness
    if transmission > 0:
        bsdf.inputs['Transmission Weight'].default_value = transmission
    if alpha < 1.0:
        bsdf.inputs['Alpha'].default_value = alpha
    if ior != 1.45:
        bsdf.inputs['IOR'].default_value = ior

    tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat
