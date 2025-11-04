# host/run/fit_rest_pose.py
import math, json, argparse, os
from pathlib import Path

def fk2d(hip_deg, knee_deg, L_thigh, L_foot):
    # Same forward-kinematics convention as server_view.py
    hip = math.radians(hip_deg)
    knee = math.radians(knee_deg)
    x1 = L_thigh * math.cos(hip)
    z1 = -L_thigh * math.sin(hip)
    x2 = x1 + L_foot * math.cos(hip + knee)
    z2 = z1 - L_foot * math.sin(hip + knee)
    return x2, -z2  # return with z positive-down for geometry.json

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hip",  type=float, required=True, help="hip-pitch at rest (deg, 0=horiz, +down)")
    ap.add_argument("--knee", type=float, required=True, help="knee at rest (deg, 0=straight, +bent)")
    ap.add_argument("--thigh", type=float, default=96.0)
    ap.add_argument("--foot",  type=float, default=125.0)
    ap.add_argument("--write", action="store_true", help="write geometry.json & calibration.json")
    a = ap.parse_args()

    x0, z0 = fk2d(a.hip, a.knee, a.thigh, a.foot)
    print(f"Neutral foot position that matches rest angles:")
    print(f"  x ≈ {x0:.1f} mm forward from hip pivot")
    print(f"  z ≈ {z0:.1f} mm down from hip pivot")

    # Offsets so that to_servo(ang, offset) maps 'ang=rest' to packet=90
    off_hip  = -a.hip
    off_knee = -a.knee
    reverse = [False, True, True, True, False, True, True, True]  # tweak later on hardware

    print("\nSuggested calibration.json edits:")
    reverse_arr = reverse
    offsets_arr = [off_hip, off_knee, off_hip, off_knee, off_hip, off_knee, off_hip, off_knee]
    print(f'  "reverse": {json.dumps(reverse_arr)}')
    print(f'  "offset_deg": {json.dumps([round(x,1) for x in offsets_arr])}')

    if a.write:
        # Update geometry.json
        gpath = Path("host/config/geometry.json")
        if gpath.exists():
            geo = json.loads(gpath.read_text())
        else:
            geo = {"link_mm": {"hip_to_knee": 28, "thigh": a.thigh, "foot": a.foot},
                   "anchors_mm": {"LF":[74,39,0],"RF":[74,-39,0],"LR":[-74,39,0],"RR":[-74,-39,0]},
                   "neutral_pose": {}}
        geo["link_mm"]["thigh"] = a.thigh
        geo["link_mm"]["foot"]  = a.foot
        geo["neutral_pose"]     = {"x": round(x0,1), "z": round(z0,1)}
        gpath.write_text(json.dumps(geo, indent=2))

        # Update calibration.json
        cpath = Path("host/config/calibration.json")
        if cpath.exists():
            cal = json.loads(cpath.read_text())
        else:
            cal = {}
        cal["reverse"] = reverse_arr
        cal["offset_deg"] = [round(x,1) for x in offsets_arr]
        cpath.write_text(json.dumps(cal, indent=2))
        print("\nWrote host/config/geometry.json and calibration.json")

if __name__ == "__main__":
    main()
