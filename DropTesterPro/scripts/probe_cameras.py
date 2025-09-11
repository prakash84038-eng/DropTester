import time
import platform

try:
    import cv2
except Exception as e:
    print("OpenCV is required to run this probe:", e)
    raise SystemExit(1)

BACKENDS = []
if platform.system().lower().startswith("windows"):
    BACKENDS = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
elif platform.system().lower() == "darwin":
    BACKENDS = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
else:
    BACKENDS = [cv2.CAP_V4L2, cv2.CAP_ANY]

TARGET_W, TARGET_H, TARGET_FPS = 1280, 720, 60
WARMUP_SEC = 1.0
MEASURE_SEC = 3.0


def open_with_backends(index: int):
    last_err = None
    for b in BACKENDS:
        try:
            cap = cv2.VideoCapture(index, b)
            if cap is not None and cap.isOpened():
                return cap
            if cap is not None:
                cap.release()
        except Exception as e:
            last_err = e
    return None


def measure_camera(index: int):
    cap = open_with_backends(index)
    if cap is None or not cap.isOpened():
        return {
            "index": index,
            "opened": False,
            "error": "Could not open camera",
        }

    # Try MJPG
    try:
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        cap.set(cv2.CAP_PROP_FOURCC, fourcc)
    except Exception:
        pass

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_H)
    cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
    # Low buffer to reduce latency
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass

    # Read actuals
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    reported_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)

    # Warmup
    t0 = time.time()
    while time.time() - t0 < WARMUP_SEC:
        cap.read()

    # Measure
    f = 0
    t0 = time.time()
    while time.time() - t0 < MEASURE_SEC:
        ret, _ = cap.read()
        if not ret:
            break
        f += 1
    elapsed = max(1e-6, time.time() - t0)
    measured_fps = f / elapsed

    cap.release()
    result = {
        "index": index,
        "opened": True,
        "requested": {"w": TARGET_W, "h": TARGET_H, "fps": TARGET_FPS},
        "actual": {"w": actual_w, "h": actual_h},
        "reported_fps": round(reported_fps, 2),
        "measured_fps": round(measured_fps, 2),
    }
    # Simple pass criteria: actual 720p and measured fps >= ~55
    result["supports_720p60"] = (actual_w >= 1280 and actual_h >= 720 and measured_fps >= 55.0)
    return result


def detect_indices(max_check=12):
    found = []
    for i in range(max_check):
        cap = open_with_backends(i)
        if cap is not None and cap.isOpened():
            found.append(i)
            cap.release()
    return found


def main():
    idx = detect_indices()
    if not idx:
        print("No cameras found.")
        return
    print(f"Cameras detected: {idx}")
    for i in idx[:2]:
        res = measure_camera(i)
        print("-" * 60)
        print(f"Camera {i}:")
        if not res.get("opened"):
            print("  opened: False")
            print(f"  error: {res.get('error')}")
            continue
        print(f"  requested: {res['requested']}")
        print(f"  actual:    {res['actual']}")
        print(f"  reported_fps: {res['reported_fps']}")
        print(f"  measured_fps: {res['measured_fps']}")
        print(f"  supports_720p60: {res['supports_720p60']}")


if __name__ == "__main__":
    main()
