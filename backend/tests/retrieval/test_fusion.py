import uuid

from app.retrieval.fusion import reciprocal_rank_fusion


def test_reciprocal_rank_fusion_prefers_items_in_both_lists() -> None:
    a = uuid.uuid4()
    b = uuid.uuid4()
    c = uuid.uuid4()

    fused = reciprocal_rank_fusion([[a, b], [a, c]], k=60)

    assert fused[0][0] == a
    assert fused[0][1] > fused[1][1]


def test_reciprocal_rank_fusion_single_list() -> None:
    a = uuid.uuid4()
    b = uuid.uuid4()

    fused = reciprocal_rank_fusion([[a, b]], k=60)

    assert [chunk_id for chunk_id, _ in fused] == [a, b]


def test_reciprocal_rank_fusion_tie_breaks_by_total_score() -> None:
    shared = uuid.uuid4()
    semantic_only = uuid.uuid4()
    fulltext_only = uuid.uuid4()

    fused = reciprocal_rank_fusion(
        [[shared, semantic_only], [shared, fulltext_only]],
        k=60,
    )

    scores = dict(fused)
    assert scores[shared] > scores[semantic_only]
    assert scores[shared] > scores[fulltext_only]
