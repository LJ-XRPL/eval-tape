"""Unit tests for Artificial Analysis matching."""

from src.evals import AAModel, match_shipped_to_aa, names_match, parse_aa_payload


def _aa(name: str, score: float, rank: int, creator: str = "OpenAI") -> AAModel:
    return AAModel(
        id=f"id-{name}",
        name=name,
        slug=name.lower().replace(" ", "-"),
        creator_name=creator,
        score=score,
        rank=rank,
    )


def test_names_match_strips_effort_suffix():
    assert names_match("Claude Opus 5", "Claude Opus 5 (max)")
    assert names_match("GPT-5.6 Sol", "GPT-5.6 Sol")


def test_names_match_rejects_unrelated():
    assert not names_match("Claude Opus 5", "GPT-5.6 Sol")
    assert not names_match("Llama 4", "Llama 3.1 8B")


def test_match_shipped_to_aa_picks_best():
    catalog = [
        _aa("Claude Opus 5 (max)", 63, 1, "Anthropic"),
        _aa("Claude Opus 5", 62, 2, "Anthropic"),
        _aa("GPT-5.6 Sol", 61, 5, "OpenAI"),
    ]
    hit = match_shipped_to_aa("Claude Opus 5", catalog)
    assert hit is not None
    assert "Claude Opus 5" in hit.name


def test_parse_aa_payload_ranks_by_intelligence_index():
    payload = {
        "data": [
            {
                "id": "a",
                "name": "Model A",
                "slug": "a",
                "model_creator": {"name": "OpenAI"},
                "evaluations": {"artificial_analysis_intelligence_index": 50},
            },
            {
                "id": "b",
                "name": "Model B",
                "slug": "b",
                "model_creator": {"name": "Anthropic"},
                "evaluations": {"artificial_analysis_intelligence_index": 70},
            },
            {
                "id": "c",
                "name": "No Score",
                "slug": "c",
                "model_creator": {"name": "xAI"},
                "evaluations": {},
            },
        ]
    }
    models = parse_aa_payload(payload)
    assert [m.name for m in models] == ["Model B", "Model A"]
    assert models[0].rank == 1
    assert models[1].rank == 2


def test_match_requires_prior_ship_semantics():
    """EVALS only fires for names we can match — not random AA models."""
    catalog = [_aa("Random Lab X", 99, 1, "Someone")]
    assert match_shipped_to_aa("Claude Opus 5", catalog) is None
