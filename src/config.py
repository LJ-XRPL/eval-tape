"""Allowlists, palettes, feeds, and skip rules for Eval Tape."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "out"
STATE_PATH = ROOT / "state.json"
AA_CACHE_MAX_AGE_SECONDS = 6 * 60 * 60  # cache AA heavily (1000 req/day)
MAX_POSTS_PER_DAY = 3
# When several evals land together: one tweet, up to 3 jumbotron photos (X's grid).
BATCH_EVALS_PHOTOS = 3
CARD_WIDTH = 1600
CARD_HEIGHT = 900  # 16:9 — X's native single-image timeline slot

AA_API_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"
HF_API_URL = "https://huggingface.co/api/models"


@dataclass(frozen=True)
class Lab:
    key: str
    display: str
    kind: str  # "closed" | "open"
    aliases: tuple[str, ...]
    hf_orgs: tuple[str, ...] = ()
    rss_urls: tuple[str, ...] = ()


# Closed frontier labs + open-weight BASE MODEL families only.
LABS: tuple[Lab, ...] = (
    Lab(
        key="openai",
        display="OpenAI",
        kind="closed",
        aliases=("openai",),
        rss_urls=("https://openai.com/blog/rss.xml", "https://openai.com/news/rss.xml"),
    ),
    Lab(
        key="anthropic",
        display="Anthropic",
        kind="closed",
        aliases=("anthropic", "claude"),
        rss_urls=("https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml",),
    ),
    Lab(
        key="google",
        display="Google",
        kind="closed",
        aliases=("google", "deepmind", "gemini"),
        hf_orgs=("google", "google-deepmind"),
        rss_urls=(
            "https://blog.google/technology/ai/rss/",
            "https://deepmind.google/blog/rss.xml",
        ),
    ),
    Lab(
        key="xai",
        display="xAI",
        kind="closed",
        aliases=("xai", "grok"),
        rss_urls=("https://x.ai/blog/rss.xml",),
    ),
    Lab(
        key="amazon",
        display="Amazon",
        kind="closed",
        aliases=("amazon", "aws", "nova"),
        rss_urls=("https://aws.amazon.com/blogs/machine-learning/feed/",),
    ),
    Lab(
        key="microsoft",
        display="Microsoft",
        kind="closed",
        aliases=("microsoft", "azure", "phi"),
        hf_orgs=("microsoft",),
        rss_urls=("https://techcommunity.microsoft.com/t5/ai-azure-ai-services-blog/bg-p/AzureAIBlogs/rss",),
    ),
    Lab(
        key="meta",
        display="Meta",
        kind="open",
        aliases=("meta", "llama", "meta-llama"),
        hf_orgs=("meta-llama",),
        rss_urls=("https://about.fb.com/news/feed/",),
    ),
    Lab(
        key="deepseek",
        display="DeepSeek",
        kind="open",
        aliases=("deepseek",),
        hf_orgs=("deepseek-ai",),
    ),
    Lab(
        key="mistral",
        display="Mistral",
        kind="open",
        aliases=("mistral", "mistralai"),
        hf_orgs=("mistralai",),
        rss_urls=("https://mistral.ai/news/rss.xml", "https://mistral.ai/feed.xml"),
    ),
    Lab(
        key="qwen",
        display="Qwen",
        kind="open",
        aliases=("qwen", "alibaba", "tongyi"),
        hf_orgs=("Qwen",),
    ),
    Lab(
        key="kimi",
        display="Kimi",
        kind="open",
        aliases=("kimi", "moonshot"),
        hf_orgs=("moonshotai",),
    ),
    Lab(
        key="minimax",
        display="MiniMax",
        kind="open",
        aliases=("minimax",),
        hf_orgs=("MiniMaxAI",),
    ),
    Lab(
        key="gemma",
        display="Gemma",
        kind="open",
        aliases=("gemma",),
        hf_orgs=("google",),  # gemma lives under google; filtered by name
    ),
    Lab(
        key="glm",
        display="GLM",
        kind="open",
        aliases=("glm", "zhipu", "thudm", "chatglm"),
        hf_orgs=("THUDM", "ZhipuAI"),
    ),
    Lab(
        key="cohere",
        display="Cohere",
        kind="open",
        aliases=("cohere", "command"),
        hf_orgs=("CohereForAI", "Cohere"),
        rss_urls=("https://cohere.com/blog/rss.xml",),
    ),
)

LAB_BY_KEY = {lab.key: lab for lab in LABS}

# Lab color is the only theme change. Hexes from official brand systems / live sites.
# Unknown → white on black.
PALETTES: dict[str, dict[str, str]] = {
    # Anthropic: clay #D97757, ink #141413, canvas #FAF9F5 (brand-guidelines)
    "anthropic": {"bg": "#D97757", "fg": "#141413", "accent": "#D97757", "pill_bg": "#141413", "pill_fg": "#FAF9F5"},
    # OpenAI: near-black + ChatGPT green #10A37F
    "openai": {"bg": "#0F0F0F", "fg": "#10A37F", "accent": "#10A37F", "pill_bg": "#10A37F", "pill_fg": "#0F0F0F"},
    # Google Blue
    "google": {"bg": "#4285F4", "fg": "#FFFFFF", "accent": "#4285F4", "pill_bg": "#FFFFFF", "pill_fg": "#1A73E8"},
    # xAI: black / white
    "xai": {"bg": "#000000", "fg": "#FFFFFF", "accent": "#FFFFFF", "pill_bg": "#FFFFFF", "pill_fg": "#000000"},
    # Amazon orange + squid ink
    "amazon": {"bg": "#232F3E", "fg": "#FF9900", "accent": "#FF9900", "pill_bg": "#FF9900", "pill_fg": "#232F3E"},
    # Microsoft logo blue
    "microsoft": {"bg": "#00A4EF", "fg": "#FFFFFF", "accent": "#00A4EF", "pill_bg": "#FFFFFF", "pill_fg": "#000000"},
    # Meta Blue (ai.meta.com)
    "meta": {"bg": "#0082FB", "fg": "#FFFFFF", "accent": "#0082FB", "pill_bg": "#FFFFFF", "pill_fg": "#0064E0"},
    # DeepSeek Blue (deepseek.com)
    "deepseek": {"bg": "#4D6BFE", "fg": "#FFFFFF", "accent": "#4D6BFE", "pill_bg": "#FFFFFF", "pill_fg": "#4D6BFE"},
    # Mistral Orange (mistral.ai)
    "mistral": {"bg": "#FA520F", "fg": "#1F1F1F", "accent": "#FA520F", "pill_bg": "#1F1F1F", "pill_fg": "#FFFFFF"},
    # Qwen indigo (qwenlm.github.io)
    "qwen": {"bg": "#615CED", "fg": "#FFFFFF", "accent": "#615CED", "pill_bg": "#FFFFFF", "pill_fg": "#4F2DDA"},
    # Kimi logo fill (platform.moonshot.ai)
    "kimi": {"bg": "#0A7AFF", "fg": "#FFFFFF", "accent": "#0A7AFF", "pill_bg": "#FFFFFF", "pill_fg": "#0A7AFF"},
    # MiniMax brand coral
    "minimax": {"bg": "#FF5530", "fg": "#0A0A0A", "accent": "#FF5530", "pill_bg": "#0A0A0A", "pill_fg": "#FFFFFF"},
    # Gemma gem-green (Google AI for Developers Gemma surfaces) — not Google Blue
    "gemma": {"bg": "#15B789", "fg": "#0A0A0A", "accent": "#15B789", "pill_bg": "#0A0A0A", "pill_fg": "#FFFFFF"},
    # GLM / Z.ai product chrome
    "glm": {"bg": "#141618", "fg": "#F4F6F8", "accent": "#F4F6F8", "pill_bg": "#F4F6F8", "pill_fg": "#141618"},
    # Cohere: navy #152455, cream #F0EEE9, coral #DA532C (cohere.com)
    "cohere": {"bg": "#152455", "fg": "#F0EEE9", "accent": "#DA532C", "pill_bg": "#DA532C", "pill_fg": "#FFFFFF"},
    "unknown": {"bg": "#000000", "fg": "#FFFFFF", "accent": "#FFFFFF", "pill_bg": "#FFFFFF", "pill_fg": "#000000"},
}

# Skip fine-tunes, merges, GGUF re-uploads, quant dumps, media models, app bumps.
SKIP_NAME_PATTERNS: tuple[str, ...] = (
    r"\bgguf\b",
    r"\bawq\b",
    r"\bgptq\b",
    r"\bexl2\b",
    r"\bexllama\b",
    r"\bqn?f?\d",  # q4, q5, q8, q4_k_m style
    r"\bint[48]\b",
    r"\bfp8\b",
    r"\bnf4\b",
    r"\blora\b",
    r"\bqlora\b",
    r"\bfine[-\s]?tun",
    r"\bfinetun",
    r"\binstruct[-\s]?tun",
    r"\bmerge(d|kit)?\b",
    r"\bsli?erp\b",
    r"\bdpo\b",
    r"\brlhf\b",
    r"\bchat[-\s]?vector\b",
    r"\buncensored\b",
    r"\babliterat",
    r"\bimage\b",
    r"\bvision\b",
    r"\bvlm\b",
    r"\bvideo\b",
    r"\btts\b",
    r"\bstt\b",
    r"\bwhisper\b",
    r"\bdall[-\s]?e\b",
    r"\bflux\b",
    r"\bsora\b",
    r"\bveo\b",
    r"\bimagen\b",
    r"\bstable[-\s]?diffusion\b",
    r"\bcli\b",
    r"\bsdk\b",
    r"\bnow in the (app|ui|chat)\b",
    r"\bplayground\b",
    r"\bapi only\b",
)

# Extra HF tags / pipeline tags that mean skip.
SKIP_HF_TAGS: frozenset[str] = frozenset(
    {
        "text-to-image",
        "image-to-image",
        "image-to-video",
        "text-to-video",
        "text-to-speech",
        "automatic-speech-recognition",
        "image-text-to-text",  # multimodal vision — skip in v1
        "gguf",
    }
)

# Keywords that suggest a real base / frontier language model drop in RSS titles.
SHIP_HINTS: tuple[str, ...] = (
    "announcing",
    "introducing",
    "releasing",
    "release",
    "launches",
    "launch",
    "ships",
    "shipped",
    "available",
    "open[- ]weight",
    "open[- ]source",
    "model",
    "gpt-",
    "claude",
    "gemini",
    "llama",
    "deepseek",
    "mistral",
    "qwen",
    "kimi",
    "glm",
    "gemma",
    "command",
    "nova",
    "phi-",
    "grok",
)
