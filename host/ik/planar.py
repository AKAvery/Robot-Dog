# host/ik/planar.py
import math

def ik2d(foot_x, foot_z, L_thigh=84.0, L_foot=127.0, elbow="down"):
    """
    Returns logical joint angles (hip, knee) in degrees.
    Conventions: +x forward, +z down. Positive angles bend DOWN.
    'elbow' can be 'down' or 'up' to choose the IK branch.
    """
    h = max(1e-6, abs(float(foot_x)))
    z = float(foot_z)
    l = min(math.hypot(h, z), L_thigh + L_foot - 1e-6)

    # interior angle at the knee: 0 = straight, 180 = folded on itself
    cos_k = (L_thigh**2 + L_foot**2 - l**2) / (2 * L_thigh * L_foot)
    cos_k = max(-1.0, min(1.0, cos_k))
    knee = math.degrees(math.acos(cos_k))

    cos_h = (L_thigh**2 + l**2 - L_foot**2) / (2 * L_thigh * l)
    cos_h = max(-1.0, min(1.0, cos_h))
    base = math.degrees(math.atan2(z, h))
    delta = math.degrees(math.acos(cos_h))

    hip = base - delta if elbow == "down" else base + delta
    return hip, knee

def to_servo(deg, reverse=False, offset=0.0):
    a = (deg + offset)
    if reverse:
        a = -a
    return max(0, min(180, int(round(90 + a))))
