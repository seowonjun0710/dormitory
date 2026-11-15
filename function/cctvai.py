import cv2
import time
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO
import sqlite3
import subprocess
import os


PERSON_CONF = 0.5
CAPTURE_INTERVAL = 2.0
MISSING_TIMEOUT = 1.5

BASE_DIR = Path(__file__).resolve().parent.parent
SAVE_DIR = BASE_DIR / "captures"
SAVE_DIR.mkdir(exist_ok=True)

CAMERA = 0
MODEL_PATH = "yolov8n.pt"
DB_PATH = BASE_DIR / "database.db"

model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(CAMERA)

if not cap.isOpened():
    raise RuntimeError("카메라를 열 수 없습니다.")


recording = False
writer = None

start_time = None
last_seen_time = None
last_seen_clock = None
last_capture_time = None
video_path = None
saved_frames = 0



def register_cctv_event(event):
    with sqlite3.connect(DB_PATH, timeout=10) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS cctv_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                expires_at REAL NOT NULL
            )
        """)

        db.execute("""
            INSERT INTO cctv_events
            (filename, event_type, start_time,
             end_time, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event["filename"],
            event["event_type"],
            event["start_time"],
            event["end_time"],
            event["expires_at"]
        ))

        db.commit()



def start_recording(frame):
    global recording, writer, start_time
    global video_path, last_capture_time, saved_frames

    start_time = datetime.now()
    last_capture_time = None
    saved_frames = 0

    filename = start_time.strftime(
        "person_%Y%m%d_%H%M%S_%f.mp4"
    )

    video_path = SAVE_DIR / filename

    height, width = frame.shape[:2]

    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        2.0,
        (width, height + 50)
    )

    if not writer.isOpened():
        writer = None
        raise RuntimeError("영상 파일을 열 수 없습니다.")

    recording = True
    print("\n사람 등장:", start_time)



def capture_frame(frame, now):
    global last_capture_time, saved_frames

    if not recording:
        return

    if last_capture_time is not None:
        if now - last_capture_time < CAPTURE_INTERVAL:
            return

    last_capture_time = now

    image = cv2.copyMakeBorder(
        frame, 0, 50, 0, 0,
        cv2.BORDER_CONSTANT,
        value=(25, 25, 25)
    )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    cv2.putText(
        image,
        timestamp,
        (15, image.shape[0] - 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    
    for _ in range(4):
        writer.write(image)

    saved_frames += 1



def convert_to_h264(original_path):
    original_path = Path(original_path)

    
    converted_path = original_path.with_name(
        original_path.stem + "_converted.mp4"
    )

    command = [
        "ffmpeg",
        "-y",
        "-i", str(original_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        str(converted_path)
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        if not converted_path.is_file():
            raise RuntimeError("변환된 영상 파일이 없습니다.")

        if converted_path.stat().st_size == 0:
            raise RuntimeError("변환된 영상 파일이 비어 있습니다.")

        
        os.replace(converted_path, original_path)

        print("H.264 영상 변환 완료:", original_path.name)
        return True

    except (subprocess.CalledProcessError, OSError, RuntimeError) as error:
        print("H.264 영상 변환 실패:", error)

        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr)

        converted_path.unlink(missing_ok=True)
        return False




def stop_recording():
    global recording, writer, start_time
    global last_capture_time, video_path
    global last_seen_time, last_seen_clock

    if not recording:
        return

    end_time = last_seen_clock or datetime.now()

    writer.release()
    writer = None
    recording = False
    
    conversion_success = convert_to_h264(video_path)

    duration = (end_time - start_time).total_seconds()

    print("\n==============================")
    print("감지 대상: 사람")
    print("시작 시간:", start_time)
    print("종료 시간:", end_time)
    print(f"지속 시간: {duration:.1f}초")
    print("촬영한 사진:", saved_frames, "장")
    print("영상 경로:", video_path)
    print("================================\n")

    event = {
    "event_type": "person",
    "start_time": start_time.isoformat(),
    "end_time": end_time.isoformat(),
    "filename": video_path.name,
    "expires_at": end_time.timestamp() + 72 * 60 * 60
}

    if conversion_success:
        register_cctv_event(event)
    else:
        print("변환에 실패하여 DB에 등록하지 않았습니다.")
        print("원본 영상은 captures 폴더에 남아 있습니다.")

    start_time = None
    last_capture_time = None
    last_seen_time = None
    last_seen_clock = None
    video_path = None

    return event



try:
    while True:
        success, frame = cap.read()

        if not success:
            print("카메라 영상을 읽지 못했습니다.")
            break

        now = time.monotonic()

        result = model.predict(
            frame,
            classes=[0],
            conf=PERSON_CONF,
            verbose=False,
            device="cpu"
        )[0]

        person_detected = (
            result.boxes is not None
            and len(result.boxes) > 0
        )

        if person_detected:
            last_seen_time = now
            last_seen_clock = datetime.now()

            if not recording:
                start_recording(frame)

            capture_frame(frame, now)

        
        elif recording:
            if now - last_seen_time >= MISSING_TIMEOUT:
                stop_recording()

        
        display = result.plot()

        if person_detected:
            status = "PERSON DETECTED"
            color = (0, 255, 0)
        elif recording:
            status = "CHECKING ABSENCE"
            color = (0, 255, 255)
        else:
            status = "NO PERSON"
            color = (0, 0, 255)

        cv2.putText(
            display,
            status,
            (20, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2
        )

        cv2.imshow("Dormitory CCTV AI", display)

        if cv2.waitKey(1) & 0xFF == 27:
            break

finally:
    stop_recording()
    cap.release()
    cv2.destroyAllWindows()
