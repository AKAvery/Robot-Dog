import math

def ik2d(foot_x, foot_z, L_thigh=84.0, L_foot=127.0):
    h = max(1e-6, abs(float(foot_x)))
    z = float(foot_z)
    l = math.hypot(h, z)
    l = min(l, L_thigh + L_foot - 1e-6)  # inside reach
    knee = math.degrees(math.acos((L_thigh**2 + L_foot**2 - l**2) / (2*L_thigh*L_foot)))
    hip  = math.degrees(math.atan2(z, h) + math.acos((L_thigh**2 + l**2 - L_foot**2) / (2*L_thigh*l)))
    return hip, knee

def to_servo(deg, reverse=False, offset=0.0):
    a = (deg + offset)
    if reverse: a = -a
    return max(0, min(180, int(round(90 + a))))
