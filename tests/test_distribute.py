"""Distribution helpers stay dry-run safe and on-voice."""

from src.distribute import (
    FOUNDER_QUOTE_CAP,
    LAUNCH_TWEET_ID,
    WEBSITE_URL,
    amplify_post,
    bootstrap_distribution,
    format_founder_quote,
)


def test_founder_quotes_have_no_urls_or_hashtags():
    for kind, name in (("launch", None), ("shipped", "Claude Opus 5"), ("evals", "GPT-5.6 Sol")):
        text = format_founder_quote(kind, name)
        assert "http://" not in text
        assert "https://" not in text
        assert "#" not in text
        assert "@evaltape" in text


def test_bootstrap_dry_run_does_not_need_tokens(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.delenv("FOUNDER_X_ACCESS_TOKEN", raising=False)
    state: dict = {}
    dist = bootstrap_distribution(state, dry_run=True)
    assert dist["profile_set"] is True
    assert dist["launch_pinned"] is True
    assert dist["pinned_tweet_id"] == LAUNCH_TWEET_ID
    assert dist["launch_quoted_id"] is None
    assert WEBSITE_URL.startswith("https://github.com/")


def test_amplify_respects_founder_cap(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "true")
    state = {"distribution": {"founder_quotes": FOUNDER_QUOTE_CAP, "pinned_tweet_id": None}}
    amplify_post(state, tweet_id="1", kind="shipped", model_name="Opus 5", dry_run=True)
    assert state["distribution"]["pinned_tweet_id"] == "1"
    assert state["distribution"]["founder_quotes"] == FOUNDER_QUOTE_CAP
