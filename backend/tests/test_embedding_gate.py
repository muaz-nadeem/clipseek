from app.ml.embedding_gate import TrackEmbeddingGate, cosine_similarity


def test_cosine_identical_is_one():
    vec = [1.0, 0.0, 0.0]
    assert cosine_similarity(vec, vec) == 1.0


def test_gate_stores_first_then_skips_similar():
    gate = TrackEmbeddingGate(threshold=0.95, max_gap_sec=15)
    first = gate.accept(1, [1.0, 0.0], 0.0)
    assert first.store and first.reason == "first"
    skip = gate.accept(1, [0.999, 0.001], 1.0)
    assert not skip.store and skip.reason == "skip"


def test_gate_stores_on_change_and_heartbeat():
    gate = TrackEmbeddingGate(threshold=0.95, max_gap_sec=15)
    gate.accept(7, [1.0, 0.0], 0.0)
    changed = gate.accept(7, [0.0, 1.0], 1.0)
    assert changed.store and changed.reason == "changed"
    heartbeat = gate.accept(7, [0.0, 1.0], 20.0)
    assert heartbeat.store and heartbeat.reason == "heartbeat"
