from app.services.search_cluster import (
    cluster_appearances, filter_relevant_matches, infer_class_names, search_class_names,
)


def test_relevance_rejects_weaker_scene_timeframes():
    rows = [
        {"class_name": "train", "timestamp": 21, "score": 0.292},
        {"class_name": "scene", "timestamp": 0, "score": 0.242},
        {"class_name": "scene", "timestamp": 18, "score": 0.231},
    ]
    assert filter_relevant_matches(rows, min_score=0.23, score_margin=0.04) == rows[:1]


def test_relevance_keeps_multiple_strong_appearances_including_scenes():
    rows = [
        {"video_id": 1, "track_id": 9, "timestamp": 10, "score": 0.30},
        {"video_id": 1, "track_id": 9, "timestamp": 40, "score": 0.29},
        {"video_id": 2, "track_id": -1, "timestamp": 60, "score": 0.28},
    ]
    relevant = filter_relevant_matches(rows, min_score=0.23, score_margin=0.04)
    assert cluster_appearances(relevant, top_k=8, appearance_gap_sec=10) == rows


def test_relevance_can_return_no_results_and_respects_stricter_floor():
    assert filter_relevant_matches([], min_score=0.23, score_margin=0.04) == []
    rows = [{"score": 0.22}, {"score": 0.19}, {"score": float("nan")}]
    assert filter_relevant_matches(rows, min_score=0.23, score_margin=0.04) == []
    assert filter_relevant_matches([{"score": 0.30}], min_score=0.35, score_margin=0.04) == []


def test_person_query_infers_person_class():
    assert infer_class_names("man wearing red cap", None) == ["person"]
    assert infer_class_names("red car", None) == ["car"]
    assert infer_class_names("man", ["car"]) == ["car"]


def test_object_queries_filter_classes():
    assert infer_class_names("show where the train appears", None) == ["train"]
    assert infer_class_names("TRAINS, trucks and buses!", None) == ["train", "truck", "bus"]
    assert infer_class_names("hot dogs beside a teddy bear", None) == ["hot dog", "teddy bear"]
    assert infer_class_names("a bike", None) == ["bicycle"]
    assert infer_class_names("training in the rain", None) is None
    assert infer_class_names("a red moving object", None) is None


def test_inferred_filters_also_search_whole_frames():
    assert search_class_names("man wearing red cap", None) == ["person", "scene"]
    assert search_class_names("red car", ["car"]) == ["car"]
    assert search_class_names("a red moving object", None) is None


def test_cluster_keeps_separate_appearances():
    rows = [
        {"video_id": 1, "track_id": 9, "timestamp": 10.0, "score": 0.9},
        {"video_id": 1, "track_id": 9, "timestamp": 11.0, "score": 0.8},
        {"video_id": 1, "track_id": 9, "timestamp": 40.0, "score": 0.7},
    ]
    kept = cluster_appearances(rows, top_k=5, appearance_gap_sec=10)
    assert len(kept) == 2
    assert [r["timestamp"] for r in kept] == [10.0, 40.0]


def test_cluster_offset_window_via_top_k():
    rows = [
        {"video_id": 1, "track_id": i, "timestamp": float(i), "score": 1.0 - i * 0.01}
        for i in range(5)
    ]
    first = cluster_appearances(rows, top_k=2, appearance_gap_sec=0.1)
    assert [r["track_id"] for r in first] == [0, 1]
