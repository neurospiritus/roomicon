"""Asset loading and creation: Empty-root with children and metadata."""

import bpy
import os
import random

_addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
FURNITURE_DIR = os.path.join(_addon_dir, "assets", "furniture")
DECOR_DIR = os.path.join(_addon_dir, "assets", "decor")

# Asset root object marker
_ASSET_ROOT_KEY = '_asset_root'
# Metadata keys stored on root
METADATA_KEYS = ('mattress_z', 'shelf_surfaces', 'surface_z', 'table_size')


# ============================================================
# Asset creation (single entry point for procedural and save/load)
# ============================================================

def wrap_as_asset(objects, name, metadata=None):
    """Wrap a list of objects into an asset with an Empty root.

    objects: list of Blender objects from a generator
    name: asset name (will be the Empty's name)
    metadata: dict of extra properties (surface_z, mattress_z, etc.)
              If None, collects from objects[0]

    Returns root Empty (or the single object if there's only one with no children).
    Root is marked _asset_root=True and contains all metadata.
    """
    if not objects:
        return None

    # Collect metadata from objects[0] if not provided explicitly
    if metadata is None:
        metadata = {}
        if objects[0]:
            for key in METADATA_KEYS:
                val = objects[0].get(key)
                if val is not None:
                    metadata[key] = val

    roots = [o for o in objects if o.parent is None]

    if len(roots) == 1 and len(objects) == 1:
        # Single object — it is the root
        obj = roots[0]
        obj.name = name
        obj[_ASSET_ROOT_KEY] = True
        for k, v in metadata.items():
            obj[k] = v
        return obj

    # Multiple objects — create an Empty (clickable in viewport)
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = 'CUBE'
    empty[_ASSET_ROOT_KEY] = True
    empty['_children'] = True

    # Link all objects to scene (required for parenting)
    for o in objects:
        if o.name not in [x.name for x in bpy.context.scene.collection.objects]:
            bpy.context.scene.collection.objects.link(o)

    # Parent only top-level objects, preserving internal hierarchy
    for o in roots:
        o.parent = empty

    # Adaptive Empty size based on children bounding box
    max_dim = 0
    for o in objects:
        if hasattr(o, 'dimensions'):
            max_dim = max(max_dim, o.dimensions.x, o.dimensions.y, o.dimensions.z)
    empty.empty_display_size = max(0.05, max_dim * 0.3)

    # Metadata on root
    for k, v in metadata.items():
        empty[k] = v

    return empty


def is_asset_root(obj):
    """Check if the object is an asset root."""
    return obj.get(_ASSET_ROOT_KEY, False)


# ============================================================
# Loading from .blend
# ============================================================

def _list_blend_files(directory):
    if not os.path.isdir(directory):
        return []
    return [f for f in os.listdir(directory) if f.endswith('.blend')]


def _blend_basename(blend_path):
    return os.path.splitext(os.path.basename(blend_path))[0]


def load_all_objects_from_blend(blend_path):
    """Load ALL objects from a .blend file (append)."""
    if not os.path.isfile(blend_path):
        return []
    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)
    return [obj for obj in data_to.objects if obj is not None]


def load_asset(blend_path, name=None):
    """Load an asset from .blend. Finds existing root or creates a new one.

    Returns root object or None.
    """
    objects = load_all_objects_from_blend(blend_path)
    if not objects:
        return None

    asset_name = name or _blend_basename(blend_path)

    # Look for existing root (marked with _asset_root)
    existing_root = None
    for obj in objects:
        if obj.get(_ASSET_ROOT_KEY):
            existing_root = obj
            break

    if existing_root:
        existing_root.name = asset_name
        return existing_root

    # No root — wrap it (legacy .blend without root)
    return wrap_as_asset(objects, asset_name)


# ============================================================
# Linking to collection
# ============================================================

def link_group_to_collection(obj, collection):
    """Add object (and all children recursively) to collection."""
    def _link_recursive(o):
        for c in o.users_collection:
            c.objects.unlink(o)
        collection.objects.link(o)
        for child in o.children:
            _link_recursive(child)
    _link_recursive(obj)


# ============================================================
# Public API
# ============================================================

def load_furniture(furniture_type, name=None, seed=None):
    """Load furniture by type from assets/furniture/."""
    blends = [f for f in _list_blend_files(FURNITURE_DIR)
              if f.startswith(furniture_type + '_') or f == f"{furniture_type}.blend"]
    if not blends:
        return None
    rng = random.Random(seed) if seed is not None else random
    chosen = rng.choice(blends)
    return load_asset(os.path.join(FURNITURE_DIR, chosen), name=name)


def load_random_decor(category, name=None, seed=None):
    """Load random decor from a subcategory."""
    cat_dir = os.path.join(DECOR_DIR, category)
    blends = _list_blend_files(cat_dir)
    if not blends:
        return None
    rng = random.Random(seed) if seed is not None else random
    chosen = rng.choice(blends)
    file_name = _blend_basename(os.path.join(cat_dir, chosen))
    return load_asset(os.path.join(cat_dir, chosen), name=name or file_name)


def list_decor_assets(category):
    cat_dir = os.path.join(DECOR_DIR, category)
    return [f[:-6] for f in _list_blend_files(cat_dir)]
