# ================================================================
# BALL TRACKING HIGHLIGHT GENERATOR
#
# DYNAMIC / VIDEO-INDEPENDENT VERSION
#
# Pipeline:
#
# YOLO Detection
#       ↓
# Ball Tracking
#       ↓
# Ball Highlight Scoring
#       ↓
# Ball Highlight Windows CSV
#       ↓
# Generate individual ball highlight clips
#       ↓
# Create concat list
#       ↓
# Generate ball-only highlight video
#
# This module is completely dynamic.
#
# It DOES NOT use:
#     test_video.mp4
#
# It DOES NOT contain:
#     fixed upload paths
#     fixed match IDs
#     fixed output directories
#
# FastAPI can call:
#
# generate_ball_highlights(
#     video_path,
#     windows_csv,
#     output_dir
# )
#
# Therefore every uploaded football match can have its own:
#
# uploads/<match_id>/video.mp4
# outputs/<match_id>/ball/
#
# ================================================================

import os
import sys
import time
import subprocess

import pandas as pd
import cv2


# ================================================================
# FFMPEG
# ================================================================

def find_ffmpeg():

    print("\nChecking FFmpeg...")

    # ------------------------------------------------------------
    # Check FFmpeg in PATH
    # ------------------------------------------------------------

    try:

        result = subprocess.run(
            ["ffmpeg", "-version"],
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
    # Check known Windows locations
    # ------------------------------------------------------------

    possible_paths = [

        r"C:\ffmpeg\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe",

        r"C:\ffmpeg\bin\ffmpeg.exe",

    ]

    for path in possible_paths:

        if os.path.exists(path):

            print(
                f"FFmpeg : {path}"
            )

            return path

    raise FileNotFoundError(
        "FFmpeg was not found.\n"
        "Please install FFmpeg or add it to PATH."
    )


# ================================================================
# PATH NORMALIZATION
# ================================================================

def normalize_path(path):

    return os.path.abspath(
        os.path.normpath(
            path
        )
    )


# ================================================================
# VIDEO INFORMATION
# ================================================================

def get_video_info(video_path):

    video_path = normalize_path(
        video_path
    )

    cap = cv2.VideoCapture(
        video_path
    )

    if not cap.isOpened():

        raise RuntimeError(
            f"Could not open video:\n{video_path}"
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

    if total_frames <= 0:

        raise RuntimeError(
            "Could not determine video frame count."
        )

    duration = (
        total_frames / fps
    )

    return {

        "fps":
            float(fps),

        "total_frames":
            int(total_frames),

        "width":
            int(width),

        "height":
            int(height),

        "duration":
            float(duration)

    }


# ================================================================
# LOAD BALL HIGHLIGHT WINDOWS
# ================================================================

def load_highlight_windows(
    windows_csv,
    video_duration
):

    windows_csv = normalize_path(
        windows_csv
    )

    print(
        "\nLoading windows CSV:"
    )

    print(
        windows_csv
    )

    if not os.path.exists(
        windows_csv
    ):

        raise FileNotFoundError(
            f"Ball highlight windows CSV not found:\n"
            f"{windows_csv}"
        )

    try:

        windows = pd.read_csv(
            windows_csv
        )

    except Exception as exc:

        raise RuntimeError(
            f"Could not read ball highlight windows CSV:\n"
            f"{windows_csv}\n\n"
            f"{exc}"
        )

    required_columns = [

        "highlight_id",
        "start",
        "end",
        "peak",
        "duration",
        "score"

    ]

    missing_columns = [

        col
        for col in required_columns
        if col not in windows.columns

    ]

    if missing_columns:

        raise ValueError(
            "Ball highlight windows CSV is missing "
            f"required columns: {missing_columns}"
        )

    valid_windows = []

    for _, row in windows.iterrows():

        try:

            highlight_id = int(
                row["highlight_id"]
            )

            start = float(
                row["start"]
            )

            end = float(
                row["end"]
            )

            peak = float(
                row["peak"]
            )

            score = float(
                row["score"]
            )

        except (
            ValueError,
            TypeError
        ):

            continue

        # --------------------------------------------------------
        # Reject NaN / infinity
        # --------------------------------------------------------

        values = [
            start,
            end,
            peak,
            score
        ]

        if not all(
            pd.notna(value)
            for value in values
        ):

            continue

        # --------------------------------------------------------
        # Clamp to video duration
        # --------------------------------------------------------

        start = max(
            0.0,
            start
        )

        end = min(
            float(video_duration),
            end
        )

        peak = min(
            max(
                0.0,
                peak
            ),
            float(video_duration)
        )

        # --------------------------------------------------------
        # Ignore invalid windows
        # --------------------------------------------------------

        if end <= start:

            continue

        valid_windows.append({

            "highlight_id":
                highlight_id,

            "start":
                start,

            "end":
                end,

            "peak":
                peak,

            "duration":
                end - start,

            "score":
                score

        })

    if not valid_windows:

        raise RuntimeError(
            "No valid ball highlight windows available."
        )

    # ------------------------------------------------------------
    # Sort chronologically
    # ------------------------------------------------------------

    valid_windows.sort(
        key=lambda item: item["start"]
    )

    return pd.DataFrame(
        valid_windows
    )


# ================================================================
# REMOVE OLD BALL CLIPS
# ================================================================

def clean_clips_directory(
    clips_dir
):

    os.makedirs(
        clips_dir,
        exist_ok=True
    )

    print(
        "\nCleaning previous ball highlight clips..."
    )

    removed = 0

    for filename in os.listdir(
        clips_dir
    ):

        filepath = os.path.join(
            clips_dir,
            filename
        )

        if not os.path.isfile(
            filepath
        ):

            continue

        # --------------------------------------------------------
        # Only remove generated ball clips.
        #
        # Do NOT delete arbitrary files placed in the directory.
        # --------------------------------------------------------

        if not filename.startswith(
            "ball_highlight_"
        ):

            continue

        if not filename.lower().endswith(
            ".mp4"
        ):

            continue

        try:

            os.remove(
                filepath
            )

            removed += 1

        except Exception as exc:

            print(
                f"WARNING: Could not remove "
                f"{filepath}: {exc}"
            )

    print(
        f"Previous ball clips removed : {removed}"
    )


# ================================================================
# CREATE INDIVIDUAL BALL HIGHLIGHT CLIPS
# ================================================================

def create_ball_highlight_clips(
    video_path,
    windows,
    clips_dir,
    ffmpeg_exe
):

    video_path = normalize_path(
        video_path
    )

    clips_dir = normalize_path(
        clips_dir
    )

    os.makedirs(
        clips_dir,
        exist_ok=True
    )

    clean_clips_directory(
        clips_dir
    )

    clip_paths = []

    start_time = time.time()

    # ============================================================
    # GENERATE CLIPS
    # ============================================================

    for _, row in windows.iterrows():

        highlight_id = int(
            row["highlight_id"]
        )

        start = float(
            row["start"]
        )

        end = float(
            row["end"]
        )

        peak = float(
            row["peak"]
        )

        score = float(
            row["score"]
        )

        duration = (
            end - start
        )

        if duration <= 0:

            continue

        clip_filename = (

            f"ball_highlight_"
            f"{highlight_id:02d}_"
            f"score_{score:.3f}.mp4"

        )

        clip_path = os.path.join(
            clips_dir,
            clip_filename
        )

        print(

            f"\nBall Highlight "
            f"{highlight_id:02d} | "
            f"{start:.2f}s - "
            f"{end:.2f}s | "
            f"duration={duration:.2f}s | "
            f"peak={peak:.2f}s | "
            f"score={score:.3f}"

        )

        # ========================================================
        # FFMPEG COMMAND
        # ========================================================

        cmd = [

            ffmpeg_exe,

            "-hide_banner",

            "-loglevel",
            "error",

            "-y",

            # ----------------------------------------------------
            # Start position
            # ----------------------------------------------------

            "-ss",
            f"{start:.3f}",

            # ----------------------------------------------------
            # Input
            # ----------------------------------------------------

            "-i",
            video_path,

            # ----------------------------------------------------
            # Duration
            # ----------------------------------------------------

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
            # Avoid unwanted subtitle/data streams
            # ----------------------------------------------------

            "-sn",

            "-dn",

            # ----------------------------------------------------
            # MP4 compatibility
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
                f"ball highlight "
                f"{highlight_id}."

            )

        if not os.path.exists(
            clip_path
        ):

            raise RuntimeError(

                f"Ball clip was not created:\n"
                f"{clip_path}"

            )

        # --------------------------------------------------------
        # Check file size
        # --------------------------------------------------------

        if os.path.getsize(
            clip_path
        ) == 0:

            raise RuntimeError(

                f"Ball clip is empty:\n"
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

    concat_list = normalize_path(
        concat_list
    )

    print(
        "\nCreating concat list..."
    )

    concat_dir = os.path.dirname(
        concat_list
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

            normalized_path = (

                normalize_path(
                    clip_path
                )

                .replace(
                    "\\",
                    "/"
                )

            )

            # ----------------------------------------------------
            # FFmpeg concat demuxer accepts:
            #
            # file 'C:/path/video.mp4'
            # ----------------------------------------------------

            f.write(
                f"file '{normalized_path}'\n"
            )

    print(
        f"Concat list : {concat_list}"
    )


# ================================================================
# ASSEMBLE BALL HIGHLIGHTS
# ================================================================

def assemble_ball_highlights(
    concat_list,
    final_video,
    ffmpeg_exe
):

    concat_list = normalize_path(
        concat_list
    )

    final_video = normalize_path(
        final_video
    )

    print(
        "\nAssembling ball highlight video..."
    )

    final_dir = os.path.dirname(
        final_video
    )

    os.makedirs(
        final_dir,
        exist_ok=True
    )

    if not os.path.exists(
        concat_list
    ):

        raise FileNotFoundError(
            f"Concat list not found:\n"
            f"{concat_list}"
        )

    # ------------------------------------------------------------
    # Check concat list is not empty
    # ------------------------------------------------------------

    if os.path.getsize(
        concat_list
    ) == 0:

        raise RuntimeError(
            "Concat list is empty. "
            "No ball clips are available."
        )

    cmd = [

        ffmpeg_exe,

        "-hide_banner",

        "-loglevel",
        "error",

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
            "Ball highlight video "
            "assembly failed."
        )

    if not os.path.exists(
        final_video
    ):

        raise RuntimeError(
            "Ball highlight video "
            "was not created."
        )

    if os.path.getsize(
        final_video
    ) == 0:

        raise RuntimeError(
            "Ball highlight video "
            "was created but is empty."
        )

    return assembly_time


# ================================================================
# MAIN BALL HIGHLIGHT GENERATOR
# ================================================================

def generate_ball_highlights(
    video_path,
    windows_csv,
    output_dir
):

    print(
        "=" * 70
    )

    print(
        "BALL TRACKING HIGHLIGHT GENERATOR"
    )

    print(
        "=" * 70
    )

    # ============================================================
    # NORMALIZE PATHS
    # ============================================================

    video_path = normalize_path(
        video_path
    )

    windows_csv = normalize_path(
        windows_csv
    )

    output_dir = normalize_path(
        output_dir
    )

    print(
        "\nDYNAMIC INPUTS"
    )

    print(
        "-" * 70
    )

    print(
        f"Video       : {video_path}"
    )

    print(
        f"Windows CSV : {windows_csv}"
    )

    print(
        f"Output dir  : {output_dir}"
    )

    # ============================================================
    # CHECK INPUTS
    # ============================================================

    print(
        "\nChecking files..."
    )

    # ------------------------------------------------------------
    # Video
    # ------------------------------------------------------------

    if not os.path.exists(
        video_path
    ):

        raise FileNotFoundError(

            f"Video not found:\n"
            f"{video_path}"

        )

    if not os.path.isfile(
        video_path
    ):

        raise ValueError(
            f"Video path is not a file:\n"
            f"{video_path}"
        )

    print(
        "Video : OK"
    )

    # ------------------------------------------------------------
    # Windows CSV
    # ------------------------------------------------------------

    if not os.path.exists(
        windows_csv
    ):

        raise FileNotFoundError(

            "Ball highlight windows CSV "
            "not found:\n"
            f"{windows_csv}"

        )

    if not os.path.isfile(
        windows_csv
    ):

        raise ValueError(
            f"Windows CSV path is not a file:\n"
            f"{windows_csv}"
        )

    print(
        "Windows CSV : OK"
    )

    # ============================================================
    # CREATE OUTPUT DIRECTORY
    # ============================================================

    os.makedirs(
        output_dir,
        exist_ok=True
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
    # OUTPUT PATHS
    #
    # Everything belongs to the supplied output directory.
    #
    # Example:
    #
    # outputs/
    #     match_001/
    #         ball/
    #
    #             clips/
    #
    #                 ball_highlight_01_score_0.850.mp4
    #
    #             ball_concat_list.txt
    #
    #             ball_AI_highlights.mp4
    #
    # ============================================================

    clips_dir = os.path.join(
        output_dir,
        "clips"
    )

    concat_list = os.path.join(
        output_dir,
        "ball_concat_list.txt"
    )

    final_video = os.path.join(
        output_dir,
        "ball_AI_highlights.mp4"
    )

    # ============================================================
    # LOAD WINDOWS
    # ============================================================

    print(
        "\nLOADING BALL HIGHLIGHT WINDOWS"
    )

    print(
        "-" * 70
    )

    windows = load_highlight_windows(

        windows_csv,

        video_info["duration"]

    )

    print(
        f"Windows loaded : "
        f"{len(windows)}"
    )

    total_duration = (
        windows["duration"].sum()
    )

    print(
        f"Ball highlight duration : "
        f"{total_duration:.2f}s"
    )

    print(
        f"Ball highlight duration : "
        f"{total_duration / 60:.2f} min"
    )

    # ============================================================
    # SHOW WINDOWS
    # ============================================================

    print(
        "\nBALL HIGHLIGHT WINDOWS"
    )

    print(
        "-" * 70
    )

    for _, row in windows.iterrows():

        print(

            f"Highlight "
            f"{int(row['highlight_id']):02d}: "

            f"{row['start']:.2f}s -> "
            f"{row['end']:.2f}s | "

            f"Peak: "
            f"{row['peak']:.2f}s | "

            f"Score: "
            f"{row['score']:.3f}"

        )

    # ============================================================
    # CREATE BALL CLIPS
    # ============================================================

    print(
        "\nCREATING BALL HIGHLIGHT CLIPS"
    )

    print(
        "-" * 70
    )

    (
        clip_paths,
        generation_time

    ) = create_ball_highlight_clips(

        video_path,

        windows,

        clips_dir,

        ffmpeg_exe

    )

    print(
        f"\nBall clips created : "
        f"{len(clip_paths)}"
    )

    print(
        f"Generation time : "
        f"{generation_time:.2f}s"
    )

    # ============================================================
    # SAFETY CHECK
    # ============================================================

    if not clip_paths:

        raise RuntimeError(
            "No ball highlight clips were created."
        )

    # ============================================================
    # CREATE CONCAT LIST
    # ============================================================

    create_concat_list(

        clip_paths,

        concat_list

    )

    # ============================================================
    # ASSEMBLE BALL-ONLY VIDEO
    # ============================================================

    print(
        "\nASSEMBLING BALL HIGHLIGHT VIDEO"
    )

    print(
        "-" * 70
    )

    assembly_time = (

        assemble_ball_highlights(

            concat_list,

            final_video,

            ffmpeg_exe

        )

    )

    # ============================================================
    # FINAL FILE SIZE
    # ============================================================

    final_size_mb = (

        os.path.getsize(
            final_video
        )

        /

        (1024 * 1024)

    )

    # ============================================================
    # FINAL RESULT
    # ============================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "BALL HIGHLIGHT GENERATION COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        f"Ball clips created : "
        f"{len(clip_paths)}"
    )

    print(
        f"Highlight duration : "
        f"{total_duration / 60:.2f} min"
    )

    print(
        f"Generation time    : "
        f"{generation_time:.2f}s"
    )

    print(
        f"Assembly time      : "
        f"{assembly_time:.2f}s"
    )

    print(
        f"Final size         : "
        f"{final_size_mb:.2f} MB"
    )

    print(
        "\nBALL HIGHLIGHT VIDEO:"
    )

    print(
        final_video
    )

    print(
        "\nBALL CLIPS DIRECTORY:"
    )

    print(
        clips_dir
    )

    print(
        "=" * 70
    )

    # ============================================================
    # RETURN RESULT
    #
    # FastAPI can directly consume these paths.
    # ============================================================

    return {

        "video_path":
            video_path,

        "windows_csv":
            windows_csv,

        "output_dir":
            output_dir,

        "final_video":
            final_video,

        "clips":
            clip_paths,

        "clips_dir":
            clips_dir,

        "concat_list":
            concat_list,

        "windows":
            len(windows),

        "duration_seconds":
            float(total_duration),

        "duration_minutes":
            float(
                total_duration / 60
            ),

        "generation_time":
            float(
                generation_time
            ),

        "assembly_time":
            float(
                assembly_time
            ),

        "final_size_mb":
            float(
                final_size_mb
            )

    }


# ================================================================
# COMMAND LINE TESTING
#
# This section is ONLY for manually testing the module.
#
# There is NO hard-coded video.
#
# Usage:
#
# python backend\pipelines\ball_highlight_generator.py ^
#     "C:\path\video.mp4" ^
#     "C:\path\ball_highlight_windows.csv" ^
#     "C:\path\output"
#
# ================================================================

if __name__ == "__main__":

    if len(sys.argv) != 4:

        print(
            "\nUsage:"
        )

        print(
            "python ball_highlight_generator.py "
            "<video_path> "
            "<windows_csv> "
            "<output_dir>"
        )

        print(
            "\nExample:"
        )

        print(
            'python ball_highlight_generator.py '
            '"C:\\Football_Project\\football_highlight_app\\backend\\uploads\\match_001\\video.mp4" '
            '"C:\\Football_Project\\football_highlight_app\\backend\\outputs\\match_001\\ball\\ball_highlight_windows.csv" '
            '"C:\\Football_Project\\football_highlight_app\\backend\\outputs\\match_001\\ball"'
        )

        sys.exit(1)

    # ------------------------------------------------------------
    # Read dynamic command-line arguments
    # ------------------------------------------------------------

    video_path = sys.argv[1]

    windows_csv = sys.argv[2]

    output_dir = sys.argv[3]

    # ------------------------------------------------------------
    # Run pipeline
    # ------------------------------------------------------------

    result = generate_ball_highlights(

        video_path=video_path,

        windows_csv=windows_csv,

        output_dir=output_dir

    )

    # ------------------------------------------------------------
    # Print result
    # ------------------------------------------------------------

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
        "\nFinal ball highlight video:"
    )

    print(
        result["final_video"]
    )

    print(
        "\nBall clips:"
    )

    print(
        result["clips_dir"]
    )

    print(
        "\nOutput directory:"
    )

    print(
        result["output_dir"]
    )

    print(
        "=" * 70
    )
