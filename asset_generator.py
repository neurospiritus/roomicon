import bpy
import os
import sys
import importlib
import random
from bpy.props import StringProperty, IntProperty, EnumProperty, BoolProperty
from core.asset_loader import wrap_as_asset

# Path to generators
_addon_dir = os.path.dirname(os.path.realpath(__file__))
_generators_dir = os.path.join(_addon_dir, "tools", "generators")

if _generators_dir not in sys.path:
    sys.path.insert(0, _generators_dir)

# Global generator cache
_generators = {}
_generator_items = []


def _load_generators():
    """Discover and load all generators."""
    global _generators, _generator_items

    _generators = {}
    _generator_items = []

    # Collect local module names from all generators automatically,
    # to clear sys.modules and avoid conflicts between generators
    _shared_module_names = set()
    for _name in os.listdir(_generators_dir):
        _gdir = os.path.join(_generators_dir, _name)
        if os.path.isdir(_gdir) and _name != 'common':
            for _f in os.listdir(_gdir):
                if _f.endswith('.py') and _f != '__init__.py':
                    _shared_module_names.add(_f[:-3])

    for name in sorted(os.listdir(_generators_dir)):
        gen_dir = os.path.join(_generators_dir, name)
        init_file = os.path.join(gen_dir, '__init__.py')
        if name == 'common' or not (os.path.isdir(gen_dir) and os.path.isfile(init_file)):
            continue

        # Clear cached modules so each generator
        # loads its own helpers/etc from its own directory
        for mod_key in list(sys.modules.keys()):
            base = mod_key.split('.')[0]
            if base in _shared_module_names:
                del sys.modules[mod_key]

        # Put generator directory at the beginning of path
        if gen_dir in sys.path:
            sys.path.remove(gen_dir)
        sys.path.insert(0, gen_dir)

        try:
            # Remove the generator module itself from cache
            if name in sys.modules:
                del sys.modules[name]

            mod = importlib.import_module(name)

            if hasattr(mod, 'GENERATOR_INFO') and hasattr(mod, 'generate_single'):
                _generators[name] = mod
                info = mod.GENERATOR_INFO
                _generator_items.append((name, info['name'], info.get('description', '')))
        except Exception as e:
            print(f"Asset Generator: failed to load '{name}': {e}")
            import traceback
            traceback.print_exc()

    if not _generator_items:
        _generator_items = [('NONE', 'No generators found', '')]


def _get_generator_items(self, context):
    if not _generator_items:
        _load_generators()
    return _generator_items


def _get_type_items(self, context):
    """Return items for type, based on selected generator."""
    gen_name = context.scene.asset_gen.generator
    mod = _generators.get(gen_name)
    if not mod or 'obj_type' not in mod.PARAMS:
        return [('mixed', 'Mixed', '')]

    items = mod.PARAMS['obj_type']['items']
    return [(i, i.replace('_', ' ').title(), '') for i in items]


def _get_subtype_items(self, context):
    """Return items for subtype, filtering by current obj_type."""
    gen_name = context.scene.asset_gen.generator
    mod = _generators.get(gen_name)
    if not mod or 'subtype' not in mod.PARAMS:
        return [('mixed', 'Mixed', '')]

    # If generator has SUBTYPES, filter by current obj_type
    if hasattr(mod, 'SUBTYPES'):
        obj_type = context.scene.asset_gen.obj_type
        if obj_type in mod.SUBTYPES:
            items = ['mixed'] + mod.SUBTYPES[obj_type]
            return [(i, i.replace('_', ' ').title(), '') for i in items]
        # For 'mixed' obj_type, show all subtypes
        all_items = set()
        for subtypes in mod.SUBTYPES.values():
            all_items.update(subtypes)
        items = ['mixed'] + sorted(all_items)
        return [(i, i.replace('_', ' ').title(), '') for i in items]

    items = mod.PARAMS['subtype']['items']
    return [(i, i.replace('_', ' ').title(), '') for i in items]


# ============================================================
# Properties
# ============================================================

def _on_generator_changed(self, context):
    """Reset obj_type and subtype when generator changes."""
    try:
        self['obj_type'] = 0
    except Exception:
        pass
    try:
        self['subtype'] = 0
    except Exception:
        pass


def _on_type_changed(self, context):
    """Reset subtype when obj_type changes."""
    try:
        self['subtype'] = 0
    except Exception:
        pass


class AssetGenProperties(bpy.types.PropertyGroup):
    generator: EnumProperty(
        name="Generator",
        items=_get_generator_items,
        description="Select asset generator",
        update=_on_generator_changed,
    )
    obj_type: EnumProperty(
        name="Type",
        items=_get_type_items,
        description="Object type",
        update=_on_type_changed,
    )
    subtype: EnumProperty(
        name="Subtype",
        items=_get_subtype_items,
        description="Object subtype",
    )
    seed: IntProperty(
        name="Seed",
        default=0,
        min=0,
        max=99999,
    )
    clear_before: BoolProperty(
        name="Clear Before",
        default=False,
        description="Clear scene before generating",
    )


# ============================================================
# Operators
# ============================================================

class ASSETGEN_OT_generate(bpy.types.Operator):
    """Generate one asset"""
    bl_idname = "assetgen.generate"
    bl_label = "Generate"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.asset_gen
        mod = _generators.get(props.generator)
        if not mod:
            self.report({'ERROR'}, f"Generator '{props.generator}' not found")
            return {'CANCELLED'}

        if props.clear_before:
            bpy.ops.assetgen.clear()

        # Collect kwargs
        kwargs = {
            'seed': props.seed,
            'obj_type': props.obj_type,
        }
        if hasattr(mod, 'PARAMS') and 'subtype' in mod.PARAMS:
            kwargs['subtype'] = props.subtype

        try:
            objects = mod.generate_single(**kwargs)
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        if not objects:
            self.report({'WARNING'}, "No objects generated")
            return {'CANCELLED'}

        # Wrap in Empty root (same as procedural/asset modes)
        name = f"{props.generator}_{props.obj_type}_{props.seed}"
        root = wrap_as_asset(objects, name)
        root['assetgen'] = True

        # Link root to scene collection
        if root.name not in [o.name for o in context.collection.objects]:
            context.collection.objects.link(root)
        for child in root.children_recursive:
            if child.name not in [o.name for o in context.collection.objects]:
                context.collection.objects.link(child)

        # Select generated objects
        bpy.ops.object.select_all(action='DESELECT')
        root.select_set(True)
        for child in root.children_recursive:
            child.select_set(True)
        context.view_layer.objects.active = root

        info = mod.GENERATOR_INFO
        self.report({'INFO'}, f"{info['name']}: {props.obj_type} (seed={props.seed})")
        return {'FINISHED'}


class ASSETGEN_OT_randomize(bpy.types.Operator):
    """Generate with new random seed"""
    bl_idname = "assetgen.randomize"
    bl_label = "Randomize"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.asset_gen
        props.seed = random.randint(0, 99999)
        return bpy.ops.assetgen.generate()


class ASSETGEN_OT_clear(bpy.types.Operator):
    """Clear all objects from scene"""
    bl_idname = "assetgen.clear"
    bl_label = "Clear"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Collect all objects to remove (roots + their children)
        to_remove = set()
        for obj in bpy.data.objects:
            if obj.get('assetgen'):
                to_remove.add(obj)
                for child in obj.children_recursive:
                    to_remove.add(child)
        removed = 0
        for obj in list(to_remove):
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
                removed += 1
            except ReferenceError:
                pass
        # Clean up orphaned data
        for mesh in list(bpy.data.meshes):
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for mat in list(bpy.data.materials):
            if mat.users == 0:
                bpy.data.materials.remove(mat)
        self.report({'INFO'}, f"Cleared {removed} generated objects")
        return {'FINISHED'}


class ASSETGEN_OT_reload(bpy.types.Operator):
    """Reload all generators"""
    bl_idname = "assetgen.reload"
    bl_label = "Reload Generators"

    def execute(self, context):
        _load_generators()
        self.report({'INFO'}, f"Loaded {len(_generators)} generators")
        return {'FINISHED'}


# ============================================================
# UI Panel
# ============================================================

class ASSETGEN_PT_main(bpy.types.Panel):
    bl_label = "Asset Generator"
    bl_idname = "ASSETGEN_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Roomicon Assets"

    def draw(self, context):
        layout = self.layout
        props = context.scene.asset_gen

        # Generator selection
        box = layout.box()
        row = box.row(align=True)
        row.prop(props, "generator", text="")
        row.operator("assetgen.reload", text="", icon='FILE_REFRESH')

        # Description
        mod = _generators.get(props.generator)
        if mod:
            info = mod.GENERATOR_INFO
            box.label(text=info.get('description', ''), icon='INFO')

        # Parameters
        box = layout.box()
        box.label(text="Parameters")

        if mod and 'obj_type' in mod.PARAMS:
            box.prop(props, "obj_type")

        if mod and 'subtype' in mod.PARAMS:
            box.prop(props, "subtype")

        box.prop(props, "seed")

        # Options
        box = layout.box()
        box.prop(props, "clear_before")

        # Buttons
        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("assetgen.generate", icon='ADD')

        row = layout.row(align=True)
        row.operator("assetgen.randomize", icon='FILE_REFRESH')
        row.operator("assetgen.clear", icon='TRASH')


# ============================================================
# Registration
# ============================================================

classes = (
    AssetGenProperties,
    ASSETGEN_OT_generate,
    ASSETGEN_OT_randomize,
    ASSETGEN_OT_clear,
    ASSETGEN_OT_reload,
    ASSETGEN_PT_main,
)


def register():
    _load_generators()
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.asset_gen = bpy.props.PointerProperty(type=AssetGenProperties)


def unregister():
    del bpy.types.Scene.asset_gen
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
