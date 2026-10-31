"""
Interactive Novel Pipeline — 主入口

端到端流水线：Seed → Director → Writers → Auditor → Output

用法：
  # 离线模式（不调 LLM，用手写示例验证流程）
  python3 pipeline.py --mode offline

  # LLM 模式（调用 LLM 生成）
  python3 pipeline.py --mode llm --seed-file data/seed.txt --api-base ... --api-key ...
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from story_graph_schema import StoryGraph, NodeType, BranchType
from director_agent import DirectorAgent, LLMClient, LLMConfig, generate_example_graph_offline
from writers import (
    BranchWriter, DeadEndWriter, PearlStringWriter,
    ContextBuilder, write_offline_narratives,
)
from auditor import RuleAuditor, PostWriteValidator


def run_pipeline(
    mode: str = "offline",
    seed_file: str = "",
    output_dir: str = "output",
    model: str = "claude-sonnet-4-6",
    api_base: str = "",
    api_key: str = "",
    extra_requirements: str = "",
    extra_headers: dict = None,
):
    """
    运行完整 Pipeline。

    Args:
        mode: "offline" (手写示例) 或 "llm" (调用 LLM)
        seed_file: Seed 文件路径（llm 模式必填）
        output_dir: 输出目录
        model: LLM 模型名
        api_base: API base URL
        api_key: API key
        extra_requirements: 传给 Director 的额外要求
    """
    os.makedirs(output_dir, exist_ok=True)
    start_time = time.time()

    print("=" * 60)
    print("🎬 Interactive Novel Pipeline")
    print(f"   模式: {mode}")
    print("=" * 60)

    # ===== Phase 0-1: Director → Story Graph =====
    print("\n📐 Phase 0-1: Director Agent — 生成 Story Graph")
    print("-" * 40)

    if mode == "offline":
        graph = generate_example_graph_offline()
        print(f"  ✅ 离线示例 Story Graph 已生成")
    else:
        if not seed_file:
            raise ValueError("LLM 模式需要 --seed-file")
        with open(seed_file, "r") as f:
            seed = f.read()

        config = LLMConfig(model=model, api_base=api_base, api_key=api_key,
                          extra_headers=extra_headers or {})
        client = LLMClient(config)
        director = DirectorAgent(client)
        graph = director.generate(seed, extra_requirements)
        print(f"  ✅ LLM 生成 Story Graph 完成")

    # 验证
    issues = graph.validate()
    if issues:
        print(f"  ⚠️ 图验证发现 {len(issues)} 个问题：")
        for i in issues[:5]:
            print(f"    - {i}")
    else:
        print(f"  ✅ 图验证通过")

    print(f"  📊 统计：{graph.stats}")

    # 保存 Story Graph
    graph_path = os.path.join(output_dir, "story_graph.json")
    with open(graph_path, "w") as f:
        f.write(graph.to_json())
    print(f"  💾 Story Graph → {graph_path}")

    # 保存 World Bible
    bible_path = os.path.join(output_dir, "world_bible.txt")
    with open(bible_path, "w") as f:
        f.write(graph.get_world_bible())
    print(f"  💾 World Bible → {bible_path}")

    # 保存 Graph Summary
    summary_path = os.path.join(output_dir, "graph_summary.txt")
    with open(summary_path, "w") as f:
        f.write(graph.get_graph_summary())
    print(f"  💾 Graph Summary → {summary_path}")

    # ===== Phase 2: Writers → Narrative Text =====
    print("\n✍️ Phase 2: Writers — 生成叙事文本")
    print("-" * 40)

    if mode == "offline":
        narratives = write_offline_narratives(graph)
        print(f"  ✅ 离线叙事文本已生成（{len(narratives)} 个节点）")
    else:
        config = LLMConfig(model=model, api_base=api_base, api_key=api_key,
                          extra_headers=extra_headers or {})
        client = LLMClient(config)

        narratives = {}

        # 1. 主线 + 各分支的 Writer
        ctx_builder = ContextBuilder(graph)
        branch_writer = BranchWriter(client, graph)

        # 收集所有需要写的 branch
        all_branches = ["main"] + list(graph.branches.keys())

        for bid in all_branches:
            try:
                branch_results = branch_writer.write_branch(bid)
                for r in branch_results:
                    narratives[r["node_id"]] = r
                print(f"  ✅ 分支 {bid} 完成（{len(branch_results)} 个节点）")
            except Exception as e:
                print(f"  ❌ 分支 {bid} 失败: {e}")

        # 2. Dead End Writer（并行）
        dead_writer = DeadEndWriter(client, graph)
        dead_results = dead_writer.write_all_dead_ends()
        for r in dead_results:
            narratives[r["node_id"]] = r
        print(f"  ✅ 死结局完成（{len(dead_results)} 个）")

        # 3. Pearl String Writer
        pearl_writer = PearlStringWriter(client, graph)
        for bid, branch in graph.branches.items():
            if branch.branch_type == BranchType.PEARL_STRING:
                # 找到珍珠串的原版和变体
                # 简化处理：假设珍珠串的第一个节点有原版
                for nid in branch.node_ids:
                    node = graph.nodes.get(nid)
                    if node and node.merge_to:
                        # 找到同一收束点的其他分支作为原版
                        for other_bid, other_branch in graph.branches.items():
                            if other_bid != bid and other_branch.merge_node_id == branch.merge_node_id:
                                for other_nid in other_branch.node_ids:
                                    if other_nid in narratives:
                                        try:
                                            variant = pearl_writer.write_variant(
                                                nid, other_nid,
                                                narratives[other_nid].get("narrative_text", ""),
                                            )
                                            narratives[nid] = variant
                                            print(f"  ✅ 珍珠串变体 {nid} 完成")
                                        except Exception as e:
                                            print(f"  ❌ 珍珠串变体 {nid} 失败: {e}")
                                        break

    # 保存叙事文本
    narr_path = os.path.join(output_dir, "narratives.json")
    with open(narr_path, "w") as f:
        json.dump(narratives, f, ensure_ascii=False, indent=2)
    print(f"  💾 叙事文本 → {narr_path}")

    # ===== Phase 2.5: PostWriteValidator =====
    print("\n🔍 Phase 2.5: PostWriteValidator — AI 痕迹检测")
    print("-" * 40)

    validator = PostWriteValidator()
    ai_issues = []
    for nid, narr in narratives.items():
        text = narr.get("narrative_text", "") + narr.get("death_text", "")
        if text:
            vi = validator.validate(text)
            for v in vi:
                v["node_id"] = nid
                ai_issues.append(v)

    if ai_issues:
        print(f"  ⚠️ 检测到 {len(ai_issues)} 个 AI 写作特征")
        for issue in ai_issues[:5]:
            print(f"    - [{issue['node_id']}] {issue['detail']}")
    else:
        print(f"  ✅ 未检测到明显 AI 写作特征")

    # ===== Phase 3: Auditor =====
    print("\n📋 Phase 3: Auditor — 质量审计")
    print("-" * 40)

    auditor = RuleAuditor(graph, narratives)
    audit_issues = auditor.audit()

    errors = [i for i in audit_issues if i.severity == "error"]
    warnings = [i for i in audit_issues if i.severity == "warning"]
    infos = [i for i in audit_issues if i.severity == "info"]

    print(f"  ❌ 错误：{len(errors)}")
    print(f"  ⚠️ 警告：{len(warnings)}")
    print(f"  ℹ️ 信息：{len(infos)}")

    if errors:
        print(f"\n  错误详情：")
        for e in errors:
            print(f"    [{e.node_id}] {e.message}")

    # 保存审计报告
    report = {
        "graph_title": graph.title,
        "pipeline_mode": mode,
        "total_nodes": len(graph.nodes),
        "total_narratives": len(narratives),
        "structural_issues": [
            {"severity": i.severity, "category": i.category, "node_id": i.node_id,
             "message": i.message, "suggestion": i.suggestion}
            for i in audit_issues
        ],
        "ai_writing_issues": ai_issues,
        "summary": {
            "errors": len(errors),
            "warnings": len(warnings),
            "info": len(infos),
            "ai_flags": len(ai_issues),
        },
    }

    report_path = os.path.join(output_dir, "audit_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  💾 审计报告 → {report_path}")

    # ===== 生成可读的故事文本 =====
    print("\n📖 生成可读故事文本...")
    readable = generate_readable_output(graph, narratives)
    readable_path = os.path.join(output_dir, "story_readable.txt")
    with open(readable_path, "w") as f:
        f.write(readable)
    print(f"  💾 可读文本 → {readable_path}")

    # ===== 完成 =====
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"✅ Pipeline 完成！耗时 {elapsed:.1f}s")
    print(f"   输出目录：{output_dir}")
    print(f"   Story Graph: {graph_path}")
    print(f"   叙事文本: {narr_path}")
    print(f"   审计报告: {report_path}")
    print(f"   可读故事: {readable_path}")
    print("=" * 60)

    return {
        "graph": graph,
        "narratives": narratives,
        "audit_report": report,
        "output_dir": output_dir,
    }


def generate_readable_output(graph: StoryGraph, narratives: dict) -> str:
    """
    生成人类可读的故事文本（带分支标注）。
    按主线顺序，遇到选择点标注分支。
    """
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  {graph.title}")
    lines.append(f"  {graph.genre} | {graph.time_period} | {graph.location}")
    lines.append(f"{'='*60}")
    lines.append("")

    # 从入口开始遍历
    visited = set()

    def walk(node_id, depth=0, prefix=""):
        if node_id in visited or node_id not in graph.nodes:
            return
        visited.add(node_id)

        node = graph.nodes[node_id]
        narr = narratives.get(node_id, {})

        indent = "  " * depth

        # 节点标题
        type_label = {
            NodeType.NARRATIVE: "📖",
            NodeType.CHOICE: "🔀",
            NodeType.DEAD_END: "💀",
            NodeType.ENDING: "🏁",
            NodeType.BRANCH_POINT: "🔱",
            NodeType.MERGE_POINT: "🔗",
        }.get(node.node_type, "📄")

        lines.append(f"{indent}{type_label} [{node.node_id}] {node.title}  (第{node.act}幕)")
        if prefix:
            lines.append(f"{indent}   ↳ {prefix}")
        lines.append(f"{indent}{'-'*40}")

        # 内容
        if node.node_type == NodeType.DEAD_END:
            death_text = narr.get("death_text", node.death_description_hint or "（死结局）")
            lines.append(f"{indent}   {death_text}")
            lines.append(f"{indent}   [死因: {node.death_cause}]")
            lines.append("")
            return

        if node.node_type == NodeType.ENDING:
            text = narr.get("narrative_text", node.scene_description)
            lines.append(f"{indent}   {text}")
            lines.append(f"{indent}   [结局类型: {node.ending_type}]")
            lines.append("")
            return

        text = narr.get("narrative_text", node.scene_description)
        if text:
            for line in text.split("\n"):
                lines.append(f"{indent}   {line}")

        lines.append("")

        # 选择点
        if node.choices:
            lines.append(f"{indent}   【请选择】")
            for i, choice in enumerate(node.choices, 1):
                marker = " 💀" if choice.is_dead_end else ""
                lines.append(f"{indent}   {i}. {choice.text}{marker}")
            lines.append("")

            # 递归各选项
            for choice in node.choices:
                branch_label = f"选择: {choice.text}"
                walk(choice.target_node_id, depth + 1, branch_label)
        else:
            # 直接后继
            for next_id in node.next_nodes:
                walk(next_id, depth)

    walk(graph.entry_node_id)

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive Novel Pipeline")
    parser.add_argument("--mode", choices=["offline", "llm"], default="offline",
                        help="offline=手写示例验证流程, llm=调用LLM生成")
    parser.add_argument("--seed-file", type=str, help="Seed 文件路径（llm 模式）")
    parser.add_argument("--output-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs"),
                        help="输出目录")
    parser.add_argument("--model", type=str,
                        default=os.environ.get("LLM_MODEL", "claude-sonnet-4-6"))
    parser.add_argument("--api-base", type=str,
                        default=os.environ.get("LLM_API_BASE", ""))
    parser.add_argument("--api-key", type=str,
                        default=os.environ.get("LLM_API_KEY", ""))
    parser.add_argument("--extra-requirements", type=str, default="")
    parser.add_argument("--extra-header", type=str, action="append", default=[],
                        help="Extra HTTP header, format: 'Key: Value'")

    args = parser.parse_args()

    # Parse extra headers
    extra_headers = {}
    for h in args.extra_header:
        if ":" in h:
            k, v = h.split(":", 1)
            extra_headers[k.strip()] = v.strip()

    result = run_pipeline(
        mode=args.mode,
        seed_file=args.seed_file or "",
        output_dir=args.output_dir,
        model=args.model,
        api_base=args.api_base,
        api_key=args.api_key,
        extra_requirements=args.extra_requirements,
        extra_headers=extra_headers,
    )
