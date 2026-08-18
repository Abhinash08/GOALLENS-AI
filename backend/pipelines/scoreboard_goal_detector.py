# ============================================================
# SCOREBOARD GOAL DETECTION PIPELINE
#
# Pipeline:
#
# Uploaded Football Video
#          ↓
# Sequential Video Reading
#          ↓
# YOLO Scoreboard Detection
#          ↓
# EasyOCR
#          ↓
# Score Parsing
#          ↓
# Temporal Score Confirmation
#          ↓
# Goal Detection
#          ↓
# goal_events.csv
#
# ============================================================
#
# TWO WAYS TO USE THIS FILE
#
# 1. FastAPI / Python:
#
#       from scoreboard_goal_detector import detect_scoreboard_goals
#
#       result = detect_scoreboard_goals(
#           video_path=video_path,
#           output_dir=output_dir
#       )
#
#
# 2. Terminal testing:
#
#       python scoreboard_goal_detector.py "video.mp4"
#
# IMPORTANT:
# sys.argv is ONLY used in the direct-execution section.
#
# ============================================================


# ============================================================
# SUPPRESS OPENCV FFMPEG LOGGING
#
# MUST BE BEFORE cv2 IMPORT
# ============================================================

import os

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "loglevel;quiet"
)


# ============================================================
# IMPORTS
# ============================================================

import re
import sys
import time

import cv2
import torch
import easyocr
import pandas as pd

from ultralytics import YOLO


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = (
    r"C:\Football_Project\football_highlight_app"
)


# ============================================================
# YOLO SCOREBOARD MODEL
# ============================================================

YOLO_PATH = (
    r"C:\Football_Project\YOLO_training"
    r"\scoreboard_training"
    r"\scoreboard_yolo11n_10ep"
    r"\weights"
    r"\best.pt"
)


# ============================================================
# DEFAULT OUTPUT DIRECTORY
# ============================================================

DEFAULT_OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "backend",
    "outputs"
)


# ============================================================
# TEMPORAL SETTINGS
# ============================================================

# Process one frame every 0.5 seconds.
SAMPLE_INTERVAL = 0.5


# Number of consecutive detections required before
# considering a score change to be a goal.
CONFIRMATIONS_REQUIRED = 3


# YOLO scoreboard confidence threshold.
YOLO_CONFIDENCE = 0.35


# Minimum OCR confidence.
MIN_OCR_CONFIDENCE = 0.30


# Maximum horizontal distance between separate
# score digits relative to scoreboard crop width.
MAX_DIGIT_DISTANCE_RATIO = 0.35


# ============================================================
# SCOREBOARD OCR PARSER
# ============================================================

def parse_scoreboard_ocr(
    ocr_results,
    crop_width
):

    items = []

    # ========================================================
    # NORMALIZE OCR RESULTS
    # ========================================================

    for result in ocr_results:

        if len(result) < 3:
            continue

        box, text, confidence = result

        text = str(
            text
        ).strip()

        if not text:
            continue

        try:

            xs = [
                float(point[0])
                for point in box
            ]

            ys = [
                float(point[1])
                for point in box
            ]

            cx = (
                sum(xs)
                /
                len(xs)
            )

            cy = (
                sum(ys)
                /
                len(ys)
            )

            confidence = float(
                confidence
            )

        except Exception:

            continue

        items.append({

            "text":
                text,

            "confidence":
                confidence,

            "x":
                cx,

            "y":
                cy

        })

    if not items:
        return None

    # ========================================================
    # SORT LEFT -> RIGHT
    # ========================================================

    items.sort(
        key=lambda item:
            item["x"]
    )

    # ========================================================
    # LOOK FOR COMBINED SCORE
    #
    # Examples:
    #
    # 0-0
    # 1-0
    # 2-1
    # 3:2
    # 2/1
    #
    # ========================================================

    combined_candidates = []

    for item in items:

        cleaned = (
            item["text"]
            .replace(" ", "")
        )

        match = re.fullmatch(
            r"([0-9])[/|:\-\\]([0-9])",
            cleaned
        )

        if match:

            left = int(
                match.group(1)
            )

            right = int(
                match.group(2)
            )

            combined_candidates.append({

                "score": (
                    left,
                    right
                ),

                "x":
                    item["x"],

                "confidence":
                    item["confidence"]

            })

    # ========================================================
    # RETURN BEST COMBINED SCORE
    # ========================================================

    if combined_candidates:

        best = max(
            combined_candidates,
            key=lambda item:
                item["confidence"]
        )

        return {

            "score":
                best["score"],

            "pair_confidence":
                best["confidence"],

            "type":
                "combined"

        }

    # ========================================================
    # FIND INDIVIDUAL DIGITS
    # ========================================================

    numeric = []

    for item in items:

        text = item["text"].strip()

        if re.fullmatch(
            r"[0-9]",
            text
        ):

            if (
                item["confidence"]
                >=
                MIN_OCR_CONFIDENCE
            ):

                numeric.append(
                    item
                )

    if len(numeric) < 2:
        return None

    # ========================================================
    # FIND CLOSEST DIGIT PAIR
    # ========================================================

    best_pair = None

    best_distance = float(
        "inf"
    )

    for i in range(
        len(numeric)
    ):

        for j in range(
            i + 1,
            len(numeric)
        ):

            a = numeric[i]
            b = numeric[j]

            distance = abs(
                b["x"]
                -
                a["x"]
            )

            if distance < best_distance:

                best_distance = (
                    distance
                )

                best_pair = (
                    a,
                    b
                )

    if best_pair is None:
        return None

    left_digit = best_pair[0]
    right_digit = best_pair[1]

    # ========================================================
    # SANITY CHECK
    # ========================================================

    try:

        left_score = int(
            left_digit["text"]
        )

        right_score = int(
            right_digit["text"]
        )

    except Exception:

        return None

    if left_score > 9:
        return None

    if right_score > 9:
        return None

    # ========================================================
    # DISTANCE CHECK
    # ========================================================

    if (
        best_distance
        >
        crop_width
        *
        MAX_DIGIT_DISTANCE_RATIO
    ):

        return None

    # ========================================================
    # CONFIDENCE
    # ========================================================

    pair_confidence = (

        left_digit["confidence"]
        +
        right_digit["confidence"]

    ) / 2.0

    if (
        pair_confidence
        <
        MIN_OCR_CONFIDENCE
    ):

        return None

    # ========================================================
    # RETURN SCORE
    # ========================================================

    return {

        "score": (

            left_score,
            right_score

        ),

        "pair_confidence":
            pair_confidence,

        "type":
            "separate"

    }


# ============================================================
# FORMAT SCORE
# ============================================================

def format_score(
    score
):

    if score is None:
        return "None"

    try:

        return (
            f"{int(score[0])}-"
            f"{int(score[1])}"
        )

    except Exception:

        return str(score)


# ============================================================
# LOAD MODELS
# ============================================================

def load_models():

    print(
        "\nLoading scoreboard YOLO..."
    )

    if not os.path.exists(
        YOLO_PATH
    ):

        raise FileNotFoundError(
            "YOLO scoreboard model "
            "not found:\n"
            f"{YOLO_PATH}"
        )

    yolo = YOLO(
        YOLO_PATH
    )

    print(
        "YOLO classes:"
    )

    print(
        yolo.names
    )

    # ========================================================
    # CUDA
    # ========================================================

    cuda_available = (
        torch.cuda.is_available()
    )

    print(
        "\nCUDA:",
        cuda_available
    )

    if cuda_available:

        print(
            "GPU:",
            torch.cuda.get_device_name(0)
        )

    device = (
        0
        if cuda_available
        else "cpu"
    )

    # ========================================================
    # EASYOCR
    # ========================================================

    print(
        "\nLoading EasyOCR..."
    )

    reader = easyocr.Reader(
        ["en"],
        gpu=cuda_available
    )

    print(
        "EasyOCR:",
        "CUDA"
        if cuda_available
        else "CPU"
    )

    return (
        yolo,
        reader,
        device,
        cuda_available
    )


# ============================================================
# PROCESS SINGLE SCOREBOARD FRAME
# ============================================================

def process_scoreboard_frame(
    frame,
    yolo,
    reader,
    device,
    width,
    height
):

    scoreboard_found = False

    best_box = None

    best_conf = 0.0

    # ========================================================
    # YOLO
    # ========================================================

    try:

        results = yolo.predict(

            frame,

            device=device,

            verbose=False,

            conf=YOLO_CONFIDENCE

        )

    except Exception as exc:

        print(
            "\nYOLO frame error:",
            exc
        )

        return {

            "scoreboard_found":
                False,

            "score":
                None,

            "confidence":
                0.0

        }

    # ========================================================
    # FIND BEST SCOREBOARD
    # ========================================================

    for result in results:

        if result.boxes is None:
            continue

        for box in result.boxes:

            try:

                conf = float(
                    box.conf[0]
                )

                cls = int(
                    box.cls[0]
                )

            except Exception:

                continue

            # Class 0 = scoreboard
            if (
                cls == 0
                and
                conf > best_conf
            ):

                best_conf = conf
                best_box = box

    if best_box is not None:

        scoreboard_found = True

    score_result = None

    # ========================================================
    # OCR SCOREBOARD
    # ========================================================

    if scoreboard_found:

        try:

            coords = (
                best_box
                .xyxy[0]
                .cpu()
                .numpy()
            )

            x1, y1, x2, y2 = map(
                int,
                coords
            )

            # ------------------------------------------------
            # Clamp coordinates
            # ------------------------------------------------

            x1 = max(
                0,
                x1
            )

            y1 = max(
                0,
                y1
            )

            x2 = min(
                width,
                x2
            )

            y2 = min(
                height,
                y2
            )

            if (
                x2 > x1
                and
                y2 > y1
            ):

                crop = frame[
                    y1:y2,
                    x1:x2
                ]

                if crop.size > 0:

                    ocr_results = (
                        reader.readtext(
                            crop,
                            detail=1,
                            paragraph=False
                        )
                    )

                    if ocr_results:

                        score_result = (
                            parse_scoreboard_ocr(
                                ocr_results,
                                crop.shape[1]
                            )
                        )

        except Exception as exc:

            print(
                "\nOCR frame error:",
                exc
            )

    # ========================================================
    # RETURN
    # ========================================================

    score = (
        score_result["score"]
        if score_result is not None
        else None
    )

    confidence = (
        score_result["pair_confidence"]
        if score_result is not None
        else 0.0
    )

    return {

        "scoreboard_found":
            scoreboard_found,

        "score":
            score,

        "confidence":
            confidence

    }


# ============================================================
# DETECT SCOREBOARD GOALS
#
# THIS IS THE REUSABLE BACKEND FUNCTION
#
# FastAPI can call:
#
#     result = detect_scoreboard_goals(
#         video_path,
#         output_dir
#     )
#
# ============================================================

def detect_scoreboard_goals(
    video_path,
    output_dir=DEFAULT_OUTPUT_DIR
):

    print(
        "=" * 70
    )

    print(
        "SCOREBOARD GOAL DETECTION"
    )

    print(
        "=" * 70
    )

    start_time = time.time()

    # ========================================================
    # INPUT VALIDATION
    # ========================================================

    print(
        "\nChecking files..."
    )

    if not video_path:

        raise ValueError(
            "video_path cannot be empty."
        )

    video_path = os.path.abspath(
        video_path
    )

    output_dir = os.path.abspath(
        output_dir
    )

    if not os.path.isfile(
        video_path
    ):

        raise FileNotFoundError(
            f"Video not found:\n"
            f"{video_path}"
        )

    if not os.path.isfile(
        YOLO_PATH
    ):

        raise FileNotFoundError(
            f"YOLO model not found:\n"
            f"{YOLO_PATH}"
        )

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    # ========================================================
    # SCOREBOARD OUTPUT DIRECTORY
    # ========================================================

    scoreboard_output_dir = os.path.join(

        output_dir,

        "scoreboard_goals"

    )

    os.makedirs(
        scoreboard_output_dir,
        exist_ok=True
    )

    goals_file = os.path.join(

        output_dir,

        "detected_goals.txt"

    )

    goal_events_file = os.path.join(

        scoreboard_output_dir,

        "goal_events.csv"

    )

    print(
        "Video : OK"
    )

    print(
        "YOLO  : OK"
    )

    print(
        "\nVideo:"
    )

    print(
        video_path
    )

    print(
        "\nOutput:"
    )

    print(
        output_dir
    )

    # ========================================================
    # LOAD MODELS
    # ========================================================

    (
        yolo,
        reader,
        device,
        cuda_available
    ) = load_models()

    # ========================================================
    # OPEN VIDEO
    # ========================================================

    print(
        "\nOpening video..."
    )

    cap = cv2.VideoCapture(
        video_path
    )

    if not cap.isOpened():

        raise RuntimeError(
            "Could not open video:\n"
            f"{video_path}"
        )

    # ========================================================
    # VIDEO INFORMATION
    # ========================================================

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

    if fps <= 0:

        cap.release()

        raise RuntimeError(
            "Could not determine video FPS."
        )

    duration = (
        total_frames
        /
        fps
    )

    print(
        "\nVIDEO"
    )

    print(
        "-" * 70
    )

    print(
        f"FPS        : {fps:.2f}"
    )

    print(
        f"Frames     : {total_frames:,}"
    )

    print(
        f"Duration   : {duration:.2f}s"
    )

    print(
        f"Duration   : {duration / 60:.2f} minutes"
    )

    print(
        f"Resolution : {width} x {height}"
    )

    # ========================================================
    # TEMPORAL VARIABLES
    # ========================================================

    current_score = None

    candidate_score = None

    candidate_count = 0

    candidate_first_time = None

    goals = []

    # ========================================================
    # SEQUENTIAL SCANNING
    #
    # IMPORTANT:
    #
    # We intentionally DO NOT use:
    #
    # cap.set(CAP_PROP_POS_FRAMES, ...)
    #
    # This avoids repeated H.264 seeking problems.
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "SCANNING VIDEO"
    )

    print(
        "Sequential frame reading enabled"
    )

    print(
        "=" * 70
    )

    sample_every_frames = max(
        1,
        int(
            fps
            *
            SAMPLE_INTERVAL
        )
    )

    frame_number = 0

    next_sample_frame = 0

    # ========================================================
    # MAIN VIDEO LOOP
    # ========================================================

    try:

        while True:

            ret, frame = cap.read()

            # ------------------------------------------------
            # END OF VIDEO
            # ------------------------------------------------

            if not ret:
                break

            # ------------------------------------------------
            # ONLY PROCESS SAMPLE FRAMES
            # ------------------------------------------------

            if (
                frame_number
                <
                next_sample_frame
            ):

                frame_number += 1

                continue

            current_time = (
                frame_number
                /
                fps
            )

            next_sample_frame = (
                frame_number
                +
                sample_every_frames
            )

            # ------------------------------------------------
            # PROCESS SCOREBOARD
            # ------------------------------------------------

            result = process_scoreboard_frame(

                frame,

                yolo,

                reader,

                device,

                width,

                height

            )

            scoreboard_found = (
                result[
                    "scoreboard_found"
                ]
            )

            score = (
                result[
                    "score"
                ]
            )

            confidence = (
                result[
                    "confidence"
                ]
            )

            # ------------------------------------------------
            # STATUS
            # ------------------------------------------------

            if (
                scoreboard_found
                or
                score is not None
            ):

                print(

                    f"{current_time:8.2f}s | "
                    f"YOLO="
                    f"{'YES' if scoreboard_found else 'NO'} | "
                    f"score="
                    f"{format_score(score)} | "
                    f"OCR="
                    f"{confidence:.2f}"

                )

            # ------------------------------------------------
            # NO SCORE
            # ------------------------------------------------

            if score is None:

                frame_number += 1

                continue

            # =================================================
            # INITIAL SCORE
            # =================================================

            if current_score is None:

                current_score = score

                print(

                    "\n"
                    "           INITIAL SCORE = "
                    f"{format_score(current_score)}"
                    "\n"

                )

                frame_number += 1

                continue

            # =================================================
            # SAME SCORE
            # =================================================

            if score == current_score:

                candidate_score = None

                candidate_count = 0

                candidate_first_time = None

                frame_number += 1

                continue

            # =================================================
            # NEW SCORE CANDIDATE
            # =================================================

            if candidate_score != score:

                candidate_score = score

                candidate_count = 1

                candidate_first_time = (
                    current_time
                )

                print(

                    "\n"
                    "           CANDIDATE: "
                    f"{format_score(current_score)}"
                    " -> "
                    f"{format_score(score)}"
                    " "
                    f"(1/"
                    f"{CONFIRMATIONS_REQUIRED}"
                    ")"

                )

            else:

                candidate_count += 1

                print(

                    "           CONFIRMATION: "
                    f"{format_score(current_score)}"
                    " -> "
                    f"{format_score(candidate_score)}"
                    " ("
                    f"{candidate_count}/"
                    f"{CONFIRMATIONS_REQUIRED}"
                    ")"

                )

            # =================================================
            # CONFIRM SCORE CHANGE
            # =================================================

            if (
                candidate_count
                >=
                CONFIRMATIONS_REQUIRED
            ):

                goal_time = (
                    candidate_first_time
                )

                print(
                    "\n"
                    +
                    "!" * 70
                )

                print(
                    "GOAL CONFIRMED"
                )

                print(

                    f"Score: "
                    f"{format_score(current_score)}"
                    " -> "
                    f"{format_score(candidate_score)}"

                )

                print(

                    f"Time : "
                    f"{goal_time:.2f}s"

                )

                print(
                    "!" * 70
                )

                goals.append({

                    "old_score":
                        current_score,

                    "new_score":
                        candidate_score,

                    "time":
                        goal_time

                })

                current_score = (
                    candidate_score
                )

                candidate_score = None

                candidate_count = 0

                candidate_first_time = None

            frame_number += 1

    finally:

        cap.release()

    # ========================================================
    # SAVE HUMAN-READABLE TXT
    # ========================================================

    with open(
        goals_file,
        "w",
        encoding="utf-8"
    ) as f:

        if not goals:

            f.write(
                "No goals detected.\n"
            )

        for i, goal in enumerate(
            goals,
            1
        ):

            old_score = (

                f"{goal['old_score'][0]}-"
                f"{goal['old_score'][1]}"

            )

            new_score = (

                f"{goal['new_score'][0]}-"
                f"{goal['new_score'][1]}"

            )

            f.write(

                f"Goal {i}: "
                f"{old_score} -> "
                f"{new_score} "
                f"@ "
                f"{goal['time']:.2f}s\n"

            )

    # ========================================================
    # SAVE MACHINE-READABLE CSV
    # ========================================================

    goal_rows = []

    for i, goal in enumerate(
        goals,
        1
    ):

        old_score = (

            f"{goal['old_score'][0]}-"
            f"{goal['old_score'][1]}"

        )

        new_score = (

            f"{goal['new_score'][0]}-"
            f"{goal['new_score'][1]}"

        )

        goal_rows.append({

            "goal_id":
                i,

            "old_score":
                old_score,

            "new_score":
                new_score,

            "time":
                goal["time"]

        })

    goal_df = pd.DataFrame(

        goal_rows,

        columns=[

            "goal_id",

            "old_score",

            "new_score",

            "time"

        ]

    )

    goal_df.to_csv(

        goal_events_file,

        index=False

    )

    # ========================================================
    # PROCESSING TIME
    # ========================================================

    processing_time = (

        time.time()
        -
        start_time

    )

    processing_fps = (

        total_frames
        /
        processing_time

        if processing_time > 0

        else 0

    )

    real_time_factor = (

        processing_time
        /
        duration

        if duration > 0

        else 0

    )

    # ========================================================
    # FINAL RESULTS
    # ========================================================

    print(
        "\nGoal events CSV saved to:"
    )

    print(
        goal_events_file
    )

    print(
        "\nDetected goals:"
    )

    if goals:

        for i, goal in enumerate(
            goals,
            1
        ):

            print(

                f"Goal {i}: "
                f"{format_score(goal['old_score'])}"
                " -> "
                f"{format_score(goal['new_score'])}"
                " @ "
                f"{goal['time']:.2f}s"

            )

    else:

        print(
            "No goals detected."
        )

    print(
        "\n" + "=" * 70
    )

    print(
        "SCOREBOARD DETECTION COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        f"Goals detected : {len(goals)}"
    )

    print(
        f"Processing time : {processing_time:.2f}s"
    )

    print(
        f"Processing FPS  : {processing_fps:.2f}"
    )

    print(
        f"Real-time factor: {real_time_factor:.2f}x"
    )

    print(
        "\nResults saved to:"
    )

    print(
        goals_file
    )

    print(
        goal_events_file
    )

    print(
        "=" * 70
    )

    # ========================================================
    # RETURN INFORMATION TO FASTAPI
    #
    # THIS IS THE IMPORTANT PART FOR STEP 3
    # ========================================================

    return {

        "video_path":
            video_path,

        "output_dir":
            output_dir,

        "goal_events_csv":
            goal_events_file,

        "detected_goals_file":
            goals_file,

        "goals":
            goals,

        "goal_count":
            len(goals),

        "frames_processed":
            total_frames,

        "duration":
            duration,

        "fps":
            fps,

        "processing_time":
            processing_time,

        "processing_fps":
            processing_fps,

        "real_time_factor":
            real_time_factor,

        "device":
            (
                "cuda"
                if cuda_available
                else "cpu"
            )

    }


# ============================================================
# DIRECT TERMINAL EXECUTION
#
# This section is ONLY for testing.
#
# It does NOT run when imported by FastAPI.
#
# Example:
#
#     python scoreboard_goal_detector.py "video.mp4"
#
# ============================================================

if __name__ == "__main__":

    print(
        "\nSCOREBOARD GOAL DETECTOR - TEST MODE"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # Require video path from command line
    # --------------------------------------------------------

    if len(sys.argv) < 2:

        print(
            "\nUsage:"
        )

        print(
            'python scoreboard_goal_detector.py "video.mp4"'
        )

        print(
            "\nExample:"
        )

        print(
            r'python scoreboard_goal_detector.py "C:\Football_Project\football_highlight_app\backend\uploads\test_video.mp4"'
        )

        raise SystemExit(1)

    # --------------------------------------------------------
    # sys.argv is ONLY used here
    # --------------------------------------------------------

    input_video = sys.argv[1]

    print(
        "\nInput video selected:"
    )

    print(
        input_video
    )

    # --------------------------------------------------------
    # Call reusable function
    # --------------------------------------------------------

    result = detect_scoreboard_goals(

        video_path=input_video,

        output_dir=DEFAULT_OUTPUT_DIR

    )

    # ========================================================
    # TEST RESULT
    # ========================================================

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
        "\nGoals detected:"
    )

    print(
        result["goal_count"]
    )

    print(
        "\nGoal events CSV:"
    )

    print(
        result["goal_events_csv"]
    )

    print(
        "\nDetected goals TXT:"
    )

    print(
        result["detected_goals_file"]
    )

    print(
        "\nProcessing time:"
    )

    print(
        f"{result['processing_time']:.2f}s"
    )

    print(
        "\nDevice:"
    )

    print(
        result["device"]
    )

    print(
        "=" * 70
    )