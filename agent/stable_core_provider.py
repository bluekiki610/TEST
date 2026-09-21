"""
agent/stable_core_provider.py - Phase B2-1: StableCoreProvider

职责：
- 从现有 Linkong 世界事实中，提取 Stable Core 层的结构化 Context。

边界（依据 Architecture Contract + B2 原则）：
- Provider ≠ Database
- Provider ≠ Memory
- Provider ≠ Decision
- Provider ≠ Prompt
- Provider 只负责：从已有系统事实中，取出一小块结构化数据

硬性约束：
1. 不修改 main.data
2. 不调用 LLM
3. 不缓存、不持久化
4. 不 import main
5. 不 import ext_*
6. 不返回 Prompt 字符串
7. 不返回整个 main.data

Stable Core 只包含真正稳定的内容：
- identity      身份（AI 名 + owner 名）
- world_lore    世界观
- persona       AI 人设
- user_profile  用户画像

明确不含（防止历史线性增长 / 敏感信息泄漏）：
- messages / sms / trails / ai_timeline / ai_memories
- notes / diaries / stories
- wallets / work_sessions / home_jobs
- ai_keys / dev_users / pairs_admin
- ai_impression（key 不一致，暂不接管）
- presence / online
"""

from typing import Dict, Any, List


STABLE_CORE_LAYER = "stable_core"


class StableCoreProvider:
    """
    Stable Core Provider。

    使用方式：
        provider = StableCoreProvider()
        items = provider.fetch(ai_name, owner, data)
        # items 是结构化 list[dict]，不是 ContextSection，也不是 Prompt
    """

    name = "stable_core"
    layer = STABLE_CORE_LAYER

    # Provider 提取的 data 字段白名单（仅用于文档和审计）
    _ALLOWED_DATA_FIELDS = ("world_lore", "ai_profiles", "user_profiles")

    # 明确排除的敏感字段（仅用于文档和审计）
    _FORBIDDEN_DATA_FIELDS = (
        "ai_keys", "dev_users", "pairs_admin", "server_id",
    )

    def fetch(
        self,
        ai_name: str,
        owner: str,
        data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        从世界事实中提取 Stable Core 的结构化 items。

        Args:
            ai_name: AI 名字（canonical）
            owner:   AI 的主人名字（canonical，可为空字符串）
            data:    只读 main.data 引用（Provider 不修改它）

        Returns:
            List[Dict[str, Any]]，每个 item 是：
            {
              "type":    "identity" | "world_lore" | "persona" | "user_profile",
              "content": str,
              "source":  str,  # 来源标记，便于调试与审计
            }

        保证：
        - 不修改 data
        - 不调用 LLM
        - 不 import main
        - 不缓存
        - 不返回整个 data
        """
        if not ai_name or not isinstance(ai_name, str):
            return []
        if not isinstance(data, dict):
            return []

        items: List[Dict[str, Any]] = []

        # 1. identity（只要有 ai_name 就生成，永远在首位）
        identity_content = f"AI: {ai_name}"
        if owner:
            identity_content += f" / Owner: {owner}"
        items.append({
            "type": "identity",
            "content": identity_content,
            "source": "argument",
        })

        # 2. world_lore（世界观）
        world_lore = data.get("world_lore", "")
        if isinstance(world_lore, str) and world_lore.strip():
            items.append({
                "type": "world_lore",
                "content": world_lore.strip(),
                "source": "main.data.world_lore",
            })

        # 3. persona（AI 人设）
        # 兼容 ext_ai.build_ai_context 现有读取逻辑：
        #   for o, prof in data["ai_profiles"].items():
        #       if prof.get("ai") == ai or o == owner:
        #           persona = prof.get("persona", "")
        if owner:
            profiles = data.get("ai_profiles", {})
            if isinstance(profiles, dict):
                prof = profiles.get(owner)
                if isinstance(prof, dict):
                    persona = prof.get("persona", "")
                    if isinstance(persona, str) and persona.strip():
                        items.append({
                            "type": "persona",
                            "content": persona.strip(),
                            "source": f"main.data.ai_profiles[{owner!r}].persona",
                        })

        # 4. user_profile（用户画像）
        if owner:
            user_profiles = data.get("user_profiles", {})
            if isinstance(user_profiles, dict):
                uprof = user_profiles.get(owner, "")
                if isinstance(uprof, str) and uprof.strip():
                    items.append({
                        "type": "user_profile",
                        "content": uprof.strip(),
                        "source": f"main.data.user_profiles[{owner!r}]",
                    })

        return items

    def describe(self) -> Dict[str, Any]:
        """
        Provider 自描述（供架构审计）。
        """
        return {
            "name": self.name,
            "layer": self.layer,
            "allowed_data_fields": list(self._ALLOWED_DATA_FIELDS),
            "forbidden_data_fields": list(self._FORBIDDEN_DATA_FIELDS),
            "returns": "List[Dict[str, Any]]",
        }