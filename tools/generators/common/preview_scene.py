"""Preview scene setup for headless rendering.

Supports multiple scene styles:
- 'product': Object on neutral surface, camera from above-side (kitchenware, lamps)
- 'wall': Object against wall backdrop, front camera (paintings, shelves, clocks, rugs)
- 'surface': Object on wooden surface, camera from side (booksets)
"""

import bpy
import math


def _compute_bounds(objects):
    """Compute bounding box for a list of objects.

    Returns (max_dim, center, min_coords, max_coords) or defaults if no geometry.
    """
    all_coords = []
    for obj in objects:
        if obj.data and hasattr(obj.data, 'vertices'):
            for v in obj.data.vertices:
                all_coords.append((
                    v.co[0] + obj.location[0],
                    v.co[1] + obj.location[1],
                    v.co[2] + obj.location[2],
                ))

    if not all_coords:
        return 0.3, (0, 0, 0.1), (0, 0, 0), (0.1, 0.1, 0.1)

    xs = [c[0] for c in all_coords]
    ys = [c[1] for c in all_coords]
    zs = [c[2] for c in all_coords]
    max_dim = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    center = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2)
    return max_dim, center, (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _setup_render_and_world(bg_color=(0.85, 0.85, 0.87, 1.0), bg_strength=0.5):
    """Set up EEVEE render and world background."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'

    world = bpy.data.worlds.get("World")
    if not world:
        world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = bg_color
        bg.inputs['Strength'].default_value = bg_strength


def _create_camera_track(location, target, lens=50, clip_end=20.0):
    """Create camera aimed at target point using track quaternion."""
    from mathutils import Vector
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens = lens
    cam_data.clip_start = 0.01
    cam_data.clip_end = clip_end
    cam_obj = bpy.data.objects.new("PreviewCam", cam_data)
    cam_obj.location = location

    direction = Vector(target) - Vector(location)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    return cam_obj


def _create_lights(center, max_dim, key_energy=30.0, fill_energy=15.0):
    """Create standard key + fill area lights."""
    key = bpy.data.lights.new("Key", 'AREA')
    key.energy = key_energy
    key.size = max_dim * 3
    key_obj = bpy.data.objects.new("Key", key)
    key_obj.location = (center[0] + max_dim * 2, center[1] + max_dim, center[2] + max_dim * 2)
    key_obj.rotation_euler = (math.radians(50), 0, math.radians(20))
    bpy.context.collection.objects.link(key_obj)

    fill = bpy.data.lights.new("Fill", 'AREA')
    fill.energy = fill_energy
    fill.size = max_dim * 5
    fill_obj = bpy.data.objects.new("Fill", fill)
    fill_obj.location = (center[0] - max_dim * 2, center[1] + max_dim, center[2] + max_dim)
    bpy.context.collection.objects.link(fill_obj)


def _create_floor_plane(center_x, min_z, max_dim, color=(0.9, 0.9, 0.9, 1.0)):
    """Create floor backdrop plane."""
    bpy.ops.mesh.primitive_plane_add(size=max_dim * 8, location=(center_x, 0, min_z - 0.001))
    plane = bpy.context.active_object
    plane.name = "Backdrop"
    bg_mat = bpy.data.materials.new("M_Backdrop")
    bg_mat.use_nodes = True
    bsdf = bg_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.8
    plane.data.materials.append(bg_mat)
    return plane


def _create_wall_plane(center, max_dim, color=(0.9, 0.88, 0.85, 1.0)):
    """Create wall backdrop plane (vertical, behind objects)."""
    wall_size = max_dim * 4
    bpy.ops.mesh.primitive_plane_add(size=wall_size, location=(center[0], center[1] - max_dim * 0.5, center[2]))
    wall = bpy.context.active_object
    wall.name = "BackWall"
    wall.rotation_euler = (math.pi / 2, 0, 0)
    bg_mat = bpy.data.materials.new("M_Wall")
    bg_mat.use_nodes = True
    bsdf = bg_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.9
    wall.data.materials.append(bg_mat)
    return wall


def setup_preview(objects, style='product', **kwargs):
    """Set up camera, lights and backdrop for preview rendering.

    Args:
        objects: list of bpy objects
        style: 'product' | 'wall' | 'surface'
        **kwargs: Override parameters:
            - cam_lens: Camera lens mm (default varies by style)
            - key_energy: Key light energy
            - fill_energy: Fill light energy
            - floor_color: Floor plane color
            - wall_color: Wall plane color
            - bg_strength: World background strength
    """
    # Опциональный поворот объектов для превью (не влияет на .blend)
    rotate_z = kwargs.get('rotate_z', 0)
    if rotate_z:
        # Крутим root-объекты (Empty parents или объекты без parent)
        rotated = set()
        for obj in objects:
            root = obj
            while root.parent:
                root = root.parent
            if root.name not in rotated:
                root.rotation_euler.z += rotate_z
                rotated.add(root.name)

    max_dim, center, mins, maxs = _compute_bounds(objects)

    if style == 'product':
        # Product shot: camera from front-side (3/4 view), slightly above
        # Objects face +Y, so camera at +Y looking back toward -Y
        cam_dist = max_dim * 2.8
        cam_loc = (
            center[0] + cam_dist * 0.5,
            center[1] + cam_dist * 0.7,
            center[2] + cam_dist * 0.4,
        )
        _create_camera_track(cam_loc, center, lens=kwargs.get('cam_lens', 50))
        _create_lights(center, max_dim,
                       key_energy=kwargs.get('key_energy', 30),
                       fill_energy=kwargs.get('fill_energy', 15))
        _create_floor_plane(center[0], mins[2], max_dim,
                            color=kwargs.get('floor_color', (0.9, 0.9, 0.9, 1.0)))

    elif style == 'wall':
        # Wall-mounted: camera from front-side, wall backdrop behind
        # Objects face +Y, camera at +Y
        cam_dist = max_dim * 2.0
        cam_loc = (
            center[0] + max_dim * 0.3,
            center[1] + cam_dist,
            center[2] + max_dim * 0.1,
        )
        _create_camera_track(cam_loc, center, lens=kwargs.get('cam_lens', 60))
        _create_lights(center, max_dim,
                       key_energy=kwargs.get('key_energy', 30),
                       fill_energy=kwargs.get('fill_energy', 15))
        _create_wall_plane(center, max_dim,
                           color=kwargs.get('wall_color', (0.9, 0.88, 0.85, 1.0)))

    elif style == 'surface':
        # Surface shot: camera from front-side, low angle
        # Objects face +Y, camera at +Y
        cam_dist = max_dim * 2.2
        cam_loc = (
            center[0] + cam_dist * 0.4,
            center[1] + cam_dist * 0.7,
            center[2] + cam_dist * 0.3,
        )
        _create_camera_track(cam_loc, center, lens=kwargs.get('cam_lens', 50))
        _create_lights(center, max_dim,
                       key_energy=kwargs.get('key_energy', 25),
                       fill_energy=kwargs.get('fill_energy', 10))
        _create_floor_plane(center[0], mins[2], max_dim,
                            color=kwargs.get('floor_color', (0.55, 0.4, 0.22, 1.0)))

    _setup_render_and_world(bg_strength=kwargs.get('bg_strength', 0.5))
