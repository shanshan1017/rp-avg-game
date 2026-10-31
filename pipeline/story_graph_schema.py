"""
Story Graph Schema — 互动小说的结构化数据模型

Director Agent 输出此结构，下游 Writer 消费。
核心原则：结构化数据而非叙事文本，让 Writer 能精确索引自己需要的信息。
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import json


class NodeType(str, Enum):
    """节点类型"""
    NARRATIVE = "narrative"       # 纯叙事节点（无选择）
    CHOICE = "choice"             # 选择点（用户做决定）
    DEAD_END = "dead_end"         # 死结局
    ENDING = "ending"             # 正常结局
    BRANCH_POINT = "branch_point" # 强分支分叉点
    MERGE_POINT = "merge_point"   # 收束点（珍珠串回归主线）


class BranchType(str, Enum):
    """分支类型"""
    PEARL_STRING = "pearl_string"   # 珍珠串：选择不同但收束回主线
    STRONG = "strong"               # 强分支：完全不同的世界线
    VALUE_BASED = "value_based"     # 数值分支：影响隐藏数值，不改变走向


@dataclass
class ValueEffect:
    """数值影响"""
    attribute: str       # 属性名（如：trust, courage, clue_count）
    delta: int           # 变化量（正/负）


@dataclass
class ChoiceOption:
    """选择点的一个选项"""
    option_id: str                 # 选项 ID（如 "opt_1a"）
    text: str                      # 选项文本（呈现给用户的措辞）
    target_node_id: str            # 跳转目标节点 ID
    is_dead_end: bool = False      # 是否导致死结局
    branch_type: BranchType = BranchType.PEARL_STRING
    value_effects: list[ValueEffect] = field(default_factory=list)
    hint: str = ""                 # 给 Writer 的提示（不展示给用户）
    gate_condition: Optional[dict] = None   # 数值门控条件（如 {"clues": ">=5"}）
    gate_branch: Optional[dict] = None      # 条件分支路由（如 {"condition": {...}, "true_target": ..., "false_target": ...}）
    locked_hint: str = ""          # 条件不满足时的提示文本


@dataclass
class StoryNode:
    """故事图中的一个节点"""
    node_id: str                    # 唯一标识（如 "node_01"）
    node_type: NodeType             # 节点类型
    title: str                      # 节点标题（如 "雾都初临"）
    act: int                        # 所属幕（1-4）
    branch_id: str = "main"         # 所属分支 ID（主线="main"）

    # 叙事内容指引（给 Writer 的指令，不是最终文本）
    scene_description: str = ""     # 场景描述
    key_events: list[str] = field(default_factory=list)    # 本节点必须发生的关键事件
    emotional_tone: str = ""        # 情感基调（如 "紧张悬疑"、"温馨回忆"）
    pov_character: str = ""         # 视角角色（默认主角）

    # 选择点特有
    choices: list[ChoiceOption] = field(default_factory=list)

    # 死结局特有
    death_cause: str = ""           # 死因标签（如 "信任了错误的人"）
    death_description_hint: str = "" # 死结局描述提示

    # 结局特有
    ending_type: str = ""           # 结局类型（如 "true_ending"、"bad_ending"、"neutral"）
    ending_condition: str = ""      # 达成条件描述

    # 图结构
    next_nodes: list[str] = field(default_factory=list)    # 后继节点 ID
    prev_nodes: list[str] = field(default_factory=list)    # 前驱节点 ID
    merge_to: str = ""              # 收束目标（珍珠串分支用）
    auto_route: Optional[dict] = None  # 条件路由（如 {"branch_a": "node_x", "branch_b": "node_y"}）

    # 信息边界（Auditor 用）
    facts_introduced: list[str] = field(default_factory=list)  # 本节点引入的新事实
    witnesses: list[str] = field(default_factory=list)          # 知情者列表


@dataclass
class Character:
    """角色定义"""
    char_id: str
    name: str
    role: str              # 主角/NPC/反派/配角
    description: str       # 外貌+性格
    speech_style: str      # 说话风格
    hidden_agenda: str = ""  # 隐藏动机（Fate 系统）
    knowledge: list[str] = field(default_factory=list)  # 初始已知事实


@dataclass
class ValueSystem:
    """数值系统定义"""
    attributes: dict = field(default_factory=dict)  # 属性名 → 初始值或详细配置
    thresholds: dict[str, dict] = field(default_factory=dict)  # 属性名 → {阈值: 效果}
    description: str = ""  # 数值系统说明
    routing_rules: list = field(default_factory=list)  # 条件路由规则列表


@dataclass
class BranchArc:
    """分支弧线"""
    branch_id: str          # 分支 ID（如 "branch_detective"）
    branch_type: BranchType
    fork_node_id: str       # 从哪个节点分叉
    merge_node_id: str = "" # 收束到哪个节点（强分支可能没有）
    node_ids: list[str] = field(default_factory=list)  # 本分支包含的节点序列
    description: str = ""   # 分支概述


@dataclass
class SPObfuscation:
    """SP 混淆配置（复用旧版系统的维度）"""
    writing_style: str = "standard_rp"    # chat/light_rp/standard_rp/novel/literary
    response_length: str = "long"         # medium/long/very_long
    action_depth: str = "rich"            # none/minimal/normal/rich/literary
    thought_depth: str = "moderate"       # none/subtle/moderate/deep
    environment_depth: str = "immersive"  # none/brief/moderate/immersive
    sensory_depth: str = "rich"           # none/occasional/rich
    paragraph_count: str = "several"      # single/few/several
    action_marker: str = "asterisk"       # asterisk/parenthesis/bracket/angle/none
    dialogue_marker: str = "quotes"       # quotes/guillemet/chinese_quotes/none
    register: str = "neutral"             # formal/neutral/colloquial/literary


@dataclass
class StoryGraph:
    """完整的故事图 — Director Agent 的输出"""

    # 元数据
    story_id: str
    title: str
    genre: str                 # 类型（悬疑/恐怖/奇幻/言情等）
    language: str = "zh"       # 语言
    total_acts: int = 4        # 总幕数

    # 世界观
    world_setting: str = ""    # 世界观描述
    time_period: str = ""      # 时代背景
    location: str = ""         # 地点

    # 角色
    characters: list[Character] = field(default_factory=list)

    # 图结构
    nodes: dict[str, StoryNode] = field(default_factory=dict)      # node_id → StoryNode
    branches: dict[str, BranchArc] = field(default_factory=dict)   # branch_id → BranchArc
    entry_node_id: str = ""    # 入口节点

    # 分支系统
    value_system: Optional[ValueSystem] = None

    # SP 配置
    sp_obfuscation: SPObfuscation = field(default_factory=SPObfuscation)

    # 统计（自动计算）
    @property
    def stats(self) -> dict:
        node_types = {}
        for n in self.nodes.values():
            node_types[n.node_type] = node_types.get(n.node_type, 0) + 1
        return {
            "total_nodes": len(self.nodes),
            "node_types": node_types,
            "total_branches": len(self.branches),
            "total_characters": len(self.characters),
        }

    def to_dict(self) -> dict:
        """序列化为 dict（可 JSON 化）"""
        def _ser(obj):
            if hasattr(obj, '__dataclass_fields__'):
                d = {}
                for f in obj.__dataclass_fields__:
                    v = getattr(obj, f)
                    d[f] = _ser(v)
                return d
            elif isinstance(obj, list):
                return [_ser(i) for i in obj]
            elif isinstance(obj, dict):
                return {k: _ser(v) for k, v in obj.items()}
            elif isinstance(obj, Enum):
                return obj.value
            else:
                return obj
        return _ser(self)

    def to_json(self, indent=2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "StoryGraph":
        """从 dict 反序列化"""
        # 构建角色
        characters = []
        for c in data.get("characters", []):
            characters.append(Character(**c))

        # 构建节点
        nodes = {}
        for nid, ndata in data.get("nodes", {}).items():
            # 处理嵌套对象
            choices = []
            for ch in (ndata.get("choices") or []):
                ve = [ValueEffect(**v) for v in (ch.get("value_effects") or [])]
                ch_copy = {k: v for k, v in ch.items() if k != "value_effects"}
                ch_copy["value_effects"] = ve
                if "branch_type" in ch_copy:
                    ch_copy["branch_type"] = BranchType(ch_copy["branch_type"])
                choices.append(ChoiceOption(**ch_copy))

            ndata_clean = {k: v for k, v in ndata.items() if k not in ("choices",)}
            # 处理 LLM 返回 null 的 list 字段
            for list_field in ("next_nodes", "prev_nodes", "key_events", "facts_introduced", "witnesses"):
                if list_field in ndata_clean and ndata_clean[list_field] is None:
                    ndata_clean[list_field] = []
            if "node_type" in ndata_clean:
                ndata_clean["node_type"] = NodeType(ndata_clean["node_type"])
            ndata_clean["choices"] = choices
            nodes[nid] = StoryNode(**ndata_clean)

        # 构建分支
        branches = {}
        for bid, bdata in data.get("branches", {}).items():
            if "branch_type" in bdata:
                bdata["branch_type"] = BranchType(bdata["branch_type"])
            branches[bid] = BranchArc(**bdata)

        # 构建数值系统
        vs_data = data.get("value_system")
        value_system = ValueSystem(**vs_data) if vs_data else None

        # 构建 SP 配置
        sp_data = data.get("sp_obfuscation", {})
        sp = SPObfuscation(**sp_data) if sp_data else SPObfuscation()

        return cls(
            story_id=data["story_id"],
            title=data["title"],
            genre=data["genre"],
            language=data.get("language", "zh"),
            total_acts=data.get("total_acts", 4),
            world_setting=data.get("world_setting", ""),
            time_period=data.get("time_period", ""),
            location=data.get("location", ""),
            characters=characters,
            nodes=nodes,
            branches=branches,
            entry_node_id=data.get("entry_node_id", ""),
            value_system=value_system,
            sp_obfuscation=sp,
        )

    def get_branch_nodes(self, branch_id: str) -> list[StoryNode]:
        """获取某分支的所有节点（按序）"""
        if branch_id not in self.branches:
            return []
        return [self.nodes[nid] for nid in self.branches[branch_id].node_ids if nid in self.nodes]

    def get_main_line(self) -> list[StoryNode]:
        """获取主线节点"""
        return [n for n in self.nodes.values() if n.branch_id == "main"]

    def validate(self) -> list[str]:
        """验证图的完整性，返回问题列表"""
        issues = []

        # 1. 入口节点存在
        if not self.entry_node_id or self.entry_node_id not in self.nodes:
            issues.append(f"入口节点 '{self.entry_node_id}' 不存在")

        # 2. 选择点必须有选项
        for nid, node in self.nodes.items():
            if node.node_type == NodeType.CHOICE and not node.choices:
                issues.append(f"选择点 {nid} 没有选项")

        # 3. 选项目标节点必须存在
        for nid, node in self.nodes.items():
            for ch in node.choices:
                if ch.target_node_id not in self.nodes:
                    issues.append(f"选项 {ch.option_id} 的目标节点 {ch.target_node_id} 不存在")

        # 4. 无孤立节点（除入口外，每个节点应有前驱）
        for nid, node in self.nodes.items():
            if nid != self.entry_node_id and not node.prev_nodes:
                issues.append(f"节点 {nid} 是孤立节点（无前驱）")

        # 5. 死结局必须有死因
        for nid, node in self.nodes.items():
            if node.node_type == NodeType.DEAD_END and not node.death_cause:
                issues.append(f"死结局 {nid} 缺少死因标签")

        # 6. 分支中的节点必须存在
        for bid, branch in self.branches.items():
            for nid in branch.node_ids:
                if nid not in self.nodes:
                    issues.append(f"分支 {bid} 引用了不存在的节点 {nid}")

        # 7-12: 结构性质量检查（可泛化到任何 story graph）
        issues.extend(self._check_pseudo_choices())
        issues.extend(self._check_funnel_convergence())
        issues.extend(self._check_value_system_usage())
        issues.extend(self._check_ending_diversity())
        issues.extend(self._check_dead_end_connectivity())
        issues.extend(self._check_choice_impact())

        return issues

    def _check_pseudo_choices(self) -> list[str]:
        """检查伪选择：所有选项指向同一节点且 value_effects 微弱"""
        issues = []
        for nid, node in self.nodes.items():
            if len(node.choices) < 2:
                continue
            targets = {ch.target_node_id for ch in node.choices}
            if len(targets) == 1:
                max_delta = max(
                    (abs(ve.delta) for ch in node.choices for ve in ch.value_effects),
                    default=0,
                )
                if max_delta <= 1:
                    issues.append(
                        f"[伪选择] {nid}: 所有 {len(node.choices)} 个选项都指向 "
                        f"{targets.pop()}，且最大 value_effect delta={max_delta}≤1，"
                        f"选择无实质影响"
                    )
        return issues

    def _check_funnel_convergence(self) -> list[str]:
        """检查漏斗收束：分支后立即合流且合流后无差异化"""
        issues = []
        for nid, node in self.nodes.items():
            if len(node.choices) < 2:
                continue
            targets = {ch.target_node_id for ch in node.choices}
            if len(targets) < 2:
                continue
            merge_targets = set()
            for tid in targets:
                tnode = self.nodes.get(tid)
                if tnode and tnode.next_nodes:
                    merge_targets.update(tnode.next_nodes)
            if len(merge_targets) == 1:
                merge_id = merge_targets.pop()
                merge_node = self.nodes.get(merge_id)
                if merge_node and not getattr(merge_node, 'auto_route', None):
                    has_different_facts = False
                    fact_sets = []
                    for tid in targets:
                        tnode = self.nodes.get(tid)
                        if tnode:
                            fact_sets.append(set(tnode.facts_introduced))
                    if len(fact_sets) >= 2 and fact_sets[0] != fact_sets[1]:
                        has_different_facts = True
                    if not has_different_facts:
                        issues.append(
                            f"[漏斗收束] {nid} 的分支 {targets} 全部收束到 "
                            f"{merge_id}，且无 auto_route 分化、无差异化 facts"
                        )
        return issues

    def _check_value_system_usage(self) -> list[str]:
        """检查 value_system 是否被实际引用"""
        issues = []
        if not self.value_system or not self.value_system.attributes:
            return issues

        defined_attrs = set(self.value_system.attributes.keys())

        used_in_effects = set()
        for node in self.nodes.values():
            for ch in node.choices:
                for ve in ch.value_effects:
                    used_in_effects.add(ve.attribute)

        unused = defined_attrs - used_in_effects
        if unused:
            issues.append(
                f"[数值空转] value_system 定义了属性 {unused}，"
                f"但没有任何选项的 value_effects 引用它们"
            )

        endings = [n for n in self.nodes.values()
                   if n.node_type == NodeType.ENDING]
        endings_without_condition = [
            n.node_id for n in endings if not n.ending_condition
        ]
        if endings_without_condition and defined_attrs:
            issues.append(
                f"[结局未门控] 结局 {endings_without_condition} 没有 ending_condition，"
                f"数值系统无法影响结局分流"
            )

        return issues

    def _check_ending_diversity(self) -> list[str]:
        """检查结局多样性"""
        issues = []
        endings = [n for n in self.nodes.values()
                   if n.node_type == NodeType.ENDING]
        if len(endings) < 3:
            issues.append(
                f"[结局不足] 仅有 {len(endings)} 个正常结局（建议≥3），"
                f"选择差异化空间不足"
            )

        ending_types = {n.ending_type for n in endings if n.ending_type}
        if len(ending_types) <= 1 and len(endings) > 1:
            issues.append(
                f"[结局同质] {len(endings)} 个结局但只有 {len(ending_types)} 种 "
                f"ending_type，缺乏差异化"
            )

        last_choice_only = True
        for nid, node in self.nodes.items():
            if node.choices:
                targets = {ch.target_node_id for ch in node.choices}
                ending_targets = {t for t in targets
                                  if t in self.nodes and
                                  self.nodes[t].node_type == NodeType.ENDING}
                non_ending_targets = targets - ending_targets
                if ending_targets and non_ending_targets:
                    continue
                if ending_targets and not non_ending_targets:
                    if len(node.prev_nodes) > 0:
                        prev_has_choice = any(
                            self.nodes.get(p) and self.nodes[p].choices
                            for p in node.prev_nodes
                        )
                        if not prev_has_choice:
                            last_choice_only = True

        return issues

    def _check_dead_end_connectivity(self) -> list[str]:
        """检查死结局是否有合法的入口路径"""
        issues = []
        for nid, node in self.nodes.items():
            if node.node_type != NodeType.DEAD_END:
                continue
            if not node.prev_nodes:
                issues.append(f"[死结局断连] {nid} 没有 prev_nodes，无法到达")
                continue
            actually_connected = False
            for prev_id in node.prev_nodes:
                prev = self.nodes.get(prev_id)
                if prev and nid in prev.next_nodes:
                    actually_connected = True
                    break
            if not actually_connected:
                issues.append(
                    f"[死结局断连] {nid} 声明 prev_nodes={node.prev_nodes}，"
                    f"但这些前驱节点的 next_nodes 均未包含 {nid}"
                )
        return issues

    def _check_choice_impact(self) -> list[str]:
        """检查选择是否有实质性数值影响"""
        issues = []
        choice_nodes = [n for n in self.nodes.values() if n.choices]
        if not choice_nodes:
            return issues

        no_effect_count = 0
        for node in choice_nodes:
            has_any_effect = any(ch.value_effects for ch in node.choices)
            if not has_any_effect:
                no_effect_count += 1

        ratio = no_effect_count / len(choice_nodes) if choice_nodes else 0
        if ratio > 0.5:
            issues.append(
                f"[数值影响不足] {no_effect_count}/{len(choice_nodes)} 个选择点 "
                f"({ratio:.0%}) 没有任何 value_effects，前期选择对后续无数值积累"
            )
        return issues

    def get_world_bible(self) -> str:
        """生成 World Bible（给 Writer 的世界观摘要）"""
        lines = []
        lines.append(f"【故事】{self.title}")
        lines.append(f"【类型】{self.genre}")
        lines.append(f"【时代】{self.time_period}")
        lines.append(f"【地点】{self.location}")
        lines.append(f"【世界观】{self.world_setting}")
        lines.append("")
        lines.append("【角色表】")
        for c in self.characters:
            lines.append(f"- {c.name}（{c.role}）：{c.description}")
            if c.speech_style:
                lines.append(f"  说话风格：{c.speech_style}")
            if c.hidden_agenda:
                lines.append(f"  隐藏动机：{c.hidden_agenda}")
        return "\n".join(lines)

    def get_graph_summary(self) -> str:
        """生成图结构摘要（给 Writer 的全局鸟瞰）"""
        lines = []
        lines.append(f"总节点数：{len(self.nodes)}")
        lines.append(f"分支数：{len(self.branches)}")
        lines.append("")
        lines.append("【主线骨架】")
        main_nodes = sorted(
            [n for n in self.nodes.values() if n.branch_id == "main"],
            key=lambda n: n.node_id
        )
        for n in main_nodes:
            suffix = ""
            if n.node_type == NodeType.CHOICE:
                suffix = f" [选择点: {len(n.choices)}个选项]"
            elif n.node_type == NodeType.BRANCH_POINT:
                suffix = " [分支点]"
            elif n.node_type == NodeType.ENDING:
                suffix = f" [结局: {n.ending_type}]"
            lines.append(f"  {n.node_id}: {n.title} (第{n.act}幕){suffix}")

        if self.branches:
            lines.append("")
            lines.append("【分支概览】")
            for bid, br in self.branches.items():
                lines.append(f"  {bid} ({br.branch_type.value}): {br.description}")
                lines.append(f"    分叉于 {br.fork_node_id}" + (f" → 收束于 {br.merge_node_id}" if br.merge_node_id else " → 独立结局"))

        return "\n".join(lines)
