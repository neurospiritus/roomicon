bl_info = {
    "name": "Roomicon",
    "author": "NeuroSpiritus",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Roomicon",
    "description": "Generates interior rooms with furniture and materials",
    "category": "3D View",
}

import bpy
import math
import os
import sys
import random
import importlib
from bpy.props import FloatProperty, IntProperty, EnumProperty, BoolProperty

# Add addon directory to sys.path for lib/ imports
_addon_dir = os.path.dirname(os.path.realpath(__file__))
if _addon_dir not in sys.path:
    sys.path.insert(0, _addon_dir)

# Reload for development convenience (reload addon without restarting Blender)
_reload_modules = [
    'materials.room_materials', 'materials.furniture_materials', 'materials',
    'core.openings',
    'core.room_geometry',
    'core.camera_lighting',
    'core.placement',
    'core.asset_loader',
    'core.material_loader',
    'core.procedural',
    'core.scene_builder',
    'core.post_placement',
    'asset_generator',
]
for _mod in _reload_modules:
    if _mod in sys.modules:
        importlib.reload(sys.modules[_mod])

import asset_generator

from materials import assign_room_materials
from materials.furniture_materials import create_window_frame_material
from materials.anime_materials import setup_anime_render, setup_realistic_render, convert_scene_to_anime
from core.openings import create_window_frame
from core.room_geometry import (
    WALL_DEFS, create_floor, create_ceiling,
    create_wall_with_openings, make_window_openings, make_door_opening,
    create_baseboards, get_wall_interior,
)
from core.camera_lighting import setup_camera, setup_lighting, setup_lighting_anime
from core.scene_builder import place_objects
from core.post_placement import place_cushions_on_beds, place_books_on_shelves, place_curtains
from core.openings import create_door_assembly


COLLECTION_NAME = "Room"





WALL_TYPE_ITEMS = [
    ('NONE', "None", "Empty wall"),
    ('DOOR', "Door", "Wall with door"),
    ('WINDOWS', "Windows", "Wall with windows"),
]

ROOM_SIZE_ITEMS = [
    ('SMALL',   "Small",   "6–12 m²"),
    ('MEDIUM',  "Medium",  "12–22 m²"),
    ('LARGE',   "Large",   "22–35 m²"),
    ('XLARGE',  "XLarge",  "35–50 m²"),
]

# Area ranges and max aspect ratio for each preset
ROOM_SIZE_RANGES = {
    'SMALL':  (6, 12, 2.5),
    'MEDIUM': (12, 22, 2.0),
    'LARGE':  (22, 35, 1.8),
    'XLARGE': (35, 50, 1.8),
}


# ============================================================
# Utilities
# ============================================================

def get_or_create_collection(name):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def link_to_collection(obj, col):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    col.objects.link(obj)




# ============================================================
# Room generation
# ============================================================

def generate_room(props):
    """Creates a room: floor, ceiling, walls, furniture, camera, lighting."""
    width = props.width
    length = props.length
    height = props.height
    wall_thickness = props.wall_thickness

    # Remove default objects (Light, Camera, Cube)
    for name in ('Light', 'Camera', 'Cube'):
        obj = bpy.data.objects.get(name)
        if obj and obj.name not in (COLLECTION_NAME,):
            bpy.data.objects.remove(obj, do_unlink=True)

    # Render settings
    scene = bpy.context.scene
    style = getattr(props, 'render_style', 'REALISTIC')
    if style == 'ANIME':
        setup_anime_render()
    else:
        setup_realistic_render()
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080

    col = get_or_create_collection(COLLECTION_NAME)

    # --- Floor and ceiling ---
    link_to_collection(create_floor(width, length), col)
    link_to_collection(create_ceiling(width, length, height), col)

    # --- Walls ---
    wall_configs = [
        ("front", props.wall_front_type, props.wall_front_windows),
        ("back",  props.wall_back_type,  props.wall_back_windows),
        ("left",  props.wall_left_type,  props.wall_left_windows),
        ("right", props.wall_right_type, props.wall_right_windows),
    ]

    # Decide curtains early (affects window sill size)
    curtain_rng = random.Random(props.seed + 777)
    has_curtains = curtain_rng.random() <= 0.7

    for i, (side, wtype, win_count) in enumerate(wall_configs):
        wdef_name, is_long, origin_fn, rot_fn = WALL_DEFS[i]
        wall_len = width if is_long else length

        openings = []
        if wtype == 'DOOR':
            openings = [make_door_opening(wall_len, props.door_width, props.door_height)]
        elif wtype == 'WINDOWS':
            openings = make_window_openings(
                wall_len, win_count,
                props.window_width, props.window_height, props.window_sill_height)

        wall = create_wall_with_openings(wdef_name, wall_len, height, wall_thickness, openings)
        wall.location = origin_fn(width, length)
        wall.rotation_euler = rot_fn(width, length)
        link_to_collection(wall, col)

        # Window frames / door
        origin = origin_fn(width, length)
        rot = rot_fn(width, length)

        if wtype == 'WINDOWS':
            frame_mat = create_window_frame_material()
            for j, op in enumerate(openings):
                frame = create_window_frame(f"WindowFrame_{side}_{j}", op, wall_thickness,
                                            props.window_divisions, props.window_crossbar,
                                            wide_sill=not has_curtains,
                                            flip_sill=(side == 'right'))
                frame.location = origin
                frame.rotation_euler = rot
                frame.data.materials.append(frame_mat)
                link_to_collection(frame, col)
        elif wtype == 'DOOR':
            create_door_assembly(col, openings[0], origin, rot, wall_thickness,
                                    lambda obj: link_to_collection(obj, col))

    # --- Baseboards ---
    baseboard = create_baseboards(width, length, wall_thickness, wall_configs, props.door_width)
    link_to_collection(baseboard, col)

    assign_room_materials(col, seed=props.seed)

    # --- Furniture and decor ---
    place_objects(col, props, width, length, height, wall_thickness, wall_configs)

    # --- Cushions on beds and books on shelves (post-generation) ---
    # Cushions, plush toys on beds and books on shelves — always procedural
    place_cushions_on_beds(col, props)
    place_books_on_shelves(col, props)

    # --- Curtains ---
    if has_curtains:
        place_curtains(col, curtain_rng, wall_configs, width, length, height, wall_thickness, props)

    # --- Camera and lighting ---
    cam = setup_camera(width, length, height, wall_thickness)
    link_to_collection(cam, col)
    lighting_fn = setup_lighting_anime if style == 'ANIME' else setup_lighting
    for light_obj in lighting_fn(width, length, height, wall_thickness, wall_configs,
                                  props.window_sill_height, props.window_height):
        link_to_collection(light_obj, col)

    # --- Anime style conversion (after all materials are assigned) ---
    if style == 'ANIME':
        cel = getattr(props, 'cel_shading', 0.5)
        convert_scene_to_anime(col, cel_shading=cel)

    # Apply visibility settings
    _apply_visibility(props)

    return col






# ============================================================
# Visibility
# ============================================================

_VISIBILITY_MAP = {
    'show_ceiling': 'Ceiling',
    'show_wall_front': 'Wall_Front',
    'show_wall_back': 'Wall_Back',
    'show_wall_left': 'Wall_Left',
    'show_wall_right': 'Wall_Right',
}


def _apply_visibility(props):
    if COLLECTION_NAME not in bpy.data.collections:
        return
    col = bpy.data.collections[COLLECTION_NAME]
    for prop_name, obj_name in _VISIBILITY_MAP.items():
        visible = getattr(props, prop_name)
        for obj in col.objects:
            if obj.name.startswith(obj_name):
                obj.hide_set(not visible)
                obj.hide_render = False


def _update_visibility(context):
    _apply_visibility(context.scene.room_gen)


# ============================================================
# Operators
# ============================================================

class ROOM_OT_generate(bpy.types.Operator):
    """Generate a room"""
    bl_idname = "room.generate"
    bl_label = "Generate Room"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.room_gen

        door_count = sum(1 for w in [props.wall_front_type, props.wall_back_type,
                                      props.wall_left_type, props.wall_right_type]
                         if w == 'DOOR')
        if door_count != 1:
            self.report({'ERROR'}, "Exactly one wall must have a door")
            return {'CANCELLED'}

        bpy.ops.room.clear()
        generate_room(props)
        self.report({'INFO'}, "Room generated")
        return {'FINISHED'}


class ROOM_OT_clear(bpy.types.Operator):
    """Clear generated room"""
    bl_idname = "room.clear"
    bl_label = "Clear Room"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if COLLECTION_NAME in bpy.data.collections:
            col = bpy.data.collections[COLLECTION_NAME]
            for obj in list(col.objects):
                data = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if data and data.users == 0:
                    if isinstance(data, bpy.types.Mesh):
                        bpy.data.meshes.remove(data)
                    elif isinstance(data, bpy.types.Camera):
                        bpy.data.cameras.remove(data)
                    elif isinstance(data, bpy.types.Light):
                        bpy.data.lights.remove(data)
            bpy.data.collections.remove(col)

        # Remove orphaned objects (children not in Room collection)
        for obj in list(bpy.data.objects):
            if not obj.users_collection and not obj.parent:
                bpy.data.objects.remove(obj, do_unlink=True)
        # Clean up orphaned meshes
        for mesh in list(bpy.data.meshes):
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)

        self.report({'INFO'}, "Room cleared")
        return {'FINISHED'}


class ROOM_OT_randomize(bpy.types.Operator):
    """Generate room with random parameters"""
    bl_idname = "room.randomize"
    bl_label = "Randomize"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import random as _rnd
        props = context.scene.room_gen

        props.seed = _rnd.randint(0, 99999)
        rng = _rnd.Random(props.seed)

        # Dimensions from area preset
        area_min, area_max, max_ratio = ROOM_SIZE_RANGES[props.room_size]
        target_area = rng.uniform(area_min, area_max)
        # Random aspect ratio (1.0 .. max_ratio)
        ratio = rng.uniform(1.0, max_ratio)
        # width >= length, area = width * length, width = length * ratio
        import math as _math
        length_val = _math.sqrt(target_area / ratio)
        width_val = length_val * ratio
        props.width = round(width_val, 1)
        props.length = round(length_val, 1)
        props.height = round(rng.uniform(2.5, 3.2), 1)
        # density is not randomized — controlled by user

        # Windows
        props.window_width = round(rng.uniform(0.8, 1.4), 1)
        props.window_height = round(rng.uniform(1.0, 1.5), 1)
        props.window_sill_height = round(rng.uniform(0.6, 1.0), 1)

        # Door
        props.door_width = round(rng.uniform(0.7, 1.0), 1)
        props.door_height = round(rng.uniform(2.0, 2.3), 1)

        # Validation: how many windows fit on a wall
        def max_windows(wall_len):
            usable = wall_len - 0.6
            if usable <= props.window_width:
                return 1 if usable > 0 else 0
            return min(4, max(1, int(usable / (props.window_width + 0.3))))

        # Window limits by room size (min, max)
        total_min, total_max = {
            'SMALL': (1, 2), 'MEDIUM': (2, 3), 'LARGE': (3, 5), 'XLARGE': (4, 6),
        }.get(props.room_size, (2, 4))

        # Walls — back always has windows
        props.wall_left_type = 'DOOR'
        props.wall_back_type = 'WINDOWS'
        props.wall_back_windows = rng.randint(1, max_windows(props.width))
        total = props.wall_back_windows

        # front and right — add if needed for minimum or by chance
        props.wall_front_type = 'NONE'
        props.wall_front_windows = 0
        need_more = total < total_min
        if (need_more or rng.random() < 0.5) and total < total_max:
            props.wall_front_type = 'WINDOWS'
            remaining = min(max_windows(props.width), total_max - total)
            needed = max(1, total_min - total) if need_more else 1
            props.wall_front_windows = rng.randint(needed, remaining)
            total += props.wall_front_windows

        props.wall_right_type = 'NONE'
        props.wall_right_windows = 0
        need_more = total < total_min
        if (need_more or rng.random() < 0.3) and total < total_max:
            props.wall_right_type = 'WINDOWS'
            remaining = min(max_windows(props.length), total_max - total)
            needed = max(1, total_min - total) if need_more else 1
            props.wall_right_windows = rng.randint(needed, remaining)
            total += props.wall_right_windows

        # Height validation
        max_sill = props.height - props.window_height - 0.2
        if props.window_sill_height > max_sill:
            props.window_sill_height = round(max(0.3, max_sill), 1)
        if props.door_height > props.height - 0.2:
            props.door_height = round(props.height - 0.3, 1)

        bpy.ops.room.clear()
        generate_room(props)
        self.report({'INFO'}, f"Randomized (seed={props.seed})")
        return {'FINISHED'}


# ============================================================
# Properties
# ============================================================

class RoomGenProperties(bpy.types.PropertyGroup):
    # Dimensions
    room_size: EnumProperty(name="Size Preset", items=ROOM_SIZE_ITEMS, default='MEDIUM',
                             description="Room size preset for Randomize")
    width: FloatProperty(name="Width", default=5.0, min=2.0, max=20.0, unit='LENGTH',
                          description="Room width (Front/Back walls)")
    length: FloatProperty(name="Length", default=4.0, min=2.0, max=20.0, unit='LENGTH',
                           description="Room length (Left/Right walls)")
    height: FloatProperty(name="Height", default=2.7, min=2.0, max=3.5, unit='LENGTH')
    wall_thickness: FloatProperty(name="Wall Thickness", default=0.15, options={'HIDDEN'})

    # Generation
    render_style: EnumProperty(
        name="Style",
        items=[
            ('REALISTIC', 'Realistic', 'Cycles with PBR materials and natural lighting'),
            ('ANIME', 'Anime', 'EEVEE with cel-shading, outlines, and flat lighting'),
        ],
        default='REALISTIC',
        description="Visual style for materials, lighting, and render engine",
    )
    cel_shading: FloatProperty(
        name="Cel Shading",
        default=0.5, min=0.0, max=1.0, subtype='FACTOR',
        description="Cel-shading contrast: 0=soft gradients, 1=hard flat colors",
    )
    density: FloatProperty(name="Density", default=0.5, min=0.0, max=1.0, subtype='FACTOR')
    seed: IntProperty(name="Seed", default=0, min=0)
    procedural: BoolProperty(name="Procedural", default=True,
                              description="Generate furniture/decor on the fly instead of loading .blend assets")

    # Door
    door_width: FloatProperty(name="Door Width", default=0.9, min=0.6, max=1.5, unit='LENGTH')
    door_height: FloatProperty(name="Door Height", default=2.1, min=1.8, max=2.5, unit='LENGTH')

    # Windows
    window_width: FloatProperty(name="Window Width", default=1.2, min=0.4, max=2.5, unit='LENGTH')
    window_height: FloatProperty(name="Window Height", default=1.4, min=0.4, max=2.0, unit='LENGTH')
    window_sill_height: FloatProperty(name="Sill Height", default=0.8, min=0.3, max=1.5, unit='LENGTH')
    window_divisions: IntProperty(name="Divisions", default=2, min=1, max=3,
                                   description="Number of panes (1=no vertical bars, 2=one, 3=two)")
    window_crossbar: FloatProperty(name="Crossbar", default=0.7, min=0.5, max=0.95, subtype='FACTOR',
                                    description="Horizontal bar position (0.5=50%, 0.7=70% height)")

    # Walls
    wall_front_type: EnumProperty(name="Front", items=WALL_TYPE_ITEMS, default='NONE')
    wall_front_windows: IntProperty(name="Windows", default=0, min=0, max=4)
    wall_back_type: EnumProperty(name="Back", items=WALL_TYPE_ITEMS, default='WINDOWS')
    wall_back_windows: IntProperty(name="Windows", default=2, min=0, max=4)
    wall_left_type: EnumProperty(name="Left", items=WALL_TYPE_ITEMS, default='DOOR')
    wall_left_windows: IntProperty(name="Windows", default=0, min=0, max=4)
    wall_right_type: EnumProperty(name="Right", items=WALL_TYPE_ITEMS, default='NONE')
    wall_right_windows: IntProperty(name="Windows", default=0, min=0, max=4)

    # Visibility
    show_ceiling: BoolProperty(name="Ceiling", default=False, update=lambda s, c: _update_visibility(c))
    show_wall_front: BoolProperty(name="Front Wall", default=True, update=lambda s, c: _update_visibility(c))
    show_wall_back: BoolProperty(name="Back Wall", default=True, update=lambda s, c: _update_visibility(c))
    show_wall_left: BoolProperty(name="Left Wall", default=True, update=lambda s, c: _update_visibility(c))
    show_wall_right: BoolProperty(name="Right Wall", default=True, update=lambda s, c: _update_visibility(c))


# ============================================================
# UI Panel
# ============================================================

def _draw_wall_row(layout, props, label, type_prop, windows_prop, vis_prop):
    row = layout.row(align=True)
    icon = 'HIDE_OFF' if getattr(props, vis_prop) else 'HIDE_ON'
    row.prop(props, vis_prop, text="", icon=icon, emboss=False)
    row.label(text=label)
    row.prop(props, type_prop, text="")
    if getattr(props, type_prop) == 'WINDOWS':
        row.prop(props, windows_prop, text="")


_PANEL_COMMON = dict(bl_space_type='VIEW_3D', bl_region_type='UI', bl_category="Roomicon")


class ROOM_PT_main(bpy.types.Panel):
    bl_label = "Roomicon"
    bl_idname = "ROOM_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Roomicon"

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("room.generate", icon='MESH_CUBE')

        row = layout.row(align=True)
        row.operator("room.randomize", icon='FILE_REFRESH')
        row.operator("room.clear", icon='TRASH')


class ROOM_PT_size(bpy.types.Panel):
    bl_label = "Room Size"
    bl_idname = "ROOM_PT_size"
    bl_parent_id = "ROOM_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Roomicon"

    def draw(self, context):
        props = context.scene.room_gen
        layout = self.layout
        layout.prop(props, "room_size")
        layout.prop(props, "width")
        layout.prop(props, "length")
        layout.prop(props, "height")
        area = props.width * props.length
        row = layout.row()
        row.label(text=f"Area: {area:.1f} m²")
        row.enabled = False


class ROOM_PT_visibility(bpy.types.Panel):
    bl_label = "Visibility"
    bl_idname = "ROOM_PT_visibility"
    bl_parent_id = "ROOM_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Roomicon"

    def draw(self, context):
        props = context.scene.room_gen
        row = self.layout.row(align=True)
        icon = 'HIDE_OFF' if props.show_ceiling else 'HIDE_ON'
        row.prop(props, "show_ceiling", text="Ceiling", icon=icon, toggle=True)


class ROOM_PT_walls(bpy.types.Panel):
    bl_label = "Walls"
    bl_idname = "ROOM_PT_walls"
    bl_parent_id = "ROOM_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Roomicon"

    def draw(self, context):
        props = context.scene.room_gen
        layout = self.layout
        _draw_wall_row(layout, props, "Front", "wall_front_type", "wall_front_windows", "show_wall_front")
        _draw_wall_row(layout, props, "Back",  "wall_back_type",  "wall_back_windows",  "show_wall_back")
        _draw_wall_row(layout, props, "Left",  "wall_left_type",  "wall_left_windows",  "show_wall_left")
        _draw_wall_row(layout, props, "Right", "wall_right_type", "wall_right_windows", "show_wall_right")


class ROOM_PT_door(bpy.types.Panel):
    bl_label = "Door"
    bl_idname = "ROOM_PT_door"
    bl_parent_id = "ROOM_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Roomicon"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        props = context.scene.room_gen
        return any(getattr(props, f"wall_{s}_type") == 'DOOR'
                   for s in ('front', 'back', 'left', 'right'))

    def draw(self, context):
        props = context.scene.room_gen
        layout = self.layout
        layout.prop(props, "door_width")
        layout.prop(props, "door_height")


class ROOM_PT_windows(bpy.types.Panel):
    bl_label = "Windows"
    bl_idname = "ROOM_PT_windows"
    bl_parent_id = "ROOM_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Roomicon"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        props = context.scene.room_gen
        return any(getattr(props, f"wall_{s}_type") == 'WINDOWS'
                   for s in ('front', 'back', 'left', 'right'))

    def draw(self, context):
        props = context.scene.room_gen
        layout = self.layout
        layout.prop(props, "window_width")
        layout.prop(props, "window_height")
        layout.prop(props, "window_sill_height")
        layout.prop(props, "window_divisions")
        layout.prop(props, "window_crossbar")


class ROOM_PT_generation(bpy.types.Panel):
    bl_label = "Generation"
    bl_idname = "ROOM_PT_generation"
    bl_parent_id = "ROOM_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Roomicon"

    def draw(self, context):
        props = context.scene.room_gen
        layout = self.layout
        layout.prop(props, "render_style")
        if props.render_style == 'ANIME':
            layout.prop(props, "cel_shading")
        layout.prop(props, "density")
        layout.prop(props, "seed")
        layout.prop(props, "procedural")


# ============================================================
# Registration
# ============================================================

classes = (
    RoomGenProperties,
    ROOM_OT_generate,
    ROOM_OT_clear,
    ROOM_OT_randomize,
    ROOM_PT_main,
    ROOM_PT_size,
    ROOM_PT_visibility,
    ROOM_PT_walls,
    ROOM_PT_door,
    ROOM_PT_windows,
    ROOM_PT_generation,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.room_gen = bpy.props.PointerProperty(type=RoomGenProperties)
    asset_generator.register()


def unregister():
    asset_generator.unregister()
    del bpy.types.Scene.room_gen
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
