"""Unit tests for fine-tune vs base skip-list."""

from src.detect import is_base_family_candidate, should_skip_model
from src.config import LAB_BY_KEY


def test_skips_gguf_reupload():
    assert should_skip_model("Llama-3.1-8B-Instruct-GGUF")


def test_skips_awq_gptq():
    assert should_skip_model("Qwen2.5-72B-Instruct-AWQ")
    assert should_skip_model("DeepSeek-R1-GPTQ")


def test_skips_lora_finetune_merge():
    assert should_skip_model("Llama 3 medical LoRA")
    assert should_skip_model("Mistral-7B-finetune")
    assert should_skip_model("Merge of Qwen and Llama")


def test_skips_image_video():
    assert should_skip_model("Flux Image model")
    assert should_skip_model("Sora video preview")
    assert should_skip_model("Whisper large v3", pipeline_tag="automatic-speech-recognition")


def test_skips_hf_media_tags():
    assert should_skip_model("something", tags=["text-to-image"])
    assert should_skip_model("something", pipeline_tag="text-to-video")


def test_allows_base_open_weight_families():
    assert not should_skip_model("Llama 4 Maverick")
    assert not should_skip_model("DeepSeek V3")
    assert not should_skip_model("Qwen3 235B")
    assert not should_skip_model("Gemma 3 27B")


def test_allows_closed_frontier_names():
    assert not should_skip_model("Claude Opus 5")
    assert not should_skip_model("GPT-5.6 Sol")
    assert not should_skip_model("Gemini 3 Pro")


def test_skips_ui_surface_of_already_shipped():
    assert should_skip_model(
        "Claude Opus 5 now in the UI",
        already_shipped_names={"Claude Opus 5"},
    )


def test_gemma_family_gate():
    gemma = LAB_BY_KEY["gemma"]
    google = LAB_BY_KEY["google"]
    assert is_base_family_candidate("Gemma 3 27B", gemma)
    assert not is_base_family_candidate("Gemini 2.5 Flash", gemma)
    assert is_base_family_candidate("Gemini 2.5 Flash", google)
