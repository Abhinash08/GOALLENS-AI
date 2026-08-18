# ======================================================================
# BALL HIGHLIGHT SCORER — IMPROVED
# ======================================================================

import os
import numpy as np
import pandas as pd


# ======================================================================
# SETTINGS
# ======================================================================

# Ignore tiny movement
MIN_SPEED = 20.0

# Rolling smoothing
SMOOTHING_WINDOW = 9

# Robust speed cap
SPEED_CAP_PERCENTILE = 90

# Minimum normalized score for a peak
MIN_SCORE = 0.45

# Distance between selected peaks
MIN_PEAK_DISTANCE_SECONDS = 8.0

# Highlight duration
PRE_EVENT_SECONDS = 6.0
POST_EVENT_SECONDS = 6.0

MIN_HIGHLIGHT_DURATION = 8.0
MAX_HIGHLIGHT_DURATION = 14.0

# Minimum gap between final highlight windows
MIN_WINDOW_GAP_SECONDS = 3.0

# Maximum number of highlights
MAX_HIGHLIGHTS = 20


# ======================================================================
# LOAD TRAJECTORY
# ======================================================================

def load_trajectory(trajectory_csv):

    print("\nLOADING FINAL BALL TRAJECTORY")
    print("-" * 70)

    if not os.path.exists(trajectory_csv):

        raise FileNotFoundError(
            f"Trajectory CSV not found:\n{trajectory_csv}"
        )

    df = pd.read_csv(
        trajectory_csv
    )

    required_columns = [
        "frame",
        "time_sec",
        "center_x",
        "center_y",
        "status"
    ]

    missing = [
        c for c in required_columns
        if c not in df.columns
    ]

    if missing:

        raise ValueError(
            f"Missing required columns: {missing}"
        )

    for column in [
        "frame",
        "time_sec",
        "center_x",
        "center_y"
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.sort_values(
        "frame"
    ).reset_index(
        drop=True
    )

    print(
        f"Trajectory rows : {len(df):,}"
    )

    return df


# ======================================================================
# CALCULATE MOVEMENT
# ======================================================================

def calculate_movement(df):

    print("\nCALCULATING BALL MOVEMENT")
    print("-" * 70)

    result = df.copy()

    dx = result[
        "center_x"
    ].diff()

    dy = result[
        "center_y"
    ].diff()

    dt = result[
        "time_sec"
    ].diff()

    distance = np.sqrt(
        dx ** 2 +
        dy ** 2
    )

    dt = dt.replace(
        0,
        np.nan
    )

    speed = (
        distance /
        dt
    )

    speed = speed.replace(
        [np.inf, -np.inf],
        np.nan
    )

    speed = speed.fillna(
        0
    )

    # --------------------------------------------------------------
    # Only trust DETECTED and KALMAN positions
    # --------------------------------------------------------------

    valid_status = result[
        "status"
    ].astype(
        str
    ).isin(
        [
            "DETECTED",
            "KALMAN"
        ]
    )

    speed.loc[
        ~valid_status
    ] = 0

    # --------------------------------------------------------------
    # Ignore tiny movement
    # --------------------------------------------------------------

    speed = speed.where(
        speed >= MIN_SPEED,
        0
    )

    result[
        "distance"
    ] = distance.fillna(
        0
    )

    result[
        "speed_raw"
    ] = speed

    # --------------------------------------------------------------
    # Robust cap
    # --------------------------------------------------------------

    nonzero_speed = speed[
        speed > 0
    ]

    if len(nonzero_speed) > 0:

        speed_cap = np.percentile(
            nonzero_speed,
            SPEED_CAP_PERCENTILE
        )

    else:

        speed_cap = 1.0

    if speed_cap <= 0:

        speed_cap = 1.0

    result[
        "speed"
    ] = np.clip(
        speed,
        0,
        speed_cap
    )

    # --------------------------------------------------------------
    # Smooth
    # --------------------------------------------------------------

    result[
        "speed_smooth"
    ] = (

        result[
            "speed"
        ]

        .rolling(
            window=SMOOTHING_WINDOW,
            center=True,
            min_periods=1
        )

        .mean()

    )

    print(
        f"Raw maximum speed : "
        f"{result['speed_raw'].max():.2f} px/s"
    )

    print(
        f"Speed cap ({SPEED_CAP_PERCENTILE}th percentile) : "
        f"{speed_cap:.2f} px/s"
    )

    print(
        f"Maximum capped speed : "
        f"{result['speed'].max():.2f} px/s"
    )

    print(
        f"Maximum smooth speed : "
        f"{result['speed_smooth'].max():.2f} px/s"
    )

    return result


# ======================================================================
# CALCULATE SCORE
# ======================================================================

def calculate_score(df):

    print("\nCALCULATING MOVEMENT SCORE")
    print("-" * 70)

    result = df.copy()

    values = result[
        "speed_smooth"
    ].to_numpy(
        dtype=float
    )

    if len(values) == 0:

        result["score"] = 0.0

        return result

    max_value = np.max(
        values
    )

    if max_value <= 0:

        result["score"] = 0.0

        return result

    scores = (
        values /
        max_value
    )

    scores = np.clip(
        scores,
        0,
        1
    )

    result[
        "score"
    ] = scores

    print(
        f"Maximum score : "
        f"{result['score'].max():.3f}"
    )

    print(
        f"Mean score    : "
        f"{result['score'].mean():.3f}"
    )

    return result


# ======================================================================
# FIND PEAKS
# ======================================================================

def find_peaks(df):

    print("\nFINDING BALL MOVEMENT PEAKS")
    print("-" * 70)

    scores = df[
        "score"
    ].to_numpy(
        dtype=float
    )

    times = df[
        "time_sec"
    ].to_numpy(
        dtype=float
    )

    if len(scores) < 3:

        return []

    candidates = []

    for i in range(
        1,
        len(scores) - 1
    ):

        score = scores[i]

        if score < MIN_SCORE:

            continue

        if (
            score >= scores[i - 1]
            and
            score >= scores[i + 1]
        ):

            candidates.append(
                i
            )

    # Strongest first
    candidates.sort(
        key=lambda i:
            scores[i],
        reverse=True
    )

    selected = []

    for index in candidates:

        current_time = times[
            index
        ]

        too_close = False

        for other in selected:

            other_time = times[
                other
            ]

            if abs(
                current_time -
                other_time
            ) < MIN_PEAK_DISTANCE_SECONDS:

                too_close = True

                break

        if not too_close:

            selected.append(
                index
            )

        if len(selected) >= MAX_HIGHLIGHTS:

            break

    # Chronological
    selected.sort(
        key=lambda i:
            times[i]
    )

    print(
        f"Candidate peaks : "
        f"{len(candidates)}"
    )

    print(
        f"Selected peaks   : "
        f"{len(selected)}"
    )

    return selected


# ======================================================================
# CREATE WINDOWS
# ======================================================================

def create_windows(
    df,
    peak_indices
):

    print("\nCREATING HIGHLIGHT WINDOWS")
    print("-" * 70)

    if len(df) == 0:

        return pd.DataFrame(
            columns=[
                "highlight_id",
                "start",
                "end",
                "peak",
                "duration",
                "score"
            ]
        )

    video_start = float(
        df[
            "time_sec"
        ].min()
    )

    video_end = float(
        df[
            "time_sec"
        ].max()
    )

    windows = []

    for index in peak_indices:

        peak = float(
            df.iloc[index][
                "time_sec"
            ]
        )

        score = float(
            df.iloc[index][
                "score"
            ]
        )

        start = (
            peak -
            PRE_EVENT_SECONDS
        )

        end = (
            peak +
            POST_EVENT_SECONDS
        )

        start = max(
            video_start,
            start
        )

        end = min(
            video_end,
            end
        )

        # ----------------------------------------------------------
        # Minimum duration
        # ----------------------------------------------------------

        duration = end - start

        if duration < MIN_HIGHLIGHT_DURATION:

            missing = (
                MIN_HIGHLIGHT_DURATION -
                duration
            )

            start -= missing / 2
            end += missing / 2

            start = max(
                video_start,
                start
            )

            end = min(
                video_end,
                end
            )

        # ----------------------------------------------------------
        # Maximum duration
        # ----------------------------------------------------------

        duration = end - start

        if duration > MAX_HIGHLIGHT_DURATION:

            half = (
                MAX_HIGHLIGHT_DURATION /
                2
            )

            start = peak - half
            end = peak + half

            start = max(
                video_start,
                start
            )

            end = min(
                video_end,
                end
            )

        windows.append({

            "start": start,
            "end": end,
            "peak": peak,
            "duration": end - start,
            "score": score

        })

    if not windows:

        return pd.DataFrame(
            columns=[
                "highlight_id",
                "start",
                "end",
                "peak",
                "duration",
                "score"
            ]
        )

    windows_df = pd.DataFrame(
        windows
    )

    # --------------------------------------------------------------
    # IMPORTANT:
    # Do NOT merge overlapping windows.
    #
    # Instead, enforce a minimum gap.
    # --------------------------------------------------------------

    windows_df = windows_df.sort_values(
        "start"
    ).reset_index(
        drop=True
    )

    final_windows = []

    for _, row in windows_df.iterrows():

        if not final_windows:

            final_windows.append(
                row.to_dict()
            )

            continue

        previous = final_windows[-1]

        gap = (
            float(row["start"])
            -
            float(previous["end"])
        )

        if gap < MIN_WINDOW_GAP_SECONDS:

            # Keep stronger highlight
            if (
                float(row["score"])
                >
                float(previous["score"])
            ):

                final_windows[-1] = (
                    row.to_dict()
                )

        else:

            final_windows.append(
                row.to_dict()
            )

    windows_df = pd.DataFrame(
        final_windows
    )

    # --------------------------------------------------------------
    # Sort strongest highlights first
    # --------------------------------------------------------------

    windows_df = windows_df.sort_values(
        "score",
        ascending=False
    ).reset_index(
        drop=True
    )

    windows_df = windows_df.head(
        MAX_HIGHLIGHTS
    )

    # --------------------------------------------------------------
    # Return chronological order
    # --------------------------------------------------------------

    windows_df = windows_df.sort_values(
        "start"
    ).reset_index(
        drop=True
    )

    windows_df[
        "highlight_id"
    ] = np.arange(
        1,
        len(windows_df) + 1
    )

    windows_df[
        "duration"
    ] = (
        windows_df["end"]
        -
        windows_df["start"]
    )

    return windows_df[
        [
            "highlight_id",
            "start",
            "end",
            "peak",
            "duration",
            "score"
        ]
    ]


# ======================================================================
# SAVE RESULTS
# ======================================================================

def save_results(
    df,
    windows,
    output_dir
):

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    scores_csv = os.path.join(
        output_dir,
        "ball_highlight_scores.csv"
    )

    windows_csv = os.path.join(
        output_dir,
        "ball_highlight_windows.csv"
    )

    df.to_csv(
        scores_csv,
        index=False
    )

    windows.to_csv(
        windows_csv,
        index=False
    )

    return (
        scores_csv,
        windows_csv
    )


# ======================================================================
# MAIN
# ======================================================================

def score_ball_highlights(
    trajectory_csv,
    output_dir
):

    print("=" * 70)

    print(
        "BALL HIGHLIGHT SCORING PIPELINE"
    )

    print("=" * 70)

    df = load_trajectory(
        trajectory_csv
    )

    df = calculate_movement(
        df
    )

    df = calculate_score(
        df
    )

    peaks = find_peaks(
        df
    )

    windows = create_windows(
        df,
        peaks
    )

    (
        scores_csv,
        windows_csv
    ) = save_results(
        df,
        windows,
        output_dir
    )

    print("\n" + "=" * 70)

    print(
        "BALL HIGHLIGHT SCORING COMPLETE"
    )

    print("=" * 70)

    print(
        f"\nTrajectory rows    : "
        f"{len(df):,}"
    )

    print(
        f"Highlight windows  : "
        f"{len(windows)}"
    )

    total_duration = (
        windows["duration"].sum()
        if len(windows) > 0
        else 0
    )

    print(
        f"Highlight duration : "
        f"{total_duration:.2f}s"
    )

    print(
        f"Highlight duration : "
        f"{total_duration / 60:.2f} min"
    )

    if len(windows) > 0:

        print(
            "\nHIGHLIGHT WINDOWS"
        )

        print(
            "-" * 70
        )

        for _, row in windows.iterrows():

            print(
                f"Highlight "
                f"{int(row['highlight_id']):02d} | "
                f"{row['start']:.2f}s -> "
                f"{row['end']:.2f}s | "
                f"Peak: "
                f"{row['peak']:.2f}s | "
                f"Score: "
                f"{row['score']:.3f}"
            )

    else:

        print(
            "\nWARNING: No highlights detected."
        )

    print(
        "\nSCORES CSV:"
    )

    print(
        scores_csv
    )

    print(
        "\nWINDOWS CSV:"
    )

    print(
        windows_csv
    )

    print(
        "\n" + "=" * 70
    )

    return {

        "trajectory_csv":
            trajectory_csv,

        "output_dir":
            output_dir,

        "scores_csv":
            scores_csv,

        "windows_csv":
            windows_csv,

        "highlights":
            len(windows),

        "duration_seconds":
            float(total_duration)

    }


# ======================================================================
# DIRECT EXECUTION
# ======================================================================

if __name__ == "__main__":

    print(
        "Ball highlight scorer module."
    )