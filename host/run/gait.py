# host/run/gait.py
import math
from typing import Dict, Tuple

ORDER = ["LF", "RF", "LR", "RR"]

def foot_path(x0: float, z0: float, stride: float, lift: float, beta: float, phase: float) -> Tuple[float, float]:
    """
    One-cycle foot path with duty factor beta (0<beta<1).
    phase in [0,1): [0, beta) stance; [beta,1) swing.
    Stance: flat on ground, move backward by 'stride'
    Swing : forward + up (half-sine lift)
    """
    phase = phase % 1.0
    if phase < beta:
        # stance: on ground, moving backward
        s = phase / beta
        x = x0 + (stride/2) - stride * s
        z = z0
    else:
        # swing: forward + up (half-sine)
        s = (phase - beta) / (1.0 - beta)  # 0..1
        x = x0 - (stride/2) + stride * s
        z = z0 - lift * math.sin(math.pi * s)
    return x, z

def phases_for_gait(gait: str) -> Dict[str, float]:
    """
    Phase offsets per leg for common gaits.
    Trot: diagonal pairs in opposition.
    """
    if gait == "trot":
        return {"LF": 0.0, "RR": 0.0, "RF": 0.5, "LR": 0.5}
    if gait == "pace":
        return {"LF": 0.0, "LR": 0.0, "RF": 0.5, "RR": 0.5}
    # default to a simple walk-ish pattern
    return {"LF": 0.00, "RF": 0.25, "RR": 0.50, "LR": 0.75}

def gait_targets(t: float, hz: float, gait: str, x0: float, z0: float,
                 stride: float, lift: float, beta: float) -> Dict[str, Tuple[float, float]]:
    p = phases_for_gait(gait)
    out = {}
    for leg in ORDER:
        phase = (t * hz + p[leg]) % 1.0
        out[leg] = foot_path(x0, z0, stride, lift, beta, phase)
    return out
