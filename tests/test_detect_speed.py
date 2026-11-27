"""Speed-path invariants: live feeds, parallel collect, AA skip."""

from src.config import LAB_BY_KEY
from src.detect import FETCH_TIMEOUT_SECONDS, FETCH_WORKERS, collect_candidates
from src.evals import models_awaiting_evals


def test_dead_feeds_replaced():
    assert LAB_BY_KEY["microsoft"].rss_urls == (
        "https://techcommunity.microsoft.com/t5/ai-azure-ai-services-blog/bg-p/AzureAIBlogs/rss",
    )
    assert LAB_BY_KEY["meta"].rss_urls == ("https://about.fb.com/news/feed/",)


def test_fetch_budget_is_short_and_parallel():
    assert FETCH_TIMEOUT_SECONDS <= 8
    assert FETCH_WORKERS >= 8
    assert callable(collect_candidates)


def test_aa_skip_when_nothing_waiting():
    assert models_awaiting_evals({"posted_models": {}}) == []
    assert models_awaiting_evals(
        {
            "posted_models": {
                "rss:openai:gpt-5": {
                    "name": "GPT-5",
                    "evals_tweet_id": "1",
                    "aa_score": 60,
                }
            }
        }
    ) == []
    waiting = models_awaiting_evals(
        {"posted_models": {"rss:openai:gpt-5": {"name": "GPT-5"}}}
    )
    assert len(waiting) == 1
