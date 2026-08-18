# ================================================================
# AI FOOTBALL HIGHLIGHT MERGER
#
# INDEPENDENT MATCH PIPELINE
#
# VIDEO
#   │
#   ├── Ball Highlight Windows
#   │
#   └── Scoreboard Goal Events
#            │
#            ▼
#       COMBINE WINDOWS
#            │
#            ▼
#   MERGE ONLY ACTUAL OVERLAP
#            │
#            ▼
#       CREATE CLIPS
#            │
#            ▼
#       CONCATENATE
#            │
#            ▼
#   FINAL AI HIGHLIGHT VIDEO
#
#
# IMPORTANT:
#
# The video is the ONLY required input.
#
# Match-specific paths are automatically generated from:
#
# backend/uploads/<match_id>/video.mp4
#
#
# Example:
#
# backend/uploads/match_20260819_004126_fd06de/video.mp4
#
# automatically uses:
#
# backend/outputs/match_20260819_004126_fd06de/
#
#
# BALL CSV:
#
# Optional.
#
# Default:
#
# backend/outputs/<match_id>/ball_highlights/
#     ball_highlight_windows.csv
#
#
# SCOREBOARD GOAL CSV:
#
# Optional.
#
# Default:
#
# backend/outputs/<match_id>/scoreboard_goals/
#     goal_events.csv
#
#
# Therefore:
#
#   BALL + GOALS  -> combine both
#   BALL only     -> use ball highlights
#   GOALS only    -> use goal highlights
#   neither       -> clear error
#
#
# GOAL WINDOW:
#
#   goal_time - 30 seconds
#   goal_time + 30 seconds
#
#
# MERGE:
#
# ONLY ACTUAL TEMPORAL OVERLAP.
#
# NO 5 SECOND TOLERANCE.
#
# Example:
#
#   10 -> 40
#   35 -> 65
#
# becomes:
#
#   10 -> 65
#
#
# But:
#
#   10 -> 40
#   40.01 -> 70
#
# stays as TWO windows.
#
# ================================================================


import os
import sys
import time
import subprocess

import pandas as pd
import cv2


# ================================================================
# PROJECT ROOT
# ================================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        ".."
    )
)


# ================================================================
# BACKEND ROOT
# ================================================================

BACKEND_ROOT = os.path.join(
    PROJECT_ROOT,
    "backend"
)


# ================================================================
# GOAL WINDOW SETTINGS
# ================================================================

GOAL_PRE_SECONDS = 30.0
GOAL_POST_SECONDS = 30.0


# ================================================================
# DEFAULT UPLOAD DIRECTORY
# ================================================================

DEFAULT_UPLOADS_DIR = os.path.join(
    BACKEND_ROOT,
    "uploads"
)


# ================================================================
# FIND NEWEST UPLOADED VIDEO
# ================================================================

def find_latest_uploaded_video():

    print(
        "\nSearching for latest uploaded video..."
    )

    if not os.path.exists(
        DEFAULT_UPLOADS_DIR
    ):

        raise FileNotFoundError(
            "Uploads directory does not exist:\n"
            f"{DEFAULT_UPLOADS_DIR}"
        )


    candidates = []


    for root, dirs, files in os.walk(
        DEFAULT_UPLOADS_DIR
    ):

        for filename in files:

            if filename.lower().endswith(
                (
                    ".mp4",
                    ".avi",
                    ".mkv",
                    ".mov"
                )
            ):

                full_path = os.path.join(
                    root,
                    filename
                )


                try:

                    mtime = os.path.getmtime(
                        full_path
                    )


                    candidates.append(
                        (
                            mtime,
                            full_path
                        )
                    )


                except Exception:

                    pass


    if not candidates:

        raise FileNotFoundError(
            "No uploaded video was found in:\n"
            f"{DEFAULT_UPLOADS_DIR}"
        )


    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )


    latest_video = candidates[0][1]


    print(
        "Latest uploaded video:"
    )


    print(
        latest_video
    )


    return latest_video


# ================================================================
# FFMPEG
# ================================================================

def find_ffmpeg():

    print(
        "\nChecking FFmpeg..."
    )


    # ------------------------------------------------------------
    # PATH
    # ------------------------------------------------------------

    try:

        result = subprocess.run(
            [
                "ffmpeg",
                "-version"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )


        if result.returncode == 0:

            print(
                "FFmpeg : Found in PATH"
            )

            return "ffmpeg"


    except Exception:

        pass


    # ------------------------------------------------------------
    # COMMON WINDOWS PATHS
    # ------------------------------------------------------------

    possible_paths = [

        r"C:\ffmpeg\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe",

        r"C:\ffmpeg\bin\ffmpeg.exe",

    ]


    for path in possible_paths:

        if os.path.exists(
            path
        ):

            print(
                f"FFmpeg : {path}"
            )

            return path


    raise FileNotFoundError(
        "FFmpeg was not found.\n"
        "Install FFmpeg or add it to PATH."
    )


# ================================================================
# VIDEO INFORMATION
# ================================================================

def get_video_info(
    video_path
):

    cap = cv2.VideoCapture(
        video_path
    )


    if not cap.isOpened():

        raise RuntimeError(
            "Could not open video:\n"
            f"{video_path}"
        )


    fps = cap.get(
        cv2.CAP_PROP_FPS
    )


    total_frames = int(
        cap.get(
            cv2.CAP_PROP_FRAME_COUNT
        )
    )


    width = int(
        cap.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )
    )


    height = int(
        cap.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )
    )


    cap.release()


    if fps <= 0:

        raise RuntimeError(
            "Could not determine video FPS."
        )


    duration = (
        total_frames / fps
    )


    return {

        "fps":
            fps,

        "total_frames":
            total_frames,

        "width":
            width,

        "height":
            height,

        "duration":
            duration

    }


# ================================================================
# DETERMINE MATCH ID
# ================================================================

def get_match_id(
    video_path
):

    video_path = os.path.abspath(
        video_path
    )


    video_directory = os.path.dirname(
        video_path
    )


    parent_name = os.path.basename(
        video_directory
    )


    # ------------------------------------------------------------
    # Normal structure:
    #
    # uploads/
    #     match_xxxxx/
    #         video.mp4
    # ------------------------------------------------------------

    if parent_name:

        return parent_name


    # ------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------

    filename = os.path.basename(
        video_path
    )


    return os.path.splitext(
        filename
    )[0]


# ================================================================
# RESOLVE MATCH-SPECIFIC PATHS
# ================================================================

def resolve_pipeline_paths(
    video_path,
    ball_windows_csv=None,
    goal_file=None,
    output_dir=None
):

    video_path = os.path.abspath(
        video_path
    )


    match_id = get_match_id(
        video_path
    )


    # ============================================================
    # MATCH OUTPUT ROOT
    # ============================================================

    if output_dir is None:

        output_root = os.path.join(

            BACKEND_ROOT,

            "outputs",

            match_id

        )

    else:

        output_root = os.path.abspath(
            output_dir
        )


    # ============================================================
    # BALL WINDOWS
    #
    # IMPORTANT:
    #
    # Your actual pipeline creates:
    #
    # ball_highlights/
    #
    # NOT:
    #
    # ball/
    # ============================================================

    if ball_windows_csv is None:

        ball_windows_csv = os.path.join(

            output_root,

            "ball_highlights",

            "ball_highlight_windows.csv"

        )

    else:

        ball_windows_csv = os.path.abspath(
            ball_windows_csv
        )


    # ============================================================
    # SCOREBOARD GOALS
    # ============================================================

    if goal_file is None:

        goal_file = os.path.join(

            output_root,

            "scoreboard_goals",

            "goal_events.csv"

        )

    else:

        goal_file = os.path.abspath(
            goal_file
        )


    # ============================================================
    # FINAL DIRECTORY
    # ============================================================

    final_output_dir = os.path.join(

        output_root,

        "final"

    )


    return {

        "match_id":
            match_id,

        "output_root":
            output_root,

        "ball_windows_csv":
            ball_windows_csv,

        "goal_file":
            goal_file,

        "final_output_dir":
            final_output_dir

    }


# ================================================================
# LOAD BALL WINDOWS
#
# BALL CSV IS OPTIONAL.
# ================================================================

def load_ball_windows(
    windows_csv,
    video_duration
):

    print(
        "\nLoading ball highlight windows..."
    )


    print(
        windows_csv
    )


    # ------------------------------------------------------------
    # Missing ball CSV
    # ------------------------------------------------------------

    if not os.path.exists(
        windows_csv
    ):

        print(
            "\nWARNING:"
        )


        print(
            "Ball highlight CSV was not found."
        )


        print(
            "Continuing without BALL highlights."
        )


        return []


    # ------------------------------------------------------------
    # Read CSV
    # ------------------------------------------------------------

    try:

        df = pd.read_csv(
            windows_csv
        )


    except Exception as e:

        print(
            "\nWARNING:"
        )


        print(
            f"Could not read ball CSV: {e}"
        )


        print(
            "Continuing without BALL highlights."
        )


        return []


    if len(df) == 0:

        print(
            "Ball CSV is empty."
        )


        return []


    print(
        f"Ball rows loaded : {len(df)}"
    )


    # ============================================================
    # REQUIRED COLUMNS
    # ============================================================

    required_columns = [

        "start",
        "end"

    ]


    missing = [

        column

        for column in required_columns

        if column not in df.columns

    ]


    if missing:

        print(
            "\nWARNING:"
        )


        print(
            "Ball CSV is missing columns:"
        )


        print(
            missing
        )


        print(
            "Continuing without BALL highlights."
        )


        return []


    windows = []


    # ============================================================
    # READ WINDOWS
    # ============================================================

    for index, row in df.iterrows():

        try:

            start = float(
                row["start"]
            )


            end = float(
                row["end"]
            )


        except Exception:

            continue


        # --------------------------------------------------------
        # Optional highlight ID
        # --------------------------------------------------------

        try:

            highlight_id = int(
                row["highlight_id"]
            )


        except Exception:

            highlight_id = (
                index + 1
            )


        # --------------------------------------------------------
        # Optional peak
        # --------------------------------------------------------

        try:

            peak = float(
                row["peak"]
            )


        except Exception:

            peak = (
                start + end
            ) / 2.0


        # --------------------------------------------------------
        # Optional score
        # --------------------------------------------------------

        try:

            score = float(
                row["score"]
            )


        except Exception:

            score = 0.0


        # --------------------------------------------------------
        # Clamp start
        # --------------------------------------------------------

        start = max(
            0.0,
            start
        )


        # --------------------------------------------------------
        # Clamp end
        # --------------------------------------------------------

        end = min(
            video_duration,
            end
        )


        # --------------------------------------------------------
        # Clamp peak
        # --------------------------------------------------------

        peak = max(
            0.0,
            min(
                video_duration,
                peak
            )
        )


        # --------------------------------------------------------
        # Validate
        # --------------------------------------------------------

        if end <= start:

            continue


        windows.append({

            "highlight_id":
                highlight_id,

            "start":
                start,

            "end":
                end,

            "peak":
                peak,

            "score":
                score,

            "source":
                "BALL",

            "description":
                "High ball movement"

        })


    return windows


# ================================================================
# LOAD SCOREBOARD GOALS
#
# GOAL CSV IS OPTIONAL.
# ================================================================

def load_goal_events(
    goal_file,
    video_duration
):

    print(
        "\nLoading scoreboard goal events..."
    )


    print(
        goal_file
    )


    # ------------------------------------------------------------
    # Missing goal CSV
    # ------------------------------------------------------------

    if not os.path.exists(
        goal_file
    ):

        print(
            "\nWARNING:"
        )


        print(
            "Scoreboard goal file was not found."
        )


        print(
            "Continuing without SCOREBOARD goals."
        )


        return []


    # ------------------------------------------------------------
    # Read CSV
    # ------------------------------------------------------------

    try:

        df = pd.read_csv(
            goal_file
        )


    except Exception as e:

        print(
            "\nWARNING:"
        )


        print(
            f"Could not read goal CSV: {e}"
        )


        print(
            "Continuing without SCOREBOARD goals."
        )


        return []


    print(
        f"Goal rows loaded : {len(df)}"
    )


    if len(df) == 0:

        print(
            "No scoreboard goal events found."
        )


        return []


    # ============================================================
    # FIND TIME COLUMN
    # ============================================================

    possible_time_columns = [

        "time",
        "timestamp",
        "start",
        "peak",
        "event_time",
        "goal_time",
        "seconds"

    ]


    time_column = None


    for column in possible_time_columns:

        if column in df.columns:

            time_column = column

            break


    if time_column is None:

        print(
            "\nWARNING:"
        )


        print(
            "Could not identify goal timestamp column."
        )


        print(
            f"Available columns: {list(df.columns)}"
        )


        return []


    print(
        f"Goal timestamp column : {time_column}"
    )


    windows = []


    # ============================================================
    # CREATE GOAL WINDOWS
    # ============================================================

    for index, row in df.iterrows():

        try:

            event_time = float(
                row[time_column]
            )


        except Exception:

            continue


        # --------------------------------------------------------
        # Validate event time
        # --------------------------------------------------------

        if event_time < 0:

            continue


        if event_time > video_duration:

            continue


        # --------------------------------------------------------
        # GOAL WINDOW
        #
        # -30 seconds
        # +30 seconds
        # --------------------------------------------------------

        start = max(

            0.0,

            event_time
            -
            GOAL_PRE_SECONDS

        )


        end = min(

            video_duration,

            event_time
            +
            GOAL_POST_SECONDS

        )


        if end <= start:

            continue


        # --------------------------------------------------------
        # Description
        # --------------------------------------------------------

        description = "Scoreboard goal"


        if "description" in df.columns:

            try:

                value = str(
                    row["description"]
                ).strip()


                if value:

                    description = value


            except Exception:

                pass


        windows.append({

            "highlight_id":
                index + 1,

            "start":
                start,

            "end":
                end,

            "peak":
                event_time,

            "score":
                1.0,

            "source":
                "GOAL",

            "description":
                description

        })


    return windows


# ================================================================
# COMBINE WINDOWS
# ================================================================

def combine_windows(
    ball_windows,
    goal_windows
):

    combined = []


    combined.extend(
        ball_windows
    )


    combined.extend(
        goal_windows
    )


    combined.sort(
        key=lambda x: (
            x["start"],
            x["end"]
        )
    )


    return combined


# ================================================================
# MERGE WINDOWS
#
# ONLY ACTUAL TEMPORAL OVERLAP.
#
# NO GAP TOLERANCE.
# ================================================================

def merge_windows(
    windows
):

    if not windows:

        return []


    windows = sorted(

        windows,

        key=lambda x: (
            x["start"],
            x["end"]
        )

    )


    merged = []


    # ============================================================
    # INITIAL WINDOW
    # ============================================================

    current = dict(
        windows[0]
    )


    current["sources"] = [

        current["source"]

    ]


    current["descriptions"] = [

        current["description"]

    ]


    # ============================================================
    # PROCESS REMAINING WINDOWS
    # ============================================================

    for next_window in windows[1:]:

        # --------------------------------------------------------
        # ACTUAL OVERLAP
        #
        # IMPORTANT:
        #
        # <= means touching boundaries are considered overlap.
        #
        # Example:
        #
        # 10 -> 40
        # 40 -> 70
        #
        # becomes:
        #
        # 10 -> 70
        #
        # If you want 40.01 to be separate, it is separate.
        # --------------------------------------------------------

        if next_window["start"] <= current["end"]:

            previous_score = current["score"]


            # ----------------------------------------------------
            # Extend end
            # ----------------------------------------------------

            current["end"] = max(

                current["end"],

                next_window["end"]

            )


            # ----------------------------------------------------
            # Strongest score
            # ----------------------------------------------------

            current["score"] = max(

                current["score"],

                next_window["score"]

            )


            # ----------------------------------------------------
            # Strongest peak
            # ----------------------------------------------------

            if next_window["score"] > previous_score:

                current["peak"] = (
                    next_window["peak"]
                )


            # ----------------------------------------------------
            # Sources
            # ----------------------------------------------------

            if (
                next_window["source"]
                not in
                current["sources"]
            ):

                current["sources"].append(

                    next_window["source"]

                )


            # ----------------------------------------------------
            # Descriptions
            # ----------------------------------------------------

            if (
                next_window["description"]
                not in
                current["descriptions"]
            ):

                current["descriptions"].append(

                    next_window["description"]

                )


        else:

            # ----------------------------------------------------
            # NO OVERLAP
            #
            # Save current window separately.
            # ----------------------------------------------------

            merged.append(
                current
            )


            current = dict(
                next_window
            )


            current["sources"] = [

                current["source"]

            ]


            current["descriptions"] = [

                current["description"]

            ]


    # ============================================================
    # SAVE LAST WINDOW
    # ============================================================

    merged.append(
        current
    )


    return merged


# ================================================================
# PRINT MERGED WINDOWS
# ================================================================

def print_merged_windows(
    windows
):

    print(
        "\nFINAL MERGED WINDOWS"
    )


    print(
        "-" * 90
    )


    if not windows:

        print(
            "No highlight windows available."
        )


        return


    for i, window in enumerate(
        windows,
        start=1
    ):

        duration = (

            window["end"]
            -
            window["start"]

        )


        sources = ",".join(
            window["sources"]
        )


        print(

            f"{i:02d} | "

            f"{window['start']:8.2f}s -> "
            f"{window['end']:8.2f}s | "

            f"{duration:7.2f}s | "

            f"{sources:15s} | "

            f"peak={window['peak']:8.2f}s | "

            f"score={window['score']:.3f}"

        )


# ================================================================
# CREATE FINAL CLIPS
# ================================================================

def create_final_clips(
    video_path,
    windows,
    clips_dir,
    ffmpeg_exe
):

    os.makedirs(
        clips_dir,
        exist_ok=True
    )


    # ============================================================
    # CLEAN OLD CLIPS
    # ============================================================

    print(
        "\nCleaning previous final clips..."
    )


    for filename in os.listdir(
        clips_dir
    ):

        path = os.path.join(

            clips_dir,

            filename

        )


        if os.path.isfile(
            path
        ):

            try:

                os.remove(
                    path
                )


            except Exception:

                pass


    clip_paths = []


    start_time = time.time()


    print(
        "\nCREATING FINAL HIGHLIGHT CLIPS"
    )


    print(
        "-" * 70
    )


    # ============================================================
    # CREATE EACH CLIP
    # ============================================================

    for i, window in enumerate(
        windows,
        start=1
    ):

        start = float(
            window["start"]
        )


        end = float(
            window["end"]
        )


        duration = (
            end - start
        )


        sources = "_".join(

            window["sources"]

        )


        sources = (

            sources

            .replace(
                "/",
                "_"
            )

            .replace(
                "\\",
                "_"
            )

            .replace(
                ":",
                "_"
            )

            .replace(
                " ",
                "_"
            )

        )


        clip_filename = (

            f"final_highlight_"
            f"{i:02d}_"
            f"{sources}.mp4"

        )


        clip_path = os.path.join(

            clips_dir,

            clip_filename

        )


        print(

            f"Clip {i:02d} | "

            f"{start:.2f}s - "
            f"{end:.2f}s | "

            f"{duration:.2f}s | "

            f"source={sources}"

        )


        # ========================================================
        # FFMPEG COMMAND
        # ========================================================

        cmd = [

            ffmpeg_exe,

            "-y",

            # ----------------------------------------------------
            # Seek before input for faster extraction
            # ----------------------------------------------------

            "-ss",
            f"{start:.3f}",

            "-i",
            video_path,

            "-t",
            f"{duration:.3f}",

            # ----------------------------------------------------
            # Video
            # ----------------------------------------------------

            "-map",
            "0:v:0",

            # ----------------------------------------------------
            # Audio if available
            # ----------------------------------------------------

            "-map",
            "0:a?",

            # ----------------------------------------------------
            # Video codec
            # ----------------------------------------------------

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "23",

            # ----------------------------------------------------
            # Audio codec
            # ----------------------------------------------------

            "-c:a",
            "aac",

            "-b:a",
            "128k",

            # ----------------------------------------------------
            # MP4 optimization
            # ----------------------------------------------------

            "-movflags",
            "+faststart",

            clip_path

        ]


        result = subprocess.run(

            cmd,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True

        )


        if result.returncode != 0:

            print(
                "\nFFmpeg ERROR:"
            )


            print(
                result.stderr[-5000:]
            )


            raise RuntimeError(

                f"Failed to create "
                f"final clip {i}"

            )


        if not os.path.exists(
            clip_path
        ):

            raise RuntimeError(

                f"Clip was not created:\n"
                f"{clip_path}"

            )


        clip_paths.append(
            clip_path
        )


    generation_time = (

        time.time()
        -
        start_time

    )


    return (

        clip_paths,

        generation_time

    )


# ================================================================
# CREATE CONCAT LIST
# ================================================================

def create_concat_list(
    clip_paths,
    concat_list
):

    print(
        "\nCreating final concat list..."
    )


    concat_dir = os.path.dirname(

        os.path.abspath(
            concat_list
        )

    )


    os.makedirs(
        concat_dir,
        exist_ok=True
    )


    with open(

        concat_list,

        "w",

        encoding="utf-8"

    ) as f:

        for clip_path in clip_paths:

            normalized = (

                os.path.abspath(
                    clip_path
                )

                .replace(
                    "\\",
                    "/"
                )

            )


            f.write(

                f"file '{normalized}'\n"

            )


    print(
        f"Concat list : {concat_list}"
    )


# ================================================================
# ASSEMBLE FINAL VIDEO
# ================================================================

def assemble_final_video(
    concat_list,
    final_video,
    ffmpeg_exe
):

    print(
        "\nASSEMBLING FINAL AI HIGHLIGHT VIDEO"
    )


    print(
        "-" * 70
    )


    if not os.path.exists(
        concat_list
    ):

        raise FileNotFoundError(

            f"Concat list not found:\n"
            f"{concat_list}"

        )


    final_dir = os.path.dirname(

        os.path.abspath(
            final_video
        )

    )


    os.makedirs(
        final_dir,
        exist_ok=True
    )


    cmd = [

        ffmpeg_exe,

        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        concat_list,

        "-c",
        "copy",

        "-movflags",
        "+faststart",

        final_video

    ]


    start_time = time.time()


    result = subprocess.run(

        cmd,

        stdout=subprocess.PIPE,

        stderr=subprocess.PIPE,

        text=True

    )


    assembly_time = (

        time.time()
        -
        start_time

    )


    if result.returncode != 0:

        print(
            "\nFFmpeg assembly ERROR:"
        )


        print(
            result.stderr[-5000:]
        )


        raise RuntimeError(
            "Final video assembly failed."
        )


    if not os.path.exists(
        final_video
    ):

        raise RuntimeError(
            "Final video was not created."
        )


    return assembly_time


# ================================================================
# SAVE MERGED WINDOWS
# ================================================================

def save_merged_windows(
    windows,
    output_path
):

    rows = []


    for i, window in enumerate(
        windows,
        start=1
    ):

        rows.append({

            "highlight_id":
                i,

            "start":
                window["start"],

            "end":
                window["end"],

            "peak":
                window["peak"],

            "duration":
                (
                    window["end"]
                    -
                    window["start"]
                ),

            "score":
                window["score"],

            "sources":
                ",".join(
                    window["sources"]
                ),

            "description":
                " | ".join(
                    window["descriptions"]
                )

        })


    df = pd.DataFrame(
        rows
    )


    df.to_csv(

        output_path,

        index=False

    )


    return df


# ================================================================
# MAIN PIPELINE
# ================================================================

def generate_final_highlights(

    video_path=None,

    ball_windows_csv=None,

    goal_file=None,

    output_dir=None

):

    print(
        "=" * 70
    )


    print(
        "AI FOOTBALL HIGHLIGHT MERGER"
    )


    print(
        "=" * 70
    )


    # ============================================================
    # VIDEO
    # ============================================================

    if video_path is None:

        video_path = find_latest_uploaded_video()


    video_path = os.path.abspath(
        video_path
    )


    # ============================================================
    # RESOLVE MATCH PATHS
    # ============================================================

    paths = resolve_pipeline_paths(

        video_path,

        ball_windows_csv,

        goal_file,

        output_dir

    )


    match_id = paths["match_id"]


    ball_windows_csv = (
        paths["ball_windows_csv"]
    )


    goal_file = (
        paths["goal_file"]
    )


    output_dir = (
        paths["final_output_dir"]
    )


    clips_dir = os.path.join(

        output_dir,

        "clips"

    )


    concat_list = os.path.join(

        output_dir,

        "final_concat_list.txt"

    )


    final_video = os.path.join(

        output_dir,

        "final_AI_highlights.mp4"

    )


    # ============================================================
    # PATH SUMMARY
    # ============================================================

    print(
        "\nPIPELINE PATHS"
    )


    print(
        "-" * 70
    )


    print(
        f"Match ID       : {match_id}"
    )


    print(
        f"Video          : {video_path}"
    )


    print(
        f"Ball windows   : {ball_windows_csv}"
    )


    print(
        f"Goal events    : {goal_file}"
    )


    print(
        f"Final output   : {output_dir}"
    )


    # ============================================================
    # VIDEO CHECK
    # ============================================================

    print(
        "\nChecking input video..."
    )


    if not os.path.exists(
        video_path
    ):

        raise FileNotFoundError(

            f"Video not found:\n"
            f"{video_path}"

        )


    print(
        "Video : OK"
    )


    # ============================================================
    # FFMPEG
    # ============================================================

    ffmpeg_exe = find_ffmpeg()


    # ============================================================
    # VIDEO INFORMATION
    # ============================================================

    print(
        "\nVIDEO INFORMATION"
    )


    print(
        "-" * 70
    )


    video_info = get_video_info(
        video_path
    )


    print(

        f"FPS        : "
        f"{video_info['fps']:.2f}"

    )


    print(

        f"Frames     : "
        f"{video_info['total_frames']:,}"

    )


    print(

        f"Resolution : "
        f"{video_info['width']} x "
        f"{video_info['height']}"

    )


    print(

        f"Duration   : "
        f"{video_info['duration']:.2f}s"

    )


    print(

        f"Duration   : "
        f"{video_info['duration'] / 60:.2f} min"

    )


    # ============================================================
    # CREATE DIRECTORIES
    # ============================================================

    os.makedirs(

        output_dir,

        exist_ok=True

    )


    os.makedirs(

        clips_dir,

        exist_ok=True

    )


    # ============================================================
    # BALL HIGHLIGHTS
    # ============================================================

    print(
        "\n" + "=" * 70
    )


    print(
        "BALL HIGHLIGHTS"
    )


    print(
        "=" * 70
    )


    ball_windows = load_ball_windows(

        ball_windows_csv,

        video_info["duration"]

    )


    print(

        f"\nBall windows loaded : "
        f"{len(ball_windows)}"

    )


    # ============================================================
    # SCOREBOARD GOALS
    # ============================================================

    print(
        "\n" + "=" * 70
    )


    print(
        "SCOREBOARD GOALS"
    )


    print(
        "=" * 70
    )


    goal_windows = load_goal_events(

        goal_file,

        video_info["duration"]

    )


    print(

        f"\nGoal windows loaded : "
        f"{len(goal_windows)}"

    )


    # ============================================================
    # PRINT GOAL WINDOWS
    # ============================================================

    if goal_windows:

        print(
            "\nGOAL WINDOWS (-30s / +30s)"
        )


        print(
            "-" * 70
        )


        for i, window in enumerate(
            goal_windows,
            start=1
        ):

            print(

                f"Goal {i:02d} | "

                f"{window['start']:.2f}s -> "
                f"{window['end']:.2f}s | "

                f"goal={window['peak']:.2f}s | "

                f"duration="
                f"{window['end'] - window['start']:.2f}s"

            )


    # ============================================================
    # SOURCE STATUS
    # ============================================================

    print(
        "\n" + "=" * 70
    )


    print(
        "DETECTION SOURCE STATUS"
    )


    print(
        "=" * 70
    )


    ball_available = (
        len(ball_windows) > 0
    )


    goals_available = (
        len(goal_windows) > 0
    )


    print(
        f"BALL highlights     : "
        f"{'AVAILABLE' if ball_available else 'NOT AVAILABLE'}"
    )


    print(
        f"SCOREBOARD goals    : "
        f"{'AVAILABLE' if goals_available else 'NOT AVAILABLE'}"
    )


    # ============================================================
    # COMBINE WINDOWS
    # ============================================================

    print(
        "\n" + "=" * 70
    )


    print(
        "COMBINING HIGHLIGHT SOURCES"
    )


    print(
        "=" * 70
    )


    combined = combine_windows(

        ball_windows,

        goal_windows

    )


    print(

        f"Ball windows : "
        f"{len(ball_windows)}"

    )


    print(

        f"Goal windows : "
        f"{len(goal_windows)}"

    )


    print(

        f"Combined     : "
        f"{len(combined)}"

    )


    # ============================================================
    # NOTHING AVAILABLE
    # ============================================================

    if not combined:

        raise RuntimeError(

            "No highlight windows are available.\n\n"

            "This merger is independent, but at least one "
            "detection pipeline must have produced results.\n\n"

            "Expected optional files:\n"

            f"BALL:\n"
            f"{ball_windows_csv}\n\n"

            f"SCOREBOARD:\n"
            f"{goal_file}\n\n"

            "Run the ball and/or scoreboard detection pipeline "
            "for this SAME match first."

        )


    # ============================================================
    # MERGE
    # ============================================================

    print(
        "\n" + "=" * 70
    )


    print(
        "MERGING HIGHLIGHT WINDOWS"
    )


    print(
        "=" * 70
    )


    print(
        "\nMerge rule:"
    )


    print(
        "ONLY actual temporal overlap is merged."
    )


    print(
        "Merge gap = 0.0 seconds."
    )


    merged = merge_windows(
        combined
    )


    print(

        f"\nMerged windows : "
        f"{len(merged)}"

    )


    print_merged_windows(
        merged
    )


    # ============================================================
    # SAVE MERGED WINDOWS
    # ============================================================

    merged_csv = os.path.join(

        output_dir,

        "final_merged_windows.csv"

    )


    save_merged_windows(

        merged,

        merged_csv

    )


    print(
        "\nMerged windows saved:"
    )


    print(
        merged_csv
    )


    # ============================================================
    # TOTAL DURATION
    # ============================================================

    total_duration = sum(

        window["end"]
        -
        window["start"]

        for window in merged

    )


    print(

        f"\nFinal highlight duration : "
        f"{total_duration:.2f}s"

    )


    print(

        f"Final highlight duration : "
        f"{total_duration / 60:.2f} min"

    )


    # ============================================================
    # CREATE FINAL CLIPS
    # ============================================================

    print(
        "\n" + "=" * 70
    )


    print(
        "CREATING FINAL CLIPS"
    )


    print(
        "=" * 70
    )


    (

        clip_paths,

        generation_time

    ) = create_final_clips(

        video_path,

        merged,

        clips_dir,

        ffmpeg_exe

    )


    print(

        f"\nFinal clips created : "
        f"{len(clip_paths)}"

    )


    print(

        f"Clip generation time : "
        f"{generation_time:.2f}s"

    )


    # ============================================================
    # CONCAT LIST
    # ============================================================

    create_concat_list(

        clip_paths,

        concat_list

    )


    # ============================================================
    # ASSEMBLE
    # ============================================================

    assembly_time = assemble_final_video(

        concat_list,

        final_video,

        ffmpeg_exe

    )


    # ============================================================
    # FILE SIZE
    # ============================================================

    final_size_mb = (

        os.path.getsize(
            final_video
        )

        /

        (1024 * 1024)

    )


    # ============================================================
    # FINAL SUMMARY
    # ============================================================

    print(
        "\n" + "=" * 70
    )


    print(
        "FINAL AI HIGHLIGHT GENERATION COMPLETE"
    )


    print(
        "=" * 70
    )


    print(
        f"Match ID          : {match_id}"
    )


    print(
        f"Input video       : {video_path}"
    )


    print(
        f"Ball windows      : {len(ball_windows)}"
    )


    print(
        f"Scoreboard goals  : {len(goal_windows)}"
    )


    print(
        f"Combined windows  : {len(combined)}"
    )


    print(
        f"Final merged clips: {len(merged)}"
    )


    print(
        f"Final duration    : "
        f"{total_duration / 60:.2f} min"
    )


    print(
        f"Generation time   : "
        f"{generation_time:.2f}s"
    )


    print(
        f"Assembly time     : "
        f"{assembly_time:.2f}s"
    )


    print(
        f"Final size        : "
        f"{final_size_mb:.2f} MB"
    )


    print(
        "\nFINAL VIDEO:"
    )


    print(
        final_video
    )


    print(
        "\nMERGED WINDOWS:"
    )


    print(
        merged_csv
    )


    print(
        "\nFINAL CLIPS:"
    )


    print(
        clips_dir
    )


    print(
        "\n" + "=" * 70
    )


    # ============================================================
    # RETURN
    # ============================================================

    return {

        "match_id":
            match_id,

        "video_path":
            video_path,

        "final_video":
            final_video,

        "merged_windows":
            merged_csv,

        "clips":
            clip_paths,

        "clips_dir":
            clips_dir,

        "ball_windows_csv":
            ball_windows_csv,

        "goal_file":
            goal_file,

        "ball_windows":
            len(ball_windows),

        "goal_windows":
            len(goal_windows),

        "combined_windows":
            len(combined),

        "final_windows":
            len(merged),

        "duration_seconds":
            total_duration,

        "duration_minutes":
            total_duration / 60,

        "generation_time":
            generation_time,

        "assembly_time":
            assembly_time,

        "size_mb":
            final_size_mb

    }


# ================================================================
# DIRECT EXECUTION
#
# OPTION 1:
#
# python backend\pipelines\highlight_merger.py
#
# Automatically selects newest uploaded video.
#
#
# OPTION 2:
#
# python backend\pipelines\highlight_merger.py ^
# "backend\uploads\match_xxxxx\video.mp4"
#
#
# OPTION 3:
#
# python backend\pipelines\highlight_merger.py ^
# "video.mp4" ^
# "ball_highlight_windows.csv" ^
# "goal_events.csv" ^
# "output_directory"
#
# ================================================================

if __name__ == "__main__":

    # ============================================================
    # VIDEO
    # ============================================================

    if len(sys.argv) >= 2:

        input_video = sys.argv[1]

    else:

        input_video = find_latest_uploaded_video()


    # ============================================================
    # OPTIONAL BALL CSV
    # ============================================================

    if len(sys.argv) >= 3:

        input_ball_csv = sys.argv[2]

    else:

        input_ball_csv = None


    # ============================================================
    # OPTIONAL GOAL CSV
    # ============================================================

    if len(sys.argv) >= 4:

        input_goal_file = sys.argv[3]

    else:

        input_goal_file = None


    # ============================================================
    # OPTIONAL OUTPUT
    # ============================================================

    if len(sys.argv) >= 5:

        input_output_dir = sys.argv[4]

    else:

        input_output_dir = None


    # ============================================================
    # SELECTED VIDEO
    # ============================================================

    print(
        "\nInput video selected:"
    )


    print(
        input_video
    )


    # ============================================================
    # RUN
    # ============================================================

    result = generate_final_highlights(

        video_path=input_video,

        ball_windows_csv=input_ball_csv,

        goal_file=input_goal_file,

        output_dir=input_output_dir

    )


    # ============================================================
    # SUCCESS
    # ============================================================

    print(
        "\n" + "=" * 70
    )


    print(
        "SUCCESS"
    )


    print(
        "=" * 70
    )


    print(
        "\nMatch ID:"
    )


    print(
        result["match_id"]
    )


    print(
        "\nFinal AI highlight video:"
    )


    print(
        result["final_video"]
    )


    print(
        "\nMerged windows:"
    )


    print(
        result["merged_windows"]
    )


    print(
        "\nFinal clips:"
    )


    print(
        result["clips_dir"]
    )


    print(
        "\n" + "=" * 70
    )