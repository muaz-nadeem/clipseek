"""Run YOLO inference on a single frame extracted from a video."""

import argparse
import sys

import cv2
from ultralytics import YOLO


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract one video frame and run YOLO detection on it."
    )
    parser.add_argument("video", help="Path to the video file")
    parser.add_argument(
        "--frame-index",
        type=int,
        default=0,
        help="0-based frame index to extract (default: 0)",
    )
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
        "--show",
        action="store_true",
        help="Display the annotated frame in a window",
    )
    args = parser.parse_args()

    if args.frame_index < 0:
        print("Error: --frame-index must be >= 0", file=sys.stderr)
        return 1

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error: could not open video '{args.video}'", file=sys.stderr)
        return 1

    cap.set(cv2.CAP_PROP_POS_FRAMES, args.frame_index)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print(
            f"Error: could not read frame {args.frame_index} from '{args.video}'",
            file=sys.stderr,
        )
        return 1

    print(f"Extracted frame {args.frame_index}, shape: {frame.shape}")

    model = YOLO(args.model)
    results = model(frame, conf=args.conf, verbose=False)[0]

    names = results.names
    boxes = results.boxes

    if boxes is None or len(boxes) == 0:
        print("No objects detected.")
        return 0

    print(f"Detected {len(boxes)} object(s):\n")
    for i, box in enumerate(boxes):
        class_id = int(box.cls[0].item())
        class_name = names[class_id]
        confidence = float(box.conf[0].item())
        x1, y1, x2, y2 = box.xyxy[0].tolist()

        print(f"[{i}] Class: {class_name}")
        print(f"    Confidence: {confidence:.4f}")
        print(f"    Bounding box (x1, y1, x2, y2): ({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f})")
        print()

    if args.show:
        annotated = results.plot()
        cv2.imshow("YOLO Detection", annotated)
        print("Press any key in the window to close...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
