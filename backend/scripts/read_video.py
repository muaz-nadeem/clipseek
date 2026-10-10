"""Read a video frame by frame with OpenCV and display it."""

import argparse
import sys

import cv2


def main() -> int:
    parser = argparse.ArgumentParser(description="Display a video frame by frame.")
    parser.add_argument("video", help="Path to the video file")
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Stop after this many frames (e.g. 1 to inspect a single frame)",
    )
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error: could not open video '{args.video}'", file=sys.stderr)
        return 1

    frame_number = 0
    window_name = "Video"

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        print(f"Frame: {frame_number}")

        cv2.imshow(window_name, frame)

        # Wait 1 ms for a key; quit on 'q'
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
