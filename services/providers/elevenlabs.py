# services/providers/elevenlabs.py
# ElevenLabs provider —— V1.1 Step 6C：真实 TTS + 真实声音克隆
#
# 协议已核对官方文档（非猜测）：
#   TTS   POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
#         header: xi-api-key; body: {"text":..., "model_id":...}
#         query : output_format（默认 mp3_44100_128）
#         → 直接返回音频字节
#   Clone POST https://api.elevenlabs.io/v1/voices/add   (multipart/form-data)
#         header: xi-api-key
#         fields: name(必填) + files(必填，可多个)
#         → {"voice_id":"...","requires_verification":false}
#
# 参考：https://elevenlabs.io/docs/api-reference/text-to-speech/convert
#       https://elevenlabs.io/docs/api-reference/voices/ivc/create

import json
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
import uuid

from .base import (
    BaseProvider,
    CAPABILITY_TTS,
    CAPABILITY_ASR,
    ok_audio_result,
    fail_result,
    not_implemented,
)
from .voice_clone import VoiceCloneProvider, clone_ok, clone_fail

DEFAULT_BASE_URL = "https://api.elevenlabs.io"
DEFAULT_MODEL = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
TTS_TIMEOUT = 60
CLONE_TIMEOUT = 300        # 克隆要上传音频，给足时间


class ElevenLabsProvider(BaseProvider, VoiceCloneProvider):
    key = "elevenlabs"
    name = "ElevenLabs"

    default_base_url = DEFAULT_BASE_URL
    default_model = DEFAULT_MODEL

    # Step 5B：已真实实现的能力位（唯一选型依据）
    implemented_capabilities = [CAPABILITY_TTS]
    planned_capabilities = [CAPABILITY_TTS, CAPABILITY_ASR]

    # ---- 克隆能力（Step 6D：按要求下调为 pending）----
    # ⚠️ 说明：6C 时我曾按官方文档接入过真实克隆协议（POST /v1/voices/add），
    #    6D 审核要求"暂不实现真实克隆接口"，因此这里下调为 pending。
    #    下面的 clone_voice() 实现**仍然保留**，等引擎选型确定后
    #    把 clone_implemented 改回 True 即可立刻恢复（无需重写）。
    supports_clone = True          # 供应商业务上支持（克隆成熟、多语言好）
    clone_implemented = False      # Step 6D：暂不启用真实克隆
    clone_note = ("待启用：真实协议已按官方文档实现（见本文件 clone_voice），"
                  "Step 6D 要求先冻结声音资产架构，等引擎选型确认后再开启")
    clone_audio_formats = ("mp3", "wav", "m4a")

    # ---------- 内部 ----------
    def _base(self):
        return (self.base_url or DEFAULT_BASE_URL).rstrip("/")

    def _tts_model(self, model=""):
        return (model or self.get_model(CAPABILITY_TTS) or self.default_model or DEFAULT_MODEL).strip()

    def _headers(self, json_body=True):
        h = {"xi-api-key": (self.api_key or "").strip()}
        if json_body:
            h["Content-Type"] = "application/json"
        return h

    # ---------- 真实 TTS ----------
    def tts(self, text="", model="", voice_id="", output_format=DEFAULT_OUTPUT_FORMAT,
            timeout=TTS_TIMEOUT, **kwargs):
        """真实 ElevenLabs 语音合成。

        voice_id 是**必需**的：ElevenLabs 把它放在 URL 路径里，
        所以没有音色就无从调用（这一点与硅基流动相反）。
        """
        use_model = self._tts_model(model)
        use_voice = (voice_id or "").strip()

        if not (self.api_key or "").strip():
            return fail_result(provider=self.key, model=use_model, error="未配置 ElevenLabs API Key")
        if not use_voice:
            return fail_result(provider=self.key, model=use_model,
                               error="缺少 voice_id（ElevenLabs 必须指定音色）")
        text = (text or "").strip()
        if not text:
            return fail_result(provider=self.key, model=use_model, error="text 不能为空")

        url = f"{self._base()}/v1/text-to-speech/{urllib.parse.quote(use_voice)}"
        if output_format:
            url += f"?output_format={urllib.parse.quote(str(output_format))}"
        payload = {"text": text, "model_id": use_model}

        try:
            body = json.dumps(payload).encode("utf-8")
        except Exception as e:
            return fail_result(provider=self.key, model=use_model, error=f"请求体序列化失败: {e}")

        req = urllib.request.Request(url, data=body, headers=self._headers(True))
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
            return fail_result(provider=self.key, model=use_model,
                               error=f"HTTP {he.code}: {detail or he.reason}", http_status=he.code)
        except urllib.error.URLError as ue:
            return fail_result(provider=self.key, model=use_model, error=f"网络错误: {ue.reason}")
        except Exception as e:
            return fail_result(provider=self.key, model=use_model, error=f"请求失败: {e}")

        if not audio:
            return fail_result(provider=self.key, model=use_model, error="上游返回了空音频")

        return ok_audio_result(
            provider=self.key, model=use_model, audio=audio,
            mime_type=(ctype or "audio/mpeg"), voice_id=use_voice,
        )

    # ---------- 真实克隆 ----------
    def clone_voice(self, audio_path="", name="", model="", timeout=CLONE_TIMEOUT, **kwargs):
        """真实 ElevenLabs 声音克隆（IVC）：POST /v1/voices/add（multipart）。"""
        if not (self.api_key or "").strip():
            return clone_fail(provider=self.key, model=model, error="未配置 ElevenLabs API Key")

        import os
        if not audio_path or not os.path.isfile(audio_path):
            return clone_fail(provider=self.key, model=model, error=f"音频文件不存在: {audio_path}")

        voice_name = (name or "").strip() or "linkong_voice"
        try:
            with open(audio_path, "rb") as f:
                file_bytes = f.read()
        except Exception as e:
            return clone_fail(provider=self.key, model=model, error=f"读取音频失败: {e}")

        filename = os.path.basename(audio_path)
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        boundary = "----LinkongBoundary" + uuid.uuid4().hex
        body = _build_multipart(
            boundary,
            fields={"name": voice_name},
            files=[("files", filename, ctype, file_bytes)],
        )

        url = f"{self._base()}/v1/voices/add"
        headers = {
            "xi-api-key": (self.api_key or "").strip(),
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        req = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as he:
            detail = ""
            try:
                detail = he.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                detail = ""
            return clone_fail(provider=self.key, model=model,
                              error=f"HTTP {he.code}: {detail or he.reason}", http_status=he.code)
        except urllib.error.URLError as ue:
            return clone_fail(provider=self.key, model=model, error=f"网络错误: {ue.reason}")
        except Exception as e:
            return clone_fail(provider=self.key, model=model, error=f"请求失败: {e}")

        try:
            out = json.loads(raw)
        except Exception as e:
            return clone_fail(provider=self.key, model=model, error=f"响应不是合法 JSON: {e}")

        vid = (out.get("voice_id") or "").strip() if isinstance(out, dict) else ""
        if not vid:
            return clone_fail(provider=self.key, model=model,
                              error=f"上游未返回 voice_id: {raw[:200]}")

        return clone_ok(
            provider=self.key, voice_id=vid,
            model=model or DEFAULT_MODEL, label=voice_name,
        )

    def asr(self, audio=None, model="", **kwargs):
        # TODO: 接入真实语音识别请求
        return not_implemented(self.key, CAPABILITY_ASR)


def _build_multipart(boundary, fields=None, files=None):
    """构造 multipart/form-data 请求体（标准库实现，不引入 requests）。

    fields —— {name: value} 普通文本字段
    files  —— [(field_name, filename, content_type, bytes), ...]
    """
    crlf = b"\r\n"
    out = bytearray()
    for k, v in (fields or {}).items():
        out += b"--" + boundary.encode() + crlf
        out += f'Content-Disposition: form-data; name="{k}"'.encode() + crlf + crlf
        out += str(v).encode("utf-8") + crlf
    for field, filename, ctype, data in (files or []):
        out += b"--" + boundary.encode() + crlf
        out += (f'Content-Disposition: form-data; name="{field}"; '
                f'filename="{filename}"').encode() + crlf
        out += f"Content-Type: {ctype}".encode() + crlf + crlf
        out += data + crlf
    out += b"--" + boundary.encode() + b"--" + crlf
    return bytes(out)
