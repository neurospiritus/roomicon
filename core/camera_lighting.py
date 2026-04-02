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
    """Lighting: Sun for ambient light, Area lights in window openings."""
    objects = []

    # EEVEE shadow settings
    eevee = bpy.context.scene.eevee
    eevee.shadow_cube_size = '1024'
    eevee.shadow_cascade_size = '2048'
    eevee.use_soft_shadows = True

    # Sun light
    sun_data = bpy.data.lights.new("RoomSun", 'SUN')
    sun_data.energy = 2.0
    sun_data.color = (1.0, 0.95, 0.9)
    sun_data.shadow_buffer_bias = 0.001
    sun_data.use_contact_shadow = True
    sun_data.contact_shadow_distance = 0.5
    sun_data.contact_shadow_bias = 0.001
    sun_obj = bpy.data.objects.new("RoomSun", sun_data)
    sun_obj.location = (width / 2, length / 2, height + 1)
    sun_obj.rotation_euler = (math.radians(50), math.radians(15), math.radians(-30))
    objects.append(sun_obj)

    # Area lights in window openings
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
            light_data.energy = 80.0
            light_data.color = (0.9, 0.95, 1.0)
            light_data.size = 1.0
            light_data.size_y = window_height * 0.8
            light_data.shadow_buffer_bias = 0.001
            light_data.use_contact_shadow = True
            light_data.contact_shadow_distance = 0.3
            light_data.contact_shadow_bias = 0.001

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
                light_obj.rotation_euler = (math.radians(90), 0, math.radians(-90))

            objects.append(light_obj)

    return objects
