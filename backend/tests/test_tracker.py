"""Detection tensors must leave GPU memory before entering ByteTrack."""
from unittest.mock import Mock

import numpy as np
import pytest

pytest.importorskip("ultralytics")
from app.ml.tracker import ObjectTracker


def test_tracker_converts_detection_boxes_before_tracking():
    wrapper = ObjectTracker.__new__(ObjectTracker)
    wrapper.tracker = Mock()
    boxes = Mock()
    cpu_boxes = boxes.cpu.return_value
    numpy_boxes = cpu_boxes.numpy.return_value
    frame = np.zeros((16, 16, 3), dtype=np.uint8)

    result = wrapper.update(boxes, frame)

    boxes.cpu.assert_called_once_with()
    cpu_boxes.numpy.assert_called_once_with()
    wrapper.tracker.update.assert_called_once_with(numpy_boxes, img=frame)
    assert result is wrapper.tracker.update.return_value
