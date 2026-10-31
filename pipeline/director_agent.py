"""
Director Agent — 从 Seed 生成完整 Story Graph

输入：Seed 数据（故事概要/世界观/角色设定）
输出：StoryGraph JSON

核心原则：Director 做一次性全局规划，输出结构化数据（不是叙事文本）。
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from story_graph_schema import (
    StoryGraph, StoryNode, Character, BranchArc, ChoiceOption,
    ValueEffect, ValueSystem, SPObfuscation,
    NodeType, BranchType
)


# ============================================================
# Director Prompt
# ============================================================

DIRECTOR_SYSTEM_PROMPT = """你是一位经验丰富的互动小说导演（Director）。你的任务是将一个故事种子（Seed）转化为完整的故事图（Story Graph）——一个结构化的 JSON 数据，精确定义故事的所有节点、分支、选择和结局。

## 你的工作原则

1. **结构化输出**：你输出的是 JSON 数据，不是叙事文本。每个节点的内容是给 Writer 的指令（场景描述、关键事件、情感基调），不是最终展示给读者的文字。

2. **四幕结构**：
   - 第1幕（~25%）：建立世界观，介绍角色，设置悬念钩子
   - 第2幕（~35%）：矛盾升级，揭示更多信息，关键选择点集中在此
   - 第3幕（~25%）：高潮，最危险的选择，多数死结局在此
   - 第4幕（~15%）：收束，结局分流

3. **分支设计**：
   - 珍珠串分支（pearl_string）：选择不同但结果收束，仅措辞/氛围差异。用于大多数选择点。
   - 强分支（strong）：选择导致完全不同的世界线。限制在 2-3 条，避免指数膨胀。
   - 数值分支（value_based）：选择影响隐藏数值（信任/勇气/线索等），最终影响结局判定。

4. **死结局设计**：
   - 每个死结局必须有明确的死因标签和因果逻辑
   - 死结局应分布在第2-3幕，第1幕不设死结局
   - 死结局是惩罚错误选择，不是随机杀人
   - 死结局可以有条件存活路径：当玩家累积了足够的数值（如 courage≥2），可以脱险进入替代节点

5. **信息边界**：
   - 每个节点标注引入的新事实和知情者（witnesses）
   - 确保角色只能知道他们应该知道的信息

6. **反模式规则（必须遵守）**：
   - **禁止漏斗收束**：不允许多个分支选择最终全部收束到同一个下一节点而不产生任何后续差异。如果两个选项的 target_node_id 相同，则至少需要：(a) 不同的 value_effects 且这些数值在后续有 gate_condition 引用，或 (b) 引入不同的 facts_introduced 且后续节点根据这些事实分化。
   - **禁止伪选择**：如果一个选择点的所有选项都指向同一个 target_node_id 且 value_effects 仅有微小差异（delta≤1），这是伪选择。必须让不同选项指向不同的中间节点，即使最终收束，中间过程也要有内容差异。
   - **数值系统必须落地**：如果定义了 value_system 的 attributes 和 thresholds，则：
     (a) 至少 50% 的选择点必须有 value_effects
     (b) 结局节点的 ending_condition 必须引用 value_system 中的属性
     (c) 至少有一个非结局节点使用 gate_condition 或 auto_route 基于数值路由
   - **结局多样性**：正常结局（非死结局）不能少于 3 个，且必须由不同的数值组合触发，不能只是最后一个选择决定结局。
   - **死结局不能断连**：每个死结局节点必须至少有一个 prev_node 连入，且该 prev_node 的 next_nodes 中包含此死结局。
   - **强分支延续效应**：强分支收束后，后续节点应根据玩家走的是哪条强分支有差异化表现。可通过 auto_route 字段指定分支路径条件路由。

7. **门控与条件路由字段**：
   - choices 中可添加 `gate_condition`（如 `{"clues": ">=5"}`），表示该选项需要满足数值条件才能选择
   - choices 中可添加 `gate_branch`（如 `{"condition": {"courage": ">=2"}, "true_target": "node_x", "false_target": "node_y"}`），表示根据数值条件路由到不同节点
   - nodes 中可添加 `auto_route`（如 `{"branch_trust": "node_a", "branch_suspect": "node_b"}`），表示根据此前分支路径自动路由

## 输出格式

严格按以下 JSON Schema 输出：

```json
{
  "story_id": "string",
  "title": "故事标题",
  "genre": "类型",
  "language": "zh",
  "total_acts": 4,
  "world_setting": "世界观描述（100-200字）",
  "time_period": "时代",
  "location": "地点",
  "characters": [
    {
      "char_id": "string",
      "name": "名字",
      "role": "主角/NPC/反派/配角",
      "description": "外貌+性格（50-100字）",
      "speech_style": "说话风格",
      "hidden_agenda": "隐藏动机（可选）",
      "knowledge": ["初始已知事实列表"]
    }
  ],
  "nodes": {
    "node_01": {
      "node_id": "node_01",
      "node_type": "narrative|choice|dead_end|ending|branch_point|merge_point",
      "title": "节点标题",
      "act": 1,
      "branch_id": "main",
      "scene_description": "场景描述（给Writer的指令）",
      "key_events": ["必须发生的事件"],
      "emotional_tone": "情感基调",
      "choices": [
        {
          "option_id": "opt_01a",
          "text": "选项文本",
          "target_node_id": "node_02",
          "is_dead_end": false,
          "branch_type": "pearl_string|strong|value_based",
          "value_effects": [{"attribute": "trust", "delta": 1}],
          "gate_condition": {"clues": ">=5"},
          "gate_branch": {"condition": {"courage": ">=2"}, "true_target": "node_x", "false_target": "node_y"},
          "locked_hint": "条件不满足时的提示文本",
          "hint": "给Writer的提示"
        }
      ],
      "death_cause": "死因（dead_end节点用）",
      "death_description_hint": "死结局描述提示",
      "ending_type": "true_ending|bad_ending|neutral|cold_ending|bittersweet_ending",
      "ending_condition": "达成条件（引用value_system属性）",
      "next_nodes": ["node_02"],
      "prev_nodes": [],
      "merge_to": "",
      "auto_route": {"description": "路由说明", "branch_a": "node_x", "branch_b": "node_y"},
      "facts_introduced": ["本节点引入的新事实"],
      "witnesses": ["知情者列表"]
    }
  },
  "branches": {
    "branch_id": {
      "branch_id": "string",
      "branch_type": "pearl_string|strong|value_based",
      "fork_node_id": "从哪分叉",
      "merge_node_id": "收束到哪（可选）",
      "node_ids": ["分支内节点序列"],
      "description": "分支概述"
    }
  },
  "entry_node_id": "node_01",
  "value_system": {
    "attributes": {"trust": 0, "courage": 0},
    "thresholds": {"trust": {">=3": "true_ending", "<0": "bad_ending"}},
    "description": "数值系统说明"
  },
  "sp_obfuscation": {
    "writing_style": "standard_rp",
    "response_length": "long",
    "action_depth": "rich",
    "thought_depth": "moderate",
    "environment_depth": "immersive",
    "sensory_depth": "rich",
    "paragraph_count": "several",
    "action_marker": "asterisk",
    "dialogue_marker": "quotes",
    "register": "neutral"
  }
}
```

## 规模要求

- 主线节点：12-20 个
- 选择点：6-10 个
- 死结局：3-8 个
- 正常结局：3-5 个（必须由不同数值组合触发）
- 强分支：1-3 条
- 数值属性：2-3 个（必选，且必须有 gate_condition 引用）
- 带 gate_condition 的选项：至少 2 个
- 带 auto_route 的节点：至少 1 个（强分支收束后）

## 质量检查清单（生成后自检）

1. 是否有选择点的所有选项都指向同一节点？→ 如有，分化中间节点
2. 是否有死结局没被任何 prev_node 连入？→ 如有，补连
3. value_system 的每个属性是否都被至少一个 gate_condition 引用？→ 如否，添加门控
4. 正常结局是否都有 ending_condition 且引用了数值属性？→ 如否，补充
5. 强分支收束后是否有 auto_route 分化？→ 如否，添加
6. 最后一个选择点之前的选择是否对结局有数值累积影响？→ 如否，增加 value_effects

只输出 JSON，不要有任何其他文字。"""


DIRECTOR_USER_PROMPT_TEMPLATE = """请根据以下故事种子生成完整的 Story Graph：

## 故事种子

{seed_content}

## 额外要求

{extra_requirements}

请输出完整的 Story Graph JSON。"""


# ============================================================
# LLM Client (抽象层)
# ============================================================

@dataclass
class LLMConfig:
    """LLM 调用配置"""
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 32000
    temperature: float = 0.7
    api_base: str = ""       # OpenAI-compatible API base URL
    api_key: str = ""
    extra_headers: dict = field(default_factory=dict)


class LLMClient:
    """LLM 客户端抽象。支持多种后端。"""

    def __init__(self, config: LLMConfig):
        self.config = config

    def call(self, system_prompt: str, user_prompt: str) -> str:
        """
        调用 LLM，返回生成文本。
        当前实现：调用 OpenAI 兼容 API。
        """
        import requests

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        # 合并额外 headers（如 X-Sub-Module）
        headers.update(self.config.extra_headers)

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        # 网络重试：代理不稳定时自动重试
        max_network_retries = 3
        for net_attempt in range(max_network_retries):
            try:
                resp = requests.post(
                    f"{self.config.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=600,
                    proxies={"http": None, "https": None},
                )
                resp.raise_for_status()
                break
            except (requests.exceptions.ProxyError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                if net_attempt < max_network_retries - 1:
                    wait = (net_attempt + 1) * 10  # 10s, 20s, 30s
                    print(f"  ⚠️ 网络错误 (attempt {net_attempt+1}): {type(e).__name__}, {wait}s 后重试...")
                    import time
                    time.sleep(wait)
                else:
                    print(f"  ❌ 网络错误，{max_network_retries} 次重试均失败")
                    raise

        data = resp.json()
        finish_reason = data["choices"][0].get("finish_reason", "")
        if finish_reason == "length":
            print(f"  ⚠️ LLM 输出被截断（max_tokens={self.config.max_tokens}），将尝试修复")
        return data["choices"][0]["message"]["content"]


# ============================================================
# Director Agent
# ============================================================

class DirectorAgent:
    """
    Director Agent: Seed → Story Graph

    一次性调用 LLM，将故事种子转化为完整的结构化故事图。
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate(
        self,
        seed_content: str,
        extra_requirements: str = "",
        max_retries: int = 2,
    ) -> StoryGraph:
        """
        从 seed 生成 StoryGraph。

        Args:
            seed_content: 故事种子文本（概要/世界观/角色等）
            extra_requirements: 额外要求（如 "多设置恐怖氛围死结局"）
            max_retries: JSON 解析失败时重试次数

        Returns:
            StoryGraph 对象
        """
        user_prompt = DIRECTOR_USER_PROMPT_TEMPLATE.format(
            seed_content=seed_content,
            extra_requirements=extra_requirements or "无",
        )

        for attempt in range(max_retries + 1):
            print(f"[Director] 调用 LLM (attempt {attempt+1})...")
            raw_output = self.llm.call(DIRECTOR_SYSTEM_PROMPT, user_prompt)

            # 提取 JSON（可能被 ```json 包裹）
            json_str = self._extract_json(raw_output)

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"[Director] JSON 初次解析失败: {e}")
                try:
                    fixed = self._fix_unescaped_quotes(json_str)
                    data = json.loads(fixed)
                    print(f"[Director] 引号修复成功")
                except (json.JSONDecodeError, Exception):
                    try:
                        fixed = json_str
                        fixed = re.sub(r'(?<=": ")(.*?)(?="[,}\]])',
                                       lambda m: m.group(0).replace('\n', '\\n'),
                                       fixed, flags=re.DOTALL)
                        fixed = self._fix_unescaped_quotes(fixed)
                        data = json.loads(fixed)
                        print(f"[Director] 换行+引号修复成功")
                    except (json.JSONDecodeError, Exception) as e2:
                        print(f"[Director] 修复失败: {e2}")
                        if attempt < max_retries:
                            print("[Director] 重试中...")
                            user_prompt = (
                                f"你上一次的输出不是合法的 JSON。错误：{e}\n"
                                f"请重新输出完整的 JSON。注意：\n"
                                f"1. 所有字符串值中的换行必须用 \\n 转义\n"
                                f"2. 双引号必须用 \\\" 转义\n"
                                f"3. 不要有尾逗号\n"
                                f"4. 确保所有括号正确匹配\n\n"
                                f"原始种子：\n{seed_content}"
                            )
                            continue
                        else:
                            raise ValueError(f"Director LLM 输出无法解析为 JSON after {max_retries+1} attempts")

            try:
                graph = StoryGraph.from_dict(data)

                # 验证
                issues = graph.validate()
                if issues:
                    print(f"[Director] 图验证发现 {len(issues)} 个问题：")
                    for issue in issues:
                        print(f"  - {issue}")
                    if attempt < max_retries:
                        print("[Director] 重试中...")
                        # 将问题反馈给 LLM
                        user_prompt = (
                            f"你上一次生成的 Story Graph 有以下问题，请修正后重新输出完整 JSON：\n\n"
                            + "\n".join(f"- {i}" for i in issues)
                            + f"\n\n原始种子：\n{seed_content}"
                        )
                        continue

                print(f"[Director] 生成完成：{graph.stats}")
                return graph

            except Exception as e:
                print(f"[Director] StoryGraph 构建失败: {e}")
                if attempt < max_retries:
                    print("[Director] 重试中...")
                    user_prompt = (
                        f"你上一次的输出虽然是合法 JSON，但构建 StoryGraph 失败。错误：{e}\n"
                        f"请检查数据结构并重新输出完整 JSON。\n\n"
                        f"原始种子：\n{seed_content}"
                    )
                else:
                    raise ValueError(f"Director 生成失败 after {max_retries+1} attempts: {e}")

        raise RuntimeError("Unreachable")

    def _fix_unescaped_quotes(self, json_str: str) -> str:
        """迭代修复 JSON 字符串值内部未转义的双引号"""
        max_iterations = 300
        for _ in range(max_iterations):
            try:
                json.loads(json_str)
                return json_str
            except json.JSONDecodeError as e:
                err_msg = str(e)
                if "Expecting ',' delimiter" not in err_msg and \
                   "Expecting ':' delimiter" not in err_msg and \
                   "Expecting value" not in err_msg:
                    return json_str
                pos = e.pos
                if pos is None or pos >= len(json_str):
                    return json_str
                last_q = json_str.rfind('"', 0, pos)
                if last_q > 0 and json_str[last_q - 1] != '\\':
                    json_str = json_str[:last_q] + '\\"' + json_str[last_q + 1:]
                else:
                    return json_str
        return json_str

    def _extract_json(self, text: str) -> str:
        """从 LLM 输出中提取并修复 JSON 字符串"""
        text = text.strip()

        # 去掉 markdown 代码块
        if text.startswith("```"):
            first_newline = text.index("\n")
            last_fence = text.rfind("```")
            if last_fence > first_newline:
                text = text[first_newline+1:last_fence].strip()

        # 提取最外层的 JSON 结构
        for open_ch, close_ch in [("{", "}"), ("[", "]")]:
            first = text.find(open_ch)
            last = text.rfind(close_ch)
            if first != -1 and last != -1 and last > first:
                text = text[first:last+1]
                break

        # 修复常见 LLM 输出问题
        # 1. 控制字符（除了 \n \r \t）
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        # 2. 尾逗号
        text = re.sub(r',\s*([}\]])', r'\1', text)

        # 3. 截断修复：如果 LLM 输出被截断（max_tokens），补齐缺失的括号
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')
        if open_braces > 0 or open_brackets > 0:
            # 先去掉可能的不完整尾部（截断的字符串值等）
            # 找到最后一个完整的 key-value 对
            last_complete = max(text.rfind('}'), text.rfind(']'))
            if last_complete > len(text) // 2:  # 确保不会截太多
                text = text[:last_complete+1]
                # 重新计算
                open_braces = text.count('{') - text.count('}')
                open_brackets = text.count('[') - text.count(']')
            text += ']' * max(0, open_brackets) + '}' * max(0, open_braces)

        return text


# ============================================================
# 本地测试用：手写一个示例 Seed
# ============================================================

EXAMPLE_SEED_DETECTIVE = """
## 故事种子：维多利亚侦探悬疑

**类型**：悬疑推理
**时代**：1862年
**地点**：伦敦

**故事概要**：
一位年轻侦探接到委托，调查一起发生在贵族庄园中的密室杀人案。死者是庄园主人——一位以收藏珍贵画作闻名的伯爵。所有门窗从内部锁死，唯一的钥匙在死者口袋里。

随着调查深入，侦探发现伯爵生前收到过多封威胁信，庄园里的仆人们各怀心事，而最大的疑点指向伯爵新婚不久的妻子和她的意大利裔管家。

三条主线交织：画作失窃案、密室杀人案、伯爵的秘密身份。最终的真相可能颠覆一切。

**主角**：
- 艾德蒙·克劳福德 — 年轻侦探，观察力敏锐但经验不足，有时过于自信

**关键 NPC**：
- 伯爵夫人伊莎贝拉 — 美丽且神秘，似乎在隐瞒什么
- 管家拉扎罗 — 意大利裔，忠诚但有不可告人的过去
- 警探威廉 — 老派警察，与侦探方法相左但心地善良
- 女仆艾米莉 — 胆小但知道关键信息

**期望的分支**：
- 选择信任伯爵夫人 vs 怀疑她（强分支）
- 是否独自调查地下室 vs 叫警探同行（死结局可能）
- 如何处理画作线索（影响最终真相揭露程度）
"""


def generate_example_graph_offline() -> StoryGraph:
    """
    离线生成示例 StoryGraph（不调用 LLM，手写）。
    用于验证 Schema 完备性和下游 Writer 的 context 切分。
    """
    characters = [
        Character(
            char_id="mc",
            name="艾德蒙·克劳福德",
            role="主角",
            description="26岁的年轻侦探，棕发绿眼，穿着得体的灰色西装。观察力惊人但经验不足，偶尔过于自信导致判断失误。",
            speech_style="礼貌但直接，喜欢用反问引导对方说出真相",
            knowledge=["受委托调查密室杀人案", "死者是伯爵", "门窗从内部锁死"],
        ),
        Character(
            char_id="isabella",
            name="伊莎贝拉",
            role="NPC",
            description="28岁的伯爵夫人，黑发蓝眼，总是穿深色丧服。举止优雅但眼神中藏着不安。",
            speech_style="措辞优雅但经常话说一半就停住，用沉默代替回答",
            hidden_agenda="她知道伯爵的秘密身份，正在保护丈夫的遗产不被同伙夺走",
            knowledge=["伯爵的秘密身份", "威胁信的真实来源"],
        ),
        Character(
            char_id="lazaro",
            name="拉扎罗·乌切洛",
            role="NPC",
            description="45岁的意大利裔管家，高瘦，灰鬓，永远一丝不苟。表面忠诚背后藏着自己的秘密。",
            speech_style="正式、简洁，偶尔冒出意大利语词汇，紧张时口音加重",
            hidden_agenda="他是伯爵秘密事业的合伙人，案发夜其实不在庄园",
            knowledge=["伯爵的商业往来", "画作的真实来源", "自己案发夜的真实去向"],
        ),
        Character(
            char_id="william",
            name="威廉·马德勒",
            role="NPC",
            description="55岁的老警探，胖硕红脸，八字胡。办案靠直觉不靠证据，但有丰富的街头经验。",
            speech_style="粗犷直白，喜欢打断别人，但关键时刻出人意料地细腻",
            knowledge=["伯爵的公开身份", "庄园周边的治安情况"],
        ),
        Character(
            char_id="emily",
            name="艾米莉",
            role="配角",
            description="19岁的女仆，红发雀斑，手指因为干活总是通红。胆小怕事但观察力好。",
            speech_style="声音很小，说话前总要环顾四周，用'先生'开头",
            hidden_agenda="她目睹了案发夜的关键细节但害怕被灭口",
            knowledge=["案发夜看到有人从书房侧门离开"],
        ),
    ]

    nodes = {}

    # ===== 第1幕：雾都迷影 =====
    nodes["node_01"] = StoryNode(
        node_id="node_01", node_type=NodeType.NARRATIVE, title="委托", act=1,
        scene_description="伦敦大雾弥漫的清晨，侦探在自己简陋的办公室里收到伯爵夫人的来信。信纸上有淡淡的薰衣草香。",
        key_events=["收到委托信", "了解案件基本情况", "决定前往庄园"],
        emotional_tone="神秘、引人入胜",
        next_nodes=["node_02"],
        facts_introduced=["伯爵在密室中死亡", "门窗从内部锁死"],
        witnesses=["mc"],
    )

    nodes["node_02"] = StoryNode(
        node_id="node_02", node_type=NodeType.NARRATIVE, title="抵达庄园", act=1,
        scene_description="侦探乘马车抵达郊外的庄园。管家在门口迎接，态度礼貌但有距离感。庄园内部装饰奢华但气氛压抑。",
        key_events=["到达庄园", "初见管家拉扎罗", "注意到庄园的异样"],
        emotional_tone="压抑、不安",
        next_nodes=["node_03"],
        prev_nodes=["node_01"],
        facts_introduced=["庄园内画作收藏丰富", "仆人们神色紧张"],
        witnesses=["mc", "lazaro"],
    )

    nodes["node_03"] = StoryNode(
        node_id="node_03", node_type=NodeType.NARRATIVE, title="初次问询", act=1,
        scene_description="在客厅中与伯爵夫人伊莎贝拉会面。她穿着黑色丧服，面容憔悴但冷静。提供了案件的基本信息，但某些问题她刻意回避。",
        key_events=["与伯爵夫人对话", "了解死亡现场细节", "注意到她的回避"],
        emotional_tone="紧张、试探",
        next_nodes=["node_04"],
        prev_nodes=["node_02"],
        facts_introduced=["伯爵生前收到威胁信", "钥匙在死者口袋"],
        witnesses=["mc", "isabella"],
    )

    nodes["node_04"] = StoryNode(
        node_id="node_04", node_type=NodeType.CHOICE, title="第一次选择：调查方向", act=1,
        scene_description="初步了解情况后，侦探需要决定先调查哪个方向。",
        key_events=["做出第一个调查决定"],
        emotional_tone="思考、抉择",
        choices=[
            ChoiceOption(
                option_id="opt_04a", text="先去检查密室现场",
                target_node_id="node_05a", branch_type=BranchType.PEARL_STRING,
                value_effects=[ValueEffect("clue_count", 1)],
                hint="发现现场的物理线索",
            ),
            ChoiceOption(
                option_id="opt_04b", text="先找仆人们问话",
                target_node_id="node_05b", branch_type=BranchType.PEARL_STRING,
                value_effects=[ValueEffect("trust", 1)],
                hint="获得人际关系线索",
            ),
        ],
        prev_nodes=["node_03"],
        facts_introduced=[],
        witnesses=["mc"],
    )

    # 珍珠串分支 - 不同调查方向但收束
    nodes["node_05a"] = StoryNode(
        node_id="node_05a", node_type=NodeType.NARRATIVE, title="密室勘察", act=1,
        branch_id="investigate_room",
        scene_description="书房密室保持原样。厚重的橡木门，铁锁完好。窗户上的插销从内部锁死。桌上散落着文件。",
        key_events=["检查门锁和窗户", "发现桌上的文件", "注意到壁炉旁的异样"],
        emotional_tone="专注、发现",
        next_nodes=["node_06"],
        prev_nodes=["node_04"],
        merge_to="node_06",
        facts_introduced=["壁炉通道可能容纳一个人", "桌上有一封未寄出的信"],
        witnesses=["mc"],
    )

    nodes["node_05b"] = StoryNode(
        node_id="node_05b", node_type=NodeType.NARRATIVE, title="仆人问话", act=1,
        branch_id="investigate_servants",
        scene_description="在仆人休息室逐一问话。大多数人闪烁其词。女仆艾米莉特别紧张，欲言又止。",
        key_events=["问话多名仆人", "注意到艾米莉的异常", "了解仆人间的关系"],
        emotional_tone="试探、观察",
        next_nodes=["node_06"],
        prev_nodes=["node_04"],
        merge_to="node_06",
        facts_introduced=["艾米莉似乎知道什么", "管家案发夜声称在房间休息"],
        witnesses=["mc", "emily"],
    )

    # ===== 第2幕：密室血案 =====
    nodes["node_06"] = StoryNode(
        node_id="node_06", node_type=NodeType.MERGE_POINT, title="线索汇合", act=2,
        scene_description="无论先调查哪个方向，此时侦探已掌握基本线索。在花园中独自整理思路时，警探威廉到来。",
        key_events=["威廉到场", "分享各自掌握的信息", "威廉提出不同看法"],
        emotional_tone="协作与摩擦",
        next_nodes=["node_07"],
        prev_nodes=["node_05a", "node_05b"],
        facts_introduced=["威廉调查到伯爵最近频繁出入码头"],
        witnesses=["mc", "william"],
    )

    nodes["node_07"] = StoryNode(
        node_id="node_07", node_type=NodeType.CHOICE, title="关键抉择：信任伯爵夫人", act=2,
        scene_description="伯爵夫人主动找到侦探，透露了一个惊人的信息——但需要侦探承诺保密。威廉建议不要相信她。",
        key_events=["伯爵夫人提出交易", "威廉表示反对", "侦探必须做出判断"],
        emotional_tone="紧张、信任危机",
        choices=[
            ChoiceOption(
                option_id="opt_07a", text="选择信任伯爵夫人，听她说",
                target_node_id="node_08a", branch_type=BranchType.STRONG,
                value_effects=[ValueEffect("trust", 2)],
                hint="开启信任线——获得关键真相但被卷入危险",
            ),
            ChoiceOption(
                option_id="opt_07b", text="拒绝她，跟威廉走官方路线",
                target_node_id="node_08b", branch_type=BranchType.STRONG,
                value_effects=[ValueEffect("trust", -1), ValueEffect("courage", 1)],
                hint="开启官方线——稳扎稳打但错过关键信息",
            ),
        ],
        prev_nodes=["node_06"],
        facts_introduced=["伯爵夫人愿意透露秘密"],
        witnesses=["mc", "isabella", "william"],
    )

    # ===== 强分支 A：信任线 =====
    nodes["node_08a"] = StoryNode(
        node_id="node_08a", node_type=NodeType.NARRATIVE, title="秘密揭露", act=2,
        branch_id="trust_line",
        scene_description="伯爵夫人带侦探到密室后的暗室。伯爵生前是地下铁路的组织者——帮助被压迫者逃离。画作是掩护。",
        key_events=["发现暗室", "了解伯爵的秘密身份", "伯爵夫人的真实面目"],
        emotional_tone="震惊、重新审视",
        next_nodes=["node_09a"],
        prev_nodes=["node_07"],
        facts_introduced=["伯爵是地下铁路组织者", "画作是秘密活动的掩护", "暗室的存在"],
        witnesses=["mc", "isabella"],
    )

    nodes["node_09a"] = StoryNode(
        node_id="node_09a", node_type=NodeType.CHOICE, title="深夜决定", act=2,
        branch_id="trust_line",
        scene_description="深夜，侦探独自在书房研究线索。听到地下室传来声响。",
        key_events=["听到异响", "决定是否独自调查"],
        emotional_tone="恐惧、抉择",
        choices=[
            ChoiceOption(
                option_id="opt_09a1", text="独自去地下室调查",
                target_node_id="dead_01", is_dead_end=True,
                value_effects=[ValueEffect("courage", 2)],
                hint="勇气有余，智慧不足——导致死结局",
            ),
            ChoiceOption(
                option_id="opt_09a2", text="先找到艾米莉问清楚再行动",
                target_node_id="node_10a",
                value_effects=[ValueEffect("clue_count", 1)],
                hint="谨慎路线——获得关键证词",
            ),
            ChoiceOption(
                option_id="opt_09a3", text="叫醒威廉一起去",
                target_node_id="node_10a",
                branch_type=BranchType.PEARL_STRING,
                value_effects=[ValueEffect("trust", -1), ValueEffect("courage", -1)],
                hint="安全但暴露了秘密",
            ),
        ],
        prev_nodes=["node_08a"],
    )

    # 死结局 1
    nodes["dead_01"] = StoryNode(
        node_id="dead_01", node_type=NodeType.DEAD_END, title="地下室的陷阱", act=2,
        branch_id="trust_line",
        death_cause="独自进入布满陷阱的地下室",
        death_description_hint="侦探推开地下室的门，脚下一空——台阶被拆除了。在坠落的瞬间，他看到黑暗中有双眼睛正在注视他。",
        prev_nodes=["node_09a"],
        facts_introduced=["地下室有人设了陷阱"],
        witnesses=["mc"],
    )

    # 信任线继续
    nodes["node_10a"] = StoryNode(
        node_id="node_10a", node_type=NodeType.NARRATIVE, title="艾米莉的证词", act=2,
        branch_id="trust_line",
        scene_description="找到艾米莉，她终于说出了真相——案发夜她看到管家从书房侧门离开，但管家声称自己一直在房间。",
        key_events=["获得关键证词", "管家的不在场证明被推翻", "艾米莉请求保护"],
        emotional_tone="突破、紧张",
        next_nodes=["node_11"],
        prev_nodes=["node_09a"],
        facts_introduced=["管家案发夜离开过书房", "管家撒了谎"],
        witnesses=["mc", "emily"],
    )

    # ===== 强分支 B：官方线 =====
    nodes["node_08b"] = StoryNode(
        node_id="node_08b", node_type=NodeType.NARRATIVE, title="官方调查", act=2,
        branch_id="official_line",
        scene_description="与威廉一起走程序。搜查庄园，找到伯爵的商业文件。发现伯爵与码头有大量可疑交易。",
        key_events=["搜查庄园", "找到商业文件", "发现码头交易记录"],
        emotional_tone="按部就班、逐步揭露",
        next_nodes=["node_09b"],
        prev_nodes=["node_07"],
        facts_introduced=["伯爵有大量码头交易", "交易对象是匿名的"],
        witnesses=["mc", "william"],
    )

    nodes["node_09b"] = StoryNode(
        node_id="node_09b", node_type=NodeType.CHOICE, title="审讯管家", act=2,
        branch_id="official_line",
        scene_description="威廉建议直接审讯管家拉扎罗。管家态度从容，但有破绽。",
        key_events=["审讯管家", "发现破绽"],
        emotional_tone="对峙、心理博弈",
        choices=[
            ChoiceOption(
                option_id="opt_09b1", text="用证据逼问，步步紧逼",
                target_node_id="node_10b",
                value_effects=[ValueEffect("courage", 1)],
                hint="获得部分真相但管家不会全说",
            ),
            ChoiceOption(
                option_id="opt_09b2", text="假装已经知道一切，套他的话",
                target_node_id="dead_02", is_dead_end=True,
                value_effects=[],
                hint="管家识破了诈术，触发反杀",
            ),
        ],
        prev_nodes=["node_08b"],
    )

    # 死结局 2
    nodes["dead_02"] = StoryNode(
        node_id="dead_02", node_type=NodeType.DEAD_END, title="识破的诈术", act=2,
        branch_id="official_line",
        death_cause="试图欺骗管家被识破",
        death_description_hint="管家嘴角微微上扬：'先生，您什么都不知道。'当晚，侦探的茶里被下了毒——永远沉睡在庄园的客房里。",
        prev_nodes=["node_09b"],
    )

    nodes["node_10b"] = StoryNode(
        node_id="node_10b", node_type=NodeType.NARRATIVE, title="部分真相", act=2,
        branch_id="official_line",
        scene_description="管家承认案发夜离开过房间，但声称是去处理一批'特殊货物'。他拒绝说明货物内容。",
        key_events=["管家部分坦白", "货物之谜", "威廉怀疑管家是凶手"],
        emotional_tone="突破但未完全",
        next_nodes=["node_11"],
        prev_nodes=["node_09b"],
        facts_introduced=["管家承认离开过房间", "存在'特殊货物'"],
        witnesses=["mc", "william", "lazaro"],
    )

    # ===== 第3幕：幽灵追踪（两线收束）=====
    nodes["node_11"] = StoryNode(
        node_id="node_11", node_type=NodeType.MERGE_POINT, title="线索交汇", act=3,
        scene_description="无论走哪条线，此时侦探都发现了管家的谎言。关键分歧在于是否知道伯爵的秘密身份。夜晚，庄园中发生了第二起事件——画作失踪了。",
        key_events=["画作失踪", "所有人被聚集", "紧张气氛升到顶点"],
        emotional_tone="危机、高潮前奏",
        next_nodes=["node_12"],
        prev_nodes=["node_10a", "node_10b"],
        facts_introduced=["画作失踪", "有人趁夜潜入"],
        witnesses=["mc", "isabella", "lazaro", "william", "emily"],
    )

    nodes["node_12"] = StoryNode(
        node_id="node_12", node_type=NodeType.CHOICE, title="最终追踪", act=3,
        scene_description="侦探推理出画作被藏在庄园某处。三个可能的地点：马厩阁楼、地下酒窖、花园假山。选错意味着让凶手逃脱。",
        key_events=["推理画作位置", "做出最终判断"],
        emotional_tone="紧迫、决断",
        choices=[
            ChoiceOption(
                option_id="opt_12a", text="马厩阁楼——管家经常去那里",
                target_node_id="dead_03", is_dead_end=True,
                hint="错误推理，中了调虎离山计",
            ),
            ChoiceOption(
                option_id="opt_12b", text="地下酒窖——与密室暗道相连",
                target_node_id="node_13",
                value_effects=[ValueEffect("clue_count", 2)],
                hint="正确！找到画作和关键证据",
            ),
            ChoiceOption(
                option_id="opt_12c", text="花园假山——伯爵夫人暗示过",
                target_node_id="dead_04", is_dead_end=True,
                hint="伯爵夫人的暗示是误导（或者她自己也被骗了）",
            ),
        ],
        prev_nodes=["node_11"],
    )

    # 死结局 3 & 4
    nodes["dead_03"] = StoryNode(
        node_id="dead_03", node_type=NodeType.DEAD_END, title="调虎离山", act=3,
        death_cause="被引诱到错误地点",
        death_description_hint="马厩阁楼空无一物。等侦探意识到上当时，身后的门已经被锁死，干草堆开始冒出浓烟。",
        prev_nodes=["node_12"],
    )

    nodes["dead_04"] = StoryNode(
        node_id="dead_04", node_type=NodeType.DEAD_END, title="花园陷阱", act=3,
        death_cause="被误导信息引入陷阱",
        death_description_hint="假山的机关被触发，侦探被困在坍塌的石块中。最后看到的是月光下一个熟悉的身影转身离去。",
        prev_nodes=["node_12"],
    )

    # 第3幕高潮
    nodes["node_13"] = StoryNode(
        node_id="node_13", node_type=NodeType.NARRATIVE, title="酒窖真相", act=3,
        scene_description="在地下酒窖中找到了画作——以及更多。暗道连接书房和酒窖，这就是密室杀人的手法。凶手通过暗道进入书房，杀人后锁门，再从暗道离开。",
        key_events=["找到画作", "发现暗道", "破解密室之谜", "确定凶手"],
        emotional_tone="震撼、恍然大悟",
        next_nodes=["node_14"],
        prev_nodes=["node_12"],
        facts_introduced=["暗道连接书房和酒窖", "密室杀人手法被破解"],
        witnesses=["mc"],
    )

    # ===== 第4幕：黎明审判 =====
    nodes["node_14"] = StoryNode(
        node_id="node_14", node_type=NodeType.CHOICE, title="最终指控", act=4,
        scene_description="所有人被召集到大厅。侦探准备指出真凶。但最终指控的方式会影响结局。",
        key_events=["召集所有人", "准备最终指控"],
        emotional_tone="庄严、决定性",
        choices=[
            ChoiceOption(
                option_id="opt_14a", text="公开揭露一切真相，包括伯爵的秘密",
                target_node_id="ending_01",
                value_effects=[ValueEffect("trust", -2)],
                hint="正义但代价沉重——伯爵的事业被曝光",
            ),
            ChoiceOption(
                option_id="opt_14b", text="只揭露凶手，保守伯爵的秘密",
                target_node_id="ending_02",
                value_effects=[ValueEffect("trust", 2)],
                hint="有所保留的正义——保护了无辜者",
            ),
            ChoiceOption(
                option_id="opt_14c", text="与伯爵夫人合作，让凶手'自首'",
                target_node_id="ending_03",
                value_effects=[ValueEffect("trust", 1), ValueEffect("courage", -1)],
                hint="灰色地带——正义与利益的妥协",
            ),
        ],
        prev_nodes=["node_13"],
    )

    # 结局
    nodes["ending_01"] = StoryNode(
        node_id="ending_01", node_type=NodeType.ENDING, title="真相大白", act=4,
        ending_type="true_ending",
        ending_condition="公开揭露一切",
        scene_description="所有真相被公之于众。凶手被捕，但伯爵的秘密事业也被摧毁。伯爵夫人悲痛欲绝，侦探在正义与代价之间无法释怀。",
        key_events=["凶手被捕", "秘密曝光", "伯爵夫人崩溃"],
        emotional_tone="苦涩的胜利",
        prev_nodes=["node_14"],
    )

    nodes["ending_02"] = StoryNode(
        node_id="ending_02", node_type=NodeType.ENDING, title="守护者", act=4,
        ending_type="good_ending",
        ending_condition="只揭露凶手，trust >= 2",
        scene_description="凶手被绳之以法，伯爵的秘密被侦探和伯爵夫人共同守护。正义得到了伸张，无辜者得到了保护。",
        key_events=["凶手认罪", "秘密被保守", "侦探获得信任"],
        emotional_tone="温暖、希望",
        prev_nodes=["node_14"],
    )

    nodes["ending_03"] = StoryNode(
        node_id="ending_03", node_type=NodeType.ENDING, title="灰色正义", act=4,
        ending_type="neutral",
        ending_condition="与伯爵夫人合作",
        scene_description="凶手在精心安排下'自首'。表面上正义得到伸张，但侦探知道这正义是打了折扣的。离开庄园时，他回头看了一眼，不确定自己是否做了对的事。",
        key_events=["安排自首", "侦探的道德拷问", "离开庄园"],
        emotional_tone="模糊、反思",
        prev_nodes=["node_14"],
    )

    # 构建分支
    branches = {
        "investigate_room": BranchArc(
            branch_id="investigate_room", branch_type=BranchType.PEARL_STRING,
            fork_node_id="node_04", merge_node_id="node_06",
            node_ids=["node_05a"],
            description="先去密室调查——获得物理线索",
        ),
        "investigate_servants": BranchArc(
            branch_id="investigate_servants", branch_type=BranchType.PEARL_STRING,
            fork_node_id="node_04", merge_node_id="node_06",
            node_ids=["node_05b"],
            description="先找仆人问话——获得人际线索",
        ),
        "trust_line": BranchArc(
            branch_id="trust_line", branch_type=BranchType.STRONG,
            fork_node_id="node_07", merge_node_id="node_11",
            node_ids=["node_08a", "node_09a", "node_10a"],
            description="信任伯爵夫人——获得秘密但卷入危险",
        ),
        "official_line": BranchArc(
            branch_id="official_line", branch_type=BranchType.STRONG,
            fork_node_id="node_07", merge_node_id="node_11",
            node_ids=["node_08b", "node_09b", "node_10b"],
            description="走官方路线——稳扎稳打但错过信息",
        ),
    }

    # 数值系统
    value_system = ValueSystem(
        attributes={"trust": 0, "courage": 0, "clue_count": 0},
        thresholds={
            "trust": {">=3": "解锁 good_ending", "<-1": "部分结局不可达"},
            "clue_count": {">=3": "额外推理线索可用"},
        },
        description="信任度影响结局分支，勇气影响特定选择的可用性，线索数影响推理深度",
    )

    # SP 配置
    sp = SPObfuscation(
        writing_style="novel",
        response_length="long",
        action_depth="rich",
        thought_depth="deep",
        environment_depth="immersive",
        sensory_depth="rich",
        paragraph_count="several",
        action_marker="none",
        dialogue_marker="quotes",
        register="literary",
    )

    graph = StoryGraph(
        story_id="detective_victoria_01",
        title="维多利亚密室",
        genre="悬疑推理",
        language="zh",
        total_acts=4,
        world_setting="1862年的伦敦，工业革命的烟尘笼罩着这座城市。贵族的庄园藏着不为人知的秘密，每个人都在面具下活着。",
        time_period="1862年·维多利亚时代",
        location="伦敦郊外·伯爵庄园",
        characters=characters,
        nodes=nodes,
        branches=branches,
        entry_node_id="node_01",
        value_system=value_system,
        sp_obfuscation=sp,
    )

    return graph


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Director Agent — Seed → Story Graph")
    parser.add_argument("--mode", choices=["offline", "llm"], default="offline",
                        help="offline=手写示例, llm=调用LLM生成")
    parser.add_argument("--seed-file", type=str, help="Seed 文件路径（llm 模式）")
    parser.add_argument("--output", type=str, default="output/story_graph.json",
                        help="输出文件路径")
    parser.add_argument("--model", type=str, default="claude-opus-4-5-20251101")
    parser.add_argument("--api-base", type=str, default="")
    parser.add_argument("--api-key", type=str, default="")

    args = parser.parse_args()

    if args.mode == "offline":
        print("[Director] 生成离线示例 Story Graph...")
        graph = generate_example_graph_offline()
    else:
        if not args.seed_file:
            print("Error: --seed-file required for llm mode")
            exit(1)
        with open(args.seed_file, "r") as f:
            seed = f.read()
        config = LLMConfig(
            model=args.model,
            api_base=args.api_base,
            api_key=args.api_key,
        )
        client = LLMClient(config)
        director = DirectorAgent(client)
        graph = director.generate(seed)

    # 验证
    issues = graph.validate()
    if issues:
        print(f"\n⚠️ 验证问题：")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ 图验证通过")

    # 输出
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        f.write(graph.to_json())
    print(f"\n📄 Story Graph 已保存到 {args.output}")
    print(f"📊 统计：{graph.stats}")
    print(f"\n📋 World Bible 预览：")
    print(graph.get_world_bible()[:500])
    print(f"\n🗺️ Graph Summary 预览：")
    print(graph.get_graph_summary()[:500])
