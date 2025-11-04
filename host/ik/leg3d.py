import math

def ik3dof(foot_xyz, anchor_xy, anchor_heading_deg, L_hip2knee=28.0, L_thigh=84.0, L_foot=127.0):
    x = foot_xyz[0] - anchor_xy[0]
    y = foot_xyz[1] - anchor_xy[1]
    z = foot_xyz[2]
    hip_yaw = math.degrees(math.atan2(y, x)) - anchor_heading_deg

    len_xy = math.hypot(x, y) or 1e-6
    x -= (x * L_hip2knee / len_xy)
    y -= (y * L_hip2knee / len_xy)

    h = math.hypot(x, y)
    l = math.hypot(h, z)
    l = min(l, L_thigh + L_foot - 1e-6)

    foot = math.degrees(math.acos((L_thigh**2 + L_foot**2 - l**2) / (2*L_thigh*L_foot)))
    knee = math.degrees(math.acos((L_thigh**2 + l**2 - L_foot**2) / (2*L_thigh*l)) + math.atan2(z, h))
    return hip_yaw, knee, foot

def to_servo(deg, reverse=False, offset=0.0):
    a = (deg + offset)
    if reverse: a = -a
    return max(0, min(180, int(round(90 + a))))
