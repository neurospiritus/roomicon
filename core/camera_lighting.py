"""Camera and lighting for the room."""

import bpy
import math


def setup_camera(width, length, height, wt=0.15):
    """Camera at the door (Left wall), aimed into the room (+X)."""
    cam_data = bpy.data.cameras.new("RoomCamera")
    cam_data.lens = 18
    cam_data.clip_start = 0.1
    cam_data.clip_end = 50.0

    cam_obj = bpy.data.objects.new("RoomCamera", cam_data)
    cam_obj.location = (wt + 0.15, length / 2, height * 0.55)
    cam_obj.rotation_euler = (math.radians(80), 0, math.radians(-90))

    bpy.context.scene.camera = cam_obj
    return cam_obj


def setup_lighting(width, length, height, wt, wall_configs, sill_height, window_height):
    """Realistic lighting for Cycles: Sun + window area lights + ambient World."""
    objects = []

    # World ambient — warm low-energy sky for soft fill
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    wtree = world.node_tree
    bg = wtree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (0.8, 0.85, 0.95, 1.0)
        bg.inputs['Strength'].default_value = 0.3

    # Sun — warm directional light through the room
    sun_data = bpy.data.lights.new("RoomSun", 'SUN')
    sun_data.energy = 1.5
    sun_data.color = (1.0, 0.93, 0.85)
    sun_data.angle = math.radians(5)  # soft sun edge
    sun_obj = bpy.data.objects.new("RoomSun", sun_data)
    sun_obj.location = (width / 2, length / 2, height + 1)
    sun_obj.rotation_euler = (math.radians(45), math.radians(10), math.radians(-30))
    objects.append(sun_obj)

    # Warm bounce fill from below (simulates floor reflection)
    fill_data = bpy.data.lights.new("RoomFill", 'AREA')
    fill_data.energy = 8.0
    fill_data.color = (1.0, 0.95, 0.88)
    fill_data.size = width * 0.6
    fill_data.size_y = length * 0.6
    fill_obj = bpy.data.objects.new("RoomFill", fill_data)
    fill_obj.location = (width / 2, length / 2, 0.05)
    fill_obj.rotation_euler = (0, 0, 0)  # facing up
    objects.append(fill_obj)

    # Area lights in window openings — energy distributed across all windows
    total_windows = sum(wc for _, wt_, wc in wall_configs if wt_ == 'WINDOWS' and wc > 0)
    total_window_energy = 200.0  # total budget for all windows
    per_window_energy = total_window_energy / max(total_windows, 1)

    window_z = sill_height + window_height / 2
    sides_info = [
        ('front', width),
        ('back', width),
        ('left', length),
        ('right', length),
    ]

    for (side, wtype, win_count), (side_name, wall_len) in zip(wall_configs, sides_info):
        if wtype != 'WINDOWS' or win_count <= 0:
            continue

        spacing = wall_len / (win_count + 1)
        for i in range(win_count):
            pos_along = spacing * (i + 1)

            light_data = bpy.data.lights.new(f"WindowLight_{side_name}_{i}", 'AREA')
            light_data.energy = per_window_energy
            light_data.color = (0.92, 0.95, 1.0)
            light_data.size = 1.2
            light_data.size_y = window_height * 0.9

            light_obj = bpy.data.objects.new(f"WindowLight_{side_name}_{i}", light_data)

            if side_name == 'front':
                light_obj.location = (pos_along, wt + 0.05, window_z)
                light_obj.rotation_euler = (math.radians(90), 0, 0)
            elif side_name == 'back':
                light_obj.location = (pos_along, length - wt - 0.05, window_z)
                light_obj.rotation_euler = (math.radians(-90), 0, 0)
            elif side_name == 'left':
                light_obj.location = (wt + 0.05, pos_along, window_z)
                light_obj.rotation_euler = (math.radians(90), 0, math.radians(90))
            elif side_name == 'right':
                light_obj.location = (width - wt - 0.05, pos_along, window_z)
                light_obj.rotation_euler = (math.radians(90), 0, math.radians(90))

            objects.append(light_obj)

    return objects


def setup_lighting_anime(width, length, height, wt, wall_configs, sill_height, window_height):
    """Anime lighting: soft, even, minimal shadows."""
    objects = []

    # Soft shadows in EEVEE
    eevee = bpy.context.scene.eevee
    eevee.shadow_cube_size = '512'
    eevee.shadow_cascade_size = '1024'
    eevee.use_soft_shadows = True

    # Main fill light — bright, from above, almost white
    sun_data = bpy.data.lights.new("AnimeSun", 'SUN')
    sun_data.energy = 3.0
    sun_data.color = (1.0, 0.98, 0.96)
    sun_data.use_shadow = False
    sun_obj = bpy.data.objects.new("AnimeSun", sun_data)
    sun_obj.location = (width / 2, length / 2, height + 1)
    sun_obj.rotation_euler = (math.radians(70), 0, math.radians(-20))
    objects.append(sun_obj)

    # Fill light from opposite side to reduce shadows
    fill_data = bpy.data.lights.new("AnimeFill", 'SUN')
    fill_data.energy = 1.5
    fill_data.color = (0.95, 0.95, 1.0)
    fill_data.use_shadow = False
    fill_obj = bpy.data.objects.new("AnimeFill", fill_data)
    fill_obj.location = (width / 2, length / 2, height)
    fill_obj.rotation_euler = (math.radians(60), 0, math.radians(160))
    objects.append(fill_obj)

    # Soft area lights in windows — lower energy, warm tint
    window_z = sill_height + window_height / 2
    sides_info = [
        ('front', width),
        ('back', width),
        ('left', length),
        ('right', length),
    ]

    for (side, wtype, win_count), (side_name, wall_len) in zip(wall_configs, sides_info):
        if wtype != 'WINDOWS' or win_count <= 0:
            continue

        spacing = wall_len / (win_count + 1)
        for i in range(win_count):
            pos_along = spacing * (i + 1)

            light_data = bpy.data.lights.new(f"AnimeWindow_{side_name}_{i}", 'AREA')
            light_data.energy = 40.0
            light_data.color = (1.0, 0.97, 0.92)
            light_data.size = 1.5
            light_data.size_y = window_height
            light_data.use_shadow = False

            light_obj = bpy.data.objects.new(f"AnimeWindow_{side_name}_{i}", light_data)

            if side_name == 'front':
                light_obj.location = (pos_along, wt + 0.05, window_z)
                light_obj.rotation_euler = (math.radians(90), 0, 0)
            elif side_name == 'back':
                light_obj.location = (pos_along, length - wt - 0.05, window_z)
                light_obj.rotation_euler = (math.radians(-90), 0, 0)
            elif side_name == 'left':
                light_obj.location = (wt + 0.05, pos_along, window_z)
                light_obj.rotation_euler = (math.radians(90), 0, math.radians(90))
            elif side_name == 'right':
                light_obj.location = (width - wt - 0.05, pos_along, window_z)
                light_obj.rotation_euler = (math.radians(90), 0, math.radians(90))

            objects.append(light_obj)

    return objects
