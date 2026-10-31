"""
Branch Writer + Dead End Worker + Pearl String Worker

从 StoryGraph 中提取局部上下文，并行生成各分支的叙事文本。
核心原则：每个 Writer 只看自己负责的局部 + 全局摘要，context 恒定大小。
"""

import json
import os
import re
import time
import concurrent.futures
from dataclasses import dataclass, field
from typing import Optional

from story_graph_schema import (
    StoryGraph, StoryNode, NodeType, BranchType, SPObfuscation
)


# ============================================================
# JSON 修复工具
# ============================================================

def _repair_json(raw: str) -> str:
    """尝试修复常见的 LLM JSON 输出问题"""
    # 去掉 markdown 代码块
    raw = raw.strip()
    if raw.startswith("```"):
        first_nl = raw.index("\n")
        last_fence = raw.rfind("```")
        if last_fence > first_nl:
            raw = raw[first_nl+1:last_fence].strip()

    # 提取最外层的 JSON 结构
    for open_ch, close_ch in [("[", "]"), ("{", "}")]:
        first = raw.find(open_ch)
        last = raw.rfind(close_ch)
        if first != -1 and last != -1 and last > first:
            raw = raw[first:last+1]
            break

    # 修复常见问题
    # 1. 控制字符（除了 \n \r \t）
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
    # 2. 尾逗号
    raw = re.sub(r',\s*([}\]])', r'\1', raw)

    return raw


def _fix_unescaped_quotes(json_str: str) -> str:
    """
    修复 JSON 字符串值内部未转义的双引号。
    LLM 常见问题：narrative_text 中用裸 " 做中文引号，如 给伯爵一个"公正的结论"
    应为 给伯爵一个\\"公正的结论\\"
    策略：迭代解析，每次修复 json.loads 报错位置前的未转义引号。
    """
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
                return json_str  # 其他类型的错误，无法修复

            pos = e.pos
            if pos is None or pos >= len(json_str):
                return json_str

            # 找到 pos 之前最近的未转义双引号，它是导致字符串提前结束的罪魁祸首
            last_q = json_str.rfind('"', 0, pos)
            if last_q > 0 and json_str[last_q - 1] != '\\':
                json_str = json_str[:last_q] + '\\"' + json_str[last_q + 1:]
            else:
                return json_str  # 找不到可修复的引号

    return json_str


def _parse_json_robust(raw: str) -> any:
    """健壮的 JSON 解析，多种策略"""
    if not raw or not raw.strip():
        raise json.JSONDecodeError("Empty response from LLM", "", 0)

    repaired = _repair_json(raw)

    # 调试日志
    print(f"  [JSON Debug] raw length={len(raw)}, repaired length={len(repaired)}, first 200 chars: {repaired[:200]!r}")

    # 策略 1：直接解析
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # 策略 2：修复字符串内未转义的双引号（LLM 常见问题）
    try:
        fixed = _fix_unescaped_quotes(repaired)
        result = json.loads(fixed)
        print(f"  [JSON Debug] 策略2(修复未转义引号)成功")
        return result
    except (json.JSONDecodeError, Exception):
        pass

    # 策略 3：截断修复（补齐缺失的括号）
    open_braces = repaired.count('{') - repaired.count('}')
    open_brackets = repaired.count('[') - repaired.count(']')
    if open_braces > 0 or open_brackets > 0:
        # 先去掉可能的不完整尾部
        last_complete = max(repaired.rfind('}'), repaired.rfind(']'))
        if last_complete > len(repaired) // 2:
            truncated = repaired[:last_complete+1]
            truncated += ']' * max(0, truncated.count('[') - truncated.count(']'))
            truncated += '}' * max(0, truncated.count('{') - truncated.count('}'))
            try:
                return json.loads(truncated)
            except json.JSONDecodeError:
                # 也尝试修复引号
                try:
                    fixed = _fix_unescaped_quotes(truncated)
                    result = json.loads(fixed)
                    print(f"  [JSON Debug] 策略3(截断+引号修复)成功")
                    return result
                except (json.JSONDecodeError, Exception):
                    pass

    # 策略 4：逐个对象解析（针对数组场景）
    objects = []
    depth = 0
    start = None
    for i, ch in enumerate(repaired):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                obj_str = repaired[start:i+1]
                try:
                    objects.append(json.loads(obj_str))
                except json.JSONDecodeError:
                    # 先尝试修复引号
                    try:
                        fixed = _fix_unescaped_quotes(obj_str)
                        objects.append(json.loads(fixed))
                    except (json.JSONDecodeError, Exception):
                        pass
                start = None
    if objects:
        return objects

    # 策略 5：正则修复字符串内换行符
    try:
        fixed = re.sub(
            r'(?<=": ")(.*?)(?="[,}\]])',
            lambda m: m.group(0).replace('\n', '\\n').replace('\r', '\\r'),
            repaired, flags=re.DOTALL
        )
        result = json.loads(fixed)
        print(f"  [JSON Debug] 策略5(正则修复换行符)成功")
        return result
    except (json.JSONDecodeError, Exception):
        pass

    raise json.JSONDecodeError("All repair strategies failed", repaired[:200], 0)


# ============================================================
# Writer Prompts
# ============================================================

BRANCH_WRITER_SYSTEM_PROMPT = """你是一位互动小说的分支写作者（Branch Writer）。你负责为故事的一个分支撰写完整的叙事文本。

## 绝对约束（不可违反）

**你必须严格按照 World Bible 中的设定写作。** 包括但不限于：
- 故事类型、时代背景、地理位置
- 角色姓名、身份、说话风格
- 世界观中的社会规则和氛围

**禁止跑题：** 不要引入 World Bible 中不存在的角色、不符合时代背景的元素、或与故事类型不匹配的情节。如果故事设定在 1862 年伦敦，就不能出现现代元素。

## 你的工作

你会收到以下信息：
1. **World Bible**：世界观、角色设定、基调（所有分支共享）——这是你的写作圣经，一切以此为准
2. **Graph Summary**：全局故事结构鸟瞰
3. **分支详情**：你负责的分支中每个节点的具体指令
4. **SP 配置**：写作风格要求

你的任务是为分支中的每个节点撰写叙事文本，包括：
- 场景描述和环境渲染
- 角色对话和互动
- 关键事件的展开
- 选择点的选项呈现

## 写作规则

1. **忠于 Graph**：每个节点的 key_events 必须全部出现，emotional_tone 必须贯穿。不要添加 Graph 中没有的重要剧情。

2. **信息边界**：角色只能说/做他们知道的事。检查 witnesses 列表——如果一个角色不在知情者列表中，他不能引用那个事实。

3. **连接流畅**：节点之间的过渡要自然。上一个节点结尾和下一个节点开头要能无缝衔接。

4. **选择点呈现**：
   - 选择点节点必须以明确的选项结尾
   - 每个选项用序号标注
   - 选项文本直接使用 Graph 中的 text 字段

5. **篇幅控制**：
   - 叙事节点：400-800 字
   - 选择点节点：200-400 字（不含选项）
   - 每个选项描述：保持 Graph 中的原文

## 风格要求

根据 SP 配置调整：
- writing_style：决定整体风格（chat/light_rp/standard_rp/novel/literary）
- action_depth：动作描写深度
- thought_depth：心理描写深度
- environment_depth：环境描写深度
- sensory_depth：感官描写丰富度
- register：语域（formal/neutral/colloquial/literary）

## 输出格式

输出一个 JSON 数组，每个元素对应一个节点：

```json
[
  {
    "node_id": "node_01",
    "title": "节点标题",
    "narrative_text": "完整的叙事文本...",
    "choices_text": [
      {"option_id": "opt_01a", "display_text": "选项1文本"},
      {"option_id": "opt_01b", "display_text": "选项2文本"}
    ]
  }
]
```

只输出 JSON，不要有任何其他文字。"""


DEAD_END_WRITER_SYSTEM_PROMPT = """你是互动小说的死结局写作者（Dead End Writer）。你负责撰写短小精悍的死结局文本。

## 绝对约束

**严格遵循故事的时代背景、类型和角色设定。** 死结局必须与故事世界观一致。

## 你的工作

每个死结局你会收到：
- 当前场景描述
- 角色状态
- 死因标签
- 死结局描述提示

## 写作规则

1. **简短有力**：5-10 行即可。死结局要有冲击力，不需要长篇大论。
2. **因果明确**：死因必须与之前的选择有直接因果关系。
3. **风格一致**：与整体故事风格保持一致。
4. **留有余味**：好的死结局让人想回去重新选择，而不是觉得被随机惩罚了。

## 输出格式

```json
{
  "node_id": "dead_01",
  "death_text": "死结局叙事文本..."
}
```

只输出 JSON。"""


PEARL_STRING_WRITER_SYSTEM_PROMPT = """你是互动小说的珍珠串变体写作者（Pearl String Writer）。你负责基于原版文本生成微变体。

## 绝对约束（不可违反）

**你必须严格保持原版文本的世界观设定。** 变体只改措辞和细节，不改时代背景、角色身份、故事类型。如果原版文本设定在 1862 年伦敦，变体也必须在 1862 年伦敦。

## 你的工作

珍珠串分支 = 选择不同但结果收束回主线。
你会收到：
- 原版文本（主线版本）
- 选择差异描述（用户选了不同选项）
- 收束节点

## 写作规则

1. **保持剧情走向不变**：关键事件和结果一样，只改措辞/氛围/细节。
2. **反映选择差异**：选择应该在文本中有所体现。比如选了"从左边走"，后续提到"之前走过的左侧通道"。
3. **篇幅一致**：变体文本长度与原版接近。
4. **收束自然**：变体的结尾要能自然衔接到收束节点。
5. **世界观一致**：角色名、地点、时代、语言风格必须与原版完全一致。

## 输出格式

```json
{
  "node_id": "node_05b",
  "variant_text": "变体叙事文本...",
  "based_on": "node_05a"
}
```

只输出 JSON。"""


# ============================================================
# Context Builder — 为 Writer 构建精确的输入 context
# ============================================================

class ContextBuilder:
    """从 StoryGraph 中为各 Writer 构建精确的上下文"""

    def __init__(self, graph: StoryGraph):
        self.graph = graph

    def build_branch_writer_context(self, branch_id: str) -> dict:
        """
        构建 Branch Writer 的上下文。
        恒定大小：world_bible + graph_summary + 本分支节点详情
        """
        world_bible = self.graph.get_world_bible()
        graph_summary = self.graph.get_graph_summary()

        # 获取分支节点
        if branch_id == "main":
            nodes = [n for n in self.graph.nodes.values() if n.branch_id == "main"]
        else:
            branch = self.graph.branches.get(branch_id)
            if not branch:
                raise ValueError(f"Branch {branch_id} not found")
            nodes = [self.graph.nodes[nid] for nid in branch.node_ids if nid in self.graph.nodes]

        # 构建节点详情
        nodes_detail = []
        for node in nodes:
            detail = {
                "node_id": node.node_id,
                "title": node.title,
                "act": node.act,
                "node_type": node.node_type.value,
                "scene_description": node.scene_description,
                "key_events": node.key_events,
                "emotional_tone": node.emotional_tone,
                "facts_introduced": node.facts_introduced,
                "witnesses": node.witnesses,
            }
            if node.choices:
                detail["choices"] = [
                    {"option_id": c.option_id, "text": c.text, "hint": c.hint}
                    for c in node.choices
                ]
            if node.merge_to:
                detail["merge_to"] = node.merge_to
            nodes_detail.append(detail)

        # SP 配置
        sp = self.graph.sp_obfuscation

        return {
            "world_bible": world_bible,
            "graph_summary": graph_summary,
            "branch_id": branch_id,
            "nodes": nodes_detail,
            "sp_config": {
                "writing_style": sp.writing_style,
                "response_length": sp.response_length,
                "action_depth": sp.action_depth,
                "thought_depth": sp.thought_depth,
                "environment_depth": sp.environment_depth,
                "sensory_depth": sp.sensory_depth,
                "register": sp.register,
            },
        }

    def build_dead_end_context(self, node_id: str) -> dict:
        """构建 Dead End Writer 的上下文。极轻量。"""
        node = self.graph.nodes.get(node_id)
        if not node or node.node_type != NodeType.DEAD_END:
            raise ValueError(f"Node {node_id} is not a dead_end")

        # 获取前驱节点的场景描述作为上下文
        prev_scene = ""
        if node.prev_nodes:
            prev = self.graph.nodes.get(node.prev_nodes[0])
            if prev:
                prev_scene = prev.scene_description

        return {
            "node_id": node.node_id,
            "title": node.title,
            "prev_scene": prev_scene,
            "death_cause": node.death_cause,
            "death_description_hint": node.death_description_hint,
            "emotional_tone": "恐惧、震撼",
            "genre": self.graph.genre,
        }

    def build_pearl_string_context(self, variant_node_id: str, original_node_id: str, original_text: str) -> dict:
        """构建 Pearl String Writer 的上下文。"""
        variant = self.graph.nodes.get(variant_node_id)
        original = self.graph.nodes.get(original_node_id)
        if not variant or not original:
            raise ValueError(f"Nodes not found: {variant_node_id} or {original_node_id}")

        return {
            "variant_node_id": variant_node_id,
            "original_node_id": original_node_id,
            "original_text": original_text,
            "variant_scene_description": variant.scene_description,
            "variant_key_events": variant.key_events,
            "merge_to": variant.merge_to,
            "choice_difference": f"用户选择了不同的选项，进入了 {variant.title} 路线而非 {original.title} 路线",
        }


# ============================================================
# Writers
# ============================================================

class BranchWriter:
    """Branch Writer: 为一个分支生成完整叙事文本"""

    def __init__(self, llm_client, graph: StoryGraph):
        self.llm = llm_client
        self.graph = graph
        self.ctx_builder = ContextBuilder(graph)

    def write_branch(self, branch_id: str, max_retries: int = 2) -> list[dict]:
        """
        生成一个分支的全部叙事文本，带重试。

        Returns:
            [{node_id, title, narrative_text, choices_text}, ...]
        """
        ctx = self.ctx_builder.build_branch_writer_context(branch_id)

        user_prompt = f"""请为以下分支撰写完整的叙事文本：

## World Bible
{ctx['world_bible']}

## 全局结构
{ctx['graph_summary']}

## 分支：{ctx['branch_id']}
节点详情：
{json.dumps(ctx['nodes'], ensure_ascii=False, indent=2)}

## 写作风格要求
{json.dumps(ctx['sp_config'], ensure_ascii=False, indent=2)}

请为每个节点生成叙事文本。确保输出是合法的 JSON 数组。narrative_text 中的换行用 \\n 表示。"""

        for attempt in range(max_retries + 1):
            print(f"[BranchWriter] 生成分支 {branch_id}（{len(ctx['nodes'])} 个节点，attempt {attempt+1}）...")
            raw = self.llm.call(BRANCH_WRITER_SYSTEM_PROMPT, user_prompt)
            print(f"  [Raw] length={len(raw) if raw else 0}")

            try:
                return _parse_json_robust(raw)
            except (json.JSONDecodeError, Exception) as e:
                print(f"  ⚠️ JSON 解析失败 (attempt {attempt+1}): {e}")
                # 保存失败的 raw output 供调试
                debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs", "debug")
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = os.path.join(debug_dir, f"branch_{branch_id}_attempt{attempt+1}.txt")
                with open(debug_path, "w") as df:
                    df.write(raw or "(empty)")
                if attempt < max_retries:
                    user_prompt = (
                        f"你上一次的输出不是合法的 JSON 数组。错误：{e}\n"
                        f"请严格输出 JSON 数组格式。注意：\n"
                        f"1. narrative_text 中的换行必须用 \\n 转义\n"
                        f"2. 双引号必须用 \\\" 转义\n"
                        f"3. 不要有尾逗号\n\n"
                        f"分支 {branch_id} 的节点：\n"
                        + json.dumps([n['node_id'] for n in ctx['nodes']], ensure_ascii=False)
                    )

        raise ValueError(f"BranchWriter 生成分支 {branch_id} 失败（{max_retries+1} 次尝试）")


class DeadEndWriter:
    """Dead End Worker: 批量生成死结局文本"""

    def __init__(self, llm_client, graph: StoryGraph):
        self.llm = llm_client
        self.graph = graph
        self.ctx_builder = ContextBuilder(graph)

    def write_dead_end(self, node_id: str) -> dict:
        """生成单个死结局文本"""
        ctx = self.ctx_builder.build_dead_end_context(node_id)

        user_prompt = f"""请为以下死结局撰写文本：

故事类型：{ctx['genre']}
前置场景：{ctx['prev_scene']}
死因：{ctx['death_cause']}
描述提示：{ctx['death_description_hint']}

请生成 5-10 行的死结局文本。确保输出是合法的 JSON。"""

        print(f"[DeadEndWriter] 生成死结局 {node_id}...")
        raw = self.llm.call(DEAD_END_WRITER_SYSTEM_PROMPT, user_prompt)
        print(f"  [Raw] length={len(raw) if raw else 0}")

        return _parse_json_robust(raw)

    def write_all_dead_ends(self, max_workers: int = 5) -> list[dict]:
        """批量并行生成所有死结局"""
        dead_end_ids = [
            nid for nid, node in self.graph.nodes.items()
            if node.node_type == NodeType.DEAD_END
        ]

        if not dead_end_ids:
            print("[DeadEndWriter] 没有死结局需要生成")
            return []

        print(f"[DeadEndWriter] 共 {len(dead_end_ids)} 个死结局，并行生成中...")

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.write_dead_end, nid): nid
                for nid in dead_end_ids
            }
            for future in concurrent.futures.as_completed(futures):
                nid = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"  ✅ {nid} 完成")
                except Exception as e:
                    print(f"  ❌ {nid} 失败: {e}")
                    results.append({"node_id": nid, "death_text": f"[生成失败: {e}]"})

        return results


class PearlStringWriter:
    """Pearl String Worker: 生成珍珠串变体文本"""

    def __init__(self, llm_client, graph: StoryGraph):
        self.llm = llm_client
        self.graph = graph
        self.ctx_builder = ContextBuilder(graph)

    def write_variant(
        self,
        variant_node_id: str,
        original_node_id: str,
        original_text: str,
    ) -> dict:
        """基于原版生成珍珠串变体"""
        ctx = self.ctx_builder.build_pearl_string_context(
            variant_node_id, original_node_id, original_text
        )

        user_prompt = f"""请基于原版文本生成珍珠串变体：

## 原版文本（{ctx['original_node_id']}）
{ctx['original_text']}

## 变体要求
- 变体节点：{ctx['variant_node_id']}
- 场景描述：{ctx['variant_scene_description']}
- 关键事件：{json.dumps(ctx['variant_key_events'], ensure_ascii=False)}
- 选择差异：{ctx['choice_difference']}
- 收束到：{ctx['merge_to']}

保持剧情走向不变，只改措辞/氛围/细节以反映不同的选择。"""

        print(f"[PearlStringWriter] 生成变体 {variant_node_id}...")
        raw = self.llm.call(PEARL_STRING_WRITER_SYSTEM_PROMPT, user_prompt)

        return _parse_json_robust(raw)


# ============================================================
# Offline Writer (不调 LLM，手写叙事文本用于测试)
# ============================================================

def write_offline_narratives(graph: StoryGraph) -> dict:
    """
    离线生成所有叙事文本（手写模板），用于验证 Pipeline 流程。
    Returns: {node_id: {narrative_text, choices_text?, death_text?}}
    """
    results = {}

    for nid, node in graph.nodes.items():
        entry = {"node_id": nid, "title": node.title}

        if node.node_type == NodeType.DEAD_END:
            entry["death_text"] = (
                node.death_description_hint
                or f"[死结局：{node.death_cause}] 故事在此结束。"
            )
        elif node.node_type == NodeType.ENDING:
            entry["narrative_text"] = (
                f"【{node.ending_type}】\n"
                f"{node.scene_description}\n\n"
                + "\n".join(f"- {e}" for e in node.key_events)
            )
        elif node.node_type == NodeType.CHOICE:
            entry["narrative_text"] = node.scene_description
            entry["choices_text"] = [
                {"option_id": c.option_id, "display_text": c.text}
                for c in node.choices
            ]
        else:
            entry["narrative_text"] = (
                f"{node.scene_description}\n\n"
                + "\n".join(f"· {e}" for e in node.key_events)
            )

        results[nid] = entry

    return results


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Branch Writer — Story Graph → Narrative Text")
    parser.add_argument("--graph", type=str, required=True, help="Story Graph JSON 文件路径")
    parser.add_argument("--mode", choices=["offline", "llm"], default="offline")
    parser.add_argument("--output", type=str, default="output/narratives.json")
    parser.add_argument("--branch", type=str, help="只生成指定分支（默认全部）")

    args = parser.parse_args()

    # 加载 graph
    with open(args.graph, "r") as f:
        data = json.load(f)
    graph = StoryGraph.from_dict(data)
    print(f"[Writer] 加载 Story Graph：{graph.title}，{graph.stats}")

    if args.mode == "offline":
        print("[Writer] 离线模式——生成模板文本...")
        results = write_offline_narratives(graph)
    else:
        raise NotImplementedError("LLM 模式需要配置 API")

    # 保存
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📄 叙事文本已保存到 {args.output}")
    print(f"📊 共生成 {len(results)} 个节点的文本")
