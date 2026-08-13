"""Allowlists, palettes, feeds, and skip rules for Eval Tape."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "out"
STATE_PATH = ROOT / "state.json"
AA_CACHE_MAX_AGE_SECONDS = 6 * 60 * 60  # cache AA heavily (1000 req/day)
MAX_POSTS_PER_DAY = 3
CARD_WIDTH = 1600
CARD_HEIGHT = 900  # 16:9

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
        rss_urls=("https://blogs.microsoft.com/ai/feed/",),
    ),
    Lab(
        key="meta",
        display="Meta",
        kind="open",
        aliases=("meta", "llama", "meta-llama"),
        hf_orgs=("meta-llama",),
        rss_urls=("https://ai.meta.com/blog/rss/",),
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

# Lab color is the only theme change. Unknown → white on black.
PALETTES: dict[str, dict[str, str]] = {
    "anthropic": {"bg": "#C15F3C", "fg": "#0A0A0A", "accent": "#0A0A0A", "pill_bg": "#0A0A0A", "pill_fg": "#F5F0EB"},
    "openai": {"bg": "#0A0A0A", "fg": "#10A37F", "accent": "#10A37F", "pill_bg": "#10A37F", "pill_fg": "#0A0A0A"},
    "google": {"bg": "#1A73E8", "fg": "#FFFFFF", "accent": "#FFFFFF", "pill_bg": "#0B1F3A", "pill_fg": "#FFFFFF"},
    "xai": {"bg": "#000000", "fg": "#FFFFFF", "accent": "#FFFFFF", "pill_bg": "#FFFFFF", "pill_fg": "#000000"},
    "amazon": {"bg": "#232F3E", "fg": "#FF9900", "accent": "#FF9900", "pill_bg": "#FF9900", "pill_fg": "#232F3E"},
    "microsoft": {"bg": "#0078D4", "fg": "#FFFFFF", "accent": "#FFFFFF", "pill_bg": "#0A0A0A", "pill_fg": "#FFFFFF"},
    "meta": {"bg": "#0668E1", "fg": "#FFFFFF", "accent": "#FFFFFF", "pill_bg": "#0A2540", "pill_fg": "#FFFFFF"},
    "deepseek": {"bg": "#0B1F3A", "fg": "#00D4FF", "accent": "#00D4FF", "pill_bg": "#00D4FF", "pill_fg": "#0B1F3A"},
    "mistral": {"bg": "#F7A019", "fg": "#1A0F00", "accent": "#1A0F00", "pill_bg": "#1A0F00", "pill_fg": "#F7A019"},
    "qwen": {"bg": "#5B2C8A", "fg": "#F3E8FF", "accent": "#E9D5FF", "pill_bg": "#2E1065", "pill_fg": "#F3E8FF"},
    "kimi": {"bg": "#0D7377", "fg": "#E6FFFA", "accent": "#99F6E4", "pill_bg": "#134E4A", "pill_fg": "#E6FFFA"},
    "minimax": {"bg": "#111827", "fg": "#F97316", "accent": "#F97316", "pill_bg": "#F97316", "pill_fg": "#111827"},
    "gemma": {"bg": "#1A73E8", "fg": "#FFFFFF", "accent": "#FFFFFF", "pill_bg": "#0B1F3A", "pill_fg": "#FFFFFF"},
    "glm": {"bg": "#1E3A5F", "fg": "#F8FAFC", "accent": "#93C5FD", "pill_bg": "#0F172A", "pill_fg": "#F8FAFC"},
    "cohere": {"bg": "#39594D", "fg": "#D4F5E9", "accent": "#D4F5E9", "pill_bg": "#0F241C", "pill_fg": "#D4F5E9"},
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
