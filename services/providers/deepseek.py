# services/providers/deepseek.py
# DeepSeek provider —— V1.1 Step 5A：只接入 chat，其余能力仍为骨架
#
# 设计约束（严格按 Step 5A 要求）：
#   1. 只实现 chat 的真实调用；vision / image / asr / tts 保持未实现。
#   2. 不修改 ext_ai.py / main.py / data.json / ai_keys / 前端。
#   3. 沿用项目既有调用方式（ext_ai.py:call_llm）：
#        请求 URL = base_url + "/chat/completions"（OpenAI 兼容）
#        temperature 0.9、urllib.request、timeout 60
#   4. 统一返回结构：{status, provider, model, error}；成功另带 content / usage。
#   5. 不保存任何对话内容到新系统（本层无持久化）。

import json
import time
import urllib.error
import urllib.request

from .base import (
    BaseProvider,
    CAPABILITY_CHAT,
    CAPABILITY_VISION,
    ok_result,
    fail_result,
    not_implemented,
)

# OpenAI 兼容端点（与 ext_ai.py 的 PROVIDERS["deepseek"] 保持一致）
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
CHAT_TIMEOUT = 60          # 与 ext_ai.call_llm 的 timeout=60 对齐
MAX_429_RETRIES = 3        # 与 ext_ai.call_llm 的 429 退避次数对齐


class DeepSeekProvider(BaseProvider):
    key = "deepseek"
    name = "DeepSeek"

    # 未显式配置 base_url 时的兜底（与 ext_ai.py 的默认值一致）
    default_base_url = DEFAULT_BASE_URL
    default_model = DEFAULT_MODEL

    # Step 5B：已真实实现的能力位（唯一选型依据）
    #   目前只有 chat —— vision 尚未实现，因此不写进来，
    #   否则会绕过 not_implemented 保护变成假成功。
    implemented_capabilities = [CAPABILITY_CHAT]
    # 计划支持（仅展示，不参与选型）
    planned_capabilities = [CAPABILITY_CHAT, CAPABILITY_VISION]

    # ---------- 内部工具 ----------
    def _resolved_base_url(self):
        return (self.base_url or self.default_base_url or DEFAULT_BASE_URL).rstrip("/")

    def _resolved_model(self, model=""):
        """优先级：调用方显式指定 > 用户配置的 models.chat > provider 默认。"""
        return (model or self.get_model(CAPABILITY_CHAT) or self.default_model or DEFAULT_MODEL).strip()

    def _chat_url(self):
        return self._resolved_base_url() + "/chat/completions"

    # ---------- 真实调用：chat ----------
    def chat(self, messages=None, model="", temperature=0.9, max_tokens=800,
             force_json=False, timeout=CHAT_TIMEOUT, **kwargs):
        """真实的 DeepSeek 对话调用。

        参数：
            messages      —— OpenAI 风格消息数组
            model         —— 覆盖模型名（不传则用用户配置/默认）
            temperature   —— 默认 0.9，与 ext_ai.call_llm 一致
            max_tokens    —— 默认 800
            force_json    —— True 时带 response_format=json_object（ext_ai 的习惯）
            timeout       —— 秒，默认 60

        返回：统一结构 {status, provider, model, error, content?, usage?}
        任何异常都在这里被捕获并转成 error 结构，**不向上抛**。
        """
        use_model = self._resolved_model(model)

        # 1) 没有 key：安全返回，绝不发请求
        if not (self.api_key or "").strip():
            return fail_result(
                provider=self.key, model=use_model,
                error="未配置 DeepSeek API Key",
            )

        # 2) 参数校验
        if not messages or not isinstance(messages, list):
            return fail_result(provider=self.key, model=use_model, error="messages 不能为空且必须是数组")

        # 3) 组装请求（与 ext_ai.call_llm 同构）
        payload = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if force_json:
            payload["response_format"] = {"type": "json_object"}
        try:
            body = json.dumps(payload).encode("utf-8")
        except Exception as e:
            return fail_result(provider=self.key, model=use_model, error=f"请求体序列化失败: {e}")

        url = self._chat_url()
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.api_key.strip(),
        })

        # 4) 发送（429 指数退避，与 ext_ai 的 hotfix 行为对齐）
        raw = None
        for attempt in range(MAX_429_RETRIES + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                break
            except urllib.error.HTTPError as he:
                detail = ""
                try:
                    detail = he.read().decode("utf-8", errors="replace")[:300]
                except Exception:
                    detail = ""
                if he.code == 429 and attempt < MAX_429_RETRIES:
                    wait = 2 ** attempt      # 1, 2, 4
                    print(f"[deepseek] 429 限流，{wait}s 后重试 {attempt + 1}/{MAX_429_RETRIES}", flush=True)
                    time.sleep(wait)
                    continue
                return fail_result(
                    provider=self.key, model=use_model,
                    error=f"HTTP {he.code}: {detail or he.reason}",
                    http_status=he.code,
                )
            except urllib.error.URLError as ue:
                return fail_result(provider=self.key, model=use_model, error=f"网络错误: {ue.reason}")
            except Exception as e:
                return fail_result(provider=self.key, model=use_model, error=f"请求失败: {e}")

        if raw is None:
            return fail_result(provider=self.key, model=use_model, error="请求未获得响应")

        # 5) 解析（安全取值，缺字段不抛 KeyError）
        try:
            out = json.loads(raw)
        except Exception as e:
            return fail_result(provider=self.key, model=use_model, error=f"响应不是合法 JSON: {e}")

        if isinstance(out, dict) and out.get("error"):
            err = out.get("error")
            msg = err.get("message") if isinstance(err, dict) else str(err)
            return fail_result(provider=self.key, model=use_model, error=f"上游返回错误: {msg}")

        choices = out.get("choices") if isinstance(out, dict) else None
        if not choices:
            return fail_result(provider=self.key, model=use_model, error="响应缺少 choices 字段")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not message:
            return fail_result(provider=self.key, model=use_model, error="响应缺少 message 字段")
        content = message.get("content")

        return ok_result(
            provider=self.key,
            model=out.get("model") or use_model,
            content=content or "",
            usage=out.get("usage"),
            finish_reason=(choices[0].get("finish_reason") or ""),
        )

    # ---------- 其余能力：Step 5A 不接 ----------
    def vision(self, image=None, prompt="", model="", **kwargs):
        # TODO(Step 6): 接入真实视觉理解请求
        return not_implemented(self.key, CAPABILITY_VISION)
