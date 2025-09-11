try:
    import cv2
    import numpy as np
    from . import utils
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

def _get_main_contour(frame):
    """Helper function to find the largest contour in a frame."""
    if frame is None:
        return None, 0

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None, 0

    # Find the largest contour by area
    main_contour = max(contours, key=cv2.contourArea)
    
    # Filter out very small contours that are likely noise
    if cv2.contourArea(main_contour) < 200:
        return None, 0
    
    # Calculate aspect ratio of the bounding box
    x, y, w, h = cv2.boundingRect(main_contour)
    aspect_ratio = w / h if h > 0 else 0
    
    return main_contour, aspect_ratio

def analyze_shatter(frame_before, frame_after):
    """Analyzes frames for shattering, suitable for brittle materials like glass."""
    config = utils.load_analysis_config()
    
    # --- Check if a bottle is present before impact ---
    contour_before, _ = _get_main_contour(frame_before)
    if contour_before is None:
        return {"result": "ERROR", "reason": "No bottle detected in the frame before impact."}

    # --- Pre-processing ---
    gray_before = cv2.cvtColor(frame_before, cv2.COLOR_BGR2GRAY)
    gray_after = cv2.cvtColor(frame_after, cv2.COLOR_BGR2GRAY)
    blurred_before = cv2.GaussianBlur(gray_before, (7, 7), 0)
    blurred_after = cv2.GaussianBlur(gray_after, (7, 7), 0)

    # --- Edge Detection ---
    edges_before = cv2.Canny(blurred_before, 50, 150)
    edges_after = cv2.Canny(blurred_after, 50, 150)

    # --- Contour Analysis ---
    contours_before, _ = cv2.findContours(edges_before, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours_after, _ = cv2.findContours(edges_after, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter out small noise contours
    min_contour_area = 75
    filtered_contours_before = [c for c in contours_before if cv2.contourArea(c) > min_contour_area]
    filtered_contours_after = [c for c in contours_after if cv2.contourArea(c) > min_contour_area]

    count_before = len(filtered_contours_before)
    count_after = len(filtered_contours_after)
    
    if count_before == 0: count_before = 1 # Avoid division by zero

    contour_increase_ratio = count_after / count_before

    # If contour count more than doubles and there are at least 5 pieces, it's a fail.
    if (contour_increase_ratio > config['shatter_contour_increase_ratio'] and 
        count_after >= config['shatter_min_contour_count']):
        reason = f"FAIL: Shattered. Contour count increased from {count_before} to {count_after}."
        return {"result": "FAIL", "reason": reason, "metric": "shatter_ratio", "value": contour_increase_ratio}
    else:
        reason = f"PASS: Not shattered. Contour count changed from {count_before} to {count_after}."
        return {"result": "PASS", "reason": reason, "metric": "shatter_ratio", "value": contour_increase_ratio}

def analyze_deformation(frame_before, frame_after):
    """Analyzes frames for deformation or spillage, suitable for plastic or steel bottles."""
    config = utils.load_analysis_config()
    
    # --- 1. Deformation Analysis ---
    contour_before, ratio_before = _get_main_contour(frame_before)
    contour_after, ratio_after = _get_main_contour(frame_after)

    if contour_before is None:
        return {"result": "ERROR", "reason": "No bottle detected in the frame before impact."}
    if contour_after is None:
        return {"result": "ERROR", "reason": "No bottle detected in the frame after impact."}

    if ratio_before > 0:
        ratio_change = abs(ratio_after - ratio_before) / ratio_before
    else:
        ratio_change = 0

    if ratio_change > config['deformation_threshold']:
        reason = f"FAIL: Deformed. Aspect ratio changed by {ratio_change:.1%}"
        return {"result": "FAIL", "reason": reason, "metric": "deformation", "value": ratio_change}

    # --- 2. Spill Detection Analysis ---
    gray_after = cv2.cvtColor(frame_after, cv2.COLOR_BGR2GRAY)
    blurred_after = cv2.GaussianBlur(gray_after, (7, 7), 0)
    edges_after = cv2.Canny(blurred_after, 50, 150)
    all_contours_after, _ = cv2.findContours(edges_after, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not all_contours_after:
        reason = f"PASS: No significant deformation. Aspect ratio change: {ratio_change:.1%}"
        return {"result": "PASS", "reason": reason, "metric": "deformation", "value": ratio_change}

    bottle_area = cv2.contourArea(contour_after)
    x_bottle, y_bottle, w_bottle, h_bottle = cv2.boundingRect(contour_after)
    
    spill_contours_found = 0
    max_spill_area = 0

    for c in all_contours_after:
        # Create a representation of the contour 'c' that is comparable to 'contour_after'
        # This check is to avoid comparing the bottle with itself.
        if len(c) == len(contour_after) and np.all(c == contour_after):
            continue

        area = cv2.contourArea(c)
        
        if area > config['spill_min_area'] and area < bottle_area * 0.5:
            x_c, y_c, w_c, h_c = cv2.boundingRect(c)
            contour_top_y = y_c
            
            # A spill should be located on the ground, near the bottle's base.
            # We check if the top of the potential spill contour is below the bottle's vertical midpoint.
            if contour_top_y > (y_bottle + h_bottle * 0.6):
                spill_contours_found += 1
                if area > max_spill_area:
                    max_spill_area = area
    
    if spill_contours_found > 0:
        reason = f"FAIL: Water spill detected. Found {spill_contours_found} potential spill puddle(s)."
        return {"result": "FAIL", "reason": reason, "metric": "spill_area", "value": max_spill_area}

    # --- 3. If both checks pass ---
    reason = f"PASS: No significant deformation or spillage. Aspect ratio change: {ratio_change:.1%}"
    return {"result": "PASS", "reason": reason, "metric": "deformation", "value": ratio_change}

def analyze_bottle(frame_before, frame_after, material_type="Plastic"):
    """
    Main analysis function that dispatches to the correct analysis method
    based on the bottle's material type.
    """
    if not CV2_AVAILABLE:
        return {"result": "ERROR", "reason": "OpenCV is not available."}
    if frame_before is None or frame_after is None:
        return {"result": "ERROR", "reason": "Invalid input frames provided."}

    if material_type in ["Plastic", "Steel"]:
        return analyze_deformation(frame_before, frame_after)
    else:  # Default to Glass/Brittle
        return analyze_shatter(frame_before, frame_after)


def pick_impact_frames(video_path: str,
                       coarse_stride: int = 3,
                       refine_window: int = 30,
                       ignore_edge: int = 10,
                       offset_frames: int = 12):
    """
    Locate the impact moment by peak motion energy and return
    (frame_before, frame_after) around the peak.

    Parameters:
      - coarse_stride: sampling stride for coarse scan (>=1)
      - refine_window: +/- frames around coarse peak for fine scan
      - ignore_edge: ignore first/last N frames to reduce camera auto-exposure spikes
      - offset_frames: frames before/after the detected peak to sample

    Returns: (frame_before_BGR, frame_after_BGR)
    Raises: RuntimeError on failure.
    """
    if not CV2_AVAILABLE:
        raise RuntimeError("OpenCV not available")
    if coarse_stride < 1:
        coarse_stride = 1

    cap = cv2.VideoCapture(video_path)
    if not cap or not cap.isOpened():
        raise RuntimeError("Cannot open video")

    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 2:
            raise RuntimeError("Video too short")

        start_idx = max(1, ignore_edge)
        end_idx = max(start_idx + 1, total - 1 - ignore_edge)
        if start_idx >= end_idx:
            start_idx, end_idx = 1, total - 1

        # Helper: read frame at index
        def read_at(idx):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, f = cap.read()
            return ok, f

        # Convert to gray blurred
        def to_gray(f):
            g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            return cv2.GaussianBlur(g, (5, 5), 0)

        # Coarse pass
        best_score, best_idx = -1.0, start_idx
        ok_prev, prev = read_at(start_idx - 1)
        if not ok_prev or prev is None:
            ok_prev, prev = read_at(start_idx)
        prev_g = to_gray(prev)

        for idx in range(start_idx, end_idx + 1, coarse_stride):
            ok, cur = read_at(idx)
            if not ok or cur is None:
                continue
            cur_g = to_gray(cur)
            diff = cv2.absdiff(cur_g, prev_g)
            score = float(diff.mean())
            if score > best_score:
                best_score, best_idx = score, idx
            prev_g = cur_g

        # Fine pass around coarse peak
        win_lo = max(1, best_idx - refine_window)
        win_hi = min(total - 1, best_idx + refine_window)
        best_score_f, peak = -1.0, best_idx

        ok_prev, prev = read_at(win_lo - 1)
        if not ok_prev or prev is None:
            ok_prev, prev = read_at(win_lo)
        prev_g = to_gray(prev)

        for idx in range(win_lo, win_hi + 1):
            ok, cur = read_at(idx)
            if not ok or cur is None:
                continue
            cur_g = to_gray(cur)
            diff = cv2.absdiff(cur_g, prev_g)
            score = float(diff.mean())
            if score > best_score_f:
                best_score_f, peak = score, idx
            prev_g = cur_g

        before_idx = max(0, peak - offset_frames)
        after_idx = min(total - 1, peak + offset_frames)

        ok_b, frame_before = read_at(before_idx)
        ok_a, frame_after = read_at(after_idx)
        if not ok_b or frame_before is None or not ok_a or frame_after is None:
            raise RuntimeError("Failed to read before/after frames")
        return frame_before, frame_after
    finally:
        try:
            cap.release()
        except Exception:
            pass