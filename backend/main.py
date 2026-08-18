import os
import time
import uuid
import shutil
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


# ============================================================
# PIPELINE IMPORTS
# ============================================================

from backend.pipelines.scoreboard_goal_detector import (
    detect_scoreboard_goals
)

from backend.pipelines.ball_detector import (
    detect_objects
)

from backend.pipelines.ball_tracker import (
    track_ball
)

from backend.pipelines.ball_highlight_scorer import (
    score_ball_highlights
)

from backend.pipelines.highlight_merger import (
    generate_final_highlights
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "outputs"
)


os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(

    title="Football AI Highlight Generator",

    description=(
        "AI-powered football video "
        "highlight generation backend."
    ),

    version="2.0.0"

)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# SERVE GENERATED OUTPUT FILES
# ============================================================

app.mount(

    "/outputs",

    StaticFiles(
        directory=OUTPUT_DIR
    ),

    name="outputs"

)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def root():

    return {

        "message":
            "Football AI Highlight Generator API",

        "status":
            "running"

    }


@app.get("/api/health")
def health():

    return {

        "status":
            "ok"

    }


# ============================================================
# CREATE MATCH ID
# ============================================================

def create_match_id():

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    random_id = uuid.uuid4().hex[:6]

    return (
        f"match_{timestamp}_{random_id}"
    )


# ============================================================
# CONVERT FILE PATH TO BROWSER URL
# ============================================================

def output_url(file_path):

    if not file_path:

        return None

    try:

        relative_path = os.path.relpath(

            file_path,

            OUTPUT_DIR

        )

    except ValueError:

        return None

    relative_path = relative_path.replace(

        os.sep,

        "/"

    )

    return (
        "/outputs/"
        + relative_path
    )


# ============================================================
# UPLOAD VIDEO + FULL AI PIPELINE
# ============================================================

@app.post("/api/upload")
async def upload_video(

    file: UploadFile = File(...)

):

    pipeline_start = time.time()

    print()

    print("=" * 70)

    print(
        "NEW VIDEO UPLOAD"
    )

    print("=" * 70)


    # ========================================================
    # VALIDATE FILENAME
    # ========================================================

    if not file.filename:

        raise HTTPException(

            status_code=400,

            detail="No filename provided."

        )


    # ========================================================
    # VALIDATE EXTENSION
    # ========================================================

    allowed_extensions = {

        ".mp4",
        ".avi",
        ".mkv",
        ".mov",
        ".webm"

    }


    extension = os.path.splitext(

        file.filename

    )[1].lower()


    if extension not in allowed_extensions:

        raise HTTPException(

            status_code=400,

            detail=(

                "Unsupported video format. "

                f"Allowed: "
                f"{sorted(allowed_extensions)}"

            )

        )


    # ========================================================
    # CREATE MATCH ID
    # ========================================================

    match_id = create_match_id()

    print()

    print(
        f"Match ID: {match_id}"
    )


    # ========================================================
    # MATCH DIRECTORIES
    # ========================================================

    match_upload_dir = os.path.join(

        UPLOAD_DIR,

        match_id

    )


    match_output_dir = os.path.join(

        OUTPUT_DIR,

        match_id

    )


    os.makedirs(

        match_upload_dir,

        exist_ok=True

    )


    os.makedirs(

        match_output_dir,

        exist_ok=True

    )


    # ========================================================
    # VIDEO PATH
    # ========================================================

    video_filename = (

        "video"
        + extension

    )


    video_path = os.path.join(

        match_upload_dir,

        video_filename

    )


    # ========================================================
    # SAVE VIDEO
    # ========================================================

    print()

    print(
        "Saving uploaded video..."
    )


    try:

        with open(

            video_path,

            "wb"

        ) as buffer:

            shutil.copyfileobj(

                file.file,

                buffer

            )

    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail=(

                "Failed to save uploaded video: "

                f"{exc}"

            )

        )


    file_size = os.path.getsize(

        video_path

    )


    print()

    print(
        f"Video saved: {video_path}"
    )

    print(

        f"File size : "
        f"{file_size / (1024 * 1024):.2f} MB"

    )


    # ============================================================
    # STAGE 1 — SCOREBOARD GOAL DETECTION
    # ============================================================

    print()

    print("=" * 70)

    print(
        "STAGE 1 — SCOREBOARD GOAL DETECTION"
    )

    print("=" * 70)


    scoreboard_start = time.time()


    try:

        scoreboard_result = detect_scoreboard_goals(

            video_path=video_path,

            output_dir=match_output_dir

        )

    except Exception as exc:

        print()

        print(
            "SCOREBOARD DETECTION FAILED"
        )

        print(exc)


        raise HTTPException(

            status_code=500,

            detail=(

                "Scoreboard goal detection failed: "

                f"{exc}"

            )

        )


    scoreboard_time = (

        time.time()
        - scoreboard_start

    )


    goal_events_csv = os.path.join(

        match_output_dir,

        "scoreboard_goals",

        "goal_events.csv"

    )


    detected_goals_txt = os.path.join(

        match_output_dir,

        "detected_goals.txt"

    )


    print()

    print(

        f"Scoreboard processing complete: "
        f"{scoreboard_time:.2f}s"

    )

    print(
        f"Goal CSV: {goal_events_csv}"
    )


    if not os.path.isfile(

        goal_events_csv

    ):

        raise HTTPException(

            status_code=500,

            detail=(

                "Scoreboard detector completed "
                "but goal_events.csv was not created."

            )

        )


    # ============================================================
    # STAGE 2 — YOLO BALL / OBJECT DETECTION
    # ============================================================

    print()

    print("=" * 70)

    print(
        "STAGE 2 — YOLO BALL / OBJECT DETECTION"
    )

    print("=" * 70)


    detection_start = time.time()


    ball_detection_dir = os.path.join(

        match_output_dir,

        "ball_detection"

    )


    os.makedirs(

        ball_detection_dir,

        exist_ok=True

    )


    detections_csv = os.path.join(

        ball_detection_dir,

        "detections.csv"

    )


    try:

        detection_result = detect_objects(

            video_path,

            detections_csv

        )

    except Exception as exc:

        print()

        print(
            "BALL DETECTION FAILED"
        )

        print(exc)


        raise HTTPException(

            status_code=500,

            detail=(

                "Ball detection failed: "

                f"{exc}"

            )

        )


    detection_time = (

        time.time()
        - detection_start

    )


    detections_csv = detection_result[

        "output_csv"

    ]


    print()

    print(

        f"Ball detection complete: "
        f"{detection_time:.2f}s"

    )

    print(

        f"Detections CSV: "
        f"{detections_csv}"

    )


    if not os.path.isfile(

        detections_csv

    ):

        raise HTTPException(

            status_code=500,

            detail=(

                "Ball detector completed "
                "but detections CSV was not created."

            )

        )


    # ============================================================
    # STAGE 3 — BALL TRACKING + KALMAN
    # ============================================================

    print()

    print("=" * 70)

    print(
        "STAGE 3 — BALL TRACKING + KALMAN"
    )

    print("=" * 70)


    tracking_start = time.time()


    tracking_dir = os.path.join(

        match_output_dir,

        "ball_tracking"

    )


    os.makedirs(

        tracking_dir,

        exist_ok=True

    )


    try:

        tracking_result = track_ball(

            detections_csv,

            tracking_dir

        )

    except Exception as exc:

        print()

        print(
            "BALL TRACKING FAILED"
        )

        print(exc)


        raise HTTPException(

            status_code=500,

            detail=(

                "Ball tracking failed: "

                f"{exc}"

            )

        )


    tracking_time = (

        time.time()
        - tracking_start

    )


    final_trajectory_csv = tracking_result[

        "final_csv"

    ]


    print()

    print(

        f"Ball tracking complete: "
        f"{tracking_time:.2f}s"

    )

    print(

        f"Final trajectory: "
        f"{final_trajectory_csv}"

    )


    if not os.path.isfile(

        final_trajectory_csv

    ):

        raise HTTPException(

            status_code=500,

            detail=(

                "Ball tracking completed "
                "but final trajectory CSV "
                "was not created."

            )

        )


    # ============================================================
    # STAGE 4 — BALL HIGHLIGHT SCORING
    # ============================================================

    print()

    print("=" * 70)

    print(
        "STAGE 4 — BALL HIGHLIGHT SCORING"
    )

    print("=" * 70)


    scoring_start = time.time()


    scoring_dir = os.path.join(

        match_output_dir,

        "ball_highlights"

    )


    os.makedirs(

        scoring_dir,

        exist_ok=True

    )


    try:

        scoring_result = score_ball_highlights(

            final_trajectory_csv,

            scoring_dir

        )

    except Exception as exc:

        print()

        print(
            "BALL HIGHLIGHT SCORING FAILED"
        )

        print(exc)


        raise HTTPException(

            status_code=500,

            detail=(

                "Ball highlight scoring failed: "

                f"{exc}"

            )

        )


    scoring_time = (

        time.time()
        - scoring_start

    )


    ball_windows_csv = scoring_result[

        "windows_csv"

    ]


    print()

    print(

        f"Ball highlight scoring complete: "
        f"{scoring_time:.2f}s"

    )

    print(

        f"Highlight windows: "
        f"{ball_windows_csv}"

    )


    if not os.path.isfile(

        ball_windows_csv

    ):

        raise HTTPException(

            status_code=500,

            detail=(

                "Ball highlight scorer completed "
                "but windows CSV was not created."

            )

        )


    # ============================================================
    # STAGE 5 — MERGE GOALS + BALL HIGHLIGHTS
    # ============================================================

    print()

    print("=" * 70)

    print(
        "STAGE 5 — FINAL HIGHLIGHT GENERATION"
    )

    print("=" * 70)


    merger_start = time.time()


    final_output_dir = os.path.join(

        match_output_dir,

        "final_highlights"

    )


    os.makedirs(

        final_output_dir,

        exist_ok=True

    )


    try:

        final_result = generate_final_highlights(

            video_path=video_path,

            ball_windows_csv=ball_windows_csv,

            goal_file=goal_events_csv,

            output_dir=final_output_dir

        )

    except Exception as exc:

        print()

        print(
            "FINAL HIGHLIGHT GENERATION FAILED"
        )

        print(exc)


        raise HTTPException(

            status_code=500,

            detail=(

                "Final highlight generation failed: "

                f"{exc}"

            )

        )


    merger_time = (

        time.time()
        - merger_start

    )


    final_video = final_result[

        "final_video"

    ]


    merged_windows = final_result[

        "merged_windows"

    ]


    # ============================================================
    # VERIFY FINAL VIDEO
    # ============================================================

    if not os.path.isfile(

        final_video

    ):

        raise HTTPException(

            status_code=500,

            detail=(

                "Final highlight generation completed "
                "but final video was not created."

            )

        )


    # ============================================================
    # TOTAL PROCESSING TIME
    # ============================================================

    total_time = (

        time.time()
        - pipeline_start

    )


    # ============================================================
    # CREATE BROWSER URLS
    # ============================================================

    final_video_url = output_url(

        final_video

    )


    merged_windows_url = output_url(

        merged_windows

    )


    goal_events_url = output_url(

        goal_events_csv

    )


    detected_goals_url = output_url(

        detected_goals_txt

    )


    detections_url = output_url(

        detections_csv

    )


    trajectory_url = output_url(

        final_trajectory_csv

    )


    ball_windows_url = output_url(

        ball_windows_csv

    )


    scores_url = output_url(

        scoring_result.get(

            "scores_csv"

        )

    )


    # ============================================================
    # FINAL PIPELINE LOG
    # ============================================================

    print()

    print("=" * 70)

    print(
        "UPLOAD + FULL AI HIGHLIGHT PIPELINE COMPLETE"
    )

    print("=" * 70)

    print(

        f"Match ID             : "
        f"{match_id}"

    )

    print(

        f"Goals detected       : "
        f"{final_result.get('goal_windows', 0)}"

    )

    print(

        f"Ball windows         : "
        f"{final_result.get('ball_windows', 0)}"

    )

    print(

        f"Combined windows     : "
        f"{final_result.get('combined_windows', 0)}"

    )

    print(

        f"Final windows        : "
        f"{final_result.get('final_windows', 0)}"

    )

    print(

        f"Final video          : "
        f"{final_video}"

    )

    print(

        f"Total processing     : "
        f"{total_time:.2f}s"

    )

    print("=" * 70)


    # ============================================================
    # API RESPONSE
    # ============================================================

    return {

        "status":
            "completed",

        "match_id":
            match_id,

        "filename":
            file.filename,

        "stored_filename":
            video_filename,

        "file_size_bytes":
            file_size,

        "video_path":
            video_path,

        # ========================================================
        # SCOREBOARD
        # ========================================================

        "scoreboard": {

            "goal_events_csv":
                goal_events_csv,

            "goal_events_url":
                goal_events_url,

            "detected_goals_file":
                detected_goals_txt,

            "detected_goals_url":
                detected_goals_url,

            "goal_count":
                scoreboard_result.get(
                    "goal_count",
                    0
                ),

            "goals":
                scoreboard_result.get(
                    "goals",
                    []
                ),

            "duration":
                scoreboard_result.get(
                    "duration"
                ),

            "fps":
                scoreboard_result.get(
                    "fps"
                ),

            "processing_time":
                scoreboard_time,

            "processing_fps":
                scoreboard_result.get(
                    "processing_fps"
                ),

            "real_time_factor":
                scoreboard_result.get(
                    "real_time_factor"
                ),

            "device":
                scoreboard_result.get(
                    "device"
                )

        },

        # ========================================================
        # BALL DETECTION
        # ========================================================

        "ball_detection": {

            "detections_csv":
                detections_csv,

            "detections_url":
                detections_url,

            "processing_time":
                detection_time,

            "frames_processed":
                detection_result.get(
                    "frames_processed"
                ),

            "detection_rows":
                detection_result.get(
                    "detection_rows"
                ),

            "processing_fps":
                detection_result.get(
                    "processing_fps"
                ),

            "real_time_factor":
                detection_result.get(
                    "real_time_factor"
                )

        },

        # ========================================================
        # BALL TRACKING
        # ========================================================

        "ball_tracking": {

            "final_csv":
                final_trajectory_csv,

            "final_csv_url":
                trajectory_url,

            "ball_positions_csv":
                tracking_result.get(
                    "ball_positions_csv"
                ),

            "interpolated_csv":
                tracking_result.get(
                    "interpolated_csv"
                ),

            "kalman_csv":
                tracking_result.get(
                    "kalman_csv"
                ),

            "ball_detections":
                tracking_result.get(
                    "ball_detections"
                ),

            "trajectory_rows":
                tracking_result.get(
                    "trajectory_rows"
                ),

            "detected":
                tracking_result.get(
                    "detected"
                ),

            "kalman":
                tracking_result.get(
                    "kalman"
                ),

            "lost":
                tracking_result.get(
                    "lost"
                ),

            "valid_positions":
                tracking_result.get(
                    "valid_positions"
                ),

            "coverage":
                tracking_result.get(
                    "coverage"
                ),

            "processing_time":
                tracking_time

        },

        # ========================================================
        # BALL HIGHLIGHTS
        # ========================================================

        "ball_highlights": {

            "windows_csv":
                ball_windows_csv,

            "windows_url":
                ball_windows_url,

            "scores_csv":
                scoring_result.get(
                    "scores_csv"
                ),

            "scores_url":
                scores_url,

            "highlights":
                scoring_result.get(
                    "highlights"
                ),

            "duration_seconds":
                scoring_result.get(
                    "duration_seconds"
                ),

            "processing_time":
                scoring_time

        },

        # ========================================================
        # FINAL HIGHLIGHTS
        # ========================================================

        "final_highlights": {

            "video":
                final_video,

            "video_url":
                final_video_url,

            "merged_windows":
                merged_windows,

            "merged_windows_url":
                merged_windows_url,

            "clips":
                final_result.get(
                    "clips"
                ),

            "clips_dir":
                final_result.get(
                    "clips_dir"
                ),

            "ball_windows":
                final_result.get(
                    "ball_windows"
                ),

            "goal_windows":
                final_result.get(
                    "goal_windows"
                ),

            "combined_windows":
                final_result.get(
                    "combined_windows"
                ),

            "final_windows":
                final_result.get(
                    "final_windows"
                ),

            "duration_seconds":
                final_result.get(
                    "duration_seconds"
                ),

            "processing_time":
                merger_time

        },

        # ========================================================
        # TOTAL
        # ========================================================

        "processing_time":
            total_time

    }


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "backend.main:app",

        host="127.0.0.1",

        port=8000,

        reload=True

    )