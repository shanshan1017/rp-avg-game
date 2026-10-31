#!/usr/bin/env python3
"""
Story Graph → Interactive HTML Visualizer

用法：
  python3 generate_viz.py story_graph.json                    # 输出到同目录 story_graph_viz.html
  python3 generate_viz.py story_graph.json -o output.html     # 指定输出路径
  python3 generate_viz.py story_graph.json --title "自定义标题"  # 覆盖标题

输入：story_graph.json（Director 生成的结构化故事图）
输出：独立 HTML 文件，包含 BFS 布局的交互式 SVG 图谱
"""

import argparse
import json
import os
import sys


def load_story_graph(path: str) -> dict:
    """加载 story_graph.json。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_metadata(data: dict) -> dict:
    """从 story graph 提取统计信息。"""
    nodes = data.get("nodes", {})
    branches = data.get("branches", {})

    node_count = len(nodes)
    branch_count = len(branches)

    # 统计结局数（ending + dead_end）
    ending_nodes = [n for n in nodes.values() if n.get("node_type") in ("ending",)]
    dead_end_nodes = [n for n in nodes.values() if n.get("node_type") == "dead_end"]
    ending_count = len(ending_nodes)
    dead_end_count = len(dead_end_nodes)

    # 统计选择点数
    choice_nodes = [n for n in nodes.values() if n.get("node_type") == "choice" or (n.get("choices") and len(n["choices"]) > 0)]
    choice_count = len(choice_nodes)

    # 统计幕数
    acts = set()
    for n in nodes.values():
        if n.get("act"):
            acts.add(n["act"])
    total_acts = max(acts) if acts else data.get("total_acts", 4)

    # 结局类型统计
    ending_types = set()
    for n in ending_nodes:
        if n.get("ending_type"):
            ending_types.add(n["ending_type"])

    title = data.get("title", "故事图谱")

    # 构建 subtitle
    parts = [f"{node_count}个节点"]
    if branch_count:
        parts.append(f"{branch_count}条分支")
    if choice_count:
        parts.append(f"{choice_count}个选择点")
    if ending_count:
        parts.append(f"{ending_count}种结局")
    if dead_end_count:
        parts.append(f"{dead_end_count}个死结局")
    subtitle = "互动小说故事图谱 · " + " · ".join(parts)

    return {
        "title": title,
        "subtitle": subtitle,
        "total_acts": total_acts,
        "node_count": node_count,
        "branch_count": branch_count,
        "ending_count": ending_count,
        "dead_end_count": dead_end_count,
        "choice_count": choice_count,
    }


def generate_html(data: dict, meta: dict, title_override: str = None) -> str:
    """生成完整的 HTML 可视化文件。"""
    title = title_override or meta["title"]
    subtitle = meta["subtitle"]
    total_acts = meta["total_acts"]
    data_json = json.dumps(data, ensure_ascii=False, indent=2)

    # ---- HTML template ----
    html = f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — 故事图谱</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
    background: #0d1117;
    color: #c9d1d9;
    overflow: hidden;
  }}

  #header {{
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    background: linear-gradient(180deg, rgba(13,17,23,0.97) 80%, rgba(13,17,23,0));
    padding: 16px 24px 28px;
    pointer-events: none;
  }}
  #header h1 {{
    font-size: 20px; font-weight: 600; color: #e6edf3;
    pointer-events: auto;
  }}
  #header .subtitle {{
    font-size: 13px; color: #7d8590; margin-top: 4px;
    pointer-events: auto;
  }}

  #legend {{
    position: fixed; top: 16px; right: 24px; z-index: 100;
    display: flex; gap: 12px; flex-wrap: wrap; align-items: center;
    font-size: 12px; color: #7d8590;
  }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; }}
  .legend-dot {{
    width: 12px; height: 12px; border-radius: 3px;
  }}

  #canvas {{ width: 100vw; height: 100vh; }}

  #tooltip {{
    position: fixed; z-index: 200;
    background: #161b22; border: 1px solid #30363d;
    border-radius: 8px; padding: 14px 16px;
    max-width: 420px; font-size: 13px;
    line-height: 1.6; color: #c9d1d9;
    pointer-events: none; opacity: 0;
    transition: opacity 0.15s;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  }}
  #tooltip .tt-title {{
    font-size: 15px; font-weight: 600; color: #e6edf3;
    margin-bottom: 6px;
  }}
  #tooltip .tt-type {{
    display: inline-block; font-size: 11px; padding: 2px 7px;
    border-radius: 10px; margin-bottom: 8px;
  }}
  #tooltip .tt-act {{
    font-size: 11px; color: #7d8590; margin-left: 6px;
  }}
  #tooltip .tt-desc {{
    font-size: 12px; color: #8b949e;
    max-height: 160px; overflow-y: auto;
    margin-top: 6px;
  }}
  #tooltip .tt-events {{
    margin-top: 8px; font-size: 12px;
  }}
  #tooltip .tt-events li {{
    margin-left: 16px; color: #8b949e;
  }}
  #tooltip .tt-choices {{
    margin-top: 8px; border-top: 1px solid #21262d; padding-top: 8px;
  }}
  #tooltip .tt-choice-item {{
    font-size: 12px; color: #79c0ff; margin-bottom: 4px;
  }}

  #detail-panel {{
    position: fixed; top: 0; right: -480px; width: 460px; height: 100vh;
    background: #161b22; border-left: 1px solid #30363d;
    z-index: 150; transition: right 0.3s ease;
    overflow-y: auto; padding: 24px;
  }}
  #detail-panel.open {{ right: 0; }}
  #detail-panel .close-btn {{
    position: absolute; top: 12px; right: 16px;
    background: none; border: none; color: #7d8590;
    font-size: 22px; cursor: pointer;
  }}
  #detail-panel .close-btn:hover {{ color: #e6edf3; }}
  #detail-panel h2 {{
    font-size: 18px; color: #e6edf3; margin-bottom: 4px;
  }}
  #detail-panel .dp-meta {{
    font-size: 12px; color: #7d8590; margin-bottom: 16px;
  }}
  #detail-panel .dp-section {{
    margin-bottom: 16px;
  }}
  #detail-panel .dp-section h3 {{
    font-size: 13px; color: #7d8590; text-transform: uppercase;
    letter-spacing: 1px; margin-bottom: 8px;
    border-bottom: 1px solid #21262d; padding-bottom: 4px;
  }}
  #detail-panel .dp-section p,
  #detail-panel .dp-section li {{
    font-size: 13px; line-height: 1.7; color: #c9d1d9;
  }}
  #detail-panel .dp-section ul {{ padding-left: 18px; }}
  #detail-panel .dp-choice {{
    background: #0d1117; border: 1px solid #30363d;
    border-radius: 6px; padding: 10px 12px; margin-bottom: 8px;
  }}
  #detail-panel .dp-choice .choice-text {{
    font-size: 13px; color: #79c0ff; font-weight: 500;
  }}
  #detail-panel .dp-choice .choice-hint {{
    font-size: 12px; color: #7d8590; margin-top: 4px;
  }}
  #detail-panel .dp-choice .choice-effects {{
    font-size: 11px; color: #3fb950; margin-top: 4px;
  }}
  .dp-tag {{
    display: inline-block; font-size: 11px; padding: 2px 8px;
    border-radius: 10px; margin-right: 6px;
  }}

  #controls {{
    position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
    z-index: 100; display: flex; gap: 8px;
  }}
  #controls button {{
    background: #21262d; border: 1px solid #30363d; color: #c9d1d9;
    padding: 6px 14px; border-radius: 6px; font-size: 12px;
    cursor: pointer; transition: background 0.15s;
  }}
  #controls button:hover {{ background: #30363d; }}

  #minimap {{
    position: fixed; bottom: 20px; right: 24px; z-index: 100;
    width: 160px; height: 120px;
    background: rgba(22,27,34,0.9); border: 1px solid #30363d;
    border-radius: 6px; overflow: hidden;
  }}
  #detail-panel .dp-choice .choice-gate {{
    font-size: 11px; color: #d29922; margin-top: 4px;
    padding: 2px 6px; background: #d2992215; border: 1px dashed #d2992244;
    border-radius: 4px; display: inline-block;
  }}
  #detail-panel .dp-section .gate-info {{
    font-size: 12px; color: #d29922; margin-top: 4px;
    padding: 6px 10px; background: #d2992210; border: 1px dashed #d2992233;
    border-radius: 6px;
  }}
  .value-badge {{
    font-size: 9px; fill: #3fb950;
  }}
  .gate-badge {{
    font-size: 9px; fill: #d29922;
  }}
</style>
</head>
<body>

<div id="header">
  <h1>{title}</h1>
  <div class="subtitle">{subtitle}</div>
</div>

<div id="legend">
  <div class="legend-item"><div class="legend-dot" style="background:#58a6ff"></div>叙事</div>
  <div class="legend-item"><div class="legend-dot" style="background:#d29922"></div>选择点</div>
  <div class="legend-item"><div class="legend-dot" style="background:#3fb950"></div>合流点</div>
  <div class="legend-item"><div class="legend-dot" style="background:#f0883e"></div>分支点</div>
  <div class="legend-item"><div class="legend-dot" style="background:#f85149"></div>死亡结局</div>
  <div class="legend-item"><div class="legend-dot" style="background:#a371f7"></div>结局</div>
  <div class="legend-item"><div class="legend-dot" style="background:#d2992233;border:2px dashed #d29922;width:10px;height:10px"></div>数值门控</div>
</div>

<svg id="canvas"></svg>
<div id="tooltip"></div>
<div id="detail-panel">
  <button class="close-btn" onclick="closePanel()">&times;</button>
  <div id="detail-content"></div>
</div>

<div id="controls">
  <button onclick="zoomIn()">放大 +</button>
  <button onclick="zoomOut()">缩小 −</button>
  <button onclick="resetView()">重置视图</button>
  <button onclick="toggleLabels()">切换标签</button>
</div>

<script>
const storyData = {data_json};

const typeColors = {{
  narrative: "#58a6ff",
  choice: "#d29922",
  merge_point: "#3fb950",
  branch_point: "#f0883e",
  dead_end: "#f85149",
  ending: "#a371f7"
}};

const typeLabels = {{
  narrative: "叙事",
  choice: "选择点",
  merge_point: "合流点",
  branch_point: "分支点",
  dead_end: "死亡结局",
  ending: "结局"
}};

const actColors = ["#264653", "#2a6f4e", "#6b4c2e", "#5a2d5e", "#3d2e5e", "#2e4a5e", "#5e3d2e", "#2e5e3d"];

const nodes = storyData.nodes;
const nodeIds = Object.keys(nodes);

// Layout — BFS from entry node
const layerMap = {{}};
const nodeLayer = {{}};
const nodeCol = {{}};

function computeLayout() {{
  const visited = new Set();
  const entryId = storyData.entry_node_id || nodeIds[0];
  const queue = [{{ id: entryId, layer: 0 }}];
  visited.add(entryId);

  while (queue.length > 0) {{
    const {{ id, layer }} = queue.shift();
    if (!layerMap[layer]) layerMap[layer] = [];
    layerMap[layer].push(id);
    nodeLayer[id] = layer;

    const node = nodes[id];
    if (!node) continue;
    for (const nxt of (node.next_nodes || [])) {{
      if (!visited.has(nxt) && nodes[nxt]) {{
        visited.add(nxt);
        queue.push({{ id: nxt, layer: layer + 1 }});
      }}
    }}
  }}

  // 处理未被 BFS 访问到的孤立节点
  for (const id of nodeIds) {{
    if (!visited.has(id)) {{
      const maxLayer = Math.max(0, ...Object.keys(layerMap).map(Number)) + 1;
      if (!layerMap[maxLayer]) layerMap[maxLayer] = [];
      layerMap[maxLayer].push(id);
      nodeLayer[id] = maxLayer;
    }}
  }}

  // Assign columns
  for (const layer of Object.keys(layerMap).sort((a,b) => a - b)) {{
    const ids = layerMap[layer];
    const count = ids.length;
    ids.forEach((id, i) => {{
      nodeCol[id] = i - (count - 1) / 2;
    }});
  }}
}}

computeLayout();

const LAYER_H = 130;
const COL_W = 200;
const NODE_R = 24;
const PADDING_TOP = 100;
const totalLayers = Math.max(...Object.keys(layerMap).map(Number)) + 1;

// SVG setup
const svg = document.getElementById("canvas");
const svgNS = "http://www.w3.org/2000/svg";
let viewBox = {{
  x: -400,
  y: -40,
  w: 800,
  h: Math.max(window.innerHeight, totalLayers * LAYER_H + 200)
}};
let showLabels = true;

function updateViewBox() {{
  svg.setAttribute("viewBox", `${{viewBox.x}} ${{viewBox.y}} ${{viewBox.w}} ${{viewBox.h}}`);
}}
updateViewBox();

function nodeX(id) {{ return nodeCol[id] * COL_W; }}
function nodeY(id) {{ return nodeLayer[id] * LAYER_H + PADDING_TOP; }}

// Defs — arrow marker + glow filter
const defs = document.createElementNS(svgNS, "defs");

const marker = document.createElementNS(svgNS, "marker");
marker.setAttribute("id", "arrow");
marker.setAttribute("viewBox", "0 0 10 6");
marker.setAttribute("refX", "10");
marker.setAttribute("refY", "3");
marker.setAttribute("markerWidth", "8");
marker.setAttribute("markerHeight", "6");
marker.setAttribute("orient", "auto");
const arrowPath = document.createElementNS(svgNS, "path");
arrowPath.setAttribute("d", "M0,0 L10,3 L0,6 Z");
arrowPath.setAttribute("fill", "#30363d");
marker.appendChild(arrowPath);
defs.appendChild(marker);

const filter = document.createElementNS(svgNS, "filter");
filter.setAttribute("id", "glow");
const blur = document.createElementNS(svgNS, "feGaussianBlur");
blur.setAttribute("stdDeviation", "3");
blur.setAttribute("result", "blur");
filter.appendChild(blur);
const fmerge = document.createElementNS(svgNS, "feMerge");
const mn1 = document.createElementNS(svgNS, "feMergeNode"); mn1.setAttribute("in", "blur");
const mn2 = document.createElementNS(svgNS, "feMergeNode"); mn2.setAttribute("in", "SourceGraphic");
fmerge.appendChild(mn1); fmerge.appendChild(mn2);
filter.appendChild(fmerge);
defs.appendChild(filter);

svg.appendChild(defs);

// Act background shading
const actGroup = document.createElementNS(svgNS, "g");
actGroup.setAttribute("class", "acts");
const maxAct = Math.max(1, ...nodeIds.map(id => nodes[id].act || 1));
for (let act = 1; act <= maxAct; act++) {{
  const actNodes = nodeIds.filter(id => nodes[id].act === act);
  if (actNodes.length === 0) continue;
  const minY = Math.min(...actNodes.map(id => nodeY(id))) - 50;
  const maxY = Math.max(...actNodes.map(id => nodeY(id))) + 50;
  const rect = document.createElementNS(svgNS, "rect");
  rect.setAttribute("x", viewBox.x);
  rect.setAttribute("y", minY);
  rect.setAttribute("width", viewBox.w * 3);
  rect.setAttribute("height", maxY - minY);
  rect.setAttribute("fill", actColors[(act - 1) % actColors.length]);
  rect.setAttribute("opacity", "0.08");
  actGroup.appendChild(rect);

  const label = document.createElementNS(svgNS, "text");
  label.setAttribute("x", -380);
  label.setAttribute("y", minY + 22);
  label.setAttribute("fill", "#7d8590");
  label.setAttribute("font-size", "12");
  label.setAttribute("font-weight", "600");
  label.textContent = `第 ${{act}} 幕`;
  actGroup.appendChild(label);
}}
svg.appendChild(actGroup);

// Edges
const edgeGroup = document.createElementNS(svgNS, "g");
edgeGroup.setAttribute("class", "edges");

const edgeElements = [];

for (const id of nodeIds) {{
  const node = nodes[id];
  const x1 = nodeX(id);
  const y1 = nodeY(id);

  for (const nxt of (node.next_nodes || [])) {{
    if (!nodes[nxt]) continue;
    const x2 = nodeX(nxt);
    const y2 = nodeY(nxt);

    let edgeColor = "#30363d";
    let edgeLabel = "";
    let valueLabel = "";
    let gateLabel = "";
    let isDead = nodes[nxt].node_type === "dead_end";

    if (node.choices && node.choices.length > 0) {{
      const choice = node.choices.find(c => c.target_node_id === nxt);
      if (choice) {{
        if (choice.is_dead_end) {{
          edgeColor = "#f8514966";
          isDead = true;
        }} else {{
          edgeColor = "#58a6ff44";
        }}
        const shortText = choice.text.length > 20 ? choice.text.slice(0, 18) + "…" : choice.text;
        edgeLabel = shortText;

        if (choice.value_effects && choice.value_effects.length > 0) {{
          valueLabel = choice.value_effects.map(e => `${{e.attribute}}${{e.delta > 0 ? "+" : ""}}${{e.delta}}`).join(" ");
        }}
        if (choice.gate_condition) {{
          const gc = choice.gate_condition;
          gateLabel = Object.entries(gc).map(([k,v]) => `${{k}}${{v}}`).join(",");
          edgeColor = "#d2992266";
        }}
        if (choice.gate_branch) {{
          gateLabel = Object.entries(choice.gate_branch.condition).map(([k,v]) => `${{k}}${{v}}`).join(",");
          edgeColor = "#d2992266";
        }}
      }}
    }}

    if (node.auto_route) {{
      const routeEntries = Object.entries(node.auto_route).filter(([k]) => k !== "description");
      const routeEntry = routeEntries.find(([_,v]) => v === nxt);
      if (routeEntry) {{
        edgeColor = "#a371f744";
        edgeLabel = edgeLabel || routeEntry[0].replace("branch_", "").replace("condition_", "");
      }}
    }}

    const path = document.createElementNS(svgNS, "path");
    const midY = (y1 + y2) / 2;
    const cpOffset = Math.abs(x2 - x1) * 0.3;
    const d = `M${{x1}},${{y1 + NODE_R}} C${{x1}},${{midY - cpOffset}} ${{x2}},${{midY + cpOffset}} ${{x2}},${{y2 - NODE_R}}`;
    path.setAttribute("d", d);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", edgeColor);
    path.setAttribute("stroke-width", isDead ? "1.5" : "2");
    if (isDead) path.setAttribute("stroke-dasharray", "6,4");
    if (gateLabel) path.setAttribute("stroke-dasharray", "8,3");
    path.setAttribute("marker-end", "url(#arrow)");
    edgeGroup.appendChild(path);

    edgeElements.push({{ path, from: id, to: nxt }});

    if (edgeLabel && showLabels) {{
      const textEl = document.createElementNS(svgNS, "text");
      const tx = (x1 + x2) / 2 + (x2 > x1 ? 10 : x2 < x1 ? -10 : 0);
      const ty = midY - 8;
      textEl.setAttribute("x", tx);
      textEl.setAttribute("y", ty);
      textEl.setAttribute("fill", "#7d8590");
      textEl.setAttribute("font-size", "10");
      textEl.setAttribute("text-anchor", "middle");
      textEl.setAttribute("class", "edge-label");
      textEl.textContent = edgeLabel;
      edgeGroup.appendChild(textEl);
    }}

    if (valueLabel && showLabels) {{
      const valEl = document.createElementNS(svgNS, "text");
      const tx = (x1 + x2) / 2 + (x2 > x1 ? 10 : x2 < x1 ? -10 : 0);
      const ty = midY + 6;
      valEl.setAttribute("x", tx);
      valEl.setAttribute("y", ty);
      valEl.setAttribute("class", "value-badge edge-label");
      valEl.setAttribute("text-anchor", "middle");
      valEl.textContent = valueLabel;
      edgeGroup.appendChild(valEl);
    }}

    if (gateLabel && showLabels) {{
      const gateEl = document.createElementNS(svgNS, "text");
      const tx = (x1 + x2) / 2 + (x2 > x1 ? 10 : x2 < x1 ? -10 : 0);
      const ty = midY + (valueLabel ? 18 : 6);
      gateEl.setAttribute("x", tx);
      gateEl.setAttribute("y", ty);
      gateEl.setAttribute("class", "gate-badge edge-label");
      gateEl.setAttribute("text-anchor", "middle");
      gateEl.textContent = "🔒 " + gateLabel;
      edgeGroup.appendChild(gateEl);
    }}
  }}
}}
svg.appendChild(edgeGroup);

// Nodes
const nodeGroup = document.createElementNS(svgNS, "g");
nodeGroup.setAttribute("class", "nodes");

const nodeElements = {{}};

for (const id of nodeIds) {{
  const node = nodes[id];
  const x = nodeX(id);
  const y = nodeY(id);
  const color = typeColors[node.node_type] || "#58a6ff";

  const g = document.createElementNS(svgNS, "g");
  g.setAttribute("class", "node-group");
  g.setAttribute("data-id", id);
  g.style.cursor = "pointer";

  // Glow
  const glow = document.createElementNS(svgNS, "circle");
  glow.setAttribute("cx", x);
  glow.setAttribute("cy", y);
  glow.setAttribute("r", NODE_R + 4);
  glow.setAttribute("fill", color);
  glow.setAttribute("opacity", "0.15");
  g.appendChild(glow);

  // Circle
  const circle = document.createElementNS(svgNS, "circle");
  circle.setAttribute("cx", x);
  circle.setAttribute("cy", y);
  circle.setAttribute("r", NODE_R);
  circle.setAttribute("fill", "#0d1117");
  circle.setAttribute("stroke", color);
  circle.setAttribute("stroke-width", "2.5");
  g.appendChild(circle);

  // Icon
  const icon = document.createElementNS(svgNS, "text");
  icon.setAttribute("x", x);
  icon.setAttribute("y", y + 1);
  icon.setAttribute("text-anchor", "middle");
  icon.setAttribute("dominant-baseline", "central");
  icon.setAttribute("fill", color);
  icon.setAttribute("font-size", "14");
  icon.setAttribute("font-weight", "600");

  const iconMap = {{
    narrative: "◆",
    choice: "◇",
    merge_point: "⊕",
    branch_point: "⊗",
    dead_end: "✕",
    ending: "★"
  }};
  icon.textContent = iconMap[node.node_type] || "●";
  g.appendChild(icon);

  // Label
  const label = document.createElementNS(svgNS, "text");
  label.setAttribute("x", x);
  label.setAttribute("y", y + NODE_R + 16);
  label.setAttribute("text-anchor", "middle");
  label.setAttribute("fill", "#e6edf3");
  label.setAttribute("font-size", "12");
  label.setAttribute("font-weight", "500");
  label.setAttribute("class", "node-label");
  label.textContent = node.title;
  g.appendChild(label);

  // Sub-label (node_id)
  const subLabel = document.createElementNS(svgNS, "text");
  subLabel.setAttribute("x", x);
  subLabel.setAttribute("y", y + NODE_R + 30);
  subLabel.setAttribute("text-anchor", "middle");
  subLabel.setAttribute("fill", "#484f58");
  subLabel.setAttribute("font-size", "9");
  subLabel.setAttribute("class", "node-label");
  subLabel.textContent = id;
  g.appendChild(subLabel);

  g.addEventListener("mouseenter", (e) => showTooltip(e, node));
  g.addEventListener("mousemove", moveTooltip);
  g.addEventListener("mouseleave", hideTooltip);
  g.addEventListener("click", () => openPanel(node));

  nodeGroup.appendChild(g);
  nodeElements[id] = {{ g, circle, glow }};
}}
svg.appendChild(nodeGroup);

// ---- Tooltip ----
const tooltip = document.getElementById("tooltip");

function showTooltip(e, node) {{
  const color = typeColors[node.node_type] || "#58a6ff";
  let html = `<div class="tt-title">${{node.title}}</div>`;
  html += `<span class="tt-type" style="background:${{color}}22;color:${{color}};border:1px solid ${{color}}44">${{typeLabels[node.node_type] || node.node_type}}</span>`;
  html += `<span class="tt-act">第 ${{node.act}} 幕</span>`;

  if (node.emotional_tone) {{
    html += `<div style="font-size:11px;color:#7d8590;margin-top:6px">情绪基调: ${{node.emotional_tone}}</div>`;
  }}

  if (node.key_events && node.key_events.length > 0) {{
    html += `<div class="tt-events"><ul>`;
    node.key_events.slice(0, 3).forEach(ev => {{
      html += `<li>${{ev}}</li>`;
    }});
    if (node.key_events.length > 3) html += `<li style="color:#484f58">...还有 ${{node.key_events.length - 3}} 个事件</li>`;
    html += `</ul></div>`;
  }}

  if (node.choices && node.choices.length > 0) {{
    html += `<div class="tt-choices">`;
    html += `<div style="font-size:11px;color:#7d8590;margin-bottom:4px">${{node.choices.length}} 个选项</div>`;
    node.choices.forEach(c => {{
      const short = c.text.length > 40 ? c.text.slice(0, 38) + "…" : c.text;
      html += `<div class="tt-choice-item">→ ${{short}}</div>`;
    }});
    html += `</div>`;
  }}

  if (node.auto_route) {{
    html += `<div style="margin-top:6px;font-size:11px;color:#d29922">🔀 ${{node.auto_route.description || "条件路由"}}</div>`;
  }}

  if (node.ending_type) {{
    const endLabels = {{ true_ending: "真结局 ★", neutral: "中立结局", neutral_ending: "中立结局", bad_ending: "坏结局", good_ending: "好结局", hidden_ending: "隐藏结局 ✦", cold_ending: "冷酷结局 ❄", bittersweet_ending: "遗憾结局 ◌" }};
    html += `<div style="margin-top:8px;font-size:12px;color:${{color}};font-weight:600">${{endLabels[node.ending_type] || node.ending_type}}</div>`;
  }}

  if (node.death_cause) {{
    html += `<div style="margin-top:6px;font-size:12px;color:#f85149">☠ ${{node.death_cause}}</div>`;
  }}

  html += `<div style="margin-top:8px;font-size:11px;color:#484f58">点击查看详情</div>`;

  tooltip.innerHTML = html;
  tooltip.style.opacity = "1";
  moveTooltip(e);

  highlightNode(node.node_id);
}}

function moveTooltip(e) {{
  let x = e.clientX + 16;
  let y = e.clientY + 16;
  if (x + 420 > window.innerWidth) x = e.clientX - 430;
  if (y + 300 > window.innerHeight) y = e.clientY - 200;
  tooltip.style.left = x + "px";
  tooltip.style.top = y + "px";
}}

function hideTooltip() {{
  tooltip.style.opacity = "0";
  clearHighlight();
}}

function highlightNode(id) {{
  for (const nid of nodeIds) {{
    const el = nodeElements[nid];
    if (!el) continue;
    el.g.style.opacity = "0.25";
  }}
  edgeElements.forEach(e => {{ e.path.style.opacity = "0.1"; }});

  const connected = new Set([id]);
  const node = nodes[id];
  (node.next_nodes || []).forEach(n => connected.add(n));
  (node.prev_nodes || []).forEach(n => connected.add(n));

  for (const nid of connected) {{
    const el = nodeElements[nid];
    if (el) el.g.style.opacity = "1";
  }}
  edgeElements.forEach(e => {{
    if (connected.has(e.from) && connected.has(e.to)) {{
      e.path.style.opacity = "1";
    }}
  }});
}}

function clearHighlight() {{
  for (const nid of nodeIds) {{
    const el = nodeElements[nid];
    if (el) el.g.style.opacity = "1";
  }}
  edgeElements.forEach(e => {{ e.path.style.opacity = "1"; }});
}}

// ---- Detail panel ----
const panel = document.getElementById("detail-panel");
const detailContent = document.getElementById("detail-content");

function openPanel(node) {{
  const color = typeColors[node.node_type] || "#58a6ff";
  let html = `<h2>${{node.title}}</h2>`;
  html += `<div class="dp-meta">`;
  html += `<span class="dp-tag" style="background:${{color}}22;color:${{color}};border:1px solid ${{color}}44">${{typeLabels[node.node_type] || node.node_type}}</span>`;
  html += `<span class="dp-tag" style="background:#21262d;color:#7d8590">第 ${{node.act}} 幕</span>`;
  html += `<span class="dp-tag" style="background:#21262d;color:#7d8590">${{node.node_id}}</span>`;
  if (node.branch_id && node.branch_id !== "main") {{
    html += `<span class="dp-tag" style="background:#8b5cf622;color:#a371f7;border:1px solid #a371f744">${{node.branch_id}}</span>`;
  }}
  html += `</div>`;

  if (node.scene_description) {{
    html += `<div class="dp-section"><h3>场景描述</h3><p>${{node.scene_description}}</p></div>`;
  }}

  if (node.emotional_tone) {{
    html += `<div class="dp-section"><h3>情绪基调</h3><p>${{node.emotional_tone}}</p></div>`;
  }}

  if (node.key_events && node.key_events.length > 0) {{
    html += `<div class="dp-section"><h3>关键事件</h3><ul>`;
    node.key_events.forEach(ev => {{ html += `<li>${{ev}}</li>`; }});
    html += `</ul></div>`;
  }}

  if (node.facts_introduced && node.facts_introduced.length > 0) {{
    html += `<div class="dp-section"><h3>引入事实</h3><ul>`;
    node.facts_introduced.forEach(f => {{ html += `<li>${{f}}</li>`; }});
    html += `</ul></div>`;
  }}

  if (node.choices && node.choices.length > 0) {{
    html += `<div class="dp-section"><h3>选项</h3>`;
    node.choices.forEach(c => {{
      html += `<div class="dp-choice">`;
      html += `<div class="choice-text">${{c.is_dead_end ? "☠ " : "→ "}}${{c.text}}</div>`;
      if (c.hint) html += `<div class="choice-hint">${{c.hint}}</div>`;
      if (c.gate_condition) {{
        const gc = Object.entries(c.gate_condition).map(([k,v]) => `${{k}} ${{v}}`).join(", ");
        html += `<div class="choice-gate">🔒 需要: ${{gc}}</div>`;
      }}
      if (c.gate_branch) {{
        const gc = Object.entries(c.gate_branch.condition).map(([k,v]) => `${{k}} ${{v}}`).join(", ");
        html += `<div class="choice-gate">🔀 条件分支: ${{gc}} → ${{c.gate_branch.true_target}} / ${{c.gate_branch.false_target}}</div>`;
      }}
      if (c.locked_hint) {{
        html += `<div style="font-size:11px;color:#f85149;margin-top:3px">🔐 ${{c.locked_hint}}</div>`;
      }}
      if (c.value_effects && c.value_effects.length > 0) {{
        const effs = c.value_effects.map(e => `${{e.attribute}} ${{e.delta > 0 ? "+" : ""}}${{e.delta}}`).join(", ");
        html += `<div class="choice-effects">${{effs}}</div>`;
      }}
      html += `<div style="font-size:10px;color:#484f58;margin-top:3px">→ ${{c.target_node_id}} | ${{c.branch_type || ""}}</div>`;
      html += `</div>`;
    }});
    html += `</div>`;
  }}

  if (node.witnesses && node.witnesses.length > 0) {{
    const charNames = node.witnesses.map(cid => {{
      const char = (storyData.characters || []).find(c => c.char_id === cid);
      return char ? char.name : cid;
    }});
    html += `<div class="dp-section"><h3>在场角色</h3><p>${{charNames.join("、")}}</p></div>`;
  }}

  if (node.ending_type) {{
    const endLabels = {{ true_ending: "真结局 ★", neutral: "中立结局", neutral_ending: "中立结局 ○", bad_ending: "坏结局 ✕", good_ending: "好结局 ✓", hidden_ending: "隐藏结局 ✦", cold_ending: "冷酷结局 ❄", bittersweet_ending: "遗憾结局 ◌" }};
    html += `<div class="dp-section"><h3>结局类型</h3>`;
    html += `<p style="color:${{color}};font-weight:600">${{endLabels[node.ending_type] || node.ending_type}}</p>`;
    if (node.ending_condition) html += `<p style="font-size:12px;color:#7d8590;margin-top:4px">条件: ${{node.ending_condition}}</p>`;
    html += `</div>`;
  }}

  if (node.death_cause) {{
    html += `<div class="dp-section"><h3>死亡原因</h3><p style="color:#f85149">${{node.death_cause}}</p></div>`;
    if (node.death_description_hint) {{
      html += `<div class="dp-section"><h3>死亡描写提示</h3><p style="color:#8b949e">${{node.death_description_hint}}</p></div>`;
    }}
  }}

  if (node.auto_route) {{
    html += `<div class="dp-section"><h3>条件路由</h3>`;
    html += `<div class="gate-info">🔀 ${{node.auto_route.description || ""}}</div>`;
    const routeEntries = Object.entries(node.auto_route).filter(([k]) => k !== "description");
    routeEntries.forEach(([k, v]) => {{
      if (typeof v === "string") {{
        html += `<p style="font-size:12px;margin-top:4px"><span style="color:#a371f7">${{k}}</span> → <span style="color:#79c0ff">${{v}}</span></p>`;
      }} else if (typeof v === "object" && v.target) {{
        html += `<p style="font-size:12px;margin-top:4px"><span style="color:#d29922">${{Object.entries(v).filter(([kk])=>kk!=="target").map(([kk,vv])=>kk+vv).join(",")}}</span> → <span style="color:#79c0ff">${{v.target}}</span></p>`;
      }}
    }});
    html += `</div>`;
  }}

  if (node.merge_to) {{
    html += `<div class="dp-section"><h3>合流至</h3><p style="color:#3fb950">${{node.merge_to}} (${{nodes[node.merge_to]?.title || ""}})</p></div>`;
  }}

  detailContent.innerHTML = html;
  panel.classList.add("open");
}}

function closePanel() {{
  panel.classList.remove("open");
}}

// ---- Pan & Zoom ----
let isDragging = false;
let dragStart = {{ x: 0, y: 0 }};
let vbStart = {{ x: 0, y: 0 }};

svg.addEventListener("mousedown", (e) => {{
  if (e.target.closest(".node-group")) return;
  isDragging = true;
  dragStart = {{ x: e.clientX, y: e.clientY }};
  vbStart = {{ x: viewBox.x, y: viewBox.y }};
  svg.style.cursor = "grabbing";
}});

window.addEventListener("mousemove", (e) => {{
  if (!isDragging) return;
  const scale = viewBox.w / window.innerWidth;
  viewBox.x = vbStart.x - (e.clientX - dragStart.x) * scale;
  viewBox.y = vbStart.y - (e.clientY - dragStart.y) * scale;
  updateViewBox();
}});

window.addEventListener("mouseup", () => {{
  isDragging = false;
  svg.style.cursor = "default";
}});

svg.addEventListener("wheel", (e) => {{
  e.preventDefault();
  const factor = e.deltaY > 0 ? 1.1 : 0.9;
  const mx = viewBox.x + (e.clientX / window.innerWidth) * viewBox.w;
  const my = viewBox.y + (e.clientY / window.innerHeight) * viewBox.h;

  viewBox.w *= factor;
  viewBox.h *= factor;
  viewBox.x = mx - (e.clientX / window.innerWidth) * viewBox.w;
  viewBox.y = my - (e.clientY / window.innerHeight) * viewBox.h;
  updateViewBox();
}});

function zoomIn() {{
  const cx = viewBox.x + viewBox.w / 2;
  const cy = viewBox.y + viewBox.h / 2;
  viewBox.w *= 0.8; viewBox.h *= 0.8;
  viewBox.x = cx - viewBox.w / 2;
  viewBox.y = cy - viewBox.h / 2;
  updateViewBox();
}}

function zoomOut() {{
  const cx = viewBox.x + viewBox.w / 2;
  const cy = viewBox.y + viewBox.h / 2;
  viewBox.w *= 1.25; viewBox.h *= 1.25;
  viewBox.x = cx - viewBox.w / 2;
  viewBox.y = cy - viewBox.h / 2;
  updateViewBox();
}}

function resetView() {{
  viewBox = {{
    x: -400,
    y: -40,
    w: 800,
    h: Math.max(window.innerHeight, totalLayers * LAYER_H + 200)
  }};
  updateViewBox();
}}

function toggleLabels() {{
  showLabels = !showLabels;
  document.querySelectorAll(".node-label, .edge-label").forEach(el => {{
    el.style.display = showLabels ? "" : "none";
  }});
}}

// Keyboard
document.addEventListener("keydown", (e) => {{
  if (e.key === "Escape") closePanel();
}});

// Resize
window.addEventListener("resize", () => {{
  updateViewBox();
}});
</script>

</body>
</html>'''

    return html


def main():
    parser = argparse.ArgumentParser(description="Story Graph → Interactive HTML Visualizer")
    parser.add_argument("input", help="story_graph.json 路径")
    parser.add_argument("-o", "--output", default=None, help="输出 HTML 路径（默认：同目录 story_graph_viz.html）")
    parser.add_argument("--title", default=None, help="覆盖标题")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ 文件不存在: {args.input}")
        sys.exit(1)

    data = load_story_graph(args.input)
    meta = compute_metadata(data)

    output_path = args.output
    if not output_path:
        output_path = os.path.join(os.path.dirname(args.input), "story_graph_viz.html")

    html = generate_html(data, meta, title_override=args.title)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 生成完成: {output_path}")
    print(f"   标题: {meta['title']}")
    print(f"   {meta['subtitle']}")


if __name__ == "__main__":
    main()
