"""
Пакетная генерация комнат в headless-режиме.

Использование:
    blender --background --python tools/batch_generate.py -- [опции]

Опции (после --):
    --count N           Количество вариантов (по умолчанию 10)
    --output DIR        Папка для результатов (по умолчанию ./output)
    --seed-start N      Начальный seed (по умолчанию случайный)
    --resolution WxH    Разрешение рендера (по умолчанию 1920x1080)
    --room-size SIZE    Пресет площади: SMALL, MEDIUM, LARGE, XLARGE (по умолчанию MEDIUM)

Пример:
    blender --background --python tools/batch_generate.py -- --count 20 --output ./batch_out
    blender --background --python tools/batch_generate.py -- --count 50 --room-size LARGE
"""

import bpy
import os
import sys
import random
import argparse
import time
import math

# Добавляем родителя корня проекта в path, чтобы import по имени папки работал
script_dir = os.path.dirname(os.path.realpath(__file__))
project_dir = os.path.dirname(script_dir)
parent_dir = os.path.dirname(project_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
# Также добавляем сам project_dir для внутренних импортов (core/, materials/ и т.д.)
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

_pkg_name = os.path.basename(project_dir)
_pkg = __import__(_pkg_name)
generate_room = _pkg.generate_room
ROOM_SIZE_RANGES = _pkg.ROOM_SIZE_RANGES
COLLECTION_NAME = _pkg.COLLECTION_NAME


def parse_args():
    argv = sys.argv
    if '--' in argv:
        argv = argv[argv.index('--') + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Batch room generation")
    parser.add_argument('--count', type=int, default=10)
    parser.add_argument('--output', type=str, default='./output')
    parser.add_argument('--seed-start', type=int, default=None)
    parser.add_argument('--resolution', type=str, default='1920x1080')
    parser.add_argument('--room-size', type=str, default='MEDIUM',
                        choices=['SMALL', 'MEDIUM', 'LARGE', 'XLARGE'])
    parser.add_argument('--style', type=str, default='REALISTIC',
                        choices=['REALISTIC', 'ANIME'])
    parser.add_argument('--cel-shading', type=float, default=0.5)
    parser.add_argument('--ambient', type=float, default=1.0,
                        help='Ambient lighting intensity 0.0-2.0 (default 1.0)')
    parser.add_argument('--lamps', type=float, default=0.0,
                        help='Decorative lamp intensity 0.0-2.0 (default 0.0)')
    return parser.parse_args(argv)


class FakeProps:
    """Имитирует RoomGenProperties для generate_room."""
    pass


def randomize_props(seed, room_size='MEDIUM', style='REALISTIC', cel_shading=0.5, **kwargs):
    """Создаёт FakeProps со случайными параметрами (аналог ROOM_OT_randomize)."""
    rng = random.Random(seed)
    p = FakeProps()

    p.seed = seed
    p.room_size = room_size
    p.procedural = True
    p.render_style = style
    p.cel_shading = cel_shading
    p.ambient_intensity = kwargs.get('ambient', 1.0)
    p.lamp_intensity = kwargs.get('lamps', 0.0)

    # Размеры из пресета
    area_min, area_max, max_ratio = ROOM_SIZE_RANGES[room_size]
    target_area = rng.uniform(area_min, area_max)
    ratio = rng.uniform(1.0, max_ratio)
    length_val = math.sqrt(target_area / ratio)
    width_val = length_val * ratio
    p.width = round(width_val, 1)
    p.length = round(length_val, 1)
    p.height = round(rng.uniform(2.5, 3.2), 1)
    p.wall_thickness = round(rng.uniform(0.12, 0.2), 2)
    p.density = round(rng.uniform(0.2, 0.9), 2)

    # Дверь
    p.door_width = round(rng.uniform(0.7, 1.0), 1)
    p.door_height = round(rng.uniform(2.0, 2.3), 1)

    # Окна
    p.window_width = round(rng.uniform(0.8, 1.4), 1)
    p.window_height = round(rng.uniform(1.0, 1.5), 1)
    p.window_sill_height = round(rng.uniform(0.6, 1.0), 1)
    p.window_divisions = rng.randint(1, 3)
    p.window_crossbar = round(rng.uniform(0.5, 0.85), 2)

    # Валидация
    def max_windows(wall_len):
        usable = wall_len - 0.6
        if usable <= p.window_width:
            return 1 if usable > 0 else 0
        return max(1, int(usable / (p.window_width + 0.3)))

    max_sill = p.height - p.window_height - 0.2
    if p.window_sill_height > max_sill:
        p.window_sill_height = round(max(0.3, max_sill), 1)
    if p.door_height > p.height - 0.2:
        p.door_height = round(p.height - 0.3, 1)

    # Стены
    p.wall_left_type = 'DOOR'
    p.wall_left_windows = 0
    p.wall_back_type = 'WINDOWS'
    p.wall_back_windows = rng.randint(1, max_windows(p.width))
    p.wall_front_type = rng.choice(['NONE', 'WINDOWS'])
    p.wall_front_windows = rng.randint(1, max_windows(p.width)) if p.wall_front_type == 'WINDOWS' else 0
    p.wall_right_type = rng.choice(['NONE', 'WINDOWS'])
    p.wall_right_windows = rng.randint(1, max_windows(p.length)) if p.wall_right_type == 'WINDOWS' else 0

    # Visibility (для generate_room)
    p.show_ceiling = False
    p.show_wall_front = True
    p.show_wall_back = True
    p.show_wall_left = True
    p.show_wall_right = True

    return p


def clear_scene():
    """Полная очистка сцены."""
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

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)
    for tex in list(bpy.data.textures):
        if tex.users == 0:
            bpy.data.textures.remove(tex)


def render_and_save(output_dir, index, seed, res_x, res_y):
    scene = bpy.context.scene
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.image_settings.file_format = 'PNG'

    basename = f"{index:05d}_seed{seed}"
    png_path = os.path.join(output_dir, f"{basename}.png")
    blend_path = os.path.join(output_dir, f"{basename}.blend")

    scene.render.filepath = png_path
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=True)

    return basename


def generate_gallery(output_dir, variants):
    """Generate index.html from ALL .png files in output_dir."""
    all_pngs = sorted(f for f in os.listdir(output_dir) if f.endswith('.png'))

    # Lookup from current batch for detailed info
    variant_map = {}
    for v in variants:
        variant_map[v['basename']] = v

    # Discover asset galleries
    generators_dir = os.path.join(os.path.dirname(output_dir), 'output')
    if not os.path.isdir(generators_dir):
        generators_dir = output_dir
    asset_links = []
    asset_dirs = [
        'tables', 'chairs', 'seating', 'wardrobes',
        'kitchenware', 'lamps', 'clocks', 'shelves',
        'paintings', 'photoframes', 'rugs', 'cushions',
        'curtains', 'mirrors', 'booksets', 'plants',
        'candles', 'plushtoys',
    ]
    for name in asset_dirs:
        idx = os.path.join(output_dir, name, 'index.html')
        if os.path.exists(idx):
            asset_links.append((name, f"{name}/index.html"))

    count = len(all_pngs)
    nav_html = ''
    if asset_links:
        links = ' · '.join(f'<a href="{href}">{name}</a>' for name, href in asset_links)
        nav_html = f'<div class="nav">Assets: {links}</div>\n'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Roomicon — {count} Rooms</title>
<style>
body {{ font-family: -apple-system, sans-serif; background: #1a1a1a; color: #eee; margin: 20px; }}
h1 {{ text-align: center; margin-bottom: 10px; }}
.nav {{ text-align: center; margin-bottom: 20px; font-size: 13px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; }}
.card {{ background: #2a2a2a; border-radius: 8px; overflow: hidden; }}
.card img {{ width: 100%; cursor: pointer; display: block; }}
.card .info {{ padding: 10px 15px; font-size: 13px; }}
.card .seed {{ font-weight: bold; color: #7cb3ff; }}
.card .params {{ color: #999; margin-top: 4px; }}
.card .filename {{ color: #888; font-size: 11px; margin-top: 2px; font-family: monospace; }}
a {{ color: #7cb3ff; text-decoration: none; }}
</style>
</head>
<body>
<h1>Roomicon — {count} Rooms</h1>
{nav_html}<div class="grid">
"""
    for png in all_pngs:
        bn = png[:-4]
        v = variant_map.get(bn)
        if v:
            info = f'<div class="seed">Seed: {v["seed"]}</div>'
            info += f'\n<div class="params">{v["width"]}×{v["length"]}m, h={v["height"]}m, density={v["density"]}, {v["room_size"]}</div>'
        else:
            info = f'<div class="seed">{bn.replace("_", " ")}</div>'

        blend_link = ''
        if os.path.exists(os.path.join(output_dir, f"{bn}.blend")):
            blend_link = f'\n<div class="params"><a href="{bn}.blend">Download .blend</a></div>'

        html += f"""<div class="card">
<a href="{png}" target="_blank"><img src="{png}" loading="lazy"></a>
<div class="info">{info}{blend_link}
<div class="filename">{bn}</div>
</div>
</div>
"""
    html += """</div>
</body>
</html>"""

    with open(os.path.join(output_dir, 'index.html'), 'w') as f:
        f.write(html)


def main():
    args = parse_args()
    res_x, res_y = [int(x) for x in args.resolution.split('x')]
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    if args.seed_start is None:
        args.seed_start = random.randint(0, 99999)

    print("=" * 60)
    print(f"Batch generation: {args.count} variants")
    print(f"Output: {output_dir}")
    print(f"Resolution: {res_x}x{res_y}")
    print(f"Room size: {args.room_size}")
    print(f"Style: {args.style}")
    print(f"Ambient: {args.ambient}, Lamps: {args.lamps}")
    print(f"Seed range: {args.seed_start} — {args.seed_start + args.count - 1}")
    print("=" * 60)

    variants = []
    t_start = time.time()

    for i in range(args.count):
        seed = args.seed_start + i
        print(f"\n[{i+1}/{args.count}] Generating seed={seed}...")

        clear_scene()
        props = randomize_props(seed, room_size=args.room_size,
                                style=args.style, cel_shading=args.cel_shading,
                                ambient=args.ambient, lamps=args.lamps)
        generate_room(props)
        basename = render_and_save(output_dir, i, seed, res_x, res_y)

        variants.append({
            'basename': basename,
            'seed': seed,
            'width': props.width,
            'length': props.length,
            'height': props.height,
            'density': props.density,
            'room_size': args.room_size,
        })

        elapsed = time.time() - t_start
        avg = elapsed / (i + 1)
        remaining = avg * (args.count - i - 1)
        print(f"  Done. Avg: {avg:.1f}s/variant, ETA: {remaining:.0f}s")

    generate_gallery(output_dir, variants)

    total = time.time() - t_start
    print(f"\n{'=' * 60}")
    print(f"Completed! {args.count} variants in {total:.1f}s")
    print(f"Gallery: {os.path.join(output_dir, 'index.html')}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
