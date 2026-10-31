(function () {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));
  const els = {
    appShell: $(".app-shell"),
    title: $("#game-title"),
    packageId: $("#package-id"),
    kicker: $(".kicker"),
    homeTitle: $("#home-title"),
    homeDescription: $("#home-description"),
    homeBackdrop: $("#home-backdrop"),
    homeMetaPanel: $(".home-meta-panel"),
    homeStats: $("#home-stats"),
    capabilityStrip: $("#capability-strip"),
    homeTab: $("#home-tab"),
    playTab: $("#play-tab"),
    worldlineTab: $("#worldline-tab"),
    recordsTab: $("#records-tab"),
    homeView: $("#home-view"),
    playView: $("#play-view"),
    worldlineView: $("#worldline-view"),
    recordsView: $("#records-view"),
    newGame: $("#new-game-button"),
    continueGame: $("#continue-button"),
    importInput: $("#import-input"),
    resetSave: $("#reset-save-button"),
    homeWorldline: $("#home-worldline-button"),
    stage: $("#stage"),
    sceneLabel: $("#scene-label"),
    nodeTitle: $("#node-title"),
    progressLabel: $("#progress-label"),
    characterStage: $("#character-stage"),
    mediaRail: $("#media-rail"),
    stateList: $("#state-list"),
    speakerName: $("#speaker-name"),
    segmentCount: $("#segment-count"),
    dialogueText: $("#dialogue-text"),
    choices: $("#choices"),
    next: $("#next-button"),
    save: $("#save-button"),
    restart: $("#restart-button"),
    history: $("#history-button"),
    sceneMedia: $("#scene-media"),
    worldline: $("#worldline"),
    fitCurrent: $("#fit-current-button"),
    fitWorldline: $("#fit-worldline-button"),
    jump: $("#jump-button"),
    zoomOut: $("#worldline-zoom-out-button"),
    zoomIn: $("#worldline-zoom-in-button"),
    resetWorldline: $("#worldline-reset-button"),
    zoomLabel: $("#worldline-zoom-label"),
    inspectorTitle: $("#inspector-title"),
    inspectorBody: $("#inspector-body"),
    inspectorMeta: $("#inspector-meta"),
    recordsTitle: $("#records-title"),
    recordsBody: $("#records-body"),
    toast: $("#toast"),
  };

  let pkg = null;
  let state = null;
  let capabilities = {};
  let currentNodeId = "";
  let selectedNodeId = "";
  let segmentIndex = 0;
  let cinematicMode = false;
  let awaitingDialogueStart = false;
  let cinematicTimer = 0;
  let activeRecordPanel = "endings";
  let worldlineViewport = { x: 0, y: 0, scale: 1 };
  let worldlineGraphSize = { width: 0, height: 0 };
  let worldlineNeedsFit = true;
  let worldlineDrag = null;
  let worldlineSuppressClick = false;

  init();

  async function init() {
    bindEvents();
    const url = new URL(window.location.href);
    const packageUrl = url.searchParams.get("package") || "runtime_game_package.json";
    try {
      const response = await fetch(`${packageUrl}${packageUrl.includes("?") ? "&" : "?"}t=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      await loadPackage(await response.json());
      setMode("home");
    } catch (error) {
      els.homeTitle.textContent = "等待导入 runtime_game_package.json";
      els.homeDescription.textContent = `默认加载失败：${error.message}`;
      setMode("home");
    }
  }

  function bindEvents() {
    els.homeTab.addEventListener("click", () => setMode("home"));
    els.playTab.addEventListener("click", () => setMode("play"));
    els.worldlineTab.addEventListener("click", () => setMode("worldline"));
    els.recordsTab.addEventListener("click", () => setMode("records"));
    els.homeWorldline?.addEventListener("click", () => setMode("worldline"));
    els.newGame.addEventListener("click", startNewGame);
    els.continueGame.addEventListener("click", continueGame);
    els.next.addEventListener("click", () => goNext({ source: "button" }));
    els.save.addEventListener("click", () => saveGame({ manual: true }));
    els.restart.addEventListener("click", startNewGame);
    els.history.addEventListener("click", () => {
      activeRecordPanel = "history";
      setMode("records");
    });
    els.fitCurrent.addEventListener("click", centerCurrentNode);
    els.fitWorldline.addEventListener("click", fitWorldlineOverview);
    els.zoomOut.addEventListener("click", () => zoomWorldline(0.84));
    els.zoomIn.addEventListener("click", () => zoomWorldline(1.18));
    els.resetWorldline.addEventListener("click", () => resetWorldlineViewport({ fit: false }));
    els.worldline.addEventListener("pointerdown", startWorldlineDrag);
    els.worldline.addEventListener("pointermove", moveWorldlineDrag);
    els.worldline.addEventListener("pointerup", endWorldlineDrag);
    els.worldline.addEventListener("pointercancel", endWorldlineDrag);
    els.worldline.addEventListener("wheel", handleWorldlineWheel, { passive: false });
    els.jump.addEventListener("click", () => {
      if (!selectedNodeId) return;
      loadNode(selectedNodeId, { reviewerJump: true });
      setMode("play");
    });
    els.resetSave.addEventListener("click", clearAllRecords);
    els.importInput.addEventListener("change", importPackage);
    $$("[data-record-panel]").forEach((button) => {
      button.addEventListener("click", () => {
        activeRecordPanel = button.dataset.recordPanel;
        setMode("records");
      });
    });
    document.addEventListener("keydown", (event) => {
      const tag = document.activeElement?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if (event.key === "Enter" || event.key === " ") {
        if (!els.playView.hidden) {
          event.preventDefault();
          goNext({ source: "keyboard" });
        }
      }
      if (event.key.toLowerCase() === "s" && !event.metaKey && !event.ctrlKey) saveGame({ manual: true });
      if (event.key.toLowerCase() === "w") setMode("worldline");
    });
  }

  async function importPackage(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    try {
      await loadPackage(JSON.parse(await file.text()));
      startNewGame();
    } catch (error) {
      showToast(`导入失败：${error.message}`);
    }
  }

  async function loadPackage(nextPackage) {
    pkg = normalizePackage(nextPackage);
    capabilities = detectCapabilities(pkg);
    pkg.capabilities = Object.assign({}, capabilities, pkg.capabilities || {});
    state = freshState();
    currentNodeId = pkg.start_node_id;
    selectedNodeId = currentNodeId;
    segmentIndex = 0;
    worldlineNeedsFit = true;
    worldlineViewport = { x: 0, y: 0, scale: 1 };
    document.title = pkg.meta?.title || pkg.game_id || "AVG Runtime";
    els.title.textContent = pkg.meta?.title || pkg.game_id;
    els.packageId.textContent = pkg.game_id || "runtime package";
    els.homeTitle.textContent = pkg.meta?.title || pkg.game_id;
    els.kicker.textContent = pkg.meta?.subtitle || pkg.meta?.genre || pkg.game_id || "AVG Game";
    els.homeDescription.textContent = pkg.meta?.description || "";
    els.homeBackdrop.style.backgroundImage = coverImage() ? `url("${coverImage()}")` : "";
    applyCapabilities();
    renderHomeStats();
    renderCapabilityStrip();
    renderWorldline();
    renderRecords();
    renderNode();
  }

  function normalizePackage(input) {
    const next = JSON.parse(JSON.stringify(input || {}));
    next.assets = next.assets || {};
    next.characters = next.characters || {};
    next.scenes = next.scenes || {};
    next.chapters = next.chapters || [];
    next.achievements = next.achievements || [];
    if (Array.isArray(next.nodes)) {
      const mapped = {};
      next.nodes.forEach((item, index) => {
        const nodeId = item.node_id || item.id || `node_${String(index + 1).padStart(3, "0")}`;
        mapped[nodeId] = Object.assign({}, item, { node_id: nodeId });
      });
      next.nodes = mapped;
    }
    next.nodes = next.nodes || {};
    Object.entries(next.nodes).forEach(([nodeId, item]) => {
      item.node_id = item.node_id || nodeId;
      item.segments = item.segments || [];
      item.choices = item.choices || [];
      item.routes = item.routes || [];
      item.media = item.media || [];
      item.character_layers = item.character_layers || [];
    });
    next.start_node_id = next.start_node_id || Object.keys(next.nodes)[0] || "";
    next.package_version = next.package_version || "0.0.0";
    next.meta = next.meta || {};
    return next;
  }

  function detectCapabilities(nextPackage) {
    const nodes = Object.values(nextPackage.nodes || {});
    const assets = Object.values(nextPackage.assets || {});
    const nodeMedia = nodes.flatMap((item) => item.media || []);
    const segmentAssets = nodes.flatMap((item) => item.segments || []).map((segment) => segment.asset_id).filter(Boolean);
    const edges = nodes.flatMap((item) => [
      item.next,
      ...(item.choices || []).map((choice) => choice.target_node_id),
      ...(item.routes || []).map((route) => route.next_node_id),
    ]).filter(Boolean);
    const endings = endingNodesForPackage(nextPackage);
    const hasStateValues = Boolean(nextPackage.state?.primary_value || Object.keys(nextPackage.state?.values || {}).length || Object.keys(nextPackage.state?.variables || {}).length);
    const hasPortraits = Object.values(nextPackage.characters || {}).some((character) => (character.portraits || []).length) || assets.some((asset) => asset.asset_id?.startsWith?.("char_") || asset.asset_id?.startsWith?.("ref_"));
    const hasGalleryAssets = assets.some((asset) => {
      const usage = asset.usage || [];
      return asset.type === "video" || usage.includes("story_still") || usage.includes("video_clip") || asset.asset_id?.startsWith?.("cg_") || asset.asset_id?.startsWith?.("vid_");
    });
    const inferred = {
      has_nodes: nodes.length > 0,
      has_multiple_nodes: nodes.length > 1,
      has_choices: nodes.some((item) => (item.choices || []).length),
      has_routes: nodes.some((item) => (item.routes || []).length),
      has_worldline: nodes.length > 1 && edges.length > 0,
      has_chapters: (nextPackage.chapters || []).length > 0,
      has_endings: endings.length > 0 || (nextPackage.endings || []).length > 0,
      has_state: hasStateValues,
      has_character_portraits: hasPortraits,
      has_character_layers: nodes.some((item) => (item.character_layers || []).length || (item.segments || []).some((segment) => (segment.show_layers || []).length)),
      has_backgrounds: assets.some((asset) => asset.type === "image" && (asset.asset_id?.startsWith?.("bg_") || (asset.usage || []).includes("background"))),
      has_scene_media: nodeMedia.length > 0 || segmentAssets.length > 0,
      has_video: assets.some((asset) => asset.type === "video") || nodeMedia.some((item) => item.media_type === "video"),
      has_cinematics: nodeMedia.some((item) => item.media_type === "video" || item.presentation === "cinematic_still" || item.display_duration_ms),
      has_gallery: Boolean(nextPackage.gallery) || hasGalleryAssets,
      has_codex: Boolean(nextPackage.codex),
      has_achievements: (nextPackage.achievements || []).length > 0,
      has_assets: assets.length > 0,
      has_settings: true,
      has_saves: true,
      has_import: true,
      has_history: true,
      node_count: nodes.length,
      choice_count: nodes.reduce((sum, item) => sum + (item.choices || []).length, 0),
      ending_count: endings.length || (nextPackage.endings || []).length,
      asset_count: assets.length,
      video_count: assets.filter((asset) => asset.type === "video").length,
      background_count: assets.filter((asset) => asset.type === "image" && (asset.asset_id?.startsWith?.("bg_") || (asset.usage || []).includes("background"))).length,
      portrait_count: assets.filter((asset) => asset.asset_id?.startsWith?.("char_") || asset.asset_id?.startsWith?.("ref_")).length,
    };
    return Object.assign({}, inferred, nextPackage.capabilities || {});
  }

  function applyCapabilities() {
    els.appShell?.classList.toggle("has-state", Boolean(capabilities.has_state));
    els.appShell?.classList.toggle("has-gallery", Boolean(capabilities.has_gallery));
    els.appShell?.classList.toggle("has-worldline", Boolean(capabilities.has_worldline));
    els.worldlineTab.hidden = !capabilities.has_worldline;
    $$("[data-record-panel]").forEach((button) => {
      const panel = button.dataset.recordPanel;
      button.hidden = !recordPanelAvailable(panel);
    });
    if (!recordPanelAvailable(activeRecordPanel)) {
      activeRecordPanel = firstAvailableRecordPanel();
    }
    els.stateList.closest(".state-hud").hidden = !capabilities.has_state;
  }

  function recordPanelAvailable(panel) {
    switch (panel) {
      case "endings": return Boolean(capabilities.has_endings);
      case "chapters": return Boolean(capabilities.has_chapters);
      case "gallery": return Boolean(capabilities.has_gallery);
      case "assets": return Boolean(capabilities.has_assets && isDebugMode());
      case "stats": return Boolean(capabilities.has_nodes);
      case "saves": return Boolean(capabilities.has_saves);
      case "settings": return Boolean(capabilities.has_settings);
      case "history": return Boolean(capabilities.has_history);
      default: return true;
    }
  }

  function firstAvailableRecordPanel() {
    return ["endings", "chapters", "gallery", "saves", "history", "stats", "settings", "assets"].find(recordPanelAvailable) || "settings";
  }

  function isDebugMode() {
    return new URL(window.location.href).searchParams.get("debug") === "1" || Boolean(pkg?.debug?.enabled);
  }

  function freshState() {
    const base = pkg?.state || {};
    return {
      primary: base.primary_value?.initial || 0,
      values: Object.assign({}, base.values || {}),
      variables: Object.assign({}, base.variables || {}),
      flags: new Set(base.flags || []),
      cinematics: new Set(),
      visits: [],
      choices: [],
      endings: readJson(`${storageKey()}_endings`, []),
      history: [],
      startedAt: Date.now(),
    };
  }

  function setMode(mode) {
    if (els.appShell) els.appShell.dataset.view = mode;
    els.homeView.hidden = mode !== "home";
    els.playView.hidden = mode !== "play";
    els.worldlineView.hidden = mode !== "worldline";
    els.recordsView.hidden = mode !== "records";
    els.homeTab.classList.toggle("is-active", mode === "home");
    els.playTab.classList.toggle("is-active", mode === "play");
    els.worldlineTab.classList.toggle("is-active", mode === "worldline");
    els.recordsTab.classList.toggle("is-active", mode === "records");
    if (mode === "worldline") renderWorldline();
    if (mode === "records") renderRecords();
  }

  function storageKey() {
    return `avg_runtime:${pkg?.game_id || "package"}`;
  }

  function saveKey() {
    return `${storageKey()}_auto`;
  }

  function readJson(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(key) || "null") ?? fallback;
    } catch (_) {
      return fallback;
    }
  }

  function writeJson(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function snapshot() {
    return {
      currentNodeId,
      selectedNodeId,
      segmentIndex,
      awaitingDialogueStart,
      state: Object.assign({}, state, { cinematics: Array.from(state.cinematics || []), flags: Array.from(state.flags) }),
      savedAt: Date.now(),
    };
  }

  function restore(payload) {
    if (!payload || !pkg) return false;
    state = payload.state || freshState();
    state.flags = new Set(state.flags || []);
    state.cinematics = new Set(state.cinematics || []);
    state.endings = state.endings || readJson(`${storageKey()}_endings`, []);
    state.history = state.history || [];
    currentNodeId = payload.currentNodeId || pkg.start_node_id;
    selectedNodeId = payload.selectedNodeId || currentNodeId;
    segmentIndex = typeof payload.segmentIndex === "number" ? payload.segmentIndex : 0;
    cinematicMode = false;
    awaitingDialogueStart = Boolean(payload.awaitingDialogueStart);
    renderNode();
    renderWorldline();
    renderHomeStats();
    return true;
  }

  function saveGame(options = {}) {
    if (!pkg || !state) return;
    writeJson(saveKey(), snapshot());
    if (options.manual) {
      showToast("已保存");
      renderHomeStats();
    }
  }

  function continueGame() {
    if (!restore(readJson(saveKey(), null))) startNewGame();
    setMode("play");
  }

  function startNewGame() {
    if (!pkg) return;
    const stats = readStats();
    stats.playthroughs += 1;
    writeJson(`${storageKey()}_stats`, stats);
    state = freshState();
    loadNode(pkg.start_node_id);
    setMode("play");
  }

  function clearAllRecords() {
    if (!pkg) return;
    localStorage.removeItem(saveKey());
    localStorage.removeItem(`${storageKey()}_endings`);
    localStorage.removeItem(`${storageKey()}_stats`);
    for (let i = 1; i <= 3; i += 1) localStorage.removeItem(slotKey(i));
    state = freshState();
    loadNode(pkg.start_node_id);
    showToast("记录已清除");
  }

  function assetUrl(assetId) {
    if (!assetId || !pkg.assets?.[assetId]) return "";
    const asset = pkg.assets[assetId];
    const assetPath = asset.path || "";
    if (/^https?:\/\//i.test(assetPath) || assetPath.startsWith("data:")) return assetPath;
    const base = pkg.engine_contract?.asset_base_path || "";
    const version = encodeURIComponent([asset.source_manifest_id || "asset", pkg.meta?.version || pkg.package_version || ""].filter(Boolean).join(":"));
    return `${base}${assetPath}?v=${version}`;
  }

  function coverImage() {
    return assetUrl("bg_qingyun_summit_arena_wide") || assetUrl(Object.keys(pkg.assets || {}).find((id) => id.startsWith("bg_")));
  }

  function nodeBackgroundUrl(item) {
    if (!item) return "";
    const scene = pkg.scenes?.[item.scene_id] || null;
    return assetUrl(item.background_asset_id || scene?.background_asset_id);
  }

  function node() {
    return pkg?.nodes?.[currentNodeId] || null;
  }

  function loadNode(nodeId, options = {}) {
    if (!pkg?.nodes?.[nodeId]) return;
    currentNodeId = nodeId;
    selectedNodeId = nodeId;
    segmentIndex = 0;
    awaitingDialogueStart = false;
    if (!state.visits.includes(nodeId)) state.visits.push(nodeId);
    if (options.reviewerJump) state.visits.push(`jump:${nodeId}`);
    const current = pkg.nodes[nodeId];
    cinematicMode = shouldPlayCinematic(current);
    if (cinematicMode) segmentIndex = -1;
    if (current.is_ending) recordEnding(nodeId);
    if (!cinematicMode) pushHistory(current);
    saveGame();
    renderNode();
    renderWorldline();
  }

  function recordEnding(nodeId) {
    if (!state.endings.includes(nodeId)) state.endings.push(nodeId);
    const endings = readJson(`${storageKey()}_endings`, []);
    if (!endings.some((item) => item.nodeId === nodeId)) {
      endings.push({ nodeId, title: pkg.nodes[nodeId]?.title || nodeId, reachedAt: Date.now() });
      writeJson(`${storageKey()}_endings`, endings);
      const stats = readStats();
      stats.endingsReached += 1;
      writeJson(`${storageKey()}_stats`, stats);
    }
  }

  function pushHistory(current) {
    const segment = (current.segments || [])[segmentIndex];
    if (!segment) return;
    const speaker = speakerName(segment);
    const entry = { nodeId: current.node_id, title: current.title, speaker, text: segment.text };
    const last = state.history[state.history.length - 1];
    if (!last || last.nodeId !== entry.nodeId || last.text !== entry.text) state.history.push(entry);
    state.history = state.history.slice(-80);
  }

  function renderNode() {
    const current = node();
    if (!pkg || !current) return;
    const scene = pkg.scenes?.[current.scene_id] || null;
    const background = assetUrl(current.background_asset_id || scene?.background_asset_id);
    els.stage.style.backgroundImage = background ? `url("${background}")` : "";
    els.stage.classList.toggle("is-cinematic", cinematicMode);
    els.appShell?.classList.toggle("is-cinematic", cinematicMode);
    els.sceneLabel.textContent = scene?.name || current.scene_id || "";
    els.progressLabel.textContent = `${Math.round(current.progress || 0)}%`;
    els.nodeTitle.textContent = playerTitle(current.title || current.node_id);
    renderVisuals(current);
    renderDialogue(current);
    renderChoices(current);
    renderState();
    renderHomeStats();
  }

  function renderVisuals(current) {
    els.characterStage.textContent = "";
    els.mediaRail.textContent = "";
    els.sceneMedia.textContent = "";
    if (cinematicMode) {
      renderCinematicMedia(current);
      return;
    }
    const featured = activeSceneMedia(current);
    renderSceneMedia(featured);
    const hiddenCharacters = featured ? assetCharacters(featured.assetId) : new Set();
    const sprites = featured?.type === "video" ? [] : selectSpriteItems(current, hiddenCharacters);
    sprites.forEach((item) => {
      const img = document.createElement("img");
      img.className = "character-sprite";
      img.dataset.active = String(Boolean(item.active));
      img.dataset.character = item.characterId;
      img.dataset.slot = item.slot || "center";
      img.src = item.url;
      img.alt = item.alt;
      img.onerror = () => img.remove();
      els.characterStage.append(img);
    });
  }

  function renderSceneMedia(item) {
    if (!item) return;
    if (item.type === "video") {
      const video = document.createElement("video");
      video.className = "scene-video";
      video.src = item.url;
      video.muted = true;
      video.playsInline = true;
      video.autoplay = true;
      video.loop = Boolean(item.loop);
      video.controls = false;
      video.onerror = () => video.remove();
      els.sceneMedia.append(video);
      video.play?.().catch(() => {});
      return;
    }
    const img = document.createElement("img");
    img.className = `scene-image${item.kind === "character" ? " is-character-cutin" : ""}`;
    img.src = item.url;
    img.alt = item.alt;
    img.onerror = () => img.remove();
    els.sceneMedia.append(img);
  }

  function activeSceneMedia(current) {
    const segment = (current.segments || [])[segmentIndex] || {};
    if (segment.asset_id) {
      const item = sceneMediaItem(segment.asset_id, { presentation: "segment" });
      if (item && !isUiAsset(item.assetId, item.asset)) return item;
    }
    const mediaItems = (current.media || [])
      .map((media) => sceneMediaItem(media.asset_id, media))
      .filter((item) => item && !isUiAsset(item.assetId, item.asset) && item.type !== "video" && item.kind !== "character");
    if (!mediaItems.length) return null;
    const index = Math.min(segmentIndex, mediaItems.length - 1);
    return mediaItems[index] || mediaItems[0];
  }

  function renderCinematicMedia(current) {
    const item = introCinematicMedia(current);
    if (!item) {
      finishCinematic();
      return;
    }
    if (item.type !== "video") {
      const img = document.createElement("img");
      img.className = "scene-image is-cinematic-image";
      img.src = item.url;
      img.alt = item.alt;
      img.onerror = finishCinematic;
      els.sceneMedia.append(img);
      scheduleCinematicFinish(item.durationMs || 10000);
      return;
    }
    const video = document.createElement("video");
    video.className = "scene-video is-cinematic-video";
    video.src = item.url;
    video.muted = true;
    video.playsInline = true;
    video.autoplay = true;
    video.loop = false;
    video.controls = false;
    video.onended = () => {
      if (!item.durationMs) finishCinematic();
    };
    video.onerror = finishCinematic;
    video.onloadedmetadata = () => scheduleCinematicFinish(video, item);
    video.onpause = () => {
      if (cinematicMode && !video.ended) video.play?.().catch(() => {});
    };
    els.sceneMedia.append(video);
    scheduleCinematicFinish(video, item);
    video.play?.().catch(() => {});
  }

  function finishCinematic() {
    const current = node();
    if (!current || !cinematicMode) return;
    window.clearTimeout(cinematicTimer);
    cinematicTimer = 0;
    state.cinematics.add(current.node_id);
    cinematicMode = false;
    awaitingDialogueStart = true;
    segmentIndex = 0;
    saveGame();
    renderNode();
  }

  function scheduleCinematicFinish(source, item = {}) {
    window.clearTimeout(cinematicTimer);
    const requestedMs = Number(item.durationMs || 0);
    const naturalSeconds = source && typeof source === "object" && Number.isFinite(source.duration) && source.duration > 0 ? source.duration : 0;
    const naturalMs = naturalSeconds ? naturalSeconds * 1000 + 700 : 0;
    const rawMs = typeof source === "number" ? source : Math.max(requestedMs, naturalMs || 10000);
    const ms = Math.max(1500, Math.min(30000, rawMs));
    cinematicTimer = window.setTimeout(finishCinematic, ms);
  }

  function shouldPlayCinematic(current) {
    return Boolean(current && introCinematicMedia(current) && !state?.cinematics?.has(current.node_id));
  }

  function introCinematicMedia(current) {
    const media = (current.media || [])
      .map((item) => sceneMediaItem(item.asset_id, item))
      .filter((item) => item && !isUiAsset(item.assetId, item.asset))
      .find((item) => item.type === "video" || item.presentation === "cinematic_still" || item.durationMs);
    return media || null;
  }

  function sceneMediaItem(assetId, media = {}) {
    const asset = pkg.assets?.[assetId];
    const url = assetUrl(assetId);
    if (!asset || !url) return null;
    return {
      asset,
      assetId,
      alt: asset.alt_text || assetId,
      kind: classifyAsset(assetId, asset, media),
      loop: media.loop,
      presentation: media.presentation || "main",
      durationMs: media.display_duration_ms || 0,
      type: asset.type === "video" || media.media_type === "video" ? "video" : "image",
      url,
    };
  }

  function isUiAsset(assetId, asset = {}) {
    const usage = asset.usage || [];
    return assetId.startsWith("ui_") || usage.includes("ui_skin");
  }

  function selectSpriteItems(current, hiddenCharacters = new Set()) {
    const segment = currentSegment(current);
    const layers = segmentAwareLayers(current, segment);
    const focusId = focusCharacterId(current, segment, layers);
    const visibleIds = visibleCharacterIds(current, segment, layers, focusId, hiddenCharacters);
    const byCharacter = new Map();
    layers.forEach((layer) => {
      if (layer.visible === false || hiddenCharacters.has(layer.character_id) || !visibleIds.has(layer.character_id)) return;
      if (byCharacter.has(layer.character_id)) return;
      const expression = expressionForBeat(layer.character_id, layer, segment, current, layer.character_id === focusId);
      const assetId = layer._segmentLayer && layer.asset_id ? layer.asset_id : portraitAsset(layer.character_id, expression) || layer.asset_id || portraitAsset(layer.character_id, "default");
      const asset = pkg.assets?.[assetId];
      const url = assetUrl(assetId);
      if (!asset || !url) return;
      byCharacter.set(layer.character_id, {
        active: layer.character_id === focusId,
        alt: asset.alt_text || layer.character_id,
        assetId,
        characterId: layer.character_id,
        priority: characterPriority(layer.character_id, current, focusId, segment),
        slot: slotForCharacter(layer.character_id, focusId, layer.position),
        url,
        zIndex: layer.z_index || 0,
      });
    });
    const selected = Array.from(byCharacter.values())
      .sort((a, b) => (b.priority - a.priority) || (b.zIndex - a.zIndex))
      .slice(0, 3);
    const usedSlots = new Set();
    const fallbackSlots = spriteSlots(selected.length);
    selected.forEach((item, index) => {
      if (!item.slot || usedSlots.has(item.slot)) item.slot = fallbackSlots[index] || "center";
      usedSlots.add(item.slot);
    });
    return selected;
  }

  function currentSegment(current) {
    return (current.segments || [])[segmentIndex] || {};
  }

  function segmentAwareLayers(current, segment) {
    const byCharacter = new Map();
    (current.character_layers || []).forEach((layer) => {
      if (!layer.character_id) return;
      byCharacter.set(layer.character_id, Object.assign({}, layer));
    });
    (segment.show_layers || []).forEach((layer) => {
      if (!layer.character_id) return;
      byCharacter.set(layer.character_id, Object.assign({}, byCharacter.get(layer.character_id) || {}, layer, { _segmentLayer: true }));
    });
    return Array.from(byCharacter.values());
  }

  function portraitAsset(characterId, expression) {
    const character = pkg.characters?.[characterId];
    if (!character) return "";
    const portraits = character.portraits || [];
    const matched = portraits.find((item) => item.expression === expression) || portraits.find((item) => item.expression === "default") || portraits[0];
    return matched?.asset_id || "";
  }

  function focusCharacterId(current, segment, layers) {
    if (segment.speaker_id && pkg.characters?.[segment.speaker_id]) return segment.speaker_id;
    const text = segment.text || "";
    const mentioned = mentionedCharacters(text).filter((id) => layers.some((layer) => layer.character_id === id));
    if (mentioned.length) return mentioned[0];
    if (/陆雪琪|白衣|青莲|剑鞘|剑尖|她/.test(text) && hasLayer(layers, "lu_xueqi")) return "lu_xueqi";
    if (/长老|判磬|令旗|验之|判之|止之/.test(text) && hasLayer(layers, "judge_elder")) return "judge_elder";
    if (/田不易|师父|师门|大竹峰/.test(text) && hasLayer(layers, "tian_buyi")) return "tian_buyi";
    if (/宋大仁|师兄/.test(text) && hasLayer(layers, "song_daren")) return "song_daren";
    if (/张小凡|袖中|数珠|佛意|道息|木剑|心口|低头|他/.test(text) && hasLayer(layers, "zhang_xiaofan")) return "zhang_xiaofan";
    if (hasLayer(layers, "zhang_xiaofan")) return "zhang_xiaofan";
    return layers[0]?.character_id || "";
  }

  function visibleCharacterIds(current, segment, layers, focusId, hiddenCharacters) {
    const ids = new Set();
    const layerIds = new Set(layers.map((layer) => layer.character_id).filter(Boolean));
    if (focusId && layerIds.has(focusId) && !hiddenCharacters.has(focusId)) ids.add(focusId);
    if (!ids.size) {
      const fallback = layers.find((layer) => !hiddenCharacters.has(layer.character_id))?.character_id;
      if (fallback) ids.add(fallback);
    }
    return new Set(Array.from(ids).slice(0, 1));
  }

  function mentionedCharacters(text) {
    const aliases = [
      ["zhang_xiaofan", ["张小凡", "小凡"]],
      ["lu_xueqi", ["陆雪琪", "雪琪"]],
      ["judge_elder", ["执事长老", "长老"]],
      ["tian_buyi", ["田不易", "师父"]],
      ["song_daren", ["宋大仁", "师兄"]],
    ];
    return aliases
      .map(([id, names]) => ({ id, index: Math.min(...names.map((name) => text.indexOf(name)).filter((index) => index >= 0)) }))
      .filter((item) => Number.isFinite(item.index))
      .sort((a, b) => a.index - b.index)
      .map((item) => item.id);
  }

  function hasLayer(layers, characterId) {
    return layers.some((layer) => layer.character_id === characterId);
  }

  function expressionForBeat(characterId, layer, segment, current, active) {
    if (layer._segmentLayer && layer.expression) return layer.expression;
    const inferred = inferExpression(characterId, segment.text || "", current);
    if (active && inferred) return inferred;
    if (layer.expression && !["default", "back_neutral", "after_duel_wait", "serious"].includes(layer.expression)) return layer.expression;
    return inferred || layer.expression || "default";
  }

  function inferExpression(characterId, text, current) {
    const lowerTitle = current.title || "";
    if (characterId === "zhang_xiaofan") {
      return firstAvailableExpression(characterId, [
        /伤|血|痛|反噬|呼吸略乱/.test(text) && "hurt_endure",
        /佛意成形|金光|展露|暴露|异象/.test(text) && "buddha_reveal",
        /真诚|本相|坦露|迎剑|回应/.test(text + lowerTitle) && "sincere_resolve",
        /收手|让|退|守拙|克制/.test(text + lowerTitle) && "yield_blade",
        /数珠|佛意|道息|袖中|藏|压|心口|沉|烫|秘密/.test(text + lowerTitle) && "inner_strain",
        "neutral_tense",
      ]);
    }
    if (characterId === "lu_xueqi") {
      return firstAvailableExpression(characterId, [
        /理解|明白|懂|共鸣/.test(text + lowerTitle) && "understanding_close",
        /痛|受伤|敬又痛|反噬/.test(text + lowerTitle) && "hurt_acknowledgement",
        /尊重|正面|相迎|稳/.test(text + lowerTitle) && "respect_press",
        /惊|震|异象|金光|佛意/.test(text + lowerTitle) && "surprised_subtle",
        /目光|看|问|试探|藏/.test(text + lowerTitle) && "probe_eye",
        /停|剑未出|剑鞘|剑尖/.test(text + lowerTitle) && "blade_pause",
        "neutral_serious",
      ]);
    }
    if (characterId === "judge_elder") {
      return firstAvailableExpression(characterId, [
        /异象|验之|止之|判之|警|判磬|令旗/.test(text + lowerTitle) && "alert_attention",
        "authoritative_calm",
      ]);
    }
    if (characterId === "song_daren") return firstAvailableExpression(characterId, ["worried_restrained", "default"]);
    return "default";
  }

  function firstAvailableExpression(characterId, expressions) {
    for (const expression of expressions) {
      if (expression && portraitAsset(characterId, expression)) return expression;
    }
    return "default";
  }

  function classifyAsset(assetId, asset, media) {
    if (asset.type === "video" || media.media_type === "video") return "video";
    if (assetId.startsWith("char_") || assetId.startsWith("ref_")) return "character";
    if (assetId.startsWith("bg_")) return "background";
    return "cutin";
  }

  function assetCharacters(assetId) {
    const matches = new Set();
    Object.keys(pkg.characters || {}).forEach((characterId) => {
      if (assetId.includes(characterId)) matches.add(characterId);
    });
    return matches;
  }

  function characterPriority(characterId, current, focusId, segment) {
    const character = pkg.characters?.[characterId];
    const name = character?.display_name || "";
    let score = 0;
    if (characterId === focusId) score += 200;
    if (segment.speaker_id === characterId) score += 100;
    if (name && (segment.text || "").includes(name)) score += 60;
    if (characterId === "zhang_xiaofan") score += 50;
    if (characterId === "lu_xueqi") score += 48;
    if (characterId === "judge_elder") score += 36;
    if (characterId === "tian_buyi") score += 28;
    if (characterId === "song_daren") score += 22;
    return score;
  }

  function normalizeSlot(position) {
    if (["left", "center", "right"].includes(position)) return position;
    return "";
  }

  function slotForCharacter(characterId, focusId, fallback) {
    const normalized = normalizeSlot(fallback);
    if (normalized && normalized !== "center") return normalized;
    if (characterId === "zhang_xiaofan") return "left";
    if (characterId === "lu_xueqi") return "right";
    if (characterId === "judge_elder") return "right";
    if (characterId === "tian_buyi" || characterId === "song_daren") return "left";
    if (normalized) return normalized;
    return focusId === "lu_xueqi" ? "left" : "right";
  }

  function spriteSlots(count) {
    if (count <= 1) return ["left"];
    if (count === 2) return ["left", "right"];
    return ["left", "center", "right"];
  }

  function renderDialogue(current) {
    const segments = current.segments || [];
    if (awaitingDialogueStart) {
      els.speakerName.textContent = playerTitle(current.title || "");
      els.segmentCount.textContent = "";
      els.dialogueText.textContent = "";
      els.next.textContent = "继续";
      return;
    }
    els.next.textContent = "继续";
    const segment = segments[segmentIndex] || segments[0] || { text: current.summary || "" };
    els.speakerName.textContent = speakerName(segment) || playerTitle(current.title || "");
    els.segmentCount.textContent = segments.length ? `${segmentIndex + 1}/${segments.length}` : "";
    els.dialogueText.textContent = segment.text || "";
  }

  function speakerName(segment) {
    return pkg.characters?.[segment.speaker_id]?.display_name || segment.speaker_name || segment.speaker_id || "";
  }

  function renderChoices(current) {
    els.choices.textContent = "";
    const segments = current.segments || [];
    const readyForChoice = !awaitingDialogueStart && segmentIndex >= 0 && (!segments.length || segmentIndex >= segments.length - 1);
    const choices = readyForChoice ? current.choices || [] : [];
    els.next.hidden = choices.length > 0 || current.is_ending;
    choices.forEach((choice) => {
      const enabled = conditionMet(choice.condition);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "choice-button";
      button.disabled = !enabled;
      button.innerHTML = `${escapeHtml(enabled ? choice.label : `${choice.label}（${choice.locked_hint || "条件不足"}）`)}${changeLabel(choice.changes)}`;
      button.addEventListener("click", () => choose(choice));
      els.choices.append(button);
    });
    if (current.is_ending) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "choice-button";
      button.textContent = "回到主菜单";
      button.addEventListener("click", () => setMode("home"));
      els.choices.append(button);
    }
  }

  function changeLabel(changes = {}) {
    const parts = [];
    if (typeof changes.primary_value_delta === "number") parts.push(`力量暴露 ${signed(changes.primary_value_delta)}`);
    Object.entries(changes.values_delta || {}).forEach(([key, value]) => parts.push(`${displayKey(key)} ${signed(value)}`));
    return parts.length ? `<small>${escapeHtml(parts.join(" · "))}</small>` : "";
  }

  function signed(value) {
    return value > 0 ? `+${value}` : String(value);
  }

  function goNext(options = {}) {
    const current = node();
    if (!current) return;
    if (cinematicMode) return;
    if (awaitingDialogueStart) {
      if (options.source !== "button") return;
      awaitingDialogueStart = false;
      segmentIndex = 0;
      pushHistory(current);
      saveGame();
      renderNode();
      return;
    }
    const segments = current.segments || [];
    if (segments.length && segmentIndex < segments.length - 1) {
      segmentIndex += 1;
      pushHistory(current);
      saveGame();
      renderNode();
      return;
    }
    const routed = resolveRoutes(current);
    if (routed) {
      loadNode(routed);
      return;
    }
    if (current.next) loadNode(current.next);
  }

  function choose(choice) {
    if (!conditionMet(choice.condition)) return;
    applyChanges(choice.changes || {});
    state.choices.push(choice.choice_id);
    const stats = readStats();
    stats.choicesMade += 1;
    writeJson(`${storageKey()}_stats`, stats);
    loadNode(choice.target_node_id);
  }

  function resolveRoutes(current) {
    for (const route of current.routes || []) {
      if (conditionMet(route.condition)) return route.next_node_id;
    }
    return null;
  }

  function conditionMet(condition) {
    if (!condition) return true;
    if (typeof condition === "string") return Boolean(readState(condition));
    if (condition.all) return condition.all.every(conditionMet);
    if (condition.any) return condition.any.some(conditionMet);
    if (condition.not) return !conditionMet(condition.not);
    if (condition.flag) return state.flags.has(condition.flag);
    if (condition.var) {
      const actual = readState(condition.var);
      const expected = condition.value;
      switch (condition.op || "==") {
        case "!=": return actual !== expected;
        case ">=": return actual >= expected;
        case "<=": return actual <= expected;
        case ">": return actual > expected;
        case "<": return actual < expected;
        default: return actual === expected;
      }
    }
    return true;
  }

  function readState(key) {
    if (key === pkg.state?.primary_value?.id) return state.primary;
    if (Object.prototype.hasOwnProperty.call(state.values, key)) return state.values[key];
    return state.variables[key];
  }

  function applyChanges(changes) {
    if (typeof changes.primary_value_delta === "number") state.primary += changes.primary_value_delta;
    if (typeof changes.primary_value_set === "number") state.primary = changes.primary_value_set;
    Object.entries(changes.values_delta || {}).forEach(([key, value]) => {
      state.values[key] = (state.values[key] || 0) + value;
    });
    Object.assign(state.variables, changes.set_variables || {});
    (changes.add_flags || []).forEach((flag) => state.flags.add(flag));
    (changes.remove_flags || []).forEach((flag) => state.flags.delete(flag));
  }

  function renderState() {
    els.stateList.textContent = "";
    els.stateList.closest(".state-hud").hidden = !capabilities.has_state;
    if (!capabilities.has_state) return;
    const primary = pkg.state?.primary_value || {};
    if (primary.id) addPair(els.stateList, primary.display_name || displayKey(primary.id || "primary"), meter(state.primary, primary.min ?? 0, primary.max ?? 5));
    Object.entries(state.values).forEach(([key, value]) => addPair(els.stateList, displayKey(key), value));
    addPair(els.stateList, "抉择", state.choices.length);
    addPair(els.stateList, "已访", state.visits.filter((item) => !String(item).startsWith("jump:")).length);
  }

  function meter(value, min, max) {
    return `<meter min="${min}" max="${max}" value="${value}"></meter>`;
  }

  function renderHomeStats() {
    els.homeStats.textContent = "";
    if (!pkg || !state) return;
    const saved = readJson(saveKey(), null);
    const savedNode = pkg.nodes?.[saved?.currentNodeId || currentNodeId];
    const previewUrl = nodeBackgroundUrl(savedNode) || coverImage();
    if (els.homeMetaPanel && previewUrl) els.homeMetaPanel.style.setProperty("--save-scene-image", `url("${previewUrl}")`);
    addPair(els.homeStats, "继续", playerTitle(savedNode?.title || "尚未开始"));
    if (savedNode) addPair(els.homeStats, "章节", chapterName(savedNode));
    if (capabilities.has_endings) addPair(els.homeStats, "结局", `${readJson(`${storageKey()}_endings`, []).length}/${endingNodes().length}`);
  }

  function renderCapabilityStrip() {
    if (!els.capabilityStrip) return;
    els.capabilityStrip.textContent = "";
    els.capabilityStrip.hidden = true;
  }

  function addPair(list, key, value) {
    const dt = document.createElement("dt");
    dt.textContent = key;
    const dd = document.createElement("dd");
    if (typeof value === "string" && value.includes("<meter")) dd.innerHTML = value;
    else dd.textContent = String(value);
    list.append(dt, dd);
  }

  function renderWorldline() {
    if (!pkg) return;
    els.worldline.textContent = "";
    const reachable = computeReachable();
    const graph = buildWorldlineGraph();
    const canvas = document.createElement("div");
    canvas.className = "worldline-canvas";
    canvas.style.width = `${graph.width}px`;
    canvas.style.height = `${graph.height}px`;
    worldlineGraphSize = { width: graph.width, height: graph.height };
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.classList.add("worldline-edges");
    svg.setAttribute("viewBox", `0 0 ${graph.width} ${graph.height}`);
    svg.setAttribute("width", String(graph.width));
    svg.setAttribute("height", String(graph.height));
    svg.innerHTML = `<defs><marker id="arrowhead" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z"></path></marker></defs>`;
    graph.edges.forEach((edge) => {
      const from = graph.positions.get(edge.from);
      const to = graph.positions.get(edge.to);
      if (!from || !to) return;
      const startX = from.x + graph.nodeWidth;
      const startY = from.y + graph.nodeHeight / 2;
      const endX = to.x;
      const endY = to.y + graph.nodeHeight / 2;
      const bend = Math.max(70, Math.abs(endX - startX) * 0.45);
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.classList.add("world-edge", `is-${edge.kind}`);
      path.setAttribute("d", `M ${startX} ${startY} C ${startX + bend} ${startY}, ${endX - bend} ${endY}, ${endX} ${endY}`);
      path.setAttribute("marker-end", "url(#arrowhead)");
      svg.append(path);
      if (edge.label && edge.kind !== "next" && (edge.from === selectedNodeId || edge.from === currentNodeId)) {
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.classList.add("world-edge-label");
        label.setAttribute("x", String((startX + endX) / 2));
        label.setAttribute("y", String((startY + endY) / 2 - 8));
        label.textContent = shortLabel(edge.label, 12);
        svg.append(label);
      }
    });
    canvas.append(svg);
    graph.nodes.forEach((item) => {
      const position = graph.positions.get(item.node_id);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "world-node";
      button.dataset.nodeId = item.node_id;
      button.style.left = `${position.x}px`;
      button.style.top = `${position.y}px`;
      button.classList.toggle("is-current", item.node_id === currentNodeId);
      button.classList.toggle("is-visited", state?.visits?.includes(item.node_id));
      button.classList.toggle("is-ending", Boolean(item.is_ending));
      button.classList.toggle("is-unreachable", !reachable.has(item.node_id));
      button.innerHTML = `${escapeHtml(playerTitle(item.title || item.node_id))}<small>${escapeHtml(chapterName(item))}</small>`;
      button.addEventListener("click", (event) => {
        if (worldlineSuppressClick) {
          worldlineSuppressClick = false;
          return;
        }
        event.stopPropagation();
        openWorldNode(item.node_id);
      });
      canvas.append(button);
    });
    els.worldline.append(canvas);
    applyWorldlineViewport();
    if (worldlineNeedsFit && !els.worldlineView.hidden) {
      requestAnimationFrame(fitWorldlineOverview);
    }
    renderInspector();
  }

  function openWorldNode(nodeId) {
    const item = pkg?.nodes?.[nodeId];
    if (!item) return;
    selectedNodeId = nodeId;
    renderInspector();
    loadNode(nodeId, { reviewerJump: true });
    setMode("play");
    showToast(`已跳转到「${playerTitle(item.title || nodeId)}」`);
  }

  function applyWorldlineViewport() {
    const canvas = els.worldline.querySelector(".worldline-canvas");
    if (!canvas) return;
    canvas.style.setProperty("--worldline-x", `${worldlineViewport.x}px`);
    canvas.style.setProperty("--worldline-y", `${worldlineViewport.y}px`);
    canvas.style.setProperty("--worldline-scale", String(worldlineViewport.scale));
    els.zoomLabel.textContent = `${Math.round(worldlineViewport.scale * 100)}%`;
  }

  function fitWorldlineOverview() {
    if (!worldlineGraphSize.width || !worldlineGraphSize.height) return;
    const rect = els.worldline.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const padding = 44;
    const availableWidth = Math.max(120, rect.width - padding * 2);
    const availableHeight = Math.max(120, rect.height - padding * 2);
    const nextScale = clamp(Math.min(
      availableWidth / worldlineGraphSize.width,
      availableHeight / worldlineGraphSize.height
    ), 0.28, 1);
    worldlineViewport = {
      scale: nextScale,
      x: (rect.width - worldlineGraphSize.width * nextScale) / 2,
      y: (rect.height - worldlineGraphSize.height * nextScale) / 2,
    };
    worldlineNeedsFit = false;
    applyWorldlineViewport();
  }

  function resetWorldlineViewport(options = {}) {
    worldlineViewport = { x: 0, y: 0, scale: 1 };
    worldlineNeedsFit = Boolean(options.fit);
    applyWorldlineViewport();
    if (options.fit && !els.worldlineView.hidden) requestAnimationFrame(fitWorldlineOverview);
  }

  function zoomWorldline(factor, anchor = null) {
    const rect = els.worldline.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const oldScale = worldlineViewport.scale;
    const nextScale = clamp(oldScale * factor, 0.28, 1.6);
    const anchorX = anchor?.x ?? rect.width / 2;
    const anchorY = anchor?.y ?? rect.height / 2;
    const graphX = (anchorX - worldlineViewport.x) / oldScale;
    const graphY = (anchorY - worldlineViewport.y) / oldScale;
    worldlineViewport = {
      scale: nextScale,
      x: anchorX - graphX * nextScale,
      y: anchorY - graphY * nextScale,
    };
    worldlineNeedsFit = false;
    applyWorldlineViewport();
  }

  function handleWorldlineWheel(event) {
    if (!pkg || els.worldlineView.hidden) return;
    event.preventDefault();
    const rect = els.worldline.getBoundingClientRect();
    zoomWorldline(event.deltaY > 0 ? 0.9 : 1.1, {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    });
  }

  function startWorldlineDrag(event) {
    if (event.button !== 0 || !pkg) return;
    if (event.target?.closest?.(".world-node")) return;
    worldlineDrag = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: worldlineViewport.x,
      originY: worldlineViewport.y,
      moved: false,
    };
    els.worldline.classList.add("is-panning");
    els.worldline.setPointerCapture?.(event.pointerId);
  }

  function moveWorldlineDrag(event) {
    if (!worldlineDrag || event.pointerId !== worldlineDrag.pointerId) return;
    const dx = event.clientX - worldlineDrag.startX;
    const dy = event.clientY - worldlineDrag.startY;
    if (Math.abs(dx) + Math.abs(dy) > 4) worldlineDrag.moved = true;
    if (!worldlineDrag.moved) return;
    event.preventDefault();
    worldlineViewport.x = worldlineDrag.originX + dx;
    worldlineViewport.y = worldlineDrag.originY + dy;
    worldlineNeedsFit = false;
    applyWorldlineViewport();
  }

  function endWorldlineDrag(event) {
    if (!worldlineDrag || event.pointerId !== worldlineDrag.pointerId) return;
    if (worldlineDrag.moved) {
      worldlineSuppressClick = true;
      window.setTimeout(() => {
        worldlineSuppressClick = false;
      }, 0);
    }
    els.worldline.releasePointerCapture?.(event.pointerId);
    els.worldline.classList.remove("is-panning");
    worldlineDrag = null;
  }

  function buildWorldlineGraph() {
    const nodes = Object.values(pkg.nodes || {});
    const edges = worldEdges();
    const graphDepths = computeDepths(edges);
    const maxColumn = 7;
    const depths = new Map();
    nodes.forEach((item) => {
      const progress = Number.isFinite(item.progress) ? item.progress : (graphDepths.get(item.node_id) || 0) * 12;
      depths.set(item.node_id, Math.max(0, Math.min(maxColumn, Math.round((progress / 100) * maxColumn))));
    });
    const groups = new Map();
    nodes.forEach((item) => {
      const depth = depths.get(item.node_id) || 0;
      if (!groups.has(depth)) groups.set(depth, []);
      groups.get(depth).push(item);
    });
    groups.forEach((items) => items.sort((a, b) => (a.progress || 0) - (b.progress || 0)));
    const nodeWidth = 230;
    const nodeHeight = 88;
    const colGap = 130;
    const rowGap = 34;
    const positions = new Map();
    const columns = Array.from(groups.keys()).sort((a, b) => a - b);
    columns.forEach((depth, colIndex) => {
      const items = groups.get(depth);
      items.forEach((item, rowIndex) => {
        positions.set(item.node_id, {
          x: 28 + colIndex * (nodeWidth + colGap),
          y: 28 + rowIndex * (nodeHeight + rowGap),
        });
      });
    });
    const maxRows = Math.max(1, ...Array.from(groups.values()).map((items) => items.length));
    return {
      edges,
      height: 56 + maxRows * nodeHeight + (maxRows - 1) * rowGap,
      nodeHeight,
      nodeWidth,
      nodes,
      positions,
      width: 56 + columns.length * nodeWidth + Math.max(0, columns.length - 1) * colGap,
    };
  }

  function computeDepths(edges) {
    const depths = new Map([[pkg.start_node_id, 0]]);
    const outgoing = new Map();
    edges.forEach((edge) => {
      if (!outgoing.has(edge.from)) outgoing.set(edge.from, []);
      outgoing.get(edge.from).push(edge.to);
    });
    const queue = [pkg.start_node_id];
    while (queue.length) {
      const from = queue.shift();
      const depth = depths.get(from) || 0;
      (outgoing.get(from) || []).forEach((to) => {
        const nextDepth = depth + 1;
        if (!depths.has(to) || nextDepth < depths.get(to)) {
          depths.set(to, nextDepth);
          queue.push(to);
        }
      });
    }
    return depths;
  }

  function worldEdges() {
    const edges = [];
    Object.values(pkg.nodes || {}).forEach((item) => {
      if (item.next) edges.push({ from: item.node_id, kind: "next", label: "推进", to: item.next });
      (item.choices || []).forEach((choice) => edges.push({
        from: item.node_id,
        kind: "choice",
        label: choice.label || "选择",
        to: choice.target_node_id,
      }));
      (item.routes || []).forEach((route) => edges.push({
        from: item.node_id,
        kind: "route",
        label: route.label || "条件",
        to: route.next_node_id,
      }));
    });
    return edges.filter((edge) => edge.from && edge.to && pkg.nodes?.[edge.to]);
  }

  function computeReachable() {
    const seen = new Set();
    const queue = [pkg.start_node_id];
    while (queue.length) {
      const id = queue.shift();
      if (!id || seen.has(id) || !pkg.nodes[id]) continue;
      seen.add(id);
      const item = pkg.nodes[id];
      if (item.next) queue.push(item.next);
      (item.choices || []).forEach((choice) => queue.push(choice.target_node_id));
      (item.routes || []).forEach((route) => queue.push(route.next_node_id));
    }
    return seen;
  }

  function renderInspector() {
    const item = pkg?.nodes?.[selectedNodeId];
    if (!item) return;
    els.inspectorTitle.textContent = playerTitle(item.title || item.node_id);
    const summary = (item.segments || []).map((segment) => segment.text).join(" ").slice(0, 320);
    els.inspectorBody.textContent = summary || item.node_id;
    els.inspectorMeta.textContent = "";
    addPair(els.inspectorMeta, "章节", chapterName(item));
    addPair(els.inspectorMeta, "分支", (item.choices || []).length);
  }

  function centerCurrentNode() {
    const button = Array.from(document.querySelectorAll(".world-node")).find((item) => item.dataset.nodeId === currentNodeId);
    if (!button) return;
    const rect = els.worldline.getBoundingClientRect();
    worldlineViewport = {
      scale: Math.max(worldlineViewport.scale, 0.52),
      x: rect.width / 2 - (button.offsetLeft + button.offsetWidth / 2) * Math.max(worldlineViewport.scale, 0.52),
      y: rect.height / 2 - (button.offsetTop + button.offsetHeight / 2) * Math.max(worldlineViewport.scale, 0.52),
    };
    worldlineNeedsFit = false;
    applyWorldlineViewport();
  }

  function renderRecords() {
    if (!pkg) return;
    if (!recordPanelAvailable(activeRecordPanel)) activeRecordPanel = firstAvailableRecordPanel();
    $$("[data-record-panel]").forEach((button) => button.classList.toggle("is-active", button.dataset.recordPanel === activeRecordPanel));
    els.recordsBody.textContent = "";
    const renderers = {
      endings: renderEndings,
      chapters: renderChapters,
      gallery: renderGallery,
      saves: renderSaves,
      stats: renderStats,
      settings: renderSettings,
      assets: renderAssets,
      history: renderHistory,
    };
    (renderers[activeRecordPanel] || renderEndings)();
  }

  function renderEndings() {
    els.recordsTitle.textContent = "结局记录";
    if (!capabilities.has_endings) return addRecord("未启用结局系统", "这个 JSON 包没有声明多结局，容器会以线性/章节记录方式运行。");
    const reached = readJson(`${storageKey()}_endings`, []);
    if (!reached.length) return addRecord("尚未抵达结局", "擂台上的答案还没有落定。");
    reached.forEach((item) => addRecord(item.title, `${item.nodeId} · ${new Date(item.reachedAt).toLocaleString()}`));
  }

  function renderChapters() {
    els.recordsTitle.textContent = "选择章节";
    if (!capabilities.has_chapters) return addRecord("未启用章节选择", "这个 JSON 包没有章节表，容器会从起始节点顺序推进。");
    (pkg.chapters || []).forEach((chapter) => {
      addRecord(chapter.title, chapter.entry_node_id, [
        ["从这里开始", () => {
          state = freshState();
          loadNode(chapter.entry_node_id);
          setMode("play");
        }],
      ]);
    });
  }

  function renderGallery() {
    els.recordsTitle.textContent = "图鉴";
    const items = galleryAssets();
    if (!items.length) return addRecord("未启用图鉴", "这个 JSON 包没有 CG、视频或可回看素材。");
    items.forEach((asset) => addRecord(asset.asset_id, [asset.type, asset.path].filter(Boolean).join(" · ")));
  }

  function renderSaves() {
    els.recordsTitle.textContent = "存档槽";
    addRecord("自动存档", saveDescription(readJson(saveKey(), null)), [["读取", () => loadSnapshot(readJson(saveKey(), null))]]);
    for (let i = 1; i <= 3; i += 1) {
      const data = readJson(slotKey(i), null);
      addRecord(`手动存档 ${i}`, saveDescription(data), [
        ["写入", () => {
          writeJson(slotKey(i), snapshot());
          showToast(`已写入存档 ${i}`);
          renderRecords();
        }],
        ["读取", () => loadSnapshot(readJson(slotKey(i), null))],
      ]);
    }
  }

  function renderStats() {
    els.recordsTitle.textContent = "游玩统计";
    const stats = readStats();
    addRecord("开始新故事", `${stats.playthroughs} 次`);
    if (capabilities.has_choices) addRecord("做出选择", `${stats.choicesMade} 次`);
    if (capabilities.has_endings) addRecord("抵达结局", `${readJson(`${storageKey()}_endings`, []).length}/${endingNodes().length}`);
    addRecord("访问节点", `${state.visits.filter((item) => !String(item).startsWith("jump:")).length}/${Object.keys(pkg.nodes || {}).length}`);
    addRecord("能力表", capabilitySummary());
  }

  function renderSettings() {
    els.recordsTitle.textContent = "设置";
    addRecord("文字", "调整游玩文字尺寸", [
      ["小", () => setFontScale(0.92)],
      ["标准", () => setFontScale(1)],
      ["大", () => setFontScale(1.14)],
    ]);
    addRecord("记录", "清除当前故事的本地存档与结局记录。", [
      ["清除记录", clearAllRecords],
    ]);
    addRecord("操作", "Enter / Space 推进，S 保存，W 打开世界线。");
  }

  function renderAssets() {
    els.recordsTitle.textContent = "素材";
    if (!capabilities.has_assets) return addRecord("纯文本包", "这个 JSON 包没有素材资产，容器会使用主题背景和文本模式运行。");
    const summary = assetSummary();
    addRecord("素材状态", `${summary.generated}/${summary.total} 可用 · 视频 ${summary.videos} 条 · placeholder ${summary.placeholder} 个`);
    Object.values(pkg.assets || {}).filter((asset) => asset.type === "video").forEach((asset) => {
      addRecord(asset.asset_id, asset.path);
    });
  }

  function renderHistory() {
    els.recordsTitle.textContent = "文本回顾";
    if (!state.history.length) return addRecord("暂无回顾", "还没有推进剧情。");
    state.history.slice().reverse().forEach((item) => addRecord(item.speaker || item.title || item.nodeId, item.text));
  }

  function addRecord(title, body, actions = []) {
    const item = document.createElement("article");
    item.className = "record-item";
    const strong = document.createElement("strong");
    strong.textContent = title;
    const p = document.createElement("p");
    p.textContent = body || "";
    item.append(strong, p);
    if (actions.length) {
      const row = document.createElement("div");
      row.className = "record-actions";
      actions.forEach(([label, handler]) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        button.addEventListener("click", handler);
        row.append(button);
      });
      item.append(row);
    }
    els.recordsBody.append(item);
  }

  function loadSnapshot(data) {
    if (!data) {
      showToast("没有存档");
      return;
    }
    restore(data);
    setMode("play");
  }

  function slotKey(index) {
    return `${storageKey()}_slot_${index}`;
  }

  function saveDescription(data) {
    if (!data) return "空";
    const current = pkg.nodes?.[data.currentNodeId];
    return `${current?.title || data.currentNodeId} · ${new Date(data.savedAt).toLocaleString()}`;
  }

  function readStats() {
    return { playthroughs: 0, choicesMade: 0, endingsReached: 0, ...readJson(`${storageKey()}_stats`, {}) };
  }

  function endingNodes() {
    return endingNodesForPackage(pkg);
  }

  function endingNodesForPackage(nextPackage) {
    const nodes = Object.values(nextPackage?.nodes || {});
    const declared = nextPackage?.endings || [];
    if (declared.length) {
      const ids = new Set(declared.map((item) => item.node_id || item.nodeId || item.id).filter(Boolean));
      return nodes.filter((item) => item.is_ending || ids.has(item.node_id));
    }
    return nodes.filter((item) => item.is_ending);
  }

  function assetSummary() {
    const assets = Object.values(pkg.assets || {});
    return {
      generated: assets.filter((asset) => !String(asset.path || "").includes("placeholders")).length,
      placeholder: assets.filter((asset) => String(asset.path || "").includes("placeholders")).length,
      total: assets.length,
      videos: assets.filter((asset) => asset.type === "video").length,
    };
  }

  function galleryAssets() {
    return Object.values(pkg.assets || {}).filter((asset) => {
      const usage = asset.usage || [];
      return asset.type === "video" || usage.includes("story_still") || usage.includes("video_clip") || asset.asset_id?.startsWith?.("cg_") || asset.asset_id?.startsWith?.("vid_");
    });
  }

  function capabilitySummary() {
    const enabled = [
      capabilities.has_choices && "choices",
      capabilities.has_worldline && "worldline",
      capabilities.has_state && "state",
      capabilities.has_character_portraits && "portraits",
      capabilities.has_video && "video",
      capabilities.has_gallery && "gallery",
      capabilities.has_endings && "endings",
      capabilities.has_chapters && "chapters",
    ].filter(Boolean);
    return enabled.length ? enabled.join(" / ") : "text-only";
  }

  function setFontScale(scale) {
    document.documentElement.style.setProperty("--font-scale", String(scale));
    showToast("设置已更新");
  }

  function chapterName(item) {
    const chapter = (pkg.chapters || []).find((entry) => entry.chapter_id === item.chapter_id || entry.entry_node_id === item.node_id);
    return chapter?.title || item.chapter_id || "未分章";
  }

  function displayKey(key) {
    const labels = {
      exposure_level: "力量暴露度",
      restraint_truth_axis: "克制/真诚",
      secret_acknowledge_axis: "秘密承认",
      sect_self_axis: "师门/自我",
      lu_understanding: "陆雪琪理解",
      xiaofan_injury: "伤势",
    };
    return labels[key] || String(key).replaceAll("_", " ");
  }

  function showToast(message) {
    els.toast.textContent = message;
    els.toast.hidden = false;
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
      els.toast.hidden = true;
    }, 1800);
  }

  function shortLabel(value, length) {
    const text = String(value).trim();
    return text.length > length ? `${text.slice(0, length)}…` : text;
  }

  function playerTitle(value) {
    return String(value || "").replace(/\s*\(CH\d+\)\s*$/i, "");
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }
})();
