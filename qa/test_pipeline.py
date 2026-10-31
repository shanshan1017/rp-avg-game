"""
Interactive Novel Pipeline — QA 测试套件

覆盖：
  1. Seed 数据格式校验
  2. Story Graph 结构完整性（schema + 图连通性 + 数值系统 + 回声系统）
  3. Narrative 输出校验（覆盖率 + 文本质量信号）
  4. Audit Report 校验
  5. Pipeline 代码校验
  6. 端到端：对已有输出做全量校验

用法：
  # 跑全部测试
  python3 test_pipeline.py

  # 跑指定类别
  python3 test_pipeline.py --only seed,graph,narrative

  # 指定输出目录（默认 outputs/seed001）
  python3 test_pipeline.py --output-dir /path/to/output

  # verbose 模式
  python3 test_pipeline.py -v
"""

import argparse
import ast
import inspect
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ============================================================
# 配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs" / "seed001"
SEED_FILE = BASE_DIR / "data" / "seeds.jsonl"
SEED_001_FILE = BASE_DIR / "data" / "seed_001.jsonl"
PIPELINE_DIR = BASE_DIR / "pipeline"
SCHEMA_FILE = PIPELINE_DIR / "story_graph_schema.py"

# Story Graph 约束
MIN_NODES = 10
MIN_CHOICE_NODES = 2
MIN_DEAD_ENDS = 1
MIN_ENDINGS = 1
MAX_ORPHAN_RATIO = 0.1  # 孤立节点占比上限

# Narrative 约束
MIN_NARRATIVE_LENGTH = 50       # 最短叙事文本（字符）
MAX_NARRATIVE_LENGTH = 5000     # 最长叙事文本
MIN_DEAD_END_LENGTH = 20
MIN_ENDING_LENGTH = 100

# AI 写作检测关键词（中文）
AI_FILLER_WORDS_ZH = [
    "然而，", "不禁", "心中暗想", "一股", "莫名的", "不由得",
    "显然，", "毫无疑问", "值得注意的是", "事实上，",
]
# AI 写作检测关键词（英文）
AI_FILLER_WORDS_EN = [
    "However, ", "Moreover, ", "Furthermore, ", "It's worth noting",
    "couldn't help but", "a sense of", "In fact, ",
]
AI_FILLER_THRESHOLD = 0.3  # 填充词密度阈值（per 1000 chars）


# ============================================================
# 测试结果收集
# ============================================================

class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "",
                 severity: str = "error"):
        self.name = name
        self.passed = passed
        self.message = message
        self.severity = severity  # error / warning / info

    def __str__(self):
        icon = "PASS" if self.passed else self.severity.upper()
        s = f"[{icon}] {self.name}"
        if self.message:
            s += f" — {self.message}"
        return s


class TestSuite:
    def __init__(self, verbose: bool = False):
        self.results: List[TestResult] = []
        self.verbose = verbose

    def add(self, name: str, passed: bool, message: str = "",
            severity: str = "error"):
        r = TestResult(name, passed, message, severity)
        self.results.append(r)
        if self.verbose or not passed:
            print(r)

    def summary(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        errors = sum(1 for r in self.results
                     if not r.passed and r.severity == "error")
        warnings = sum(1 for r in self.results
                       if not r.passed and r.severity == "warning")
        return {
            "total": total,
            "passed": passed,
            "errors": errors,
            "warnings": warnings,
            "pass_rate": f"{passed/total*100:.1f}%" if total else "N/A",
        }

    def print_summary(self):
        s = self.summary()
        print("\n" + "=" * 60)
        print(f"  Total: {s['total']}  |  Passed: {s['passed']}  |  "
              f"Errors: {s['errors']}  |  Warnings: {s['warnings']}")
        print(f"  Pass Rate: {s['pass_rate']}")
        print("=" * 60)
        if s["errors"] > 0:
            print("\n  Failed tests:")
            for r in self.results:
                if not r.passed and r.severity == "error":
                    print(f"    {r}")

    def exit_code(self) -> int:
        return 1 if any(
            not r.passed and r.severity == "error" for r in self.results
        ) else 0


# ============================================================
# 1. Seed 数据格式校验
# ============================================================

def test_seed_format(suite: TestSuite):
    """校验 seeds.jsonl 和 seed_001.jsonl 格式。"""
    for fpath in [SEED_FILE, SEED_001_FILE]:
        label = fpath.name
        suite.add(f"seed.{label}.exists", fpath.exists(),
                  f"文件不存在: {fpath}")
        if not fpath.exists():
            continue

        lines = fpath.read_text().strip().split("\n")
        suite.add(f"seed.{label}.not_empty", len(lines) > 0, "文件为空")

        for i, line in enumerate(lines):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                suite.add(f"seed.{label}.line_{i}.json", False,
                          f"JSON 解析失败: {e}")
                continue

            suite.add(f"seed.{label}.line_{i}.json", True)

            # 必需字段
            has_id = "id" in rec
            suite.add(f"seed.{label}.line_{i}.has_id", has_id,
                      "缺少 id 字段")

            has_seed = "seed_content" in rec or "query" in rec
            suite.add(f"seed.{label}.line_{i}.has_content", has_seed,
                      "缺少 seed_content 或 query 字段")

            if "seed_content" in rec:
                content = rec["seed_content"]
                suite.add(f"seed.{label}.line_{i}.content_length",
                          len(content) > 50,
                          f"seed_content 太短 ({len(content)} chars)")

            # config 字段（可选但推荐）
            if "config" in rec:
                cfg = rec["config"]
                suite.add(f"seed.{label}.line_{i}.config_is_dict",
                          isinstance(cfg, dict),
                          f"config 应为 dict，实际为 {type(cfg).__name__}")


# ============================================================
# 2. Story Graph 结构校验
# ============================================================

def test_story_graph(suite: TestSuite, output_dir: Path):
    """校验 story_graph.json 的结构完整性。"""
    sg_path = output_dir / "story_graph.json"
    suite.add("graph.file_exists", sg_path.exists(),
              f"文件不存在: {sg_path}")
    if not sg_path.exists():
        return

    try:
        sg = json.loads(sg_path.read_text())
    except json.JSONDecodeError as e:
        suite.add("graph.valid_json", False, f"JSON 解析失败: {e}")
        return

    suite.add("graph.valid_json", True)

    # ---- 顶层字段 ----
    required_top = ["nodes", "entry_node_id"]
    recommended_top = ["title", "genre", "characters", "branches",
                       "value_system"]
    for field in required_top:
        suite.add(f"graph.has_{field}", field in sg,
                  f"缺少必需字段: {field}")
    for field in recommended_top:
        suite.add(f"graph.has_{field}", field in sg,
                  f"缺少推荐字段: {field}", severity="warning")

    nodes = sg.get("nodes", {})
    entry = sg.get("entry_node_id", "")

    # ---- 节点数量 ----
    suite.add("graph.node_count", len(nodes) >= MIN_NODES,
              f"节点数 {len(nodes)} < 最小要求 {MIN_NODES}")

    # ---- 入口节点 ----
    suite.add("graph.entry_exists", entry in nodes,
              f"入口节点 '{entry}' 不在 nodes 中")

    # ---- 节点类型分布 ----
    type_counter = Counter()
    for nid, node in nodes.items():
        ntype = node.get("node_type", "unknown")
        type_counter[ntype] += 1

    suite.add("graph.has_choice_nodes",
              type_counter.get("choice", 0) >= MIN_CHOICE_NODES,
              f"选择节点 {type_counter.get('choice', 0)} < {MIN_CHOICE_NODES}")

    dead_end_count = type_counter.get("dead_end", 0)
    suite.add("graph.has_dead_ends",
              dead_end_count >= MIN_DEAD_ENDS,
              f"死结局 {dead_end_count} < {MIN_DEAD_ENDS}")

    ending_count = type_counter.get("ending", 0)
    suite.add("graph.has_endings",
              ending_count >= MIN_ENDINGS,
              f"结局 {ending_count} < {MIN_ENDINGS}")

    # ---- 选择点必须有选项 ----
    for nid, node in nodes.items():
        if node.get("node_type") == "choice":
            choices = node.get("choices", [])
            suite.add(f"graph.choice_{nid}.has_options",
                      len(choices) >= 2,
                      f"选择节点 {nid} 只有 {len(choices)} 个选项")

    # ---- 选项目标节点存在 ----
    for nid, node in nodes.items():
        for ch in node.get("choices", []):
            target = ch.get("target_node_id", "")
            if target:
                suite.add(f"graph.choice_target_{nid}_{target}",
                          target in nodes,
                          f"{nid} 的选项指向不存在的节点 {target}")

    # ---- 图连通性：BFS 从入口出发 ----
    if entry in nodes:
        reachable = set()
        queue = [entry]
        while queue:
            curr = queue.pop(0)
            if curr in reachable:
                continue
            reachable.add(curr)
            node = nodes.get(curr, {})
            # next_nodes
            for nxt in node.get("next_nodes", []):
                if nxt not in reachable:
                    queue.append(nxt)
            # choices targets
            for ch in node.get("choices", []):
                t = ch.get("target_node_id", "")
                if t and t not in reachable:
                    queue.append(t)

        unreachable = set(nodes.keys()) - reachable
        orphan_ratio = len(unreachable) / len(nodes) if nodes else 0
        suite.add("graph.reachability",
                  orphan_ratio <= MAX_ORPHAN_RATIO,
                  f"{len(unreachable)}/{len(nodes)} 节点不可达: "
                  f"{list(unreachable)[:5]}")

    # ---- 死结局有死因 ----
    for nid, node in nodes.items():
        if node.get("node_type") == "dead_end":
            has_cause = bool(node.get("death_cause") or
                           node.get("death_description_hint"))
            suite.add(f"graph.dead_end_{nid}.has_cause", has_cause,
                      f"死结局 {nid} 缺少死因", severity="warning")

    # ---- 结局有类型 ----
    for nid, node in nodes.items():
        if node.get("node_type") == "ending":
            suite.add(f"graph.ending_{nid}.has_type",
                      bool(node.get("ending_type")),
                      f"结局 {nid} 缺少 ending_type", severity="warning")

    # ---- 分支结构 ----
    branches = sg.get("branches", {})
    for bid, branch in branches.items():
        suite.add(f"graph.branch_{bid}.has_type",
                  bool(branch.get("branch_type")),
                  f"分支 {bid} 缺少 branch_type", severity="warning")

        # 分支节点都存在
        for nid in branch.get("node_ids", []):
            suite.add(f"graph.branch_{bid}.node_{nid}_exists",
                      nid in nodes,
                      f"分支 {bid} 引用不存在节点 {nid}")

    # ---- 数值系统（如果存在） ----
    vs = sg.get("value_system")
    if vs:
        dims = vs.get("dimensions") or vs.get("attributes")
        if dims:
            suite.add("graph.value_system.has_dimensions", True)
            if isinstance(dims, list):
                for d in dims:
                    suite.add(f"graph.vs.dim_{d.get('name','?')}.has_range",
                              "range" in d or "initial" in d,
                              f"维度 {d.get('name')} 缺少 range/initial",
                              severity="warning")
        else:
            suite.add("graph.value_system.has_dimensions", False,
                      "value_system 存在但无 dimensions/attributes",
                      severity="warning")

    # ---- 角色列表 ----
    characters = sg.get("characters", [])
    suite.add("graph.has_characters", len(characters) >= 2,
              f"角色数 {len(characters)} < 2", severity="warning")


# ============================================================
# 3. Narrative 输出校验
# ============================================================

def test_narratives(suite: TestSuite, output_dir: Path):
    """校验 narratives.json 的完整性和文本质量。"""
    narr_path = output_dir / "narratives.json"
    suite.add("narrative.file_exists", narr_path.exists(),
              f"文件不存在: {narr_path}")
    if not narr_path.exists():
        return

    try:
        narr = json.loads(narr_path.read_text())
    except json.JSONDecodeError as e:
        suite.add("narrative.valid_json", False, f"JSON 解析失败: {e}")
        return

    suite.add("narrative.valid_json", True)
    suite.add("narrative.not_empty", len(narr) > 0, "narratives 为空")

    # ---- 与 story_graph 对齐 ----
    sg_path = output_dir / "story_graph.json"
    if sg_path.exists():
        sg = json.loads(sg_path.read_text())
        sg_nodes = set(sg.get("nodes", {}).keys())
        narr_nodes = set(narr.keys())

        missing = sg_nodes - narr_nodes
        extra = narr_nodes - sg_nodes

        # 不要求 100% 覆盖，但警告缺失较多的情况
        coverage = len(narr_nodes & sg_nodes) / len(sg_nodes) if sg_nodes else 0
        suite.add("narrative.coverage",
                  coverage >= 0.7,
                  f"覆盖率 {coverage:.0%} ({len(missing)} 节点无叙事)",
                  severity="warning" if coverage >= 0.5 else "error")

        if missing and len(missing) <= 10:
            suite.add("narrative.missing_nodes", False,
                      f"缺少叙事: {sorted(missing)}", severity="warning")

    # ---- 文本质量 ----
    all_text = ""
    for nid, entry in narr.items():
        text = entry.get("narrative_text", "") or ""
        all_text += text

        # 基本长度检查
        if "dead" in nid.lower() or (isinstance(entry, dict) and
                                      entry.get("death_text")):
            min_len = MIN_DEAD_END_LENGTH
        elif "ending" in nid.lower() or (isinstance(entry, dict) and
                                          entry.get("ending_type")):
            min_len = MIN_ENDING_LENGTH
        else:
            min_len = MIN_NARRATIVE_LENGTH

        suite.add(f"narrative.{nid}.min_length",
                  len(text) >= min_len,
                  f"文本太短 ({len(text)} < {min_len})",
                  severity="warning")

        suite.add(f"narrative.{nid}.max_length",
                  len(text) <= MAX_NARRATIVE_LENGTH,
                  f"文本过长 ({len(text)} > {MAX_NARRATIVE_LENGTH})",
                  severity="warning")

    # ---- AI 写作痕迹检测 ----
    if all_text:
        filler_words = (AI_FILLER_WORDS_ZH
                       if any("\u4e00" <= c <= "\u9fff" for c in all_text[:100])
                       else AI_FILLER_WORDS_EN)

        filler_count = sum(all_text.count(w) for w in filler_words)
        density = filler_count / (len(all_text) / 1000) if all_text else 0

        suite.add("narrative.ai_filler_density",
                  density <= AI_FILLER_THRESHOLD,
                  f"填充词密度 {density:.2f}/千字 > 阈值 {AI_FILLER_THRESHOLD}",
                  severity="warning")

    # ---- 段落均匀度检测 ----
    for nid, entry in narr.items():
        text = entry.get("narrative_text", "") or ""
        if len(text) < 200:
            continue
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if len(paragraphs) >= 3:
            lengths = [len(p) for p in paragraphs]
            avg = sum(lengths) / len(lengths)
            if avg > 0:
                cv = (sum((l - avg) ** 2 for l in lengths)
                      / len(lengths)) ** 0.5 / avg
                # CV < 0.3 = 段落长度太均匀（AI 特征）
                suite.add(f"narrative.{nid}.paragraph_variance",
                          cv >= 0.25,
                          f"段落长度变异系数 {cv:.2f} 过低（疑似 AI 生成）",
                          severity="warning")


# ============================================================
# 4. Audit Report 校验
# ============================================================

def test_audit_report(suite: TestSuite, output_dir: Path):
    """校验 audit_report.json。"""
    audit_path = output_dir / "audit_report.json"
    suite.add("audit.file_exists", audit_path.exists(),
              f"文件不存在: {audit_path}")
    if not audit_path.exists():
        return

    try:
        audit = json.loads(audit_path.read_text())
    except json.JSONDecodeError as e:
        suite.add("audit.valid_json", False, f"JSON 解析失败: {e}")
        return

    suite.add("audit.valid_json", True)

    # 检查是否有严重问题
    issues = audit.get("structural_issues", [])
    if isinstance(issues, list):
        error_issues = [i for i in issues
                       if isinstance(i, dict) and i.get("severity") == "error"]
        suite.add("audit.no_structural_errors",
                  len(error_issues) == 0,
                  f"审计发现 {len(error_issues)} 个结构性错误",
                  severity="warning")

    # AI 写作问题
    ai_issues = audit.get("ai_writing_issues", [])
    if isinstance(ai_issues, list):
        suite.add("audit.ai_writing_check_ran", True,
                  "AI 写作检测已执行")
        if ai_issues:
            suite.add("audit.ai_writing_clean",
                      len(ai_issues) <= 3,
                      f"检测到 {len(ai_issues)} 处 AI 写作痕迹",
                      severity="warning")


# ============================================================
# 7. Pipeline 代码校验
# ============================================================

def test_pipeline_code(suite: TestSuite):
    """校验 pipeline 目录下的核心文件。"""
    required_files = [
        "pipeline.py",
        "story_graph_schema.py",
        "director_agent.py",
        "writers.py",
        "auditor.py",
    ]

    for fname in required_files:
        fpath = PIPELINE_DIR / fname
        suite.add(f"pipeline.{fname}.exists", fpath.exists(),
                  f"核心文件缺失: {fpath}")
        if fpath.exists():
            content = fpath.read_text()
            suite.add(f"pipeline.{fname}.not_empty",
                      len(content) > 100,
                      f"文件内容过少 ({len(content)} bytes)")

    # schema 特有检查
    if SCHEMA_FILE.exists():
        schema_src = SCHEMA_FILE.read_text()
        for cls_name in ["StoryNode", "StoryGraph", "Character",
                         "ChoiceOption", "BranchArc"]:
            suite.add(f"pipeline.schema.has_{cls_name}",
                      f"class {cls_name}" in schema_src,
                      f"schema 缺少 {cls_name} 类")

        suite.add("pipeline.schema.has_validate",
                  "def validate" in schema_src,
                  "StoryGraph 缺少 validate 方法", severity="warning")


# ============================================================
# 8. 端到端：完整输出校验
# ============================================================

def test_e2e(suite: TestSuite, output_dir: Path):
    """对指定输出目录做完整校验。"""
    suite.add("e2e.output_dir_exists", output_dir.exists(),
              f"输出目录不存在: {output_dir}")
    if not output_dir.exists():
        return

    expected_files = ["story_graph.json", "narratives.json"]
    optional_files = ["audit_report.json", "story_readable.txt",
                      "world_bible.txt", "graph_summary.txt"]

    for fname in expected_files:
        fpath = output_dir / fname
        suite.add(f"e2e.has_{fname}", fpath.exists(),
                  f"缺少输出文件: {fname}")

    for fname in optional_files:
        fpath = output_dir / fname
        suite.add(f"e2e.has_{fname}", fpath.exists(),
                  f"缺少可选文件: {fname}", severity="info")

    # ---- story_graph ↔ narratives 交叉校验 ----
    sg_path = output_dir / "story_graph.json"
    narr_path = output_dir / "narratives.json"

    if sg_path.exists() and narr_path.exists():
        try:
            sg = json.loads(sg_path.read_text())
            narr = json.loads(narr_path.read_text())

            sg_nodes = set(sg.get("nodes", {}).keys())
            narr_nodes = set(narr.keys())

            # 叙事覆盖了哪些节点类型
            covered_types = Counter()
            missing_types = Counter()
            for nid in sg_nodes:
                ntype = sg["nodes"][nid].get("node_type", "unknown")
                if nid in narr_nodes:
                    covered_types[ntype] += 1
                else:
                    missing_types[ntype] += 1

            if missing_types:
                suite.add("e2e.narrative_coverage_by_type", False,
                          f"未覆盖节点类型分布: {dict(missing_types)}",
                          severity="warning")
            else:
                suite.add("e2e.narrative_coverage_by_type", True)

            # 选择节点的叙事必须包含选项文本
            for nid in sg_nodes & narr_nodes:
                node = sg["nodes"][nid]
                if node.get("node_type") == "choice" and node.get("choices"):
                    narr_entry = narr[nid]
                    has_choices_text = bool(
                        narr_entry.get("choices_text") or
                        narr_entry.get("choice_presentation")
                    )
                    suite.add(f"e2e.choice_{nid}.has_choices_text",
                              has_choices_text,
                              f"选择节点 {nid} 的叙事缺少选项文本",
                              severity="warning")

        except (json.JSONDecodeError, KeyError) as e:
            suite.add("e2e.cross_validation", False,
                      f"交叉校验失败: {e}")


# ============================================================
# Main
# ============================================================

CATEGORY_MAP = {
    "seed": test_seed_format,
    "graph": test_story_graph,
    "narrative": test_narratives,
    "audit": test_audit_report,
    "pipeline": test_pipeline_code,
    "e2e": test_e2e,
}

# 需要 output_dir 参数的测试
NEEDS_OUTPUT_DIR = {"graph", "narrative", "audit", "e2e"}


def main():
    parser = argparse.ArgumentParser(
        description="Interactive Novel Pipeline QA Test Suite"
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="输出目录（默认 outputs/seed001）")
    parser.add_argument("--only", type=str, default=None,
                        help="只跑指定类别（逗号分隔，如 seed,graph,audit）")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="打印所有测试结果（含通过的）")
    args = parser.parse_args()

    suite = TestSuite(verbose=args.verbose)

    categories = (args.only.split(",") if args.only
                  else list(CATEGORY_MAP.keys()))

    print(f"Interactive Novel Pipeline QA")
    print(f"Output dir: {args.output_dir}")
    print(f"Categories: {', '.join(categories)}")
    print("-" * 60)

    for cat in categories:
        cat = cat.strip()
        if cat not in CATEGORY_MAP:
            print(f"[SKIP] 未知类别: {cat}")
            continue

        print(f"\n--- {cat} ---")
        fn = CATEGORY_MAP[cat]
        if cat in NEEDS_OUTPUT_DIR:
            fn(suite, args.output_dir)
        else:
            fn(suite)

    suite.print_summary()

    # 输出 JSON 报告
    report_path = args.output_dir / "qa_report.json" if args.output_dir.exists() else Path("/tmp/qa_report.json")
    report = {
        "output_dir": str(args.output_dir),
        "summary": suite.summary(),
        "results": [
            {
                "name": r.name,
                "passed": r.passed,
                "message": r.message,
                "severity": r.severity,
            }
            for r in suite.results
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n报告已保存: {report_path}")

    sys.exit(suite.exit_code())


if __name__ == "__main__":
    main()
