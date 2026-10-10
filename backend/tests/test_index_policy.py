from app.utils.index_policy import duration_exceeds_limit, index_stride_for_fps, iter_sampled_frame_indices


def test_sampling_covers_video_with_fewer_frames():
    stride = index_stride_for_fps(30, target_fps=5)
    frames = iter_sampled_frame_indices(718, stride)
    assert stride == 6
    assert len(frames) == 120
    assert frames[0] == 0 and frames[-1] == 714


def test_low_fps_and_explicit_full_frame_override():
    assert index_stride_for_fps(2, target_fps=5) == 1
    assert index_stride_for_fps(30, target_fps=5, override=1) == 1


def test_duration_limit_is_inclusive_and_ignores_unknown_length():
    assert not duration_exceeds_limit(600, 600)
    assert duration_exceeds_limit(600.5, 600)
    assert not duration_exceeds_limit(None, 600)
