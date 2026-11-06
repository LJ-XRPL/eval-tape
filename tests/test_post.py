"""Dry-run posting accepts a 3-photo EVALS batch."""

from pathlib import Path

from src.post import post_with_media


def test_dry_run_posts_three_photos(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DRY_RUN", "true")
    paths = []
    for i in range(3):
        p = tmp_path / f"evals_{i}.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
        paths.append(p)
    result = post_with_media(
        caption="Independent evals just landed:\n1. Opus 5 — 63\nArtificial Analysis. Not vendor scorecards.",
        media_paths=paths,
        alt_texts=["a", "b", "c"],
        source_url="https://artificialanalysis.ai/",
    )
    assert result.dry_run is True
    assert result.tweet_id is None
    assert len(result.media_paths) == 3
    assert result.media_path == str(paths[0])


def test_batch_evals_photo_cap():
    from src.config import BATCH_EVALS_PHOTOS

    assert BATCH_EVALS_PHOTOS == 3
