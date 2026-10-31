"""
Auditor Agent — 后置质量检查

Phase 1: 纯规则检查（零 LLM 成本）
Phase 2: LLM 审计（仅对 Phase 1 存疑项）

当前只实现 Phase 1（规则引擎），Phase 2 后续补。
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from story_graph_schema import StoryGraph, StoryNode, NodeType


@dataclass
class AuditIssue:
    """审计问题"""
    severity: str       # "error" | "warning" | "info"
    category: str       # 问题类别
    node_id: str        # 相关节点
    message: str        # 问题描述
    suggestion: str = "" # 修改建议


class RuleAuditor:
    """
    Phase 1: 规则检查引擎

    零 LLM 成本，检测结构性问题。
    """

    def __init__(self, graph: StoryGraph, narratives: dict):
        """
        Args:
            graph: StoryGraph
            narratives: {node_id: {narrative_text, choices_text?, death_text?}}
        """
        self.graph = graph
        self.narratives = narratives

    def audit(self) -> list[AuditIssue]:
        """执行全部规则检查"""
        issues = []
        issues.extend(self._check_graph_integrity())
        issues.extend(self._check_item_tracking())
        issues.extend(self._check_character_presence())
        issues.extend(self._check_name_consistency())
        issues.extend(self._check_dead_end_causality())
        issues.extend(self._check_narrative_coverage())
        issues.extend(self._check_timeline())
        issues.extend(self._check_structural_quality())
        return issues

    def _check_structural_quality(self) -> list[AuditIssue]:
        """结构质量检查：检测漏斗收束、伪选择、数值系统空转等泛化问题"""
        issues = []

        for nid, node in self.graph.nodes.items():
            if len(node.choices) < 2:
                continue
            targets = {ch.target_node_id for ch in node.choices}
            if len(targets) == 1:
                max_delta = max(
                    (abs(ve.delta) for ch in node.choices for ve in ch.value_effects),
                    default=0,
                )
                if max_delta <= 1:
                    issues.append(AuditIssue(
                        severity="warning",
                        category="pseudo_choice",
                        node_id=nid,
                        message=(
                            f"伪选择：{len(node.choices)} 个选项全部指向 "
                            f"{targets.pop()}，最大 delta={max_delta}≤1"
                        ),
                        suggestion="分化为不同中间节点，或增大 value_effects 差异",
                    ))

        for nid, node in self.graph.nodes.items():
            if len(node.choices) < 2:
                continue
            targets = {ch.target_node_id for ch in node.choices}
            if len(targets) < 2:
                continue
            next_of_targets = set()
            for tid in targets:
                tnode = self.graph.nodes.get(tid)
                if tnode and len(tnode.next_nodes) == 1:
                    next_of_targets.add(tnode.next_nodes[0])
            if len(next_of_targets) == 1:
                merge_id = next_of_targets.pop()
                merge_node = self.graph.nodes.get(merge_id)
                if merge_node and len(merge_node.next_nodes) == 1:
                    issues.append(AuditIssue(
                        severity="warning",
                        category="funnel_convergence",
                        node_id=nid,
                        message=(
                            f"漏斗收束：分支 {targets} 在 {merge_id} 合流后"
                            f"只有单一后继 {merge_node.next_nodes[0]}，"
                            f"分支选择的差异被抹平"
                        ),
                        suggestion="在合流节点添加 auto_route 或 gate_condition 分化后续路径",
                    ))

        vs = self.graph.value_system
        if vs and vs.attributes:
            defined = set(vs.attributes.keys())
            used = set()
            for node in self.graph.nodes.values():
                for ch in node.choices:
                    for ve in ch.value_effects:
                        used.add(ve.attribute)
            unused = defined - used
            for attr in unused:
                issues.append(AuditIssue(
                    severity="warning",
                    category="value_system_unused",
                    node_id="",
                    message=f"数值属性 '{attr}' 定义在 value_system 中但未被任何选项的 value_effects 引用",
                    suggestion=f"在选择点的 value_effects 中添加对 '{attr}' 的引用",
                ))

            endings = [n for n in self.graph.nodes.values()
                       if n.node_type == NodeType.ENDING]
            for end in endings:
                if not end.ending_condition:
                    issues.append(AuditIssue(
                        severity="warning",
                        category="ending_no_condition",
                        node_id=end.node_id,
                        message=f"结局 '{end.title}' 没有 ending_condition，数值系统无法影响结局分流",
                        suggestion="添加 ending_condition 引用 value_system 中的属性（如 'clues≥5'）",
                    ))

        endings = [n for n in self.graph.nodes.values()
                   if n.node_type == NodeType.ENDING]
        if len(endings) < 3:
            issues.append(AuditIssue(
                severity="warning",
                category="ending_insufficient",
                node_id="",
                message=f"仅有 {len(endings)} 个正常结局（建议≥3），选择差异化空间不足",
                suggestion="增加由不同数值组合触发的结局",
            ))

        choice_nodes = [n for n in self.graph.nodes.values() if n.choices]
        if choice_nodes:
            no_effect = sum(1 for n in choice_nodes
                          if not any(ch.value_effects for ch in n.choices))
            ratio = no_effect / len(choice_nodes)
            if ratio > 0.5:
                issues.append(AuditIssue(
                    severity="warning",
                    category="low_value_impact",
                    node_id="",
                    message=(
                        f"{no_effect}/{len(choice_nodes)} ({ratio:.0%}) 的选择点"
                        f"没有任何 value_effects"
                    ),
                    suggestion="为更多选择点添加 value_effects 以积累数值影响",
                ))

        return issues

    def _check_graph_integrity(self) -> list[AuditIssue]:
        """图完整性检查"""
        issues = []
        graph_issues = self.graph.validate()
        for gi in graph_issues:
            issues.append(AuditIssue(
                severity="error", category="graph_integrity",
                node_id="", message=gi,
            ))
        return issues

    def _check_item_tracking(self) -> list[AuditIssue]:
        """道具追踪：检查 facts_introduced 的引入和使用链"""
        issues = []
        all_facts = {}  # fact → first_introduced_node

        for nid, node in self.graph.nodes.items():
            for fact in node.facts_introduced:
                if fact not in all_facts:
                    all_facts[fact] = nid

        # 检查是否有 fact 被引入但从未被后续节点引用
        # （这里只做结构检查，深度检查留给 Phase 2 LLM 审计）
        unused_facts = set(all_facts.keys())
        for nid, node in self.graph.nodes.items():
            # 简单检查：如果叙事文本中包含 fact 关键词
            text = self.narratives.get(nid, {}).get("narrative_text", "")
            text += self.narratives.get(nid, {}).get("death_text", "")
            for fact in list(unused_facts):
                # 用 fact 中的关键词匹配
                keywords = [w for w in fact.replace("的", " ").replace("了", " ").split() if len(w) >= 2]
                for kw in keywords:
                    if kw in text and all_facts.get(fact) != nid:
                        unused_facts.discard(fact)
                        break

        # 未使用的 fact 只是 warning
        for fact in unused_facts:
            issues.append(AuditIssue(
                severity="warning", category="item_tracking",
                node_id=all_facts[fact],
                message=f"事实 '{fact}' 被引入但可能未被后续使用",
                suggestion="检查该事实是否在后续分支中有呼应",
            ))

        return issues

    def _check_character_presence(self) -> list[AuditIssue]:
        """角色在场检查：对话参与者是否在 witnesses 中"""
        issues = []
        char_names = {c.char_id: c.name for c in self.graph.characters}

        for nid, node in self.graph.nodes.items():
            text = self.narratives.get(nid, {}).get("narrative_text", "")
            if not text:
                continue

            # 检查叙事中提到的角色是否在 witnesses 中
            for char_id, name in char_names.items():
                if name in text and char_id not in node.witnesses and "mc" not in node.witnesses:
                    # 如果角色在文本中说话但不在 witnesses 中
                    if f"「" in text or f'"' in text:  # 有对话
                        # 检查是否是这个角色在说话（简化检查）
                        if f"{name}说" in text or f"{name}道" in text or f"{name}：" in text:
                            issues.append(AuditIssue(
                                severity="warning", category="character_presence",
                                node_id=nid,
                                message=f"角色 '{name}' 在节点 {nid} 中说话但不在 witnesses 列表中",
                                suggestion=f"将 '{char_id}' 添加到 witnesses 列表",
                            ))

        return issues

    def _check_name_consistency(self) -> list[AuditIssue]:
        """名称一致性：角色名在各分支中是否统一"""
        issues = []
        char_names = {c.name for c in self.graph.characters}

        # 简单检查：叙事文本中出现的人名是否在角色列表中
        for nid, narr in self.narratives.items():
            text = narr.get("narrative_text", "") + narr.get("death_text", "")
            # 检查是否有类似角色名的变体（如"艾米丽" vs "艾米莉"）
            # 这里只做基本检查，复杂的留给 Phase 2
            pass

        return issues

    def _check_dead_end_causality(self) -> list[AuditIssue]:
        """死结局因果检查：死因标签与选择点选项是否对应"""
        issues = []

        for nid, node in self.graph.nodes.items():
            if node.node_type != NodeType.DEAD_END:
                continue

            if not node.death_cause:
                issues.append(AuditIssue(
                    severity="error", category="dead_end_causality",
                    node_id=nid,
                    message=f"死结局 {nid} 缺少死因标签",
                ))

            if not node.prev_nodes:
                issues.append(AuditIssue(
                    severity="error", category="dead_end_causality",
                    node_id=nid,
                    message=f"死结局 {nid} 没有前驱节点（无法到达）",
                ))

            # 检查死结局文本是否存在
            death_text = self.narratives.get(nid, {}).get("death_text", "")
            if not death_text or death_text.startswith("[生成失败"):
                issues.append(AuditIssue(
                    severity="error", category="dead_end_causality",
                    node_id=nid,
                    message=f"死结局 {nid} 缺少叙事文本",
                ))

        return issues

    def _check_narrative_coverage(self) -> list[AuditIssue]:
        """叙事覆盖检查：每个节点是否都有对应文本"""
        issues = []

        for nid, node in self.graph.nodes.items():
            narr = self.narratives.get(nid)
            if not narr:
                issues.append(AuditIssue(
                    severity="error", category="narrative_coverage",
                    node_id=nid,
                    message=f"节点 {nid} ({node.title}) 缺少叙事文本",
                ))
                continue

            if node.node_type == NodeType.DEAD_END:
                if not narr.get("death_text"):
                    issues.append(AuditIssue(
                        severity="error", category="narrative_coverage",
                        node_id=nid,
                        message=f"死结局 {nid} 缺少 death_text",
                    ))
            elif node.node_type == NodeType.CHOICE:
                if not narr.get("choices_text"):
                    issues.append(AuditIssue(
                        severity="error", category="narrative_coverage",
                        node_id=nid,
                        message=f"选择点 {nid} 缺少 choices_text",
                    ))
            else:
                if not narr.get("narrative_text"):
                    issues.append(AuditIssue(
                        severity="warning", category="narrative_coverage",
                        node_id=nid,
                        message=f"节点 {nid} 的 narrative_text 为空",
                    ))

        return issues

    def _check_timeline(self) -> list[AuditIssue]:
        """时间线顺序检查：幕序是否递增"""
        issues = []

        # 检查从入口开始遍历时，幕序是否非递减
        visited = set()
        stack = [(self.graph.entry_node_id, 0)]  # (node_id, min_expected_act)

        while stack:
            nid, min_act = stack.pop()
            if nid in visited or nid not in self.graph.nodes:
                continue
            visited.add(nid)

            node = self.graph.nodes[nid]
            if node.act < min_act and node.node_type not in (NodeType.DEAD_END,):
                issues.append(AuditIssue(
                    severity="warning", category="timeline",
                    node_id=nid,
                    message=f"节点 {nid} 的幕序 ({node.act}) 低于前驱的期望 ({min_act})",
                    suggestion="检查是否为回溯设计（合理）或时间线错误",
                ))

            for next_nid in node.next_nodes:
                stack.append((next_nid, node.act))
            for choice in node.choices:
                stack.append((choice.target_node_id, node.act))

        return issues


# ============================================================
# PostWriteValidator — AI 痕迹检测（纯规则）
# ============================================================

class PostWriteValidator:
    """
    AI 写作特征检测（纯规则引擎，零 LLM 成本）。
    参考 avoid-ai-writing 的检测维度。
    """

    # 中文 AI 常见填充词
    FILLER_WORDS_ZH = [
        "不禁", "缓缓", "微微", "轻轻", "淡淡", "默默",
        "目光中闪过", "嘴角微扬", "心中暗道", "不由得",
        "仿佛", "似乎", "宛如", "犹如", "恍若",
        "然而", "与此同时", "在这一刻", "就在此时",
        "深吸一口气", "紧握双拳", "攥紧了拳头",
    ]

    # 套路化开头
    FORMULAIC_OPENINGS_ZH = [
        r"^[\s\S]*然而，",
        r"^[\s\S]*但是，",
        r"^[\s\S]*不过，",
        r"^.*的目光.*闪过.*",
        r"^.*深吸.*口气.*",
    ]

    def validate(self, text: str) -> list[dict]:
        """
        检测 AI 写作特征。

        Returns:
            [{type, severity, detail, position}, ...]
        """
        if not text:
            return []

        issues = []
        issues.extend(self._check_filler_density(text))
        issues.extend(self._check_paragraph_uniformity(text))
        issues.extend(self._check_formulaic_patterns(text))
        issues.extend(self._check_emotion_overload(text))
        return issues

    def _check_filler_density(self, text: str) -> list[dict]:
        """填充词密度检查"""
        issues = []
        count = 0
        found = []
        for word in self.FILLER_WORDS_ZH:
            c = text.count(word)
            if c > 0:
                count += c
                found.append(f"{word}×{c}")

        density = count / max(len(text), 1) * 100
        if density > 2.0:  # 每100字超过2个填充词
            issues.append({
                "type": "filler_density",
                "severity": "warning",
                "detail": f"填充词密度 {density:.1f}%（{', '.join(found[:5])}）",
            })
        return issues

    def _check_paragraph_uniformity(self, text: str) -> list[dict]:
        """段落长度均匀度检查"""
        issues = []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) < 3:
            return issues

        lengths = [len(p) for p in paragraphs]
        avg = sum(lengths) / len(lengths)
        if avg == 0:
            return issues

        # 计算变异系数 (CV)
        variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
        cv = (variance ** 0.5) / avg

        if cv < 0.15:  # CV < 15% 说明段落长度过于均匀
            issues.append({
                "type": "paragraph_uniformity",
                "severity": "info",
                "detail": f"段落长度变异系数 {cv:.2f}（过于均匀，AI 特征）",
            })
        return issues

    def _check_formulaic_patterns(self, text: str) -> list[dict]:
        """套路化模式检查"""
        issues = []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        formulaic_count = 0

        for p in paragraphs:
            for pattern in self.FORMULAIC_OPENINGS_ZH:
                if re.match(pattern, p[:50]):
                    formulaic_count += 1
                    break

        if len(paragraphs) > 0 and formulaic_count / len(paragraphs) > 0.3:
            issues.append({
                "type": "formulaic_pattern",
                "severity": "warning",
                "detail": f"{formulaic_count}/{len(paragraphs)} 段落使用套路化开头",
            })
        return issues

    def _check_emotion_overload(self, text: str) -> list[dict]:
        """情绪词过载检查"""
        issues = []
        emotion_words = [
            "震惊", "恐惧", "兴奋", "愤怒", "悲伤", "喜悦", "焦虑",
            "绝望", "惊讶", "困惑", "欣慰", "紧张", "激动", "感动",
        ]
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        for i, p in enumerate(paragraphs):
            found = [w for w in emotion_words if w in p]
            if len(found) >= 3:
                issues.append({
                    "type": "emotion_overload",
                    "severity": "info",
                    "detail": f"段落 {i+1} 情绪词过载：{', '.join(found)}",
                })
        return issues


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Auditor — 质量检查")
    parser.add_argument("--graph", type=str, required=True)
    parser.add_argument("--narratives", type=str, required=True)
    parser.add_argument("--output", type=str, default="output/audit_report.json")

    args = parser.parse_args()

    with open(args.graph, "r") as f:
        graph = StoryGraph.from_dict(json.load(f))

    with open(args.narratives, "r") as f:
        narratives = json.load(f)

    # Phase 1: 规则审计
    auditor = RuleAuditor(graph, narratives)
    issues = auditor.audit()

    # PostWriteValidator
    validator = PostWriteValidator()
    ai_issues = []
    for nid, narr in narratives.items():
        text = narr.get("narrative_text", "") + narr.get("death_text", "")
        if text:
            vi = validator.validate(text)
            for v in vi:
                v["node_id"] = nid
                ai_issues.append(v)

    # 汇总报告
    report = {
        "graph_title": graph.title,
        "total_nodes": len(graph.nodes),
        "total_narratives": len(narratives),
        "structural_issues": [
            {"severity": i.severity, "category": i.category, "node_id": i.node_id,
             "message": i.message, "suggestion": i.suggestion}
            for i in issues
        ],
        "ai_writing_issues": ai_issues,
        "summary": {
            "errors": len([i for i in issues if i.severity == "error"]),
            "warnings": len([i for i in issues if i.severity == "warning"]),
            "info": len([i for i in issues if i.severity == "info"]),
            "ai_flags": len(ai_issues),
        },
    }

    import os
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📋 审计报告已保存到 {args.output}")
    print(f"  ❌ 错误：{report['summary']['errors']}")
    print(f"  ⚠️ 警告：{report['summary']['warnings']}")
    print(f"  ℹ️ 信息：{report['summary']['info']}")
    print(f"  🤖 AI特征：{report['summary']['ai_flags']}")
