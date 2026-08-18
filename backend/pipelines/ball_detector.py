# ======================================================================
# BALL DETECTOR
# ======================================================================
# Webapp pipeline equivalent of Stage 8A
#
# INPUT:
#   Any uploaded football video
#
# MODEL:
#   backend/models/ball_tracking/best.pt
#
# OUTPUT:
#   YOLO detection CSV
#
# The detector:
#   - Uses the trained football YOLO model
#   - Samples every 2nd frame
#   - Processes frames in batches
#   - Uses CUDA automatically when available
#   - Detects player, goalkeeper, referee and ball
# ======================================================================

import os
import time
import cv2
import torch
import pandas as pd

from ultralytics import YOLO


# ======================================================================
# PATHS
# ======================================================================

# backend/pipelines/ball_detector.py
#                 ↑
# parents[0] = pipelines
# parents[1] = backend
# parents[2] = football_highlight_app

BACKEND_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

MODEL_PATH = os.path.join(
    BACKEND_DIR,
    "models",
    "ball_tracking",
    "best.pt"
)


# ======================================================================
# SETTINGS
# ======================================================================

SAMPLING_FACTOR = 2

BATCH_SIZE = 32

IMAGE_SIZE = 640

CONFIDENCE = 0.25


# ======================================================================
# GET DEVICE
# ======================================================================

def get_device():

    if torch.cuda.is_available():

        device = "cuda:0"

        print(
            "GPU available :",
            torch.cuda.get_device_name(0)
        )

        print(
            "CUDA version  :",
            torch.version.cuda
        )

    else:

        device = "cpu"

        print(
            "WARNING: CUDA unavailable."
        )

    return device


# ======================================================================
# GET VIDEO INFORMATION
# ======================================================================

def get_video_info(video_path):

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

    duration = (
        total_frames / fps
    )

    return {

        "fps": fps,

        "total_frames": total_frames,

        "width": width,

        "height": height,

        "duration": duration
    }


# ======================================================================
# PROCESS ONE BATCH
# ======================================================================

def process_batch(
    model,
    frames,
    frame_numbers,
    fps,
    device,
    all_rows
):

    results = model.predict(

        frames,

        imgsz=IMAGE_SIZE,

        conf=CONFIDENCE,

        device=device,

        verbose=False

    )

    detection_count = 0

    for frame_no, result in zip(
        frame_numbers,
        results
    ):

        time_sec = (
            frame_no / fps
        )

        if result.boxes is None:
            continue

        boxes = result.boxes

        for i in range(
            len(boxes)
        ):

            cls_id = int(
                boxes.cls[i].item()
            )

            confidence = float(
                boxes.conf[i].item()
            )

            x1, y1, x2, y2 = (
                boxes.xyxy[i].tolist()
            )

            center_x = (
                x1 + x2
            ) / 2

            center_y = (
                y1 + y2
            ) / 2

            box_width = (
                x2 - x1
            )

            box_height = (
                y2 - y1
            )

            if cls_id in model.names:

                class_name = (
                    model.names[cls_id]
                )

            else:

                class_name = str(
                    cls_id
                )

            all_rows.append({

                "frame":
                    frame_no,

                "time_sec":
                    time_sec,

                "class_id":
                    cls_id,

                "class_name":
                    class_name,

                "confidence":
                    confidence,

                "x1":
                    x1,

                "y1":
                    y1,

                "x2":
                    x2,

                "y2":
                    y2,

                "center_x":
                    center_x,

                "center_y":
                    center_y,

                "width":
                    box_width,

                "height":
                    box_height
            })

            detection_count += 1

    return detection_count


# ======================================================================
# MAIN DETECTOR
# ======================================================================

def detect_objects(
    video_path,
    output_csv
):

    print("=" * 70)
    print("BALL / PLAYER YOLO DETECTION")
    print("=" * 70)


    # ==================================================================
    # INPUT CHECK
    # ==================================================================

    if not os.path.exists(
        video_path
    ):

        raise FileNotFoundError(
            f"Video not found:\n{video_path}"
        )


    if not os.path.exists(
        MODEL_PATH
    ):

        raise FileNotFoundError(
            f"Ball tracking model not found:\n{MODEL_PATH}"
        )


    os.makedirs(
        os.path.dirname(
            output_csv
        ),
        exist_ok=True
    )


    print("\nINPUT")
    print("-" * 70)

    print(
        "Video :",
        video_path
    )

    print(
        "Model :",
        MODEL_PATH
    )

    print(
        "Output:",
        output_csv
    )


    # ==================================================================
    # DEVICE
    # ==================================================================

    print("\nGPU")
    print("-" * 70)

    print(
        "PyTorch version:",
        torch.__version__
    )

    print(
        "CUDA available:",
        torch.cuda.is_available()
    )

    device = get_device()

    print(
        "Device:",
        device
    )


    # ==================================================================
    # VIDEO INFORMATION
    # ==================================================================

    print("\nVIDEO INFORMATION")
    print("-" * 70)

    video_info = get_video_info(
        video_path
    )

    fps = video_info["fps"]

    total_frames = (
        video_info["total_frames"]
    )

    duration = (
        video_info["duration"]
    )

    print(
        f"FPS        : {fps:.2f}"
    )

    print(
        f"Frames     : {total_frames:,}"
    )

    print(
        f"Resolution : "
        f"{video_info['width']} x "
        f"{video_info['height']}"
    )

    print(
        f"Duration   : "
        f"{duration:.2f}s"
    )

    print(
        f"Duration   : "
        f"{duration / 60:.2f} min"
    )


    expected_frames = (
        total_frames
        + SAMPLING_FACTOR
        - 1
    ) // SAMPLING_FACTOR

    print(
        f"\nSampling factor : "
        f"{SAMPLING_FACTOR}×"
    )

    print(
        f"Expected YOLO frames : "
        f"{expected_frames:,}"
    )

    print(
        f"Batch size : "
        f"{BATCH_SIZE}"
    )

    print(
        f"Image size : "
        f"{IMAGE_SIZE}"
    )

    print(
        f"Confidence : "
        f"{CONFIDENCE}"
    )


    # ==================================================================
    # LOAD MODEL
    # ==================================================================

    print("\nLOADING YOLO MODEL")
    print("-" * 70)

    model = YOLO(
        MODEL_PATH
    )

    print(
        "Model loaded successfully."
    )

    print(
        "Classes:",
        model.names
    )


    # ==================================================================
    # GPU WARMUP
    # ==================================================================

    if torch.cuda.is_available():

        print("\nWARMING UP GPU")
        print("-" * 70)

        dummy = torch.zeros(
            (
                1,
                3,
                IMAGE_SIZE,
                IMAGE_SIZE
            ),
            device="cuda"
        )

        torch.cuda.synchronize()

        del dummy

        torch.cuda.empty_cache()

        print(
            "GPU warm-up complete."
        )


    # ==================================================================
    # OPEN VIDEO
    # ==================================================================

    print("\n" + "=" * 70)
    print("STARTING YOLO EXTRACTION")
    print("=" * 70)

    cap = cv2.VideoCapture(
        video_path
    )

    if not cap.isOpened():

        raise RuntimeError(
            "Could not open input video."
        )


    # ==================================================================
    # PROCESS VIDEO
    # ==================================================================

    frames_batch = []

    frame_numbers = []

    all_rows = []

    frame_index = 0

    processed_frames = 0

    detection_count = 0

    start_time = time.time()

    last_report = time.time()


    while True:

        ret, frame = cap.read()

        if not ret:
            break


        # --------------------------------------------------------------
        # Temporal sampling
        # --------------------------------------------------------------

        if (
            frame_index
            % SAMPLING_FACTOR
            != 0
        ):

            frame_index += 1

            continue


        frames_batch.append(
            frame
        )

        frame_numbers.append(
            frame_index
        )


        # --------------------------------------------------------------
        # Process full batch
        # --------------------------------------------------------------

        if len(
            frames_batch
        ) >= BATCH_SIZE:

            batch_detections = process_batch(

                model,

                frames_batch,

                frame_numbers,

                fps,

                device,

                all_rows

            )

            detection_count += (
                batch_detections
            )

            processed_frames += (
                len(frames_batch)
            )


            frames_batch = []

            frame_numbers = []


            # ----------------------------------------------------------
            # Progress
            # ----------------------------------------------------------

            now = time.time()

            elapsed = (
                now - start_time
            )

            processing_fps = (

                processed_frames
                / elapsed

                if elapsed > 0
                else 0
            )

            video_time = (

                processed_frames
                * SAMPLING_FACTOR
                / fps
            )

            if (
                now - last_report
                >= 5
            ):

                percent = (

                    processed_frames
                    / expected_frames
                    * 100

                )

                print(

                    f"Processed "
                    f"{processed_frames:,}/"
                    f"{expected_frames:,}"
                    f" | "
                    f"{percent:5.1f}%"
                    f" | Video "
                    f"{video_time / 60:.2f} min"
                    f" | Processing "
                    f"{processing_fps:.2f} FPS"
                    f" | Detections "
                    f"{detection_count:,}"

                )

                last_report = now


        frame_index += 1


    # ==================================================================
    # PROCESS REMAINING BATCH
    # ==================================================================

    if len(
        frames_batch
    ) > 0:

        batch_detections = process_batch(

            model,

            frames_batch,

            frame_numbers,

            fps,

            device,

            all_rows

        )

        detection_count += (
            batch_detections
        )

        processed_frames += (
            len(frames_batch)
        )


    cap.release()


    # ==================================================================
    # TIMING
    # ==================================================================

    processing_time = (

        time.time()
        - start_time

    )

    processing_fps = (

        processed_frames
        / processing_time

        if processing_time > 0
        else 0

    )

    real_time_factor = (

        duration
        / processing_time

        if processing_time > 0
        else 0

    )


    # ==================================================================
    # CREATE DATAFRAME
    # ==================================================================

    print("\nCREATING DETECTION DATAFRAME")
    print("-" * 70)

    df = pd.DataFrame(
        all_rows
    )

    print(
        f"Detection rows : "
        f"{len(df):,}"
    )


    # ==================================================================
    # SAVE CSV
    # ==================================================================

    print("\nSAVING CSV")
    print("-" * 70)

    df.to_csv(
        output_csv,
        index=False
    )

    csv_size_mb = (

        os.path.getsize(
            output_csv
        )
        / (1024 * 1024)

    )


    # ==================================================================
    # SUMMARY
    # ==================================================================

    print("\n" + "=" * 70)
    print("YOLO DETECTION COMPLETE")
    print("=" * 70)

    print("\nPROCESSING")
    print("-" * 70)

    print(
        f"Frames processed : "
        f"{processed_frames:,}"
    )

    print(
        f"Detection rows   : "
        f"{len(df):,}"
    )

    print(
        f"Processing time  : "
        f"{processing_time:.2f} sec"
    )

    print(
        f"Processing time  : "
        f"{processing_time / 60:.2f} min"
    )

    print(
        f"Processing FPS   : "
        f"{processing_fps:.2f}"
    )

    print(
        f"Real-time factor : "
        f"{real_time_factor:.2f}x"
    )


    # ==================================================================
    # CLASS DISTRIBUTION
    # ==================================================================

    print("\nCLASS DISTRIBUTION")
    print("-" * 70)

    if len(df) > 0:

        print(
            df[
                "class_name"
            ].value_counts()
        )

    else:

        print(
            "No detections found."
        )


    print("\nOUTPUT")
    print("-" * 70)

    print(
        output_csv
    )

    print(
        f"CSV size : "
        f"{csv_size_mb:.2f} MB"
    )


    print("\n" + "=" * 70)
    print("BALL DETECTOR FINISHED")
    print("=" * 70)


    # ==================================================================
    # RETURN INFORMATION TO FASTAPI
    # ==================================================================

    return {

        "video_path":
            video_path,

        "output_csv":
            output_csv,

        "frames_processed":
            processed_frames,

        "detection_rows":
            len(df),

        "processing_time":
            processing_time,

        "processing_fps":
            processing_fps,

        "real_time_factor":
            real_time_factor,

        "duration":
            duration,

        "fps":
            fps
    }


# ======================================================================
# TEST EXECUTION
# ======================================================================

if __name__ == "__main__":

    print(
        "\nThis file is a reusable backend pipeline."
    )

    print(
        "It should normally be called by the FastAPI backend."
    )