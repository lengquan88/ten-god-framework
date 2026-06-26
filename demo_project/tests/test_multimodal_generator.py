"""Tests for multimodal_generator.py — 多模态生成模块测试"""

import pytest

from tengod.食神_创生输出.multimodal_generator import (
    MultimodalGenerator,
    StableDiffusionConnector,
    TTSConnector,
)


# ════════════════════════════════════════════════════════════════════
# MultimodalGenerator
# ════════════════════════════════════════════════════════════════════


class TestMultimodalGeneratorInit:
    """初始化测试"""

    def test_init_creates_empty_history(self):
        gen = MultimodalGenerator()
        assert gen._generation_history == []

    def test_init_sets_supported_formats(self):
        gen = MultimodalGenerator()
        assert "image" in gen._supported_formats
        assert "audio" in gen._supported_formats
        assert "video" in gen._supported_formats
        assert gen._supported_formats["image"] == ["png", "jpg", "webp"]
        assert gen._supported_formats["audio"] == ["wav", "mp3", "ogg"]
        assert gen._supported_formats["video"] == ["mp4"]


# ── generate_image ─────────────────────────────────────────────────


class TestGenerateImage:
    """图片生成测试"""

    STYLES = ["realistic", "anime", "oil_painting", "chinese_ink", "calligraphy"]

    def test_returns_expected_fields(self):
        gen = MultimodalGenerator()
        result = gen.generate_image("a mountain at sunset")
        assert "image_id" in result
        assert "prompt" in result
        assert "style" in result
        assert "size" in result
        assert "format" in result
        assert result["status"] == "mock"

    @pytest.mark.parametrize("style", STYLES)
    def test_style_produces_modifier_in_prompt(self, style):
        gen = MultimodalGenerator()
        result = gen.generate_image("a dragon", style=style)
        assert result["style"] == style
        assert "a dragon" in result["prompt"]

    def test_default_style_is_realistic(self):
        gen = MultimodalGenerator()
        result = gen.generate_image("test")
        assert result["style"] == "realistic"

    def test_custom_size(self):
        gen = MultimodalGenerator()
        result = gen.generate_image("test", size=(1024, 768))
        assert result["size"] == (1024, 768)

    def test_custom_format(self):
        gen = MultimodalGenerator()
        result = gen.generate_image("test", format="webp")
        assert result["format"] == "webp"

    def test_image_id_is_unique(self):
        gen = MultimodalGenerator()
        ids = [gen.generate_image("test")["image_id"] for _ in range(10)]
        assert len(set(ids)) == 10

    def test_records_in_history(self):
        gen = MultimodalGenerator()
        gen.generate_image("test")
        history = gen.get_history("image")
        assert len(history) == 1
        assert history[0]["type"] == "image"


# ── generate_image_batch ────────────────────────────────────────────


class TestGenerateImageBatch:
    """批量图片生成测试"""

    def test_batch_returns_list(self):
        gen = MultimodalGenerator()
        results = gen.generate_image_batch(["a", "b", "c"])
        assert isinstance(results, list)
        assert len(results) == 3

    def test_batch_each_entry_has_status_mock(self):
        gen = MultimodalGenerator()
        results = gen.generate_image_batch(["a", "b"])
        for r in results:
            assert r["status"] == "mock"

    def test_batch_prompts_are_distinct(self):
        gen = MultimodalGenerator()
        results = gen.generate_image_batch(["cat", "dog"])
        assert "cat" in results[0]["prompt"]
        assert "dog" in results[1]["prompt"]


# ── generate_illustration ───────────────────────────────────────────


class TestGenerateIllustration:
    """插图生成测试"""

    def test_returns_image_with_scene_and_elements(self):
        gen = MultimodalGenerator()
        result = gen.generate_illustration("mountain", ["river", "tree"])
        assert result["status"] == "mock"
        assert "mountain" in result["prompt"]
        assert "river" in result["prompt"]
        assert "tree" in result["prompt"]

    def test_default_style_is_chinese_ink(self):
        gen = MultimodalGenerator()
        result = gen.generate_illustration("scene", [])
        assert result["style"] == "chinese_ink"

    def test_illustration_size_is_1024(self):
        gen = MultimodalGenerator()
        result = gen.generate_illustration("scene", [])
        assert result["size"] == (1024, 1024)


# ── generate_audio ──────────────────────────────────────────────────


class TestGenerateAudio:
    """音频生成测试"""

    def test_returns_expected_fields(self):
        gen = MultimodalGenerator()
        result = gen.generate_audio("你好世界")
        assert result["status"] == "mock"
        assert "audio_id" in result
        assert result["text"] == "你好世界"
        assert result["voice"] == "default"
        assert result["format"] == "wav"
        assert result["speed"] == 1.0

    def test_custom_voice(self):
        gen = MultimodalGenerator()
        result = gen.generate_audio("test", voice="ancient")
        assert result["voice"] == "ancient"

    def test_custom_speed(self):
        gen = MultimodalGenerator()
        result = gen.generate_audio("test", speed=1.5)
        assert result["speed"] == 1.5

    def test_custom_format(self):
        gen = MultimodalGenerator()
        result = gen.generate_audio("test", format="mp3")
        assert result["format"] == "mp3"


# ── generate_poem_reading ───────────────────────────────────────────


class TestGeneratePoemReading:
    """古诗朗诵测试"""

    def test_voice_is_style(self):
        gen = MultimodalGenerator()
        result = gen.generate_poem_reading("床前明月光", style="ancient")
        assert result["voice"] == "ancient"

    def test_speed_is_0_8(self):
        gen = MultimodalGenerator()
        result = gen.generate_poem_reading("静夜思")
        assert result["speed"] == 0.8

    def test_format_is_mp3(self):
        gen = MultimodalGenerator()
        result = gen.generate_poem_reading("春晓")
        assert result["format"] == "mp3"


# ── generate_meditation_audio ───────────────────────────────────────


class TestGenerateMeditationAudio:
    """冥想音频生成测试"""

    THEMES = ["道法自然", "阴阳调和", "静心"]

    @pytest.mark.parametrize("theme", THEMES)
    def test_known_theme_returns_mock(self, theme):
        gen = MultimodalGenerator()
        result = gen.generate_meditation_audio(theme=theme)
        assert result["status"] == "mock"
        assert result["voice"] == "ancient"
        assert result["speed"] == 0.6
        assert result["format"] == "mp3"

    def test_unknown_theme_defaults_to_道法自然(self):
        gen = MultimodalGenerator()
        result = gen.generate_meditation_audio(theme="不存在的主题")
        assert "道可道" in result["text"]
        assert result["status"] == "mock"


# ── generate_video ──────────────────────────────────────────────────


class TestGenerateVideo:
    """视频生成测试"""

    def test_returns_expected_fields(self):
        gen = MultimodalGenerator()
        result = gen.generate_video("a sunset")
        assert result["status"] == "mock"
        assert "video_id" in result
        assert result["prompt"] == "a sunset"
        assert result["duration"] == 5.0
        assert result["fps"] == 24
        assert result["resolution"] == (1024, 576)

    def test_custom_duration(self):
        gen = MultimodalGenerator()
        result = gen.generate_video("test", duration=10.0)
        assert result["duration"] == 10.0

    def test_custom_fps(self):
        gen = MultimodalGenerator()
        result = gen.generate_video("test", fps=60)
        assert result["fps"] == 60

    def test_custom_resolution(self):
        gen = MultimodalGenerator()
        result = gen.generate_video("test", resolution=(1920, 1080))
        assert result["resolution"] == (1920, 1080)


# ── get_history ─────────────────────────────────────────────────────


class TestGetHistory:
    """历史记录查询测试"""

    def test_returns_all_entries(self):
        gen = MultimodalGenerator()
        gen.generate_image("img")
        gen.generate_audio("aud")
        gen.generate_video("vid")
        all_history = gen.get_history()
        assert len(all_history) == 3

    def test_filter_image(self):
        gen = MultimodalGenerator()
        gen.generate_image("img1")
        gen.generate_image("img2")
        gen.generate_audio("aud")
        result = gen.get_history("image")
        assert len(result) == 2
        for h in result:
            assert h["type"] == "image"

    def test_filter_audio(self):
        gen = MultimodalGenerator()
        gen.generate_audio("aud1")
        gen.generate_audio("aud2")
        gen.generate_image("img")
        result = gen.get_history("audio")
        assert len(result) == 2
        for h in result:
            assert h["type"] == "audio"

    def test_filter_video(self):
        gen = MultimodalGenerator()
        gen.generate_video("vid1")
        gen.generate_video("vid2")
        gen.generate_image("img")
        result = gen.get_history("video")
        assert len(result) == 2
        for h in result:
            assert h["type"] == "video"


# ── stats ───────────────────────────────────────────────────────────


class TestStats:
    """统计测试"""

    def test_returns_correct_counts(self):
        gen = MultimodalGenerator()
        gen.generate_image("img1")
        gen.generate_image("img2")
        gen.generate_audio("aud1")
        gen.generate_video("vid1")
        s = gen.stats()
        assert s["total_generations"] == 4
        assert s["by_type"]["image"] == 2
        assert s["by_type"]["audio"] == 1
        assert s["by_type"]["video"] == 1

    def test_includes_supported_formats(self):
        gen = MultimodalGenerator()
        s = gen.stats()
        assert "supported_formats" in s
        assert s["supported_formats"]["image"] == ["png", "jpg", "webp"]
        assert s["supported_formats"]["audio"] == ["wav", "mp3", "ogg"]
        assert s["supported_formats"]["video"] == ["mp4"]


# ════════════════════════════════════════════════════════════════════
# StableDiffusionConnector
# ════════════════════════════════════════════════════════════════════


class TestStableDiffusionConnector:
    """Stable Diffusion 连接器测试"""

    def test_init_default_url(self):
        conn = StableDiffusionConnector()
        assert conn._api_url == "http://localhost:7860"

    def test_init_custom_url(self):
        conn = StableDiffusionConnector(api_url="http://192.168.1.100:7860")
        assert conn._api_url == "http://192.168.1.100:7860"

    def test_txt2img_returns_ready(self):
        conn = StableDiffusionConnector()
        result = conn.txt2img("a cat")
        assert result["status"] == "ready"
        assert result["prompt"] == "a cat"
        assert "sdapi/v1/txt2img" in result["endpoint"]

    def test_img2img_returns_ready(self):
        conn = StableDiffusionConnector()
        result = conn.img2img("a dog", init_image="base64data")
        assert result["status"] == "ready"
        assert result["prompt"] == "a dog"
        assert "sdapi/v1/img2img" in result["endpoint"]


# ════════════════════════════════════════════════════════════════════
# TTSConnector
# ════════════════════════════════════════════════════════════════════


class TestTTSConnector:
    """TTS 连接器测试"""

    def test_init_default_provider(self):
        conn = TTSConnector()
        assert conn._provider == "edge-tts"

    def test_init_custom_provider(self):
        conn = TTSConnector(provider="azure-tts")
        assert conn._provider == "azure-tts"

    def test_synthesize_returns_ready(self):
        conn = TTSConnector()
        result = conn.synthesize("你好", voice="zh-CN-XiaoxiaoNeural")
        assert result["status"] == "ready"
        assert result["text"] == "你好"
        assert result["voice"] == "zh-CN-XiaoxiaoNeural"