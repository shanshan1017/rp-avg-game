#!/usr/bin/env python3
"""Generate an interactive story tree visualization from batch rollout JSONL output.

Each JSONL line: {"seed_id", "output": {"story_graph", "narratives"}, "reward", "duration"}.
"""

import argparse
import json
import os


def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("jsonl_path", help="batch rollout JSONL file")
    parser.add_argument("--output", default=os.path.join(base_dir, "outputs", "story_tree_viz.html"))
    args = parser.parse_args()
    jsonl_path = args.jsonl_path
    out_path = args.output

    stories = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                sg = obj["output"]["story_graph"]
                narr = obj["output"]["narratives"]
                stories.append(
                    {
                        "seed_id": obj["seed_id"],
                        "story_graph": sg,
                        "narratives": narr,
                        "reward": obj["reward"],
                        "duration": obj["duration"],
                    }
                )

    stories_json = json.dumps(stories, ensure_ascii=False)
    html = get_html_template().replace("__STORIES_DATA__", stories_json)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated: {out_path}")
    print(f"File size: {os.path.getsize(out_path)} bytes")


def get_html_template():
    return r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>互动小说 — 故事树可视化</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
  background: #0d1117;
  color: #c9d1d9;
  overflow: hidden;
}

#header {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  background: linear-gradient(180deg, rgba(13,17,23,0.97) 80%, rgba(13,17,23,0));
  padding: 16px 28px 32px;
  pointer-events: none;
  display: flex; align-items: flex-start; gap: 20px;
}
#header h1 {
  font-size: 20px; font-weight: 700; color: #e6edf3;
  pointer-events: auto; white-space: nowrap;
}
#header .subtitle {
  font-size: 13px; color: #7d8590; margin-top: 5px;
  pointer-events: auto;
}
#story-selector {
  pointer-events: auto;
  background: #161b22; color: #c9d1d9;
  border: 1px solid #30363d; border-radius: 8px;
  padding: 8px 14px; font-size: 14px;
  cursor: pointer; outline: none; margin-top: 2px;
}
#story-selector:hover { border-color: #58a6ff; }

#legend {
  position: fixed; top: 18px; right: 28px; z-index: 100;
  display: flex; gap: 14px; flex-wrap: wrap; align-items: center;
  font-size: 12px; color: #7d8590;
}
.legend-item { display: flex; align-items: center; gap: 6px; }
.legend-dot { width: 12px; height: 12px; border-radius: 50%; }

#canvas { width: 100vw; height: 100vh; cursor: grab; }
#canvas:active { cursor: grabbing; }

#tooltip {
  position: fixed; z-index: 200;
  background: #161b22; border: 1px solid #30363d;
  border-radius: 10px; padding: 16px 18px;
  max-width: 440px; font-size: 13px;
  line-height: 1.7; color: #c9d1d9;
  pointer-events: none; opacity: 0;
  transition: opacity 0.15s;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}
.tt-title { font-size: 16px; font-weight: 700; color: #e6edf3; margin-bottom: 6px; }
.tt-type {
  display: inline-block; font-size: 11px; padding: 2px 8px;
  border-radius: 10px; margin-bottom: 8px;
}
.tt-act { font-size: 11px; color: #7d8590; margin-left: 8px; }
.tt-desc { font-size: 13px; color: #8b949e; margin-top: 6px; line-height: 1.7; }
.tt-choices { margin-top: 8px; border-top: 1px solid #21262d; padding-top: 8px; }
.tt-choice-item { font-size: 12px; color: #79c0ff; margin-bottom: 3px; }

#detail-panel {
  position: fixed; top: 0; right: -560px; width: 540px; height: 100vh;
  background: #161b22; border-left: 1px solid #30363d;
  z-index: 150; transition: right 0.35s cubic-bezier(0.4,0,0.2,1);
  overflow-y: auto; padding: 28px;
}
#detail-panel.open { right: 0; }
#detail-panel .close-btn {
  position: absolute; top: 14px; right: 18px;
  background: none; border: none; color: #7d8590;
  font-size: 24px; cursor: pointer;
  width: 36px; height: 36px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
#detail-panel .close-btn:hover { color: #e6edf3; background: #21262d; }
#detail-panel h2 { font-size: 20px; color: #e6edf3; margin-bottom: 6px; line-height: 1.3; }
.dp-meta {
  font-size: 12px; color: #7d8590; margin-bottom: 20px;
  display: flex; gap: 8px; flex-wrap: wrap;
}
.dp-tag {
  display: inline-block; font-size: 11px; padding: 3px 10px;
  border-radius: 10px; font-weight: 500;
}
.dp-section { margin-bottom: 20px; }
.dp-section h3 {
  font-size: 13px; color: #7d8590; text-transform: uppercase;
  letter-spacing: 1px; margin-bottom: 10px;
  border-bottom: 1px solid #21262d; padding-bottom: 5px;
  font-weight: 600;
}
.dp-section p,
.dp-section li {
  font-size: 14px; line-height: 1.8; color: #c9d1d9;
}
.dp-section ul { padding-left: 20px; }
.dp-narrative {
  font-size: 14px; line-height: 2; color: #c9d1d9;
  padding: 16px 20px;
  background: #0d1117; border: 1px solid #21262d;
  border-radius: 10px;
  max-height: 50vh; overflow-y: auto;
  white-space: pre-wrap;
}
.dp-choice {
  background: #0d1117; border: 1px solid #30363d;
  border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;
  cursor: pointer; transition: all 0.15s;
}
.dp-choice:hover { border-color: #58a6ff; background: #161b2a; }
.dp-choice .choice-text { font-size: 14px; color: #79c0ff; font-weight: 500; line-height: 1.5; }
.dp-choice .choice-hint { font-size: 12px; color: #7d8590; margin-top: 5px; line-height: 1.5; }
.dp-choice .choice-effects { font-size: 12px; color: #3fb950; margin-top: 5px; }
.dp-choice.dead-choice { border-color: #f8514944; }
.dp-choice.dead-choice .choice-text { color: #f85149; }

.dp-characters { display: flex; flex-wrap: wrap; gap: 8px; }
.dp-char-tag {
  font-size: 13px; padding: 4px 12px;
  background: #a371f715; border: 1px solid #a371f730;
  border-radius: 20px; color: #a371f7;
}
.dp-facts { display: flex; flex-direction: column; gap: 8px; }
.dp-fact {
  font-size: 13px; padding: 10px 14px; line-height: 1.6;
  background: #58a6ff08; border-left: 3px solid #58a6ff;
  border-radius: 0 8px 8px 0; color: #c9d1d9;
}
.dp-death {
  padding: 14px 16px; background: #f8514910;
  border: 1px solid #f8514930; border-radius: 10px;
  color: #f85149; font-size: 14px; line-height: 1.7;
}
.dp-ending {
  padding: 14px 16px; border-radius: 10px;
  font-size: 15px; line-height: 1.6; font-weight: 600;
}

.dp-next { display: flex; flex-wrap: wrap; gap: 8px; }
.dp-next-link {
  font-size: 13px; padding: 6px 14px;
  background: #21262d; border: 1px solid #30363d;
  border-radius: 8px; color: #79c0ff;
  cursor: pointer; transition: all 0.15s;
}
.dp-next-link:hover { border-color: #58a6ff; background: #161b2a; }

#controls {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  z-index: 100; display: flex; gap: 8px;
}
#controls button {
  background: #21262d; border: 1px solid #30363d; color: #c9d1d9;
  padding: 8px 16px; border-radius: 8px; font-size: 13px;
  cursor: pointer; transition: all 0.15s; font-weight: 500;
}
#controls button:hover { background: #30363d; border-color: #484f58; }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #484f58; }

.value-badge { font-size: 10px; fill: #3fb950; }
.edge-label { pointer-events: none; }
</style>
</head>
<body>

<div id="header">
  <div>
    <h1 id="title">互动小说故事树</h1>
    <div class="subtitle" id="subtitle"></div>
  </div>
  <select id="story-selector"></select>
</div>

<div id="legend">
  <div class="legend-item"><div class="legend-dot" style="background:#58a6ff"></div>叙事</div>
  <div class="legend-item"><div class="legend-dot" style="background:#d29922"></div>选择</div>
  <div class="legend-item"><div class="legend-dot" style="background:#f85149"></div>死亡</div>
  <div class="legend-item"><div class="legend-dot" style="background:#a371f7"></div>结局</div>
  <div class="legend-item"><div class="legend-dot" style="background:#3fb950"></div>门控</div>
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
const STORIES = __STORIES_DATA__;

const typeColors = {
  narrative: "#58a6ff",
  choice: "#d29922",
  dead_end: "#f85149",
  ending: "#a371f7",
  gate: "#3fb950",
  condition_gate: "#3fb950",
  merge_point: "#3fb950",
  branch_point: "#f0883e"
};
const typeLabels = {
  narrative: "叙事",
  choice: "选择",
  dead_end: "死亡结局",
  ending: "结局",
  gate: "门控",
  condition_gate: "条件门控"
};
const typeIcons = {
  narrative: "\u25c6",
  choice: "\u25c7",
  dead_end: "\u2715",
  ending: "\u2605",
  gate: "\u2295",
  condition_gate: "\u2295"
};
const endingLabels = {
  good_ending: "\ud83c\udf1f 好结局",
  bad_ending: "\ud83d\udc80 坏结局",
  true_ending: "\u2728 真结局",
  neutral_ending: "\u2696\ufe0f 中性结局",
  hidden_ending: "\ud83d\udd2e 隐藏结局"
};

let currentStory = null;
let showLabels = true;
let viewBox = { x: 0, y: 0, w: 800, h: 600 };

const LAYER_H = 120;
const COL_W = 180;
const NODE_R = 22;
const PADDING_TOP = 80;

const svgNS = "http://www.w3.org/2000/svg";
const svg = document.getElementById("canvas");
const tooltip = document.getElementById("tooltip");
const panel = document.getElementById("detail-panel");
const detailContent = document.getElementById("detail-content");

let nodePositions = {};
let nodeElements = {};
let edgeElements = [];
let nodeIds = [];
let nodes = {};
let narratives = {};

// Selector
const sel = document.getElementById("story-selector");
STORIES.forEach((s, i) => {
  const opt = document.createElement("option");
  opt.value = i;
  opt.textContent = s.story_graph.title + " (" + s.seed_id + ")";
  sel.appendChild(opt);
});
sel.addEventListener("change", () => loadStory(parseInt(sel.value)));

function loadStory(idx) {
  currentStory = STORIES[idx];
  const sg = currentStory.story_graph;
  nodes = sg.nodes;
  narratives = currentStory.narratives;
  nodeIds = Object.keys(nodes);

  document.getElementById("title").textContent = sg.title;

  const nt = {};
  nodeIds.forEach(id => { const t = nodes[id].node_type; nt[t] = (nt[t]||0)+1; });
  document.getElementById("subtitle").textContent =
    nodeIds.length + " 个节点 \u00b7 " +
    (nt.choice||0) + " 个选择点 \u00b7 " +
    (nt.ending||0) + " 种结局 \u00b7 " +
    (nt.dead_end||0) + " 个死结局";

  computeLayout(sg);
  renderSVG(sg);
  closePanel();

  resetView();
}

function computeLayout(sg) {
  const layerMap = {};
  const nodeLayer = {};
  const nodeCol = {};
  const visited = new Set();
  const entryId = sg.entry_node_id || nodeIds[0];
  const queue = [{ id: entryId, layer: 0 }];
  visited.add(entryId);

  while (queue.length > 0) {
    const { id, layer } = queue.shift();
    if (!nodes[id]) continue;
    if (!layerMap[layer]) layerMap[layer] = [];
    layerMap[layer].push(id);
    nodeLayer[id] = layer;

    const node = nodes[id];
    const nexts = [];
    if (node.choices) node.choices.forEach(c => { if (c.target_node_id) nexts.push(c.target_node_id); });
    (node.next_nodes || []).forEach(nid => nexts.push(nid));

    nexts.forEach(nid => {
      if (!visited.has(nid) && nodes[nid]) {
        visited.add(nid);
        queue.push({ id: nid, layer: layer + 1 });
      }
    });
  }

  nodeIds.forEach(id => {
    if (!visited.has(id)) {
      const maxL = Math.max(0, ...Object.keys(layerMap).map(Number)) + 1;
      if (!layerMap[maxL]) layerMap[maxL] = [];
      layerMap[maxL].push(id);
      nodeLayer[id] = maxL;
    }
  });

  Object.keys(layerMap).sort((a,b) => a-b).forEach(layer => {
    const ids = layerMap[layer];
    ids.forEach((id, i) => {
      nodeCol[id] = i - (ids.length - 1) / 2;
    });
  });

  nodePositions = {};
  nodeIds.forEach(id => {
    nodePositions[id] = {
      x: (nodeCol[id] || 0) * COL_W,
      y: (nodeLayer[id] || 0) * LAYER_H + PADDING_TOP
    };
  });
}

function renderSVG(sg) {
  svg.innerHTML = "";
  nodeElements = {};
  edgeElements = [];

  // Defs
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

  // Act backgrounds
  const actGroup = document.createElementNS(svgNS, "g");
  const actColors = ["#264653", "#2a6f4e", "#6b4c2e", "#5a2d5e"];
  const maxAct = Math.max(1, ...nodeIds.map(id => nodes[id].act || 1));
  for (let act = 1; act <= maxAct; act++) {
    const actNodes = nodeIds.filter(id => nodes[id].act === act);
    if (actNodes.length === 0) continue;
    const minY = Math.min(...actNodes.map(id => nodePositions[id].y)) - 45;
    const maxY = Math.max(...actNodes.map(id => nodePositions[id].y)) + 45;
    const rect = document.createElementNS(svgNS, "rect");
    rect.setAttribute("x", -5000);
    rect.setAttribute("y", minY);
    rect.setAttribute("width", 10000);
    rect.setAttribute("height", maxY - minY);
    rect.setAttribute("fill", actColors[(act-1) % actColors.length]);
    rect.setAttribute("opacity", "0.07");
    actGroup.appendChild(rect);

    const label = document.createElementNS(svgNS, "text");
    label.setAttribute("x", -380);
    label.setAttribute("y", minY + 20);
    label.setAttribute("fill", "#7d8590");
    label.setAttribute("font-size", "12");
    label.setAttribute("font-weight", "600");
    label.textContent = "\u7b2c " + act + " \u5e55";
    actGroup.appendChild(label);
  }
  svg.appendChild(actGroup);

  // Edges
  const edgeGroup = document.createElementNS(svgNS, "g");
  nodeIds.forEach(id => {
    const node = nodes[id];
    const p1 = nodePositions[id];
    if (!p1) return;

    (node.next_nodes || []).forEach(nxt => {
      if (!nodes[nxt] || !nodePositions[nxt]) return;
      const p2 = nodePositions[nxt];

      let edgeColor = "#30363d";
      let edgeLabel = "";
      let valueLabel = "";
      let isDead = nodes[nxt].node_type === "dead_end";

      if (node.choices && node.choices.length > 0) {
        const choice = node.choices.find(c => c.target_node_id === nxt);
        if (choice) {
          isDead = isDead || choice.is_dead_end;
          edgeColor = isDead ? "#f8514966" : "#58a6ff44";
          const t = choice.text;
          edgeLabel = t.length > 18 ? t.slice(0, 16) + "\u2026" : t;
          if (choice.value_changes && choice.value_changes.length > 0) {
            valueLabel = choice.value_changes.map(e =>
              e.dimension + (e.delta > 0 ? "+" : "") + e.delta
            ).join(" ");
          }
        }
      }

      const midY = (p1.y + p2.y) / 2;
      const cpOff = Math.abs(p2.x - p1.x) * 0.3;
      const d = "M" + p1.x + "," + (p1.y + NODE_R) +
        " C" + p1.x + "," + (midY - cpOff) +
        " " + p2.x + "," + (midY + cpOff) +
        " " + p2.x + "," + (p2.y - NODE_R);

      const path = document.createElementNS(svgNS, "path");
      path.setAttribute("d", d);
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", edgeColor);
      path.setAttribute("stroke-width", isDead ? "1.5" : "2");
      if (isDead) path.setAttribute("stroke-dasharray", "6,4");
      path.setAttribute("marker-end", "url(#arrow)");
      edgeGroup.appendChild(path);
      edgeElements.push({ path, from: id, to: nxt });

      if (edgeLabel) {
        const tx = (p1.x + p2.x) / 2 + (p2.x > p1.x ? 12 : p2.x < p1.x ? -12 : 0);
        const ty = midY - 6;
        const textEl = document.createElementNS(svgNS, "text");
        textEl.setAttribute("x", tx);
        textEl.setAttribute("y", ty);
        textEl.setAttribute("fill", "#7d8590");
        textEl.setAttribute("font-size", "10");
        textEl.setAttribute("text-anchor", "middle");
        textEl.setAttribute("class", "edge-label");
        textEl.textContent = edgeLabel;
        edgeGroup.appendChild(textEl);
      }

      if (valueLabel) {
        const tx = (p1.x + p2.x) / 2 + (p2.x > p1.x ? 12 : p2.x < p1.x ? -12 : 0);
        const ty = midY + 8;
        const valEl = document.createElementNS(svgNS, "text");
        valEl.setAttribute("x", tx);
        valEl.setAttribute("y", ty);
        valEl.setAttribute("class", "value-badge edge-label");
        valEl.setAttribute("text-anchor", "middle");
        valEl.textContent = valueLabel;
        edgeGroup.appendChild(valEl);
      }
    });
  });
  svg.appendChild(edgeGroup);

  // Nodes
  const nodeGroup = document.createElementNS(svgNS, "g");
  nodeIds.forEach(id => {
    const node = nodes[id];
    const pos = nodePositions[id];
    if (!pos) return;
    const color = typeColors[node.node_type] || "#58a6ff";

    const g = document.createElementNS(svgNS, "g");
    g.setAttribute("data-id", id);
    g.style.cursor = "pointer";

    const glow = document.createElementNS(svgNS, "circle");
    glow.setAttribute("cx", pos.x);
    glow.setAttribute("cy", pos.y);
    glow.setAttribute("r", NODE_R + 4);
    glow.setAttribute("fill", color);
    glow.setAttribute("opacity", "0.15");
    g.appendChild(glow);

    const circle = document.createElementNS(svgNS, "circle");
    circle.setAttribute("cx", pos.x);
    circle.setAttribute("cy", pos.y);
    circle.setAttribute("r", NODE_R);
    circle.setAttribute("fill", "#0d1117");
    circle.setAttribute("stroke", color);
    circle.setAttribute("stroke-width", "2.5");
    g.appendChild(circle);

    const icon = document.createElementNS(svgNS, "text");
    icon.setAttribute("x", pos.x);
    icon.setAttribute("y", pos.y + 1);
    icon.setAttribute("text-anchor", "middle");
    icon.setAttribute("dominant-baseline", "central");
    icon.setAttribute("fill", color);
    icon.setAttribute("font-size", "14");
    icon.setAttribute("font-weight", "600");
    icon.textContent = typeIcons[node.node_type] || "\u25cf";
    g.appendChild(icon);

    const label = document.createElementNS(svgNS, "text");
    label.setAttribute("x", pos.x);
    label.setAttribute("y", pos.y + NODE_R + 16);
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("fill", "#e6edf3");
    label.setAttribute("font-size", "12");
    label.setAttribute("font-weight", "500");
    label.setAttribute("class", "node-label");
    const titleText = node.title || id;
    label.textContent = titleText.length > 10 ? titleText.slice(0,9) + "\u2026" : titleText;
    g.appendChild(label);

    const subLabel = document.createElementNS(svgNS, "text");
    subLabel.setAttribute("x", pos.x);
    subLabel.setAttribute("y", pos.y + NODE_R + 29);
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
    nodeElements[id] = { g, circle, glow };
  });
  svg.appendChild(nodeGroup);
}

// Tooltip
function showTooltip(e, node) {
  const color = typeColors[node.node_type] || "#58a6ff";
  let html = '<div class="tt-title">' + esc(node.title) + '</div>';
  html += '<span class="tt-type" style="background:' + color + '22;color:' + color + ';border:1px solid ' + color + '44">' + (typeLabels[node.node_type] || node.node_type) + '</span>';
  html += '<span class="tt-act">\u7b2c ' + node.act + ' \u5e55 \u00b7 ' + node.node_id + '</span>';

  if (node.scene_description) {
    const desc = node.scene_description.length > 120 ? node.scene_description.slice(0, 118) + "\u2026" : node.scene_description;
    html += '<div class="tt-desc">' + esc(desc) + '</div>';
  }

  if (node.choices && node.choices.length > 0) {
    html += '<div class="tt-choices">';
    html += '<div style="font-size:11px;color:#7d8590;margin-bottom:4px">' + node.choices.length + ' \u4e2a\u9009\u9879</div>';
    node.choices.forEach(c => {
      const short = c.text.length > 35 ? c.text.slice(0, 33) + "\u2026" : c.text;
      html += '<div class="tt-choice-item">\u2192 ' + esc(short) + '</div>';
    });
    html += '</div>';
  }

  if (node.ending_type) {
    html += '<div style="margin-top:8px;font-size:13px;color:' + color + ';font-weight:600">' + (endingLabels[node.ending_type] || node.ending_type) + '</div>';
  }

  if (node.death_cause) {
    html += '<div style="margin-top:6px;font-size:12px;color:#f85149">\u2620 ' + esc(node.death_cause) + '</div>';
  }

  html += '<div style="margin-top:8px;font-size:11px;color:#484f58">\u70b9\u51fb\u67e5\u770b\u8be6\u60c5</div>';

  tooltip.innerHTML = html;
  tooltip.style.opacity = "1";
  moveTooltip(e);
  highlightNode(node.node_id);
}

function moveTooltip(e) {
  let x = e.clientX + 18;
  let y = e.clientY + 18;
  if (x + 440 > window.innerWidth) x = e.clientX - 450;
  if (y + 300 > window.innerHeight) y = e.clientY - 200;
  tooltip.style.left = x + "px";
  tooltip.style.top = y + "px";
}

function hideTooltip() {
  tooltip.style.opacity = "0";
  clearHighlight();
}

function highlightNode(id) {
  nodeIds.forEach(nid => {
    const el = nodeElements[nid];
    if (el) el.g.style.opacity = "0.2";
  });
  edgeElements.forEach(e => { e.path.style.opacity = "0.1"; });

  const connected = new Set([id]);
  const node = nodes[id];
  (node.next_nodes || []).forEach(n => connected.add(n));
  if (node.choices) node.choices.forEach(c => { if (c.target_node_id) connected.add(c.target_node_id); });
  nodeIds.forEach(nid => {
    const n = nodes[nid];
    if ((n.next_nodes || []).includes(id)) connected.add(nid);
    if (n.choices) n.choices.forEach(c => { if (c.target_node_id === id) connected.add(nid); });
  });

  connected.forEach(nid => {
    const el = nodeElements[nid];
    if (el) el.g.style.opacity = "1";
  });
  edgeElements.forEach(e => {
    if (connected.has(e.from) && connected.has(e.to)) e.path.style.opacity = "1";
  });
}

function clearHighlight() {
  nodeIds.forEach(nid => {
    const el = nodeElements[nid];
    if (el) el.g.style.opacity = "1";
  });
  edgeElements.forEach(e => { e.path.style.opacity = "1"; });
}

// Detail panel
function openPanel(node) {
  const color = typeColors[node.node_type] || "#58a6ff";
  let html = '<h2>' + esc(node.title || node.node_id) + '</h2>';
  html += '<div class="dp-meta">';
  html += '<span class="dp-tag" style="background:' + color + '22;color:' + color + ';border:1px solid ' + color + '44">' + (typeLabels[node.node_type] || node.node_type) + '</span>';
  html += '<span class="dp-tag" style="background:#21262d;color:#7d8590">\u7b2c ' + node.act + ' \u5e55</span>';
  html += '<span class="dp-tag" style="background:#21262d;color:#7d8590">' + node.node_id + '</span>';
  html += '</div>';

  if (node.scene_description) {
    html += '<div class="dp-section"><h3>\u573a\u666f\u63cf\u8ff0</h3><p>' + esc(node.scene_description) + '</p></div>';
  }

  if (node.characters_present && node.characters_present.length > 0) {
    html += '<div class="dp-section"><h3>\u5728\u573a\u4eba\u7269</h3><div class="dp-characters">';
    node.characters_present.forEach(c => {
      html += '<span class="dp-char-tag">' + esc(c) + '</span>';
    });
    html += '</div></div>';
  }

  // Narrative text
  const narrativeData = narratives[node.node_id];
  const narrativeText = narrativeData
    ? (typeof narrativeData === "string" ? narrativeData : narrativeData.narrative_text || "")
    : "";
  if (narrativeText) {
    html += '<div class="dp-section"><h3>\u53d9\u4e8b\u6587\u672c</h3><div class="dp-narrative">' + esc(narrativeText) + '</div></div>';
  }

  if (node.choices && node.choices.length > 0) {
    html += '<div class="dp-section"><h3>\u73a9\u5bb6\u9009\u62e9</h3>';
    node.choices.forEach(c => {
      const isDead = c.is_dead_end;
      html += '<div class="dp-choice ' + (isDead ? 'dead-choice' : '') + '" onclick="navigateToNode(\'' + c.target_node_id + '\')">';
      html += '<div class="choice-text">' + (isDead ? '\u2620 ' : '\u2192 ') + esc(c.text) + '</div>';
      if (c.value_changes && c.value_changes.length > 0) {
        html += '<div class="choice-effects">' + c.value_changes.map(e =>
          e.dimension + (e.delta > 0 ? " +" : " ") + e.delta
        ).join("  \u00b7  ") + '</div>';
      }
      html += '<div style="font-size:11px;color:#484f58;margin-top:3px">\u2192 ' + c.target_node_id + (isDead ? ' \u26a0\ufe0f \u6b7b\u4ea1\u8def\u7ebf' : '') + '</div>';
      html += '</div>';
    });
    html += '</div>';
  }

  if (node.node_type === "dead_end" && node.death_cause) {
    html += '<div class="dp-section"><h3>\u6b7b\u4ea1\u4fe1\u606f</h3>';
    html += '<div class="dp-death"><strong>\u6b7b\u56e0\uff1a</strong>' + esc(node.death_cause);
    if (node.death_description_hint) html += '<br/><br/>' + esc(node.death_description_hint);
    html += '</div></div>';
  }

  if (node.node_type === "ending" && node.ending_type) {
    html += '<div class="dp-section"><h3>\u7ed3\u5c40\u7c7b\u578b</h3>';
    html += '<div class="dp-ending" style="color:' + color + ';background:' + color + '10;border:1px solid ' + color + '30">';
    html += (endingLabels[node.ending_type] || node.ending_type);
    if (node.value_conditions && node.value_conditions.length > 0) {
      html += '<div style="font-size:12px;margin-top:6px;color:#7d8590">\u89e6\u53d1\u6761\u4ef6\uff1a' +
        node.value_conditions.map(vc => vc.dimension + " " + vc.operator + " " + vc.value).join(", ") + '</div>';
    }
    html += '</div></div>';
  }

  if (node.knowledge_facts && node.knowledge_facts.length > 0) {
    html += '<div class="dp-section"><h3>\u77e5\u8bc6\u7ebf\u7d22</h3><div class="dp-facts">';
    node.knowledge_facts.forEach(f => {
      html += '<div class="dp-fact"><strong>' + f.fact_id + '\uff1a</strong>' + esc(f.content) +
        '<br/><span style="font-size:11px;color:#484f58">\u76ee\u51fb\u8005\uff1a' + (f.witnesses || []).join("\u3001") + '</span></div>';
    });
    html += '</div></div>';
  }

  if (node.next_nodes && node.next_nodes.length > 0 && !node.choices) {
    html += '<div class="dp-section"><h3>\u540e\u7eed\u8282\u70b9</h3><div class="dp-next">';
    node.next_nodes.forEach(nid => {
      const nn = nodes[nid];
      html += '<span class="dp-next-link" onclick="navigateToNode(\'' + nid + '\')">' + (nn ? esc(nn.title) : nid) + '</span>';
    });
    html += '</div></div>';
  }

  if (node.merge_to) {
    const mn = nodes[node.merge_to];
    html += '<div class="dp-section"><h3>\u5408\u5e76\u81f3</h3><div class="dp-next">';
    html += '<span class="dp-next-link" onclick="navigateToNode(\'' + node.merge_to + '\')">' + (mn ? esc(mn.title) : node.merge_to) + '</span>';
    html += '</div></div>';
  }

  detailContent.innerHTML = html;
  panel.classList.add("open");
}

function closePanel() { panel.classList.remove("open"); }

function navigateToNode(nodeId) {
  if (!nodes[nodeId]) return;
  const pos = nodePositions[nodeId];
  if (pos) {
    viewBox.x = pos.x - viewBox.w / 2;
    viewBox.y = pos.y - viewBox.h / 2;
    updateViewBox();
  }
  openPanel(nodes[nodeId]);
}

function esc(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Pan & Zoom
let isDragging = false;
let dragStart = { x: 0, y: 0 };
let vbStart = { x: 0, y: 0 };

svg.addEventListener("mousedown", (e) => {
  if (e.target.closest("[data-id]")) return;
  isDragging = true;
  dragStart = { x: e.clientX, y: e.clientY };
  vbStart = { x: viewBox.x, y: viewBox.y };
});

window.addEventListener("mousemove", (e) => {
  if (!isDragging) return;
  const scale = viewBox.w / window.innerWidth;
  viewBox.x = vbStart.x - (e.clientX - dragStart.x) * scale;
  viewBox.y = vbStart.y - (e.clientY - dragStart.y) * scale;
  updateViewBox();
});

window.addEventListener("mouseup", () => { isDragging = false; });

svg.addEventListener("wheel", (e) => {
  e.preventDefault();
  const factor = e.deltaY > 0 ? 1.12 : 0.89;
  const mx = viewBox.x + (e.clientX / window.innerWidth) * viewBox.w;
  const my = viewBox.y + (e.clientY / window.innerHeight) * viewBox.h;
  viewBox.w *= factor;
  viewBox.h *= factor;
  viewBox.x = mx - (e.clientX / window.innerWidth) * viewBox.w;
  viewBox.y = my - (e.clientY / window.innerHeight) * viewBox.h;
  updateViewBox();
});

function updateViewBox() {
  svg.setAttribute("viewBox", viewBox.x + " " + viewBox.y + " " + viewBox.w + " " + viewBox.h);
}

function zoomIn() {
  const cx = viewBox.x + viewBox.w / 2;
  const cy = viewBox.y + viewBox.h / 2;
  viewBox.w *= 0.75; viewBox.h *= 0.75;
  viewBox.x = cx - viewBox.w / 2;
  viewBox.y = cy - viewBox.h / 2;
  updateViewBox();
}

function zoomOut() {
  const cx = viewBox.x + viewBox.w / 2;
  const cy = viewBox.y + viewBox.h / 2;
  viewBox.w *= 1.35; viewBox.h *= 1.35;
  viewBox.x = cx - viewBox.w / 2;
  viewBox.y = cy - viewBox.h / 2;
  updateViewBox();
}

function resetView() {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  nodeIds.forEach(id => {
    const p = nodePositions[id];
    if (p) {
      minX = Math.min(minX, p.x);
      maxX = Math.max(maxX, p.x);
      minY = Math.min(minY, p.y);
      maxY = Math.max(maxY, p.y);
    }
  });
  const pad = 120;
  viewBox = {
    x: minX - pad,
    y: minY - pad,
    w: Math.max(800, maxX - minX + pad * 2),
    h: Math.max(600, maxY - minY + pad * 2)
  };
  updateViewBox();
}

function toggleLabels() {
  showLabels = !showLabels;
  document.querySelectorAll(".node-label, .edge-label").forEach(el => {
    el.style.display = showLabels ? "" : "none";
  });
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closePanel();
});

window.addEventListener("resize", updateViewBox);

loadStory(0);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
