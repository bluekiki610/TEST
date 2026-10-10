# services/providers/siliconflow.py
# 硅基流动 SiliconFlow provider —— V1.1 Step 6A：已接入真实 TTS
#
# 能力位现状（implemented_capabilities 才是唯一选型依据）：
#   tts     ✅ 真实可用（Step 6A）
#   chat / vision / image / asr —— 仍为未实现骨架
#
# 本项目现有代码里已经在用它（ext_ai.py 的 PROVIDERS 表、
# ext_mem.py 的 /api/tts 走 api.siliconflow.cn），本文件把它纳入统一服务层。

import json
import urllib.error
import urllib.request

from .base import (
    BaseProvider,
    CAPABILITY_CHAT,
    CAPABILITY_VISION,
    CAPABILITY_IMAGE,
    CAPABILITY_ASR,
    CAPABILITY_TTS,
    ok_audio_result,
    fail_result,
    not_implemented,
)

# 与 ext_mem.py:/api/tts 保持一致的默认 TTS 模型与端点
DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_TTS_MODEL = "FunAudioLLM/CosyVoice2-0.5B"
TTS_TIMEOUT = 30           # 与 ext_mem.py 的 timeout=30 对齐
TTS_MAX_CHARS = 500        # 与 ext_mem.py 的 text[:500] 对齐


class SiliconFlowProvider(BaseProvider):
    key = "siliconflow"
    name = "硅基流动"

    # 与 ext_ai.py 的 PROVIDERS["siliconflow"] 保持一致；
    # 未填 base_url 时用它兜底，避免误用别的供应商端点。
    default_base_url = DEFAULT_BASE_URL
    default_model = DEFAULT_TTS_MODEL

    # Step 5B/6A：已真实实现的能力位（唯一选型依据）
    #   6A 只接了 tts；chat / vision / image / asr 仍未实现，不能写进来。
    implemented_capabilities = [CAPABILITY_TTS]
    # 计划支持（仅展示，不参与选型）
    planned_capabilities = [
        CAPABILITY_CHAT,
        CAPABILITY_VISION,
        CAPABILITY_IMAGE,
        CAPABILITY_ASR,
        CAPABILITY_TTS,
    ]

    def _tts_url(self):
        return (self.base_url or DEFAULT_BASE_URL).rstrip("/") + "/audio/speech"

    def chat(self, messages=None, model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实对话请求
        return not_implemented(self.key, CAPABILITY_CHAT)

    def vision(self, image=None, prompt="", model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实视觉理解请求
        return not_implemented(self.key, CAPABILITY_VISION)

    def image(self, prompt="", model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实文生图请求
        return not_implemented(self.key, CAPABILITY_IMAGE)

    def asr(self, audio=None, model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实语音识别请求
        return not_implemented(self.key, CAPABILITY_ASR)

    def tts(self, text="", model="", voice_id="", response_format="mp3",
            timeout=TTS_TIMEOUT, **kwargs):
        """真实的硅基流动语音合成调用（Step 6A）。

        与项目现有 ext_mem.py 的 /api/tts 完全同构：
            POST https://api.siliconflow.cn/v1/audio/speech
            {"model": <TTS模型>, "input": <文本>, "response_format": "mp3"}
            → 直接返回音频字节

        语义说明（重要，别搞错）：
            硅基流动的 /audio/speech **只有 model 一个选择字段，没有独立的 voice 参数**：
            它的「音色」是绑在 TTS 模型上的（例如 CosyVoice2 系列里的不同 voice 模型）。
            因此这里：
              · `model`     = 要用的 TTS 模型（决定音色）
              · `voice_id`  = 只作为**返回里的标记**回传，方便调用方确认"用的是哪个声音"，
                              不写进请求体（写会 400）。
        若将来硅基流动支持独立 voice 字段，再在此处加上即可。
        """
        use_model = (model or self.get_model(CAPABILITY_TTS) or DEFAULT_TTS_MODEL).strip()
        # voice_id 仅用于回传标记；硅基流动不接受独立 voice 字段
        use_voice = (voice_id or "").strip()

        # 1) 无 key：安全返回，不发请求
        if not (self.api_key or "").strip():
            return fail_result(provider=self.key, model=use_model, error="未配置硅基流动 API Key")

        # 2) 文本校验（沿用项目现有的 500 字上限，避免超长请求被上游拒绝）
        text = (text or "").strip()
        if not text:
            return fail_result(provider=self.key, model=use_model, error="text 不能为空")
        if len(text) > TTS_MAX_CHARS:
            text = text[:TTS_MAX_CHARS]

        # ⚠️ 严格只发硅基流动支持的字段（与 ext_mem.py:/api/tts 完全一致）
        payload = {
            "model": use_model,
            "input": text,
            "response_format": response_format or "mp3",
        }

        url = self._tts_url()
        try:
            body = json.dumps(payload).encode("utf-8")
        except Exception as e:
            return fail_result(provider=self.key, model=use_model, error=f"请求体序列化失败: {e}")

        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.api_key.strip(),
        })

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                audio = resp.read()
                ctype = resp.headers.get("Content-Type", "") if hasattr(resp, "headers") else ""
        except urllib.error.HTTPError as he:
            detail = ""
            try:
                detail = he.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                detail = ""
            return fail_result(
                provider=self.key, model=use_model,
                error=f"HTTP {he.code}: {detail or he.reason}",
                http_status=he.code,
            )
        except urllib.error.URLError as ue:
            return fail_result(provider=self.key, model=use_model, error=f"网络错误: {ue.reason}")
        except Exception as e:
            return fail_result(provider=self.key, model=use_model, error=f"请求失败: {e}")

        if not audio:
            return fail_result(provider=self.key, model=use_model, error="上游返回了空音频")

        return ok_audio_result(
            provider=self.key,
            model=use_model,
            audio=audio,
            mime_type=(ctype or "audio/mpeg"),
            voice_id=use_voice,
        )
