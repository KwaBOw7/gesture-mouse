"""Robust hand-geometry features and static gesture classification.

The classifier deliberately uses the full finger chains instead of a single
MCP-PIP-TIP angle.  All measurements are normalized by hand size so the
result is much less sensitive to distance from the camera and small rotations.
"""

import math


def distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def angle(a, b, c):
    """Angle ABC in degrees."""
    ab = (a[0] - b[0], a[1] - b[1])
    cb = (c[0] - b[0], c[1] - b[1])
    denom = math.hypot(*ab) * math.hypot(*cb)
    if denom <= 1e-9:
        return 0.0
    value = (ab[0] * cb[0] + ab[1] * cb[1]) / denom
    return math.degrees(math.acos(max(-1.0, min(1.0, value))))


def map_range(value, in_min, in_max, out_min, out_max):
    """Linearly map a value from one range to another."""
    if abs(in_max - in_min) < 1e-12:
        return out_min
    ratio = (value - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _norm(v):
    return math.hypot(v[0], v[1])


def _unit(v):
    n = _norm(v)
    return (v[0] / n, v[1] / n) if n > 1e-9 else (0.0, 0.0)


# MediaPipe Hands landmark indices.
WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4

INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8

MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12

RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16

PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20

FINGER_DATA = (
    (INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),
    (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
    (RING_MCP, RING_PIP, RING_DIP, RING_TIP),
    (PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),
)


def palm_size(points):
    # A stable scale that does not change much as individual fingers move.
    return max(
        1e-6,
        0.5
        * (
            distance(points[WRIST], points[MIDDLE_MCP])
            + distance(points[INDEX_MCP], points[PINKY_MCP])
        ),
    )


def finger_metrics(points, mcp, pip, dip, tip):
    scale = palm_size(points)
    return {
        "pip_angle": angle(points[mcp], points[pip], points[dip]),
        "dip_angle": angle(points[pip], points[dip], points[tip]),
        "tip_reach": distance(points[WRIST], points[tip]) / scale,
        "pip_reach": distance(points[WRIST], points[pip]) / scale,
        "tip_to_mcp": distance(points[mcp], points[tip]) / scale,
        "chain_ratio": (
            distance(points[mcp], points[pip])
            + distance(points[pip], points[dip])
            + distance(points[dip], points[tip])
        )
        / max(1e-6, distance(points[mcp], points[tip])),
    }


def is_finger_extended(points, mcp, pip, dip, tip, config=None):
    """Return True when a finger is geometrically extended.

    Two joint angles + normalized reach are used.  This is much more stable
    than the old MCP-PIP-TIP-only test, especially for 3/4 fingers.
    """
    cfg = config or {}
    metrics = finger_metrics(points, mcp, pip, dip, tip)

    angle_threshold = float(cfg.get("extended_angle", 150.0))
    dip_threshold = float(cfg.get("extended_dip_angle", 145.0))
    reach_threshold = float(cfg.get("extended_reach", 1.35))
    max_chain_ratio = float(cfg.get("max_chain_ratio", 1.32))

    return (
        metrics["pip_angle"] >= angle_threshold
        and metrics["dip_angle"] >= dip_threshold
        and metrics["tip_reach"] >= reach_threshold
        and metrics["chain_ratio"] <= max_chain_ratio
    )


def get_finger_states(points, geometry=None):
    geometry = geometry or {}
    return tuple(is_finger_extended(points, *finger, geometry) for finger in FINGER_DATA)


def thumb_metrics(points):
    scale = palm_size(points)
    return {
        "mcp_angle": angle(points[THUMB_CMC], points[THUMB_MCP], points[THUMB_IP]),
        "ip_angle": angle(points[THUMB_MCP], points[THUMB_IP], points[THUMB_TIP]),
        "reach": distance(points[WRIST], points[THUMB_TIP]) / scale,
        "tip_to_index_mcp": distance(points[THUMB_TIP], points[INDEX_MCP]) / scale,
        "tip_to_palm": distance(points[THUMB_TIP], points[MIDDLE_MCP]) / scale,
    }


def is_thumb_extended(points, geometry=None):
    geometry = geometry or {}
    m = thumb_metrics(points)

    mcp_threshold = float(geometry.get("thumb_mcp_angle", 145.0))
    ip_threshold = float(geometry.get("thumb_ip_angle", 145.0))
    reach_threshold = float(geometry.get("thumb_reach", 1.25))
    palm_clearance = float(geometry.get("thumb_palm_clearance", 0.72))

    # The clearance test is important: a curled thumb can still be relatively
    # far from the wrist, but it normally remains close to the palm/index MCP.
    return (
        m["mcp_angle"] >= mcp_threshold
        and m["ip_angle"] >= ip_threshold
        and m["reach"] >= reach_threshold
        and m["tip_to_index_mcp"] >= palm_clearance
    )


def is_fist_like(points, ratio=1.35):
    scale = palm_size(points)
    return distance(points[WRIST], points[INDEX_TIP]) / scale < ratio


def is_thumb_up(points, finger_states, thumb_extended):
    if any(finger_states) or not thumb_extended:
        return False

    # Use the palm's own axis rather than image Y.  The thumb must point away
    # from the palm in roughly the same direction as the wrist->middle-MCP axis.
    palm_axis = _unit(
        (
            points[MIDDLE_MCP][0] - points[WRIST][0],
            points[MIDDLE_MCP][1] - points[WRIST][1],
        )
    )
    thumb_axis = _unit(
        (
            points[THUMB_TIP][0] - points[THUMB_MCP][0],
            points[THUMB_TIP][1] - points[THUMB_MCP][1],
        )
    )

    # In image coordinates, this is only a secondary guard.  The geometry
    # above keeps the test tied to the hand instead of the camera.
    return _dot(palm_axis, thumb_axis) > 0.15


def classify_static_shape(points, config):
    """Return the best static gesture label."""
    geometry = config.get("finger_geometry", {})
    index, middle, ring, pinky = get_finger_states(points, geometry)
    thumb = is_thumb_extended(points, geometry)

    pinch_distance = distance(points[THUMB_TIP], points[INDEX_TIP]) / palm_size(points)
    pinch_start = float(config["pinch"].get("start_normalized", 0.42))

    # Pinch first.  The normalized distance is independent of camera distance.
    if pinch_distance <= pinch_start and not is_fist_like(
        points, float(config.get("fist_pinch_ratio", 1.35))
    ):
        if not middle and not ring and not pinky:
            return "PINCH"
        if middle and ring and pinky:
            return "OK_SIGN"

    if is_thumb_up(points, (index, middle, ring, pinky), thumb):
        return "THUMB_UP"

    if index and not middle and not ring and not pinky:
        return "POINT"

    if index and middle and not ring and not pinky:
        return "TWO_FINGER"

    # IMPORTANT: four fingers is deliberately checked before open palm.
    # Open palm requires a confidently extended thumb.
    if index and middle and ring and pinky:
        return "OPEN_PALM" if thumb else "FOUR_FINGER"

    if index and middle and ring and not pinky:
        return "THREE_FINGER"

    if not index and not middle and not ring and not pinky:
        return "FIST"

    return "UNKNOWN"


def get_diagnostics(points, config):
    """Small diagnostic payload for the camera overlay."""
    geometry = config.get("finger_geometry", {})
    states = get_finger_states(points, geometry)
    tm = thumb_metrics(points)
    return {
        "fingers": states,
        "thumb": is_thumb_extended(points, geometry),
        "pip_angles": [round(finger_metrics(points, *f)["pip_angle"]) for f in FINGER_DATA],
        "dip_angles": [round(finger_metrics(points, *f)["dip_angle"]) for f in FINGER_DATA],
        "thumb_angles": (round(tm["mcp_angle"]), round(tm["ip_angle"])),
        "thumb_reach": round(tm["reach"], 2),
        "pinch": round(
            distance(points[THUMB_TIP], points[INDEX_TIP]) / palm_size(points),
            2,
        ),
    }
