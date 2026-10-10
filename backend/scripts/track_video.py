"""Read a video frame by frame, run YOLO + ByteTrack, print track info."""

import argparse
import sys

import cv2
from ultralytics import YOLO


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track objects in a video with YOLO + ByteTrack."
    )
    parser.add_argument("video", help="Path to the video file")
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="Ultralytics YOLO model weights (default: yolov8n.pt)",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Confidence threshold (default: 0.25)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Stop after this many frames",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display annotated frames in a window",
    )
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error: could not open video '{args.video}'", file=sys.stderr)
        return 1

    model = YOLO(args.model)
    frame_number = 0
    window_name = "YOLO + ByteTrack"

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=args.conf,
            verbose=False,
        )[0]

        print(f"--- Frame {frame_number} ---")
        boxes = results.boxes

        if boxes is None or len(boxes) == 0:
            print("No objects tracked.\n")
        else:
            names = results.names
            for box in boxes:
                if box.id is None:
                    continue

                track_id = int(box.id[0].item())
                class_id = int(box.cls[0].item())
                class_name = names[class_id]
                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                print(f"Track ID: {track_id}")
                print(f"Class: {class_name}")
                print(f"Confidence: {confidence:.4f}")
                print(
                    f"Bounding box (x1, y1, x2, y2): "
                    f"({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f})"
                )
                print()

        if args.show:
            annotated = results.plot()
            cv2.imshow(window_name, annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        frame_number += 1
        if args.max_frames is not None and frame_number >= args.max_frames:
            break

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
