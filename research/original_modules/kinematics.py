"""
WATHBA — kinematics.py
Shared KPI extraction core.

THE GOLDEN RULE
---------------
Mocap reference data and pose-model video output must pass through the
SAME compute_kpis() function. Different code paths make the comparison
methodologically invalid. If you need model-specific handling, put it in
the ADAPTER, never in the KPI functions.

Pipeline shape:
    any source  ->  adapter  ->  StandardPose  ->  compute_kpis()  ->  dict
"""

import numpy as np
from scipy.signal import savgol_filter, find_peaks

# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────
G = 9.81

# AthleticsPose raw_markers_in_world: (frames, 84, 3), millimetres, world coords
AP_AXES = {'H': 0, 'LAT': 1, 'V': 2}   # X=travel, Y=lateral, Z=vertical

AP_MARKERS = {
    'foot_R':  [15, 16, 17, 18, 19, 20, 21],
    'foot_L':  [33, 34, 35, 36, 37, 38, 39],
    'shank_R': [9, 10, 11, 12, 13, 14],
    'shank_L': [27, 28, 29, 30, 31, 32],
    'pelvis':  [0, 1, 2, 3, 4, 5, 6, 7, 22, 23, 24, 25, 83],
    'torso':   [44, 45, 46, 53, 54, 55, 56, 68, 69, 70, 71],
    'head':    [47, 48, 49, 50, 51, 52],
}

# MediaPipe Pose — 33 landmarks
MP_JOINTS = {
    'ankle_L': 27, 'ankle_R': 28,
    'foot_L':  31, 'foot_R':  32,   # foot index
    'heel_L':  29, 'heel_R':  30,
    'knee_L':  25, 'knee_R':  26,
    'hip_L':   23, 'hip_R':   24,
    'shoulder_L': 11, 'shoulder_R': 12,
    'nose': 0,
}

# YOLO-Pose / COCO — 17 keypoints
YOLO_JOINTS = {
    'ankle_L': 15, 'ankle_R': 16,
    'knee_L':  13, 'knee_R':  14,
    'hip_L':   11, 'hip_R':   12,
    'shoulder_L': 5, 'shoulder_R': 6,
    'nose': 0,
}
# NOTE: COCO has NO heel or foot-index points. Foot-strike detection from
# COCO must use the ankle only. Expect slightly later strike timing than
# MediaPipe, which can use heel/toe. Quantify this offset before comparing.


# ─────────────────────────────────────────────────────────────
# STANDARD POSE CONTRACT
# ─────────────────────────────────────────────────────────────
class StandardPose:
    """
    Unified representation every source must be converted into.

    foot_R_v, foot_L_v : (n_frames,) vertical height of each foot, higher = up
    pelvis_h           : (n_frames,) horizontal position (travel axis)
    joints             : dict of name -> (n_frames, 3) for angle computation
    fps                : float
    height_m           : float or None (body height, for normalisation)
    scale_to_m         : float or None; multiply raw units to get metres.
                         None means horizontal distance is uncalibrated.
    source             : str, for provenance
    """

    def __init__(self, foot_R_v, foot_L_v, pelvis_h, joints,
                 fps, height_m=None, scale_to_m=1.0, source='unknown'):
        self.foot_R_v   = np.asarray(foot_R_v, dtype=float)
        self.foot_L_v   = np.asarray(foot_L_v, dtype=float)
        self.pelvis_h   = np.asarray(pelvis_h, dtype=float)
        self.joints     = joints
        self.fps        = float(fps)
        self.height_m   = height_m
        self.scale_to_m = None if scale_to_m is None else float(scale_to_m)
        self.source     = source

        n = len(self.foot_R_v)
        if n == 0 or len(self.foot_L_v) != n or len(self.pelvis_h) != n:
            raise ValueError('foot and pelvis signals must be non-empty and have equal length')
        if not np.isfinite(self.fps) or self.fps <= 0:
            raise ValueError('fps must be a positive finite number')
        if self.height_m is not None:
            self.height_m = float(self.height_m)
            if not np.isfinite(self.height_m) or self.height_m <= 0:
                raise ValueError('height_m must be positive when provided')
        if self.scale_to_m is not None and (
                not np.isfinite(self.scale_to_m) or self.scale_to_m <= 0):
            raise ValueError('scale_to_m must be positive or None')
        required = {'hip', 'knee_R', 'knee_L', 'ankle_R', 'ankle_L', 'shoulder'}
        missing = required.difference(joints)
        if missing:
            raise ValueError(f'missing required joints: {sorted(missing)}')
        self.joints = {name: np.asarray(value, dtype=float)
                       for name, value in joints.items()}
        if any(len(value) != n for value in self.joints.values()):
            raise ValueError('all joint signals must match the number of frames')

    @property
    def n_frames(self):
        return len(self.foot_R_v)


# ─────────────────────────────────────────────────────────────
# ADAPTERS  — model-specific code lives ONLY here
# ─────────────────────────────────────────────────────────────
def from_athleticspose(p, fps=60, height_m=None):
    """p: (frames, 84, 3) raw_markers_in_world, millimetres."""
    p = np.asarray(p, dtype=float)
    if p.ndim != 3 or p.shape[1:] != (84, 3):
        raise ValueError('AthleticsPose input must have shape (frames, 84, 3)')
    V, H = AP_AXES['V'], AP_AXES['H']
    joints = {
        'hip':      p[:, AP_MARKERS['pelvis'], :].mean(axis=1),
        'knee_R':   p[:, AP_MARKERS['shank_R'], :].mean(axis=1),
        'knee_L':   p[:, AP_MARKERS['shank_L'], :].mean(axis=1),
        'ankle_R':  p[:, AP_MARKERS['foot_R'], :].mean(axis=1),
        'ankle_L':  p[:, AP_MARKERS['foot_L'], :].mean(axis=1),
        'shoulder': p[:, AP_MARKERS['torso'], :].mean(axis=1),
    }
    if height_m is None:
        head_z = p[:, AP_MARKERS['head'], V].max()
        ground = p[:, :, V].min()
        height_m = (head_z - ground) / 1000 * 1.02

    return StandardPose(
        foot_R_v = p[:, AP_MARKERS['foot_R'], V].min(axis=1),
        foot_L_v = p[:, AP_MARKERS['foot_L'], V].min(axis=1),
        pelvis_h = p[:, AP_MARKERS['pelvis'], H].mean(axis=1),
        joints=joints, fps=fps, height_m=height_m,
        scale_to_m=0.001, source='athleticspose')


def from_mediapipe(world_landmarks, fps, height_m,
                   pelvis_h=None, pelvis_scale_to_m=None):
    """
    world_landmarks: (frames, 33, 3) from results.pose_world_landmarks,
    metres, origin near the hip centre. Y increases DOWNWARD -> we flip it.

    pelvis_h: optional global/calibrated horizontal pelvis trajectory. Raw
    pose_world_landmarks are body-centred and cannot measure forward travel.
    pelvis_scale_to_m: multiplier that converts pelvis_h units to metres.
    Without both values, step length and speed are intentionally unavailable.
    """
    lm = np.asarray(world_landmarks, dtype=float)
    if lm.ndim != 3 or lm.shape[1:] != (33, 3):
        raise ValueError('MediaPipe input must have shape (frames, 33, 3)')
    J = MP_JOINTS

    # MediaPipe Y grows downward, so max(Y) is the anatomically lowest point.
    foot_R = np.maximum(lm[:, J['heel_R'], 1], lm[:, J['foot_R'], 1])
    foot_L = np.maximum(lm[:, J['heel_L'], 1], lm[:, J['foot_L'], 1])

    joints = {
        'hip':      lm[:, [J['hip_L'],  J['hip_R']],  :].mean(axis=1),
        'knee_R':   lm[:, J['knee_R'],  :],
        'knee_L':   lm[:, J['knee_L'],  :],
        'ankle_R':  lm[:, J['ankle_R'], :],
        'ankle_L':  lm[:, J['ankle_L'], :],
        'shoulder': lm[:, [J['shoulder_L'], J['shoulder_R']], :].mean(axis=1),
    }
    if pelvis_h is None:
        pelvis_track = lm[:, [J['hip_L'], J['hip_R']], 0].mean(axis=1)
        scale_to_m = None
    else:
        pelvis_track = np.asarray(pelvis_h, dtype=float)
        if pelvis_track.shape != (len(lm),):
            raise ValueError('pelvis_h must have shape (frames,)')
        if pelvis_scale_to_m is None:
            raise ValueError('pelvis_scale_to_m is required when pelvis_h is provided')
        scale_to_m = pelvis_scale_to_m

    return StandardPose(
        foot_R_v = -foot_R,                       # flip: higher = up
        foot_L_v = -foot_L,
        pelvis_h = pelvis_track,
        joints=joints, fps=fps, height_m=height_m,
        scale_to_m=scale_to_m, source='mediapipe')


def from_yolo(keypoints, fps, height_m, image_h=1.0, pixel_to_m=None):
    """
    keypoints: (frames, 17, 2 or 3) COCO order, IMAGE pixel coordinates.
    Y increases downward -> flipped.

    WARNING: this is 2D. Depth is unavailable, so joint angles are the
    projected angle, not the true 3D angle. Angles from YOLO are only
    comparable to mocap for near-perfect side views. Flag them as low
    confidence anywhere else.
    """
    kp = np.asarray(keypoints, dtype=float)
    if kp.ndim != 3 or kp.shape[1] != 17 or kp.shape[2] not in (2, 3):
        raise ValueError('YOLO input must have shape (frames, 17, 2 or 3)')
    if image_h is not None and (not np.isfinite(image_h) or image_h <= 0):
        raise ValueError('image_h must be positive when provided')
    J = YOLO_JOINTS

    joints = {
        'hip':      kp[:, [J['hip_L'],  J['hip_R']],  :2].mean(axis=1),
        'knee_R':   kp[:, J['knee_R'],  :2],
        'knee_L':   kp[:, J['knee_L'],  :2],
        'ankle_R':  kp[:, J['ankle_R'], :2],
        'ankle_L':  kp[:, J['ankle_L'], :2],
        'shoulder': kp[:, [J['shoulder_L'], J['shoulder_R']], :2].mean(axis=1),
    }
    return StandardPose(
        foot_R_v = -kp[:, J['ankle_R'], 1],       # ankle only — no heel in COCO
        foot_L_v = -kp[:, J['ankle_L'], 1],
        pelvis_h = kp[:, [J['hip_L'], J['hip_R']], 0].mean(axis=1),
        joints=joints, fps=fps, height_m=height_m,
        scale_to_m=pixel_to_m, source='yolo')     # None = uncalibrated


# ─────────────────────────────────────────────────────────────
# CORE SIGNAL PROCESSING
# ─────────────────────────────────────────────────────────────
def detect_strikes(foot_v, fps, min_cycle_s=0.30, prom_frac=0.30):
    """
    Foot strikes = local minima of foot height.
    min_cycle_s targets a FULL stride cycle for one foot (~0.45 s at
    sprint pace). Set it too low and you double-detect: a step rate of
    8+ Hz is the classic symptom.
    """
    foot_v = np.asarray(foot_v, dtype=float)
    n = len(foot_v)
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError('fps must be positive')
    if n == 0 or not np.all(np.isfinite(foot_v)):
        return np.array([], dtype=int), foot_v
    w = min(9, n - 1 if n % 2 == 0 else n)
    if w < 5:
        return np.array([], dtype=int), foot_v
    sm = savgol_filter(foot_v, w, 2)
    span = sm.max() - sm.min()
    if span <= 0:
        return np.array([], dtype=int), sm
    pk, _ = find_peaks(-sm, distance=max(2, int(fps * min_cycle_s)),
                       prominence=span * prom_frac)
    return pk, sm


def contact_time(foot_v, strikes, fps, thr_frac=0.15,
                 lo=0.06, hi=0.25):
    """Frames the foot stays below a near-ground threshold."""
    foot_v = np.asarray(foot_v, dtype=float)
    if len(strikes) == 0 or not np.all(np.isfinite(foot_v)):
        return np.nan
    thr = foot_v.min() + (np.percentile(foot_v, 90) - foot_v.min()) * thr_frac
    out = []
    for s in strikes:
        i = j = int(s)
        while i < len(foot_v) - 1 and foot_v[i] <= thr:
            i += 1
        while j > 0 and foot_v[j] <= thr:
            j -= 1
        ct = (i - j) / fps
        if lo < ct < hi:
            out.append(ct)
    return float(np.median(out)) if out else np.nan


def joint_angle(a, b, c):
    """Angle at b, formed by a-b-c. Works in 2D or 3D."""
    v1, v2 = np.asarray(a) - np.asarray(b), np.asarray(c) - np.asarray(b)
    denom = np.linalg.norm(v1) * np.linalg.norm(v2)
    if not np.isfinite(denom) or denom < 1e-9:
        return np.nan
    cosine = np.dot(v1, v2) / denom
    if not np.isfinite(cosine):
        return np.nan
    return float(np.degrees(np.arccos(np.clip(cosine, -1, 1))))


# ─────────────────────────────────────────────────────────────
# KPI EXTRACTION  — one function, every source
# ─────────────────────────────────────────────────────────────
VALIDITY = {
    'stride_s':    (0.30, 1.20),
    'step_len_m':  (0.60, 2.90),
    'flight_s':    (0.03, 0.20),
    'min_strikes': 4,
}


def compute_kpis(sp: StandardPose, validate=True):
    """
    Returns a dict matching the WATHBA data contract, or None if the
    clip fails validity checks. Never returns a partially-invented result.
    """
    sR, _ = detect_strikes(sp.foot_R_v, sp.fps)
    sL, _ = detect_strikes(sp.foot_L_v, sp.fps)
    if len(sR) < 2 or len(sL) < 2:
        return None

    all_s = np.sort(np.concatenate([sR, sL]))
    if validate and len(all_s) < VALIDITY['min_strikes']:
        return None

    stride_s = float(np.median(np.concatenate([np.diff(sR), np.diff(sL)])) / sp.fps)
    if validate and not (VALIDITY['stride_s'][0] < stride_s < VALIDITY['stride_s'][1]):
        return None

    step_f = 2.0 / stride_s                      # step = half a stride cycle
    step_t = stride_s / 2.0

    # step length
    if sp.scale_to_m is None:
        step_l = np.nan                          # uncalibrated source
    else:
        step_l = float(np.median(np.abs(np.diff(sp.pelvis_h[all_s]))) * sp.scale_to_m)
        if validate and not (VALIDITY['step_len_m'][0] < step_l < VALIDITY['step_len_m'][1]):
            return None

    contacts = np.asarray([contact_time(sp.foot_R_v, sR, sp.fps),
                           contact_time(sp.foot_L_v, sL, sp.fps)], dtype=float)
    finite_contacts = contacts[np.isfinite(contacts)]
    gct = float(np.median(finite_contacts)) if len(finite_contacts) else np.nan
    flight = step_t - gct if np.isfinite(gct) else np.nan
    if validate and not np.isfinite(gct):
        return None
    if validate and not np.isnan(flight):
        if not (VALIDITY['flight_s'][0] < flight < VALIDITY['flight_s'][1]):
            return None

    # knee angle at touchdown, and minimum during stance
    J = sp.joints
    knee_td, knee_min = [], []
    for side, strikes in (('R', sR), ('L', sL)):
        for s in strikes:
            s = int(s)
            knee_td.append(joint_angle(J['hip'][s], J[f'knee_{side}'][s],
                                       J[f'ankle_{side}'][s]))
            end = min(s + int(sp.fps * 0.12), len(J['hip']) - 1)
            if end > s:
                stance_angles = [
                    joint_angle(J['hip'][k], J[f'knee_{side}'][k],
                                J[f'ankle_{side}'][k])
                    for k in range(s, end)]
                stance_angles = [x for x in stance_angles if np.isfinite(x)]
                if stance_angles:
                    knee_min.append(min(stance_angles))
    knee_td = [x for x in knee_td if np.isfinite(x)]
    knee_touchdown = float(np.median(knee_td)) if knee_td else np.nan
    knee_minimum   = float(np.median(knee_min)) if knee_min else np.nan

    # trunk lean from vertical
    H = 0
    V = 1 if sp.source in ('mediapipe', 'yolo') else 2
    dh = np.abs(J['shoulder'][:, H] - J['hip'][:, H])
    dv = np.abs(J['shoulder'][:, V] - J['hip'][:, V])
    trunk = float(np.median(np.degrees(np.arctan2(dh, dv))))

    knee_delta = (knee_touchdown - knee_minimum
                  if np.isfinite(knee_touchdown) and np.isfinite(knee_minimum)
                  else np.nan)
    kpis = {
        # primary
        'step_frequency':       round(step_f, 3),
        'step_length':          round(step_l, 3) if not np.isnan(step_l) else None,
        'ground_contact_time':  round(gct, 4),
        'flight_time':          round(flight, 4),
        'knee_angle_strike':    round(knee_touchdown, 1) if np.isfinite(knee_touchdown) else None,
        'knee_angle_touchdown': round(knee_touchdown, 1) if np.isfinite(knee_touchdown) else None,
        'knee_angle_min':       round(knee_minimum, 1) if np.isfinite(knee_minimum) else None,
        'trunk_lean':           round(trunk, 1),
        # derived — dimensionless, these are what we actually compare
        'knee_delta':           round(knee_delta, 1) if np.isfinite(knee_delta) else None,
        'duty_factor':          round(gct / step_t, 3),
        'contact_flight_ratio': round(gct / flight, 3) if np.isfinite(flight) and flight > 0 else None,
        # context
        'n_steps':              int(len(all_s)),
        'n_strides':            int(max(0, (len(all_s) - 1) // 2)),
        'fps':                  sp.fps,
        'source':               sp.source,
    }

    if np.isfinite(step_l) and sp.height_m is not None:
        speed = step_l * step_f
        kpis.update({
            'speed':            round(speed, 3),
            'rel_step_length':  round(step_l / sp.height_m, 3),
            'norm_step_freq':   round(float(step_f * np.sqrt(sp.height_m / G)), 3),
            'norm_speed':       round(float(speed / np.sqrt(G * sp.height_m)), 3),
            'froude_number':    round(float(speed ** 2 / (G * sp.height_m)), 3),
        })

    # asymmetry
    if len(sR) > 1 and len(sL) > 1:
        tR, tL = np.median(np.diff(sR)), np.median(np.diff(sL))
        asymmetry = abs(tR - tL) / np.mean([tR, tL]) * 100
        kpis['asym_step_time'] = round(float(asymmetry), 1)

    return kpis


# ─────────────────────────────────────────────────────────────
# VALIDATION HARNESS — for the pose-model comparison
# ─────────────────────────────────────────────────────────────
KPI_TOLERANCE = {
    'step_frequency':       0.15,   # Hz
    'ground_contact_time':  0.015,  # s
    'flight_time':          0.015,  # s
    'duty_factor':          0.05,
    'contact_flight_ratio': 0.15,
    'rel_step_length':      0.08,
    'knee_angle_touchdown': 8.0,    # degrees
    'knee_delta':           6.0,
}


def compare_kpis(ref, test, tolerance=None):
    """
    ref  : KPIs from mocap ground truth
    test : KPIs from a pose model on the same clip
    Returns a per-KPI table of error and pass/fail against tolerance.
    """
    tol = tolerance or KPI_TOLERANCE
    rows = []
    for k, t in tol.items():
        a, b = ref.get(k), test.get(k)
        if (a is None or b is None or not np.isscalar(a) or not np.isscalar(b)
                or not np.isfinite(a) or not np.isfinite(b)):
            rows.append({'kpi': k, 'ref': a, 'test': b,
                         'abs_err': None, 'pct_err': None,
                         'tolerance': t, 'passes': None})
            continue
        err = abs(b - a)
        rows.append({'kpi': k, 'ref': round(a, 4), 'test': round(b, 4),
                     'abs_err': round(err, 4),
                     'pct_err': round(err / abs(a) * 100, 1) if a else None,
                     'tolerance': t, 'passes': bool(err <= t)})
    return rows


def strike_timing_error(strikes_ref, strikes_test, fps):
    """
    Match each reference strike to its nearest detected strike.
    This is the most diagnostic single check: if strike timing is wrong,
    every temporal KPI is wrong downstream.
    """
    if len(strikes_ref) == 0 or len(strikes_test) == 0:
        return None
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError('fps must be positive')

    # Greedy one-to-one matching prevents one test strike from being reused
    # for several reference strikes and hiding missed detections.
    available = [int(t) for t in strikes_test]
    errs = []
    for r in sorted(int(x) for x in strikes_ref):
        if not available:
            break
        idx = min(range(len(available)), key=lambda i: abs(r - available[i]))
        errs.append(abs(r - available.pop(idx)) / fps)
    if not errs:
        return None
    return {
        'n_ref': len(strikes_ref),
        'n_test': len(strikes_test),
        'count_diff': len(strikes_test) - len(strikes_ref),
        'mean_err_ms': round(float(np.mean(errs)) * 1000, 1),
        'max_err_ms':  round(float(np.max(errs)) * 1000, 1),
        'frames_at_fps': round(float(np.mean(errs)) * fps, 2),
    }
