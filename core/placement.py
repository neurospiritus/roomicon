"""Furniture and decor placement algorithm for the room."""

import random
import math

from core.room_geometry import get_wall_interior, get_inner_bounds

# Furniture dimensions (footprint: width_x, depth_y) and placement preferences
# placement: 'wall' — flush against wall, 'center' — can be in center
FURNITURE_DEFS = {
    'wardrobe':   {'size': (1.4, 0.6), 'placement': 'wall', 'weight': 0.7, 'group': 'wardrobe',
                   'limits': {'SMALL': (0, 1), 'MEDIUM': (1, 1), 'LARGE': (1, 2), 'XLARGE': (1, 2)}},
    'nightstand': {'size': (0.45, 0.4), 'placement': 'wall', 'weight': 0.3, 'group': 'nightstand',
                   'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 1), 'LARGE': (0, 2), 'XLARGE': (1, 2)}},
    'dresser':    {'size': (1.0, 0.45), 'placement': 'wall', 'weight': 0.5, 'group': 'dresser',
                   'limits': {'SMALL': (0, 0), 'MEDIUM': (0, 1), 'LARGE': (0, 1), 'XLARGE': (0, 1)}},
    'bed':      {'size': (0.9, 2.0),  'placement': 'wall', 'weight': 0.6, 'group': 'sleeping'},
    'sofa':     {'size': (1.8, 0.85), 'placement': 'wall', 'weight': 0.7, 'group': 'sleeping'},
    'table':    {'size': (1.5, 1.0),  'placement': 'center', 'weight': 1.0, 'group': 'table',
                 'limits': {'SMALL': (1, 1), 'MEDIUM': (1, 2), 'LARGE': (1, 2), 'XLARGE': (1, 3)}},
    'desk':     {'size': (1.6, 0.8),  'placement': 'wall', 'weight': 0.6, 'group': 'table',
                 'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 1), 'LARGE': (0, 1), 'XLARGE': (0, 1)}},
    'armchair': {'size': (0.9, 0.75), 'placement': 'wall', 'weight': 0.6,
                 'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 2), 'LARGE': (0, 2), 'XLARGE': (1, 2)}},
    'chair':    {'size': (0.45, 0.45), 'placement': 'center', 'weight': 0.8,
                 'limits': {'SMALL': (1, 2), 'MEDIUM': (2, 4), 'LARGE': (2, 5), 'XLARGE': (3, 6)}},
}

# Group limits (shared counter for all types in a group)
GROUP_LIMITS = {
    'sleeping': {'SMALL': (1, 1), 'MEDIUM': (1, 1), 'LARGE': (1, 2), 'XLARGE': (1, 2)},
}

# Decor: placement determines where it goes
# limits: (min, max) by room_size — item count. chance: spawn probability (default 1.0)
# source: 'procedural' — via tools/generators/, 'asset' — from assets/decor/, 'generator' — legacy generators/decor/
DECOR_DEFS = {
    # --- Tabletop (on tables) ---
    'candle':         {'size': (0.10, 0.10), 'placement': 'surface', 'height': 0.15,
                       'asset_category': 'tabletop', 'radius': 0.06, 'chance': 0.3,
                       'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 1), 'LARGE': (0, 2), 'XLARGE': (0, 2)}},
    'kitchenware':    {'size': (0.12, 0.12), 'placement': 'surface', 'height': 0.15,
                       'asset_category': 'tabletop', 'radius': 0.08,
                       'limits': {'SMALL': (0, 2), 'MEDIUM': (1, 3), 'LARGE': (1, 4), 'XLARGE': (2, 5)}},
    'book_single':    {'size': (0.04, 0.17), 'placement': 'surface', 'height': 0.25,
                       'asset_category': 'tabletop', 'radius': 0.10,
                       'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 2), 'LARGE': (0, 2), 'XLARGE': (1, 3)}},
    'book_stack':     {'size': (0.18, 0.14), 'placement': 'surface', 'height': 0.12,
                       'asset_category': 'tabletop', 'radius': 0.12, 'chance': 0.3,
                       'limits': {'SMALL': (0, 0), 'MEDIUM': (0, 1), 'LARGE': (0, 1), 'XLARGE': (0, 1)}},
    'plant_tabletop': {'size': (0.16, 0.16), 'placement': 'surface', 'height': 0.25,
                       'asset_category': 'tabletop', 'radius': 0.10,
                       'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 2), 'LARGE': (1, 2), 'XLARGE': (1, 3)}},
    'photoframe_tabletop': {'size': (0.10, 0.08), 'placement': 'surface', 'height': 0.20,
                       'asset_category': 'tabletop', 'radius': 0.08, 'chance': 0.5,
                       'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 1), 'LARGE': (0, 2), 'XLARGE': (0, 2)}},
    'clock_tabletop': {'size': (0.12, 0.07), 'placement': 'surface', 'height': 0.12,
                       'asset_category': 'tabletop', 'radius': 0.08, 'chance': 0.7,
                       'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 1), 'LARGE': (0, 1), 'XLARGE': (0, 1)}},
    'lamp_tabletop':  {'size': (0.18, 0.18), 'placement': 'surface', 'height': 0.35,
                       'asset_category': 'tabletop', 'radius': 0.12, 'chance': 0.5,
                       'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 1), 'LARGE': (0, 2), 'XLARGE': (0, 2)}},
    # --- Floor (on floor) ---
    'rug':            {'size': (1.50, 1.00), 'placement': 'rug', 'height': 0.01,
                       'asset_category': 'floor', 'chance': 0.6,
                       'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 1), 'LARGE': (0, 1), 'XLARGE': (0, 1)}},
    # --- Wall (on walls) ---
    'shelf':          {'size': (0.90, 0.25), 'placement': 'wall_hang', 'height': 0.25,
                       'asset_category': 'wall',
                       'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 2), 'LARGE': (1, 2), 'XLARGE': (1, 3)}},
    'painting':       {'size': (0.85, 0.03), 'placement': 'wall_hang', 'height': 0.40,
                       'asset_category': 'wall', 'chance': 0.8,
                       'limits': {'SMALL': (1, 2), 'MEDIUM': (1, 3), 'LARGE': (1, 4), 'XLARGE': (1, 5)}},
    'mirror':         {'size': (0.60, 0.03), 'placement': 'wall_hang', 'height': 0.50,
                       'asset_category': 'wall', 'chance': 0.5,
                       'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 1), 'LARGE': (0, 1), 'XLARGE': (0, 2)}},
    'photoframe_wall': {'size': (0.25, 0.03), 'placement': 'wall_hang', 'height': 0.20,
                       'asset_category': 'wall', 'chance': 0.5,
                       'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 2), 'LARGE': (0, 2), 'XLARGE': (0, 3)}},
    'clock_wall':     {'size': (0.40, 0.05), 'placement': 'wall_hang', 'height': 0.40,
                       'asset_category': 'wall', 'chance': 0.5,
                       'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 1), 'LARGE': (0, 1), 'XLARGE': (0, 1)}},
    'lamp_wall':      {'size': (0.25, 0.15), 'placement': 'wall_hang', 'height': 0.25,
                       'asset_category': 'wall', 'chance': 0.3,
                       'limits': {'SMALL': (0, 1), 'MEDIUM': (0, 2), 'LARGE': (0, 2), 'XLARGE': (0, 2)}},
    # --- Wall-floor (wall-adjacent floor items) ---
    'clock_floor':    {'size': (0.35, 0.20), 'placement': 'wall_floor', 'height': 2.0,
                       'asset_category': 'wall_floor',
                       'chance': {'LARGE': 0.4, 'XLARGE': 0.7},
                       'limits': {'SMALL': (0, 0), 'MEDIUM': (0, 0), 'LARGE': (0, 1), 'XLARGE': (0, 1)}},
    'lamp_floor':     {'size': (0.40, 0.40), 'placement': 'wall_floor', 'height': 1.6,
                       'asset_category': 'wall_floor', 'chance': 0.4,
                       'limits': {'SMALL': (0, 0), 'MEDIUM': (0, 1), 'LARGE': (0, 1), 'XLARGE': (0, 2)}},
    # --- Ceiling ---
    'lamp_ceiling':   {'size': (0.40, 0.40), 'placement': 'ceiling', 'height': 0.40,
                       'asset_category': 'ceiling',
                       'limits': {'SMALL': (1, 1), 'MEDIUM': (1, 1), 'LARGE': (1, 1), 'XLARGE': (1, 1)}},
}

MIN_GAP = 0.15
WALL_OFFSET = 0.05
OPENING_MARGIN = 0.2  # margin from opening edge when placing along wall


def _make_density_counter(rng, density):
    """Returns a function that interpolates count between min and max by density."""
    def _density_count(lmin, lmax):
        target = lmin + (lmax - lmin) * density
        count = int(target)
        if rng.random() < (target - count):
            count += 1
        return count
    return _density_count


def place_furniture(width, length, height, wall_thickness, density, seed,
                    wall_configs, door_width, door_height,
                    window_width=1.2, window_height=1.4, window_sill_height=0.8,
                    room_size='MEDIUM'):
    """
    Phase 1: places furniture only.
    Returns a list of furniture placements.
    """
    rng = random.Random(seed)

    wt = wall_thickness
    inner_x_min, inner_x_max, inner_y_min, inner_y_max = get_inner_bounds(width, length, wt)

    forbidden = _get_door_zones(width, length, wt, wall_configs, door_width)
    wall_segments = _get_wall_free_segments(width, length, wall_configs,
                                             door_width, window_width)

    # --- Type and group limits for this room_size ---
    type_limits = {}
    group_limits_active = {}

    for ftype, fdef in FURNITURE_DEFS.items():
        limits = fdef.get('limits', {}).get(room_size)
        if limits:
            type_limits[ftype] = limits
        group = fdef.get('group')
        if group and group in GROUP_LIMITS:
            gl = GROUP_LIMITS[group].get(room_size)
            if gl:
                group_limits_active[group] = gl

    placed = []
    result = []

    def _place_one(ftype):
        fdef = FURNITURE_DEFS[ftype]
        fw, fd = fdef['size']
        for _ in range(20):
            if fdef['placement'] == 'wall':
                p = _try_place_wall(rng, ftype, fw, fd,
                                    inner_x_min, inner_x_max,
                                    inner_y_min, inner_y_max,
                                    wt, placed, forbidden, wall_segments)
            else:
                p = _try_place_center(rng, ftype, fw, fd,
                                      inner_x_min, inner_x_max,
                                      inner_y_min, inner_y_max,
                                      placed, forbidden)
            if p:
                placed.append(p)
                result.append({
                    'type': p['type'], 'x': p['x'], 'y': p['y'], 'z': 0.0,
                    'rotation': p['rotation'], 'category': 'furniture',
                    'sx': p.get('sx', 0), 'sy': p.get('sy', 0),
                    'fw': p.get('fw', 0), 'fd': p.get('fd', 0),
                })
                return True
        return False

    _density_count = _make_density_counter(rng, density)

    # 1. Groups
    handled_types = set()
    for group, glimits in group_limits_active.items():
        count = _density_count(*glimits)
        group_types = [ft for ft, fd in FURNITURE_DEFS.items() if fd.get('group') == group]
        handled_types.update(group_types)
        for _ in range(count):
            ftype = rng.choice(group_types)
            _place_one(ftype)

    # 2. Types with individual limits (except chairs — placed around tables)
    for ftype, flimits in type_limits.items():
        if ftype in handled_types or ftype == 'chair':
            continue
        count = _density_count(*flimits)
        handled_types.add(ftype)
        for _ in range(count):
            _place_one(ftype)

    # 3. Chairs around tables
    chair_limits = type_limits.get('chair', (0, 0))
    total_chairs = _density_count(*chair_limits)
    chairs_placed = 0

    # Collect center tables (not desks)
    center_tables = [p for p in placed if p['type'] == 'table']

    if center_tables and total_chairs > 0:
        chair_def = FURNITURE_DEFS['chair']
        cw, cd = chair_def['size']
        chw, chd = cw / 2, cd / 2
        gap = 0.25  # distance from table edge to chair center

        # Distribute chairs across tables
        chairs_per_table = max(1, total_chairs // len(center_tables))

        for table in center_tables:
            tx, ty = table['x'], table['y']
            t_rot = table['rotation']
            t_hw = table.get('fw', table['sx']) / 2
            t_hd = table.get('fd', table['sy']) / 2

            # Chair positions: on 4 sides of table
            # In table local coordinates, then rotated
            slots = []
            # Long sides (along X): more chairs
            n_long = max(1, int(t_hw * 2 / 0.55))
            for i in range(n_long):
                lx = -t_hw + t_hw * 2 * (i + 0.5) / n_long
                slots.append((lx, -t_hd - gap))  # front side
                slots.append((lx, t_hd + gap))    # back side
            # Short sides (along Y): 1 chair if table is wide enough
            if t_hd > 0.35:
                slots.append((-t_hw - gap, 0))
                slots.append((t_hw + gap, 0))

            rng.shuffle(slots)
            n_here = min(chairs_per_table, total_chairs - chairs_placed, len(slots))

            for si in range(n_here):
                lx, ly = slots[si]
                # Rotate to world coordinates
                cos_r = math.cos(t_rot)
                sin_r = math.sin(t_rot)
                wx = tx + lx * cos_r - ly * sin_r
                wy = ty + lx * sin_r + ly * cos_r

                # Bounds check
                if (wx - chw < inner_x_min or wx + chw > inner_x_max or
                        wy - chd < inner_y_min or wy + chd > inner_y_max):
                    continue

                # Direction toward table center + random deviation
                angle_to_table = math.atan2(ty - wy, tx - wx)
                deviation = rng.uniform(-math.pi / 3, math.pi / 3)
                chair_rot = angle_to_table + deviation - math.pi / 2  # chair front (+Y) faces table

                # Collisions (exclude current table)
                col_r = max(chw, chd)
                others = [p for p in placed if p is not table]
                if _check_collision(wx, wy, col_r, col_r, others, forbidden):
                    continue

                p = {'type': 'chair', 'x': wx, 'y': wy,
                     'sx': cw, 'sy': cd, 'fw': cw, 'fd': cd,
                     'rotation': chair_rot}
                placed.append(p)
                result.append({
                    'type': 'chair', 'x': wx, 'y': wy, 'z': 0.0,
                    'rotation': chair_rot, 'category': 'furniture',
                    'sx': cw, 'sy': cd, 'fw': cw, 'fd': cd,
                })
                chairs_placed += 1

    return result


def place_decor(width, length, height, wall_thickness, density, seed,
                wall_configs, door_width, window_width=1.2,
                room_size='MEDIUM', tables=None, furniture_placed=None):
    """
    Phase 2: places decor. Receives actual table data.
    tables: list of {'x', 'y', 'rotation', 'surface_z', 'width', 'depth'}
    furniture_placed: list of furniture placements (for collisions)
    """
    rng = random.Random(seed + 10000)  # different seed to avoid repeating furniture

    wt = wall_thickness
    inner_x_min, inner_x_max, inner_y_min, inner_y_max = get_inner_bounds(width, length, wt)
    inner_w = inner_x_max - inner_x_min
    inner_l = inner_y_max - inner_y_min

    forbidden = _get_door_zones(width, length, wt, wall_configs, door_width)
    wall_segments = _get_wall_free_segments(width, length, wall_configs,
                                             door_width, window_width)

    if tables is None:
        tables = []
    if furniture_placed is None:
        furniture_placed = []

    # Use furniture placements for collision detection
    placed = list(furniture_placed)
    result = []

    _density_count = _make_density_counter(rng, density)

    for dtype, ddef in DECOR_DEFS.items():
        chance = ddef.get('chance', 1.0)
        if isinstance(chance, dict):
            chance = chance.get(room_size, 0.0)
        if rng.random() > chance * density:
            continue

        limits = ddef.get('limits', {}).get(room_size)
        if limits:
            dmin, dmax = limits
            if dmax <= 0:
                continue
            count = _density_count(dmin, dmax)
        else:
            count = 1

        placement = ddef['placement']

        for _ in range(count):
            d = None
            if placement == 'surface':
                d = _try_place_on_surface(rng, dtype, ddef, tables, result)
            elif placement == 'floor':
                d = _try_place_floor(rng, dtype, ddef,
                                     inner_x_min, inner_x_max,
                                     inner_y_min, inner_y_max,
                                     placed, forbidden)
            elif placement == 'wall_hang':
                d = _try_place_wall_hanging(rng, dtype, ddef,
                                             width, length, height, wt,
                                             wall_configs, wall_segments,
                                             furniture_placed + result)
            elif placement == 'wall_floor':
                d = _try_place_wall_floor(rng, dtype, ddef,
                                           width, length, wt,
                                           inner_x_min, inner_x_max,
                                           inner_y_min, inner_y_max,
                                           placed, forbidden, wall_segments)
            elif placement == 'ceiling':
                d = _try_place_ceiling(rng, dtype, ddef,
                                        width, length, height, wt)
            elif placement == 'rug':
                d = _try_place_rug(rng, placed, inner_x_min, inner_x_max,
                                    inner_y_min, inner_y_max, inner_w, inner_l)

            if d:
                result.append(d)
                # Add floor decor objects to placed for collision checks
                if placement in ('wall_floor', 'floor'):
                    fw, fd = ddef['size']
                    placed.append({'type': dtype, 'x': d['x'], 'y': d['y'],
                                   'sx': fw, 'sy': fd})

    return result


# ============================================================
# Forbidden zones and free wall segments
# ============================================================

def _get_door_zones(width, length, wt, wall_configs, door_width):
    """Returns forbidden floor zones in front of doors."""
    zones = []
    door_clearance = 1.0

    for side, wtype, _ in wall_configs:
        if wtype != 'DOOR':
            continue
        if side == 'front':
            cx = width / 2
            zones.append((cx - door_width/2 - 0.2, 0,
                          cx + door_width/2 + 0.2, door_clearance + wt))
        elif side == 'back':
            cx = width / 2
            zones.append((cx - door_width/2 - 0.2, length - door_clearance - wt,
                          cx + door_width/2 + 0.2, length))
        elif side == 'left':
            cy = length / 2
            zones.append((0, cy - door_width/2 - 0.2,
                          door_clearance + wt, cy + door_width/2 + 0.2))
        elif side == 'right':
            cy = length / 2
            zones.append((width - door_clearance - wt, cy - door_width/2 - 0.2,
                          width, cy + door_width/2 + 0.2))
    return zones


def _get_wall_free_segments(width, length, wall_configs, door_width, window_width):
    """
    For each wall, returns a list of free segments (min, max) along the wall
    where there are no openings. Coordinates are along the wall (0..wall_length).

    Returns dict: { wall_idx: [(seg_min, seg_max), ...] }
    wall_idx: 0=front, 1=back, 2=left, 3=right
    """
    wall_lengths = [width, width, length, length]
    segments = {}

    for i, (side, wtype, win_count) in enumerate(wall_configs):
        wlen = wall_lengths[i]
        if wtype == 'NONE':
            # Entire wall is free
            segments[i] = [(0, wlen)]
        elif wtype == 'DOOR':
            # Door centered
            d_min = wlen / 2 - door_width / 2 - OPENING_MARGIN
            d_max = wlen / 2 + door_width / 2 + OPENING_MARGIN
            segs = []
            if d_min > 0:
                segs.append((0, d_min))
            if d_max < wlen:
                segs.append((d_max, wlen))
            segments[i] = segs
        elif wtype == 'WINDOWS':
            # Windows evenly spaced
            if win_count <= 0:
                segments[i] = [(0, wlen)]
                continue
            spacing = wlen / (win_count + 1)
            blocked = []
            for wi in range(win_count):
                cx = spacing * (wi + 1)
                blocked.append((cx - window_width / 2 - OPENING_MARGIN,
                                cx + window_width / 2 + OPENING_MARGIN))
            # Free gaps between blocked zones
            segs = []
            prev = 0
            for bmin, bmax in sorted(blocked):
                bmin = max(0, bmin)
                bmax = min(wlen, bmax)
                if bmin > prev:
                    segs.append((prev, bmin))
                prev = bmax
            if prev < wlen:
                segs.append((prev, wlen))
            segments[i] = segs
        else:
            segments[i] = [(0, wlen)]

    return segments


# ============================================================
# Collision
# ============================================================

def _rect_overlap(ax, ay, aw, ah, bx, by, bw, bh):
    """Checks overlap of two rectangles (center + half-sizes)."""
    return (abs(ax - bx) < aw + bw and abs(ay - by) < ah + bh)


def _check_collision(x, y, hw, hd, placed, forbidden, gap=MIN_GAP):
    """Checks collisions with already placed objects and forbidden zones."""
    for p in placed:
        if _rect_overlap(x, y, hw + gap, hd + gap,
                         p['x'], p['y'], p['sx'] / 2 + gap, p['sy'] / 2 + gap):
            return True
    for zone in forbidden:
        zx = (zone[0] + zone[2]) / 2
        zy = (zone[1] + zone[3]) / 2
        zhw = (zone[2] - zone[0]) / 2
        zhd = (zone[3] - zone[1]) / 2
        if _rect_overlap(x, y, hw, hd, zx, zy, zhw, zhd):
            return True
    return False


# ============================================================
# Furniture placement
# ============================================================

def _try_place_wall(rng, ftype, fw, fd, x_min, x_max, y_min, y_max, wt,
                    placed, forbidden, wall_segments):
    """Tries to place furniture against a random wall, only in free segments."""
    # Shuffle walls
    walls = [0, 1, 2, 3]
    rng.shuffle(walls)

    for wall in walls:
        segs = wall_segments.get(wall, [])
        if not segs:
            continue

        # Pick a random segment where furniture fits
        # fw — furniture width along the wall
        valid_segs = [(s_min, s_max) for s_min, s_max in segs if s_max - s_min >= fw + 0.1]
        if not valid_segs:
            continue

        seg = rng.choice(valid_segs)
        # Random position along wall within segment
        pos_along = rng.uniform(seg[0] + fw / 2, seg[1] - fw / 2)

        if wall == 0:  # front, Y=min
            hw, hd = fw / 2, fd / 2
            x = x_min + pos_along
            y = y_min + WALL_OFFSET + hd
            rotation = 0.0
        elif wall == 1:  # back, Y=max
            hw, hd = fw / 2, fd / 2
            x = x_min + pos_along
            y = y_max - WALL_OFFSET - hd
            rotation = math.pi
        elif wall == 2:  # left, X=min — front (+Y) should face +X
            hw, hd = fd / 2, fw / 2
            x = x_min + WALL_OFFSET + hw
            y = y_min + pos_along
            rotation = -math.pi / 2
        elif wall == 3:  # right, X=max — front (+Y) should face -X
            hw, hd = fd / 2, fw / 2
            x = x_max - WALL_OFFSET - hw
            y = y_min + pos_along
            rotation = math.pi / 2

        # Check that furniture doesn't exceed room bounds
        if (x - hw < x_min or x + hw > x_max or
                y - hd < y_min or y + hd > y_max):
            continue

        if not _check_collision(x, y, hw, hd, placed, forbidden):
            return {'type': ftype, 'x': x, 'y': y, 'rotation': rotation,
                    'sx': hw * 2, 'sy': hd * 2, 'fw': fw, 'fd': fd}

    return None


def _try_place_center(rng, ftype, fw, fd, x_min, x_max, y_min, y_max, placed, forbidden):
    """Tries to place furniture in an open area."""
    hw, hd = fw / 2, fd / 2
    margin = 0.3

    x = rng.uniform(x_min + hw + margin, x_max - hw - margin)
    y = rng.uniform(y_min + hd + margin, y_max - hd - margin)

    if ftype in ('chair',):
        rotation = rng.uniform(0, math.pi * 2)
    else:
        rotation = rng.choice([0, math.pi / 2, math.pi, math.pi * 1.5])

    # For collisions: arbitrary rotation — use max, multiples of pi/2 — swap
    if ftype in ('chair',):
        max_h = max(hw, hd)
        hw, hd = max_h, max_h
    elif rotation in (math.pi / 2, math.pi * 1.5):
        hw, hd = hd, hw

    if _check_collision(x, y, hw, hd, placed, forbidden):
        return None

    return {'type': ftype, 'x': x, 'y': y, 'rotation': rotation,
            'sx': hw * 2, 'sy': hd * 2, 'fw': fw, 'fd': fd}


# ============================================================
# Decor placement
# ============================================================


def _try_place_on_surface(rng, dtype, ddef, tables, all_results):
    """Places decor on a table surface.
    tables: list of {'x', 'y', 'rotation', 'surface_z', 'width', 'depth'}
    """
    if not tables:
        return None

    table = rng.choice(tables)
    surface_h = table['surface_z']

    radius = ddef.get('radius', max(ddef['size'][0], ddef['size'][1]) * 0.5)
    margin = radius + 0.03

    t_hw = table['width'] / 2
    t_hd = table['depth'] / 2
    if t_hw <= margin or t_hd <= margin:
        return None
    dx = rng.uniform(-t_hw + margin, t_hw - margin)
    dy = rng.uniform(-t_hd + margin, t_hd - margin)

    rot = table['rotation']
    rx = dx * math.cos(rot) - dy * math.sin(rot)
    ry = dx * math.sin(rot) + dy * math.cos(rot)

    x = table['x'] + rx
    y = table['y'] + ry

    # Check collisions with other decor
    for r in all_results:
        if r.get('category') != 'decor' or r.get('placement_type') == 'ceiling':
            continue
        other_radius = r.get('_radius', 0.08)
        min_dist = radius + other_radius
        if (r['x'] - x) ** 2 + (r['y'] - y) ** 2 < min_dist ** 2:
            return None

    result = {
        'type': dtype, 'x': x, 'y': y, 'z': surface_h,
        'rotation': rng.uniform(0, math.pi * 2), 'category': 'decor',
        'source': ddef.get('source', 'generator'),
        '_radius': radius,
    }
    if 'asset_category' in ddef:
        result['asset_category'] = ddef['asset_category']
    return result


def _try_place_floor(rng, dtype, ddef, x_min, x_max, y_min, y_max, placed, forbidden):
    """Places decor on the floor."""
    fw, fd = ddef['size']
    hw, hd = fw / 2, fd / 2
    margin = 0.3

    x = rng.uniform(x_min + hw + margin, x_max - hw - margin)
    y = rng.uniform(y_min + hd + margin, y_max - hd - margin)

    if _check_collision(x, y, hw, hd, placed, forbidden, gap=0.05):
        return None

    result = {
        'type': dtype, 'x': x, 'y': y, 'z': 0.0,
        'rotation': rng.uniform(0, math.pi * 2), 'category': 'decor',
        'source': ddef.get('source', 'generator'),
    }
    if 'asset_category' in ddef:
        result['asset_category'] = ddef['asset_category']
    return result


def _try_place_rug(rng, placed, x_min, x_max, y_min, y_max, inner_w, inner_l):
    """Rug at room center. Uniform scale (preserves proportions)."""
    x = (x_min + x_max) / 2 + rng.uniform(-0.3, 0.3)
    y = (y_min + y_max) / 2 + rng.uniform(-0.3, 0.3)
    # Target scale — fraction of the smaller room side
    target = min(inner_w, inner_l) * rng.uniform(0.5, 0.8)

    return {
        'type': 'rug', 'x': x, 'y': y, 'z': 0.001,
        'rotation': rng.uniform(-0.05, 0.05),
        'category': 'decor', 'source': 'asset', 'asset_category': 'floor',
        'rug_scale': target,
    }


def _try_place_ceiling(rng, dtype, ddef, width, length, height, wt):
    """Places an object on the ceiling — at room center."""
    x = width / 2
    y = length / 2

    result = {
        'type': dtype, 'x': x, 'y': y, 'z': height,
        'rotation': 0, 'category': 'decor',
        'placement_type': 'ceiling',
        'source': ddef.get('source', 'generator'),
    }
    if 'asset_category' in ddef:
        result['asset_category'] = ddef['asset_category']
    return result


def _try_place_wall_floor(rng, dtype, ddef, width, length, wt,
                           x_min, x_max, y_min, y_max,
                           placed, forbidden, wall_segments):
    """Places a wall-adjacent floor object (grandfather clock, floor lamp).
    Like wall furniture: back against wall, in free segment, Z=0."""
    fw, fd = ddef['size']

    walls = [0, 1, 2, 3]
    rng.shuffle(walls)

    for wall in walls:
        segs = wall_segments.get(wall, [])
        if not segs:
            continue

        valid_segs = [(s_min, s_max) for s_min, s_max in segs if s_max - s_min >= fw + 0.1]
        if not valid_segs:
            continue

        seg = rng.choice(valid_segs)
        pos_along = rng.uniform(seg[0] + fw / 2, seg[1] - fw / 2)

        if wall == 0:  # front
            hw, hd = fw / 2, fd / 2
            x = x_min + pos_along
            y = y_min + WALL_OFFSET + hd
            rotation = 0.0
        elif wall == 1:  # back
            hw, hd = fw / 2, fd / 2
            x = x_min + pos_along
            y = y_max - WALL_OFFSET - hd
            rotation = math.pi
        elif wall == 2:  # left
            hw, hd = fd / 2, fw / 2
            x = x_min + WALL_OFFSET + hw
            y = y_min + pos_along
            rotation = -math.pi / 2
        elif wall == 3:  # right
            hw, hd = fd / 2, fw / 2
            x = x_max - WALL_OFFSET - hw
            y = y_min + pos_along
            rotation = math.pi / 2

        # Check that object doesn't exceed room bounds
        if (x - hw < x_min or x + hw > x_max or
                y - hd < y_min or y + hd > y_max):
            continue

        if not _check_collision(x, y, hw, hd, placed, forbidden):
            result = {
                'type': dtype, 'x': x, 'y': y, 'z': 0.0,
                'rotation': rotation, 'category': 'decor',
                'placement_type': 'wall_floor',
                'source': ddef.get('source', 'generator'),
            }
            if 'asset_category' in ddef:
                result['asset_category'] = ddef['asset_category']
            return result

    return None


def _try_place_wall_hanging(rng, dtype, ddef, width, length, height, wt,
                             wall_configs, wall_segments=None, all_results=None):
    """
    Places decor on walls — on NONE walls (fully) or in free segments
    of windowed walls (between windows). Avoids door walls.
    Uses get_wall_interior for positions and rotations.
    """
    item_w = ddef['size'][0]
    hang_z = rng.uniform(max(1.3, height * 0.45), min(1.8, height * 0.65))
    walls = get_wall_interior(width, length, wt)
    x_min, x_max, y_min, y_max = get_inner_bounds(width, length, wt)

    # Collect available walls with their free positions
    wall_options = []  # (side, wall_idx, seg_min, seg_max)
    sides = ['front', 'back', 'left', 'right']

    for i, (side, wtype, win_count) in enumerate(wall_configs):
        if wtype == 'DOOR':
            continue

        wlen = walls[side]['wall_len']

        if wtype == 'NONE':
            wall_options.append((side, i, 0.1, wlen - 0.1))
        elif wall_segments and i in wall_segments:
            for seg_min, seg_max in wall_segments[i]:
                if seg_max - seg_min >= item_w + 0.1:
                    wall_options.append((side, i, seg_min + 0.05, seg_max - 0.05))

    if not wall_options:
        return None

    side, wall_idx, seg_min, seg_max = rng.choice(wall_options)
    wi = walls[side]

    # Position along wall (in wall local coordinates)
    pos = rng.uniform(seg_min + item_w / 2, seg_max - item_w / 2)

    # World coordinates: origin + along * pos + inward * offset
    offset = 0.01
    x = wi['origin'][0] + wi['along'][0] * pos + wi['inward'][0] * offset
    y = wi['origin'][1] + wi['along'][1] * pos + wi['inward'][1] * offset
    rotation = wi['rot_hanging']

    # Check that item doesn't exceed room bounds
    # +0.05 margin for frames and nominal size inaccuracy
    hw = item_w / 2 + 0.05
    edge_x1 = wi['origin'][0] + wi['along'][0] * (pos - hw)
    edge_x2 = wi['origin'][0] + wi['along'][0] * (pos + hw)
    edge_y1 = wi['origin'][1] + wi['along'][1] * (pos - hw)
    edge_y2 = wi['origin'][1] + wi['along'][1] * (pos + hw)
    for ex in (edge_x1, edge_x2):
        if ex < x_min or ex > x_max:
            return None
    for ey in (edge_y1, edge_y2):
        if ey < y_min or ey > y_max:
            return None

    # Check not too close to other wall-mounted objects
    if all_results:
        for r in all_results:
            if r.get('placement_type') == 'wall_hang':
                dist = math.hypot(r['x'] - x, r['y'] - y)
                if dist < item_w * 0.8:
                    return None
            # Check overlap with wall furniture (wardrobe, bed, sofa)
            if r.get('category') == 'furniture' and 'sx' in r:
                fhw = r['sx'] / 2 + 0.05
                fhd = r['sy'] / 2 + 0.05
                if abs(r['x'] - x) < fhw + hw and abs(r['y'] - y) < fhd + 0.1:
                    return None

    result = {
        'type': dtype, 'x': x, 'y': y, 'z': hang_z,
        'rotation': rotation, 'category': 'decor',
        'placement_type': 'wall_hang',
        'source': ddef.get('source', 'generator'),
    }
    if 'asset_category' in ddef:
        result['asset_category'] = ddef['asset_category']
    return result
