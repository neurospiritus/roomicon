# Roomicon — Blender Interior Generator

🇷🇺 [Русская версия](README_RU.md)

A Blender 4.0 add-on that procedurally generates interior rooms: geometry, furniture, decor, and materials.

Generate complete room interiors in one click — use as a starting point for architectural visualization, quickly produce backgrounds for visual novels or animations, or automate the routine part of interior modeling and focus on creative details.

![Room Generator UI](docs/images/s1_blender.png)
![Asset Generator UI](docs/images/s2_blender.png)
![Render Example 1](docs/images/s3_render.png)
![Render Example 2](docs/images/s4_render.png)
![Batch Gallery](docs/images/s5_gallery.png)

## Features

- Rectangular room with customizable dimensions (width, length, height)
- Window frames (configurable: divisions, crossbar height)
- Procedural materials for floors (parquet, tile, laminate), walls (plaster, paint, wallpaper), doors, baseboards — optionally bakeable to .blend
- Furniture: tables (8 types), chairs (6 types), beds & sofas (6 types), wardrobes, nightstands, dressers
- Decor: kitchenware, lamps, clocks, shelves, paintings, photo frames, rugs, cushions, curtains, mirrors, books, plants, candles, plush toys
- **Procedural** mode — generates furniture and decor on-the-fly (no pre-built .blend files needed)
- Chairs automatically placed around tables
- Curtains on windows, rugs on floor, cushions & plush toys on beds, books on shelves — all automatic
- Paintings, photo frames, and rugs use procedural patterns by default; optionally drop your own images into `assets/pool/pictures/`, `assets/pool/photoframes/`, or `assets/pool/rugs/`
- Collision-aware placement respecting room boundaries and existing objects
- Room size presets: Small / Medium / Large / XLarge for **Randomize**
- **Density** and **Seed** parameters for controlling fill level and reproducibility
- Visibility toggles for ceiling and each wall

## Installation

1. Download the .zip from [Releases](https://github.com/neurospiritus/roomicon/releases) and install via **Edit > Preferences > Add-ons > Install**, or clone the repository and copy the `roomicon/` folder to Blender's add-ons directory.

2. Enable the **Roomicon** add-on in the list.

3. (Optional) Pre-generate .blend assets:
   ```
   blender --background --python tools/generate_assets.py
   blender --background --python tools/generate_materials.py
   ```
   Without this step, the plugin uses procedural generation (fallback).

## Usage

1. Open the sidebar (N) in 3D Viewport
2. Switch to the **Roomicon** tab
3. Configure parameters (collapsible sections):
   - **Room Size** — preset (Small/Medium/Large/XLarge), width, length, height, area
   - **Visibility** — show/hide ceiling
   - **Walls** — wall type (None / Door / Windows), window count, visibility (eye icon)
   - **Door** ▸ — door width and height (collapsed by default)
   - **Windows** ▸ — width, height, sill height, divisions, crossbar (collapsed by default)
   - **Generation** — density and seed
4. Click **Generate Room**
5. **Randomize** — random parameters from the size preset + generate
6. **Clear Room** — remove everything generated

## Batch Generation

Generate multiple room variations in headless mode with rendering and HTML gallery:

```bash
# 10 variants with random seeds
blender --background --python tools/batch_generate.py -- --count 10

# Large rooms only
blender --background --python tools/batch_generate.py -- --count 10 --room-size LARGE

# Custom seed range and resolution
blender --background --python tools/batch_generate.py -- --count 20 --seed-start 100 --resolution 2560x1440

# Full list of options
blender --background --python tools/batch_generate.py -- --help
```

Output in `output/` folder: PNG renders, .blend files, `index.html` gallery.

## Asset Generation

### Bulk generation (all types)

```bash
# Default: 5 variants per type
blender --background --python tools/generate_assets.py

# Only tables, 20 variants
blender --background --python tools/generate_assets.py -- --type table --count 20
```

Assets are saved to `assets/furniture/` and `assets/decor/<category>/`.

### Individual generators (with preview)

Each generator has its own script with render previews and HTML gallery:

```bash
# Tables: 10 variants with preview renders
blender --background --python tools/generators/tables/generate.py -- --count 10

# Chairs: only armchairs
blender --background --python tools/generators/chairs/generate.py -- --type armchair --count 5

# Lamps: save as .blend assets
blender --background --python tools/generators/lamps/generate.py -- --count 10 --save-blend

# Any generator supports: --type, --count, --seed, --output, --resolution, --save-blend
```

Output: `output/<generator>/` with PNG renders and `index.html` gallery.

### Editing assets

You can open generated .blend files in Blender, edit them, and the room generator will use your curated set. Important rules:

- **Keep the Empty root object.** Each asset has an Empty parent (marked `_asset_root`) that stores metadata (`surface_z`, `table_size`, `mattress_z`, etc.). Don't delete it.
- **Keep the hierarchy.** Child objects must remain parented to the root Empty. You can add/remove/modify children, but don't break the parent chain.
- **Don't rename the root** to a different type prefix. The loader matches files by name prefix (e.g. `table_*.blend`).
- **Custom properties matter.** If you modify a table's height, update `surface_z` on the root Empty. If you change bed mattress height, update `mattress_z`. These values control where decor is placed on the surface.
- **Origin = base center.** Objects should have their origin at the center of the base (floor level). The placement system uses this as the reference point.
- **Face direction = +Y.** Furniture faces forward along +Y. Wall furniture has its back along +Y (against the wall).

### Asset mode vs Procedural mode

- **Procedural** (default): all objects generated on-the-fly from 20 built-in generators. Infinite variety via seed. No .blend files needed.
- **Asset**: objects loaded from `assets/` .blend files. You control exactly which objects appear. Generate a set, curate it, then use for consistent results.

The project is self-contained — all .blend assets are generated by the included tools, not downloaded from external sources. Both modes use the same placement algorithm.

## Procedural Generators (20)

**Furniture:** Tables (8 types), Chairs (6), Seating & Beds (6), Wardrobes (5 incl. nightstands & dressers)

**Decor:** Kitchenware, Lamps, Clocks, Shelves, Paintings, Photoframes, Rugs, Cushions, Curtains, Mirrors, Booksets, Plants, Candles, Plush Toys

## Requirements

- Blender 4.0+

## Author

[NeuroSpiritus](https://github.com/neurospiritus)

## License

GPL v3 — see [LICENSE](LICENSE)
