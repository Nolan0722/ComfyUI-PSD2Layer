import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const MERGE_CONFIGS = {
    "PSD2Layer Merge PSD Files": {
        slotPrefix: "psd",
        inputType: "PSD",
        slotCount: 5,
        allowPath: true,
        emptyHint: "连接 PSD 后拖动画布操作",
        connectHint: "请连接 PSD 输出到 psd_1…",
        slotLabel: (i) => `psd_${i}`,
    },
    "PSD2Layer Merge Layer Images": {
        slotPrefix: "image",
        inputType: "IMAGE",
        slotCount: 10,
        allowPath: false,
        emptyHint: "连接图像后拖动画布操作",
        connectHint: "请连接图像到 image_1…（先 Queue 上游以刷新预览）",
        slotLabel: (i) => `image_${i}`,
    },
};
const LOAD_FILE_NODE = "PSD2Layer Load File";
const PREVIEW_MAX = 1200;
const DEFAULT_CANVAS_W = 3000;
const DEFAULT_CANVAS_H = 6000;
const PREVIEW_PANEL_WIDTH = 520;
const PREVIEW_STAGE_SIZE = 480;
const PREVIEW_TOOLBAR_HEIGHT = 40;
const HANDLE_R = 7;
const ROT_HANDLE_DIST = 30;
const MIN_SCALE = 0.1;
const MAX_SCALE = 10;
const MIN_VIEW_ZOOM = 0.15;
const MAX_VIEW_ZOOM = 8;
const VIEW_FIT_PADDING = 0.92;

function injectMergeStyles() {
    if (document.getElementById("psd2layer-merge-styles")) return;
    const style = document.createElement("style");
    style.id = "psd2layer-merge-styles";
    style.textContent = `
.psd2layer-merge-preview {
    width: 100%;
    box-sizing: border-box;
    padding: 4px 2px 2px;
    font-family: var(--comfy-font-family, system-ui, sans-serif);
}
.psd2layer-merge-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    min-height: ${PREVIEW_TOOLBAR_HEIGHT}px;
}
.psd2layer-merge-status {
    flex: 1;
    font-size: 11px;
    line-height: 1.35;
    color: rgba(255, 255, 255, 0.55);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.psd2layer-merge-refresh {
    flex-shrink: 0;
    font-size: 11px;
    padding: 5px 12px;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.14);
    background: rgba(255,255,255,0.06);
    color: rgba(255, 255, 255, 0.88);
    cursor: pointer;
}
.psd2layer-merge-refresh:hover:not(:disabled) {
    border-color: rgba(120, 170, 255, 0.45);
}
.psd2layer-merge-refresh:disabled { opacity: 0.45; cursor: default; }
.psd2layer-merge-slotbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
}
.psd2layer-merge-slotlabel {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.45);
    margin-right: 2px;
}
.psd2layer-merge-slotbtn {
    font-size: 10px;
    line-height: 1;
    padding: 4px 10px;
    border-radius: 5px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.75);
    cursor: pointer;
}
.psd2layer-merge-slotbtn:hover {
    border-color: rgba(120, 170, 255, 0.45);
    color: rgba(255, 255, 255, 0.95);
}
.psd2layer-merge-slotbtn.active {
    border-color: rgba(120, 180, 255, 0.75);
    background: rgba(80, 140, 255, 0.22);
    color: #fff;
}
.psd2layer-merge-stage {
    position: relative;
    width: 100%;
    height: ${PREVIEW_STAGE_SIZE}px;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: #141414;
}
.psd2layer-merge-checker {
    position: absolute;
    inset: 0;
    background-color: #1c1c1c;
    background-image:
        linear-gradient(45deg, #2a2a2a 25%, transparent 25%),
        linear-gradient(-45deg, #2a2a2a 25%, transparent 25%),
        linear-gradient(45deg, transparent 75%, #2a2a2a 75%),
        linear-gradient(-45deg, transparent 75%, #2a2a2a 75%);
    background-size: 14px 14px;
    background-position: 0 0, 0 7px, 7px -7px, -7px 0;
    opacity: 0.5;
    pointer-events: none;
}
.psd2layer-merge-stage canvas {
    position: absolute;
    inset: 0;
    z-index: 1;
    display: block;
    width: 100%;
    height: 100%;
    touch-action: none;
}
.psd2layer-merge-badge {
    position: absolute;
    z-index: 2;
    right: 8px;
    bottom: 8px;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 10px;
    color: rgba(255, 255, 255, 0.9);
    background: rgba(0, 0, 0, 0.62);
    border: 1px solid rgba(255, 255, 255, 0.12);
    pointer-events: none;
}
.psd2layer-merge-empty {
    position: absolute;
    z-index: 2;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(255, 255, 255, 0.35);
    font-size: 12px;
    pointer-events: none;
}
`;
    document.head.appendChild(style);
}

function ensureNodeWidth(node) {
    if (!node.size || node.size[0] < PREVIEW_PANEL_WIDTH) {
        node.size[0] = PREVIEW_PANEL_WIDTH;
        node.setDirtyCanvas(true, true);
    }
}

function widgetValue(node, name, fallback = 0) {
    const w = node.widgets?.find((x) => x.name === name);
    if (!w) return fallback;
    return w.value ?? fallback;
}

function setWidgetValue(node, name, value) {
    const w = node.widgets?.find((x) => x.name === name);
    if (!w) return;
    w.value = value;
}

function hideTransformWidgets(node) {
    const re = /^(offset_|scale_|rotation_)/;
    node.widgets?.forEach((w) => {
        if (w.name && re.test(w.name)) w.hidden = true;
    });
}

function getGraphLink(linkId) {
    const graph = app.graph;
    if (!graph || linkId == null) return null;
    if (graph.links?.[linkId]) return graph.links[linkId];
    if (typeof graph.getLink === "function") return graph.getLink(linkId);
    return null;
}

function connectedSlotSource(node, slotIndex, cfg) {
    const input = node.inputs?.find(
        (inp) => inp.name === `${cfg.slotPrefix}_${slotIndex}`,
    );
    if (!input || input.link == null) return null;
    const link = getGraphLink(input.link);
    if (!link) return null;
    const upstream = app.graph.getNodeById(link.origin_id);
    if (!upstream) return null;
    const out = upstream.outputs?.[link.origin_slot];
    if (!out || out.type !== cfg.inputType) return null;

    if (cfg.allowPath && upstream.type === LOAD_FILE_NODE) {
        const pathWidget = upstream.widgets?.find((w) => w.name === "psd_file");
        const path = pathWidget?.value;
        if (path && String(path).trim()) {
            return { kind: "path", path: String(path).trim() };
        }
    }
    return { kind: "node", nodeId: link.origin_id };
}

function collectSlots(node, cfg) {
    const slots = [];
    const slotCount = cfg.slotCount || 5;
    for (let i = 1; i <= slotCount; i++) {
        const source = connectedSlotSource(node, i, cfg);
        if (!source) continue;
        slots.push({
            slotIndex: i,
            source,
            offsetX: Number(widgetValue(node, `offset_x_${i}`, 0)),
            offsetY: Number(widgetValue(node, `offset_y_${i}`, 0)),
            scale: Number(widgetValue(node, `scale_${i}`, 1)),
            rotation: Number(widgetValue(node, `rotation_${i}`, 0)),
        });
    }
    return slots;
}

function syncSlotWidgets(node, slot) {
    const i = slot.slotIndex;
    setWidgetValue(node, `offset_x_${i}`, Math.round(slot.offsetX));
    setWidgetValue(node, `offset_y_${i}`, Math.round(slot.offsetY));
    setWidgetValue(node, `scale_${i}`, Math.round(slot.scale * 100) / 100);
    setWidgetValue(node, `rotation_${i}`, Math.round(slot.rotation * 10) / 10);
}

function mergeCanvasSize(canvasWidth, canvasHeight) {
    const w = canvasWidth > 0 ? canvasWidth : DEFAULT_CANVAS_W;
    const h = canvasHeight > 0 ? canvasHeight : DEFAULT_CANVAS_H;
    return { width: w, height: h };
}

function layerSourceSignature(slots, includeHidden) {
    return JSON.stringify({
        sources: slots.map((s) => s.source),
        include_hidden: includeHidden,
    });
}

function loadImageFromBase64(b64) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error("图像解码失败"));
        img.src = `data:image/png;base64,${b64}`;
    });
}

function loadImageFromUrl(url) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error("图像加载失败"));
        img.src = url;
    });
}

function nodeOutputImages(nodeId) {
    const outs = app.nodeOutputs?.[String(nodeId)];
    return outs?.images?.length ? outs.images : null;
}

function viewImageUrl(imgMeta) {
    const q = new URLSearchParams({
        filename: imgMeta.filename,
        type: imgMeta.type || "temp",
        subfolder: imgMeta.subfolder || "",
        rand: String(Math.random()),
    });
    return `/view?${q}`;
}

async function resolveSourcePreview(source, includeHidden) {
    if (source.kind === "node") {
        const images = nodeOutputImages(source.nodeId);
        if (images?.length) {
            const meta = images[images.length - 1];
            const image = await loadImageFromUrl(viewImageUrl(meta));
            return {
                image,
                width: image.naturalWidth,
                height: image.naturalHeight,
                preview_width: image.naturalWidth,
                preview_height: image.naturalHeight,
            };
        }
    }

    const body =
        source.kind === "path"
            ? { sources: [{ path: source.path }], include_hidden: includeHidden }
            : {
                  sources: [{ node_id: source.nodeId }],
                  include_hidden: includeHidden,
              };
    const res = await fetch("/psd2layer/merge_flat_layers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
        throw new Error(data.error || res.statusText);
    }
    const layer = (data.layers || [])[0];
    if (!layer) {
        throw new Error(
            source.kind === "node"
                ? `节点 ${source.nodeId} 尚无预览，请先 Queue 运行该节点`
                : "预览数据为空",
        );
    }
    const image = await loadImageFromBase64(layer.image);
    return {
        image,
        width: layer.width,
        height: layer.height,
        preview_width: layer.preview_width,
        preview_height: layer.preview_height,
    };
}

function contentDims(canvasW, canvasH) {
    const fit = Math.min(1, PREVIEW_MAX / Math.max(canvasW, canvasH));
    const pw = Math.max(1, Math.round(canvasW * fit));
    const ph = Math.max(1, Math.round(pw * (canvasH / canvasW)));
    const displayScale = pw / canvasW;
    return { pw, ph, displayScale };
}

function viewportMetrics(pw, ph, view, viewportSize) {
    const fitZoom =
        Math.min(viewportSize / pw, viewportSize / ph) * VIEW_FIT_PADDING;
    const zoom = fitZoom * view.zoom;
    return { fitZoom, zoom, viewportSize };
}

function screenToScene(sx, sy, pw, ph, view, viewportSize) {
    const { zoom, viewportSize: vc } = viewportMetrics(pw, ph, view, viewportSize);
    return {
        x: (sx - vc / 2 - view.panX) / zoom + pw / 2,
        y: (sy - vc / 2 - view.panY) / zoom + ph / 2,
    };
}

function screenPointer(canvas, clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const sx = (clientX - rect.left) * (canvas.width / rect.width);
    const sy = (clientY - rect.top) * (canvas.height / rect.height);
    return { sx, sy };
}

function spriteCenter(sprite, canvasW, canvasH, displayScale) {
    return {
        cx: (canvasW / 2 + sprite.offsetX) * displayScale,
        cy: (canvasH / 2 + sprite.offsetY) * displayScale,
    };
}

function spriteImageSize(sprite) {
    const img = sprite.image;
    const imgW =
        sprite.meta?.width ||
        img?.naturalWidth ||
        sprite.meta?.preview_width ||
        1;
    const imgH =
        sprite.meta?.height ||
        img?.naturalHeight ||
        sprite.meta?.preview_height ||
        1;
    return { imgW, imgH };
}

function spriteDrawSize(sprite, displayScale) {
    const sc = sprite.scale > 0 ? sprite.scale : 1;
    const { imgW, imgH } = spriteImageSize(sprite);
    const factor = displayScale * sc;
    return {
        w: imgW * factor,
        h: imgH * factor,
        imgW,
        imgH,
        factor,
    };
}

function drawCanvasBounds(ctx, pw, ph) {
    ctx.save();
    ctx.strokeStyle = "rgba(80, 150, 255, 0.9)";
    ctx.lineWidth = 2;
    ctx.setLineDash([7, 5]);
    ctx.strokeRect(1, 1, pw - 2, ph - 2);
    ctx.restore();
}

function drawCrosshairs(ctx, pw, ph, canvasW, canvasH, displayScale) {
    const cx = (canvasW / 2) * displayScale;
    const cy = (canvasH / 2) * displayScale;
    ctx.save();
    ctx.strokeStyle = "rgba(90, 150, 255, 0.45)";
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(cx, 0);
    ctx.lineTo(cx, ph);
    ctx.moveTo(0, cy);
    ctx.lineTo(pw, cy);
    ctx.stroke();
    ctx.restore();
}

function drawSprite(ctx, sprite, canvasW, canvasH, displayScale, selected) {
    const { cx, cy } = spriteCenter(sprite, canvasW, canvasH, displayScale);
    const { w, h } = spriteDrawSize(sprite, displayScale);
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((sprite.rotation * Math.PI) / 180);
    ctx.drawImage(sprite.image, -w / 2, -h / 2, w, h);
    if (selected) {
        ctx.strokeStyle = "rgba(120, 180, 255, 0.95)";
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 3]);
        ctx.strokeRect(-w / 2, -h / 2, w, h);
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(0, -h / 2);
        ctx.lineTo(0, -h / 2 - ROT_HANDLE_DIST);
        ctx.strokeStyle = "rgba(255, 200, 80, 0.9)";
        ctx.stroke();
        ctx.fillStyle = "rgba(255, 200, 80, 0.95)";
        ctx.beginPath();
        ctx.arc(0, -h / 2 - ROT_HANDLE_DIST, HANDLE_R, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "rgba(120, 220, 255, 0.95)";
        for (const [hx, hy] of [
            [-w / 2, -h / 2],
            [w / 2, -h / 2],
            [w / 2, h / 2],
            [-w / 2, h / 2],
        ]) {
            ctx.beginPath();
            ctx.arc(hx, hy, HANDLE_R, 0, Math.PI * 2);
            ctx.fill();
        }
    }
    ctx.restore();
}

function hitDist(x1, y1, x2, y2) {
    return Math.hypot(x1 - x2, y1 - y2);
}

function localPointer(px, py, sprite, canvasW, canvasH, displayScale) {
    const { cx, cy } = spriteCenter(sprite, canvasW, canvasH, displayScale);
    const angle = (-sprite.rotation * Math.PI) / 180;
    const dx = px - cx;
    const dy = py - cy;
    return {
        lx: dx * Math.cos(angle) - dy * Math.sin(angle),
        ly: dx * Math.sin(angle) + dy * Math.cos(angle),
        cx,
        cy,
    };
}

function hitTestSprite(px, py, sprite, canvasW, canvasH, displayScale) {
    const { lx, ly } = localPointer(px, py, sprite, canvasW, canvasH, displayScale);
    const { w, h } = spriteDrawSize(sprite, displayScale);
    return lx >= -w / 2 && lx <= w / 2 && ly >= -h / 2 && ly <= h / 2;
}

function hitTestHandle(px, py, sprite, canvasW, canvasH, displayScale) {
    const { lx, ly } = localPointer(px, py, sprite, canvasW, canvasH, displayScale);
    const { w, h } = spriteDrawSize(sprite, displayScale);
    const rotY = -h / 2 - ROT_HANDLE_DIST;
    if (hitDist(lx, ly, 0, rotY) <= HANDLE_R + 3) return "rotate";
    for (const [hx, hy] of [
        [-w / 2, -h / 2],
        [w / 2, -h / 2],
        [w / 2, h / 2],
        [-w / 2, h / 2],
    ]) {
        if (hitDist(lx, ly, hx, hy) <= HANDLE_R + 3) return "scale";
    }
    if (hitTestSprite(px, py, sprite, canvasW, canvasH, displayScale)) return "move";
    return null;
}

function composeScene(sceneCanvas, sprites, selectedSlot, canvasW, canvasH) {
    const { pw, ph, displayScale } = contentDims(canvasW, canvasH);
    sceneCanvas.width = pw;
    sceneCanvas.height = ph;
    const ctx = sceneCanvas.getContext("2d");
    ctx.clearRect(0, 0, pw, ph);
    drawCanvasBounds(ctx, pw, ph);
    drawCrosshairs(ctx, pw, ph, canvasW, canvasH, displayScale);
    for (let i = sprites.length - 1; i >= 0; i--) {
        const sp = sprites[i];
        drawSprite(ctx, sp, canvasW, canvasH, displayScale, sp.slotIndex === selectedSlot);
    }
    return { pw, ph, displayScale };
}

function renderViewport(displayCanvas, sceneCanvas, view, viewportSize) {
    const pw = sceneCanvas.width;
    const ph = sceneCanvas.height;
    displayCanvas.width = viewportSize;
    displayCanvas.height = viewportSize;
    const ctx = displayCanvas.getContext("2d");
    ctx.fillStyle = "#1a1a1a";
    ctx.fillRect(0, 0, viewportSize, viewportSize);
    const { zoom } = viewportMetrics(pw, ph, view, viewportSize);
    ctx.save();
    ctx.translate(viewportSize / 2 + view.panX, viewportSize / 2 + view.panY);
    ctx.scale(zoom, zoom);
    ctx.translate(-pw / 2, -ph / 2);
    ctx.drawImage(sceneCanvas, 0, 0);
    ctx.restore();
}

function clampSpriteScale(s) {
    return Math.min(MAX_SCALE, Math.max(MIN_SCALE, s));
}

function clampViewZoom(z) {
    return Math.min(MAX_VIEW_ZOOM, Math.max(MIN_VIEW_ZOOM, z));
}

app.registerExtension({
    name: "PSD2Layer.MergeCanvas",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        const cfg = MERGE_CONFIGS[nodeData.name];
        if (!cfg) return;

        injectMergeStyles();

        const onComputeSize = nodeType.prototype.computeSize;
        nodeType.prototype.computeSize = function (...args) {
            const size = onComputeSize
                ? onComputeSize.apply(this, args)
                : [this.size?.[0] ?? 200, this.size?.[1] ?? 100];
            size[0] = Math.max(size[0], PREVIEW_PANEL_WIDTH);
            return size;
        };

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const ret = onNodeCreated?.apply(this, arguments);
            ensureNodeWidth(this);
            hideTransformWidgets(this);

            const node = this;
            const root = document.createElement("div");
            root.className = "psd2layer-merge-preview";

            const toolbar = document.createElement("div");
            toolbar.className = "psd2layer-merge-toolbar";
            const status = document.createElement("span");
            status.className = "psd2layer-merge-status";
            status.textContent = "滚轮缩放视图 · 中键/Alt 拖动平移 · 拖动物体调整";
            const refreshBtn = document.createElement("button");
            refreshBtn.type = "button";
            refreshBtn.className = "psd2layer-merge-refresh";
            refreshBtn.textContent = "↻ 刷新图层";
            toolbar.appendChild(status);
            toolbar.appendChild(refreshBtn);

            const slotBar = document.createElement("div");
            slotBar.className = "psd2layer-merge-slotbar";

            const stage = document.createElement("div");
            stage.className = "psd2layer-merge-stage";
            const checker = document.createElement("div");
            checker.className = "psd2layer-merge-checker";
            const emptyHint = document.createElement("div");
            emptyHint.className = "psd2layer-merge-empty";
            emptyHint.textContent = cfg.emptyHint;
            const canvas = document.createElement("canvas");
            canvas.style.visibility = "hidden";
            const sceneCanvas = document.createElement("canvas");
            const badge = document.createElement("div");
            badge.className = "psd2layer-merge-badge";
            badge.textContent = "—";
            stage.appendChild(checker);
            stage.appendChild(emptyHint);
            stage.appendChild(canvas);
            stage.appendChild(badge);
            root.appendChild(toolbar);
            root.appendChild(slotBar);
            root.appendChild(stage);

            this.addDOMWidget("merge_canvas", "mergecanvas", root, {
                getMinHeight: () =>
                    PREVIEW_STAGE_SIZE + PREVIEW_TOOLBAR_HEIGHT + 36,
                hideOnZoom: false,
            });

            const layerCache = { signature: null, images: [], meta: [] };
            const renderDims = {
                pw: 1,
                ph: 1,
                displayScale: 1,
                canvasW: DEFAULT_CANVAS_W,
                canvasH: DEFAULT_CANVAS_H,
            };
            const view = { zoom: 1, panX: 0, panY: 0 };
            let selectedSlot = null;
            let inflight = false;

            const editor = {
                mode: null,
                startPx: 0,
                startPy: 0,
                startSlot: null,
                startOx: 0,
                startOy: 0,
                startScale: 1,
                startRot: 0,
                startDist: 1,
                startAngle: 0,
                startPanX: 0,
                startPanY: 0,
                startSx: 0,
                startSy: 0,
            };

            const setPreviewVisible = (visible) => {
                canvas.style.visibility = visible ? "visible" : "hidden";
                emptyHint.style.display = visible ? "none" : "flex";
                badge.style.display = visible ? "block" : "none";
                slotBar.style.display = visible ? "flex" : "none";
            };

            const updateSlotBar = () => {
                slotBar.innerHTML = "";
                const slots = collectSlots(node, cfg);
                if (!slots.length) return;
                const label = document.createElement("span");
                label.className = "psd2layer-merge-slotlabel";
                label.textContent = "选择编辑:";
                slotBar.appendChild(label);
                for (const s of slots) {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className =
                        "psd2layer-merge-slotbtn" +
                        (selectedSlot === s.slotIndex ? " active" : "");
                    btn.textContent = cfg.slotLabel(s.slotIndex);
                    btn.addEventListener("click", () => {
                        selectedSlot = s.slotIndex;
                        render();
                    });
                    slotBar.appendChild(btn);
                }
            };

            const buildSprites = () => {
                const slots = collectSlots(node, cfg);
                return slots.map((s, i) => ({
                    slotIndex: s.slotIndex,
                    offsetX: s.offsetX,
                    offsetY: s.offsetY,
                    scale: s.scale > 0 ? s.scale : 1,
                    rotation: s.rotation,
                    image: layerCache.images[i],
                    meta: layerCache.meta[i],
                }));
            };

            const render = () => {
                if (!layerCache.images.length) {
                    setPreviewVisible(false);
                    return;
                }
                setPreviewVisible(true);
                const { width: cw, height: ch } = mergeCanvasSize(
                    Number(widgetValue(node, "canvas_width", DEFAULT_CANVAS_W)),
                    Number(widgetValue(node, "canvas_height", DEFAULT_CANVAS_H)),
                );
                const sprites = buildSprites();
                const dims = composeScene(
                    sceneCanvas,
                    sprites,
                    selectedSlot,
                    cw,
                    ch,
                );
                renderDims.pw = dims.pw;
                renderDims.ph = dims.ph;
                renderDims.displayScale = dims.displayScale;
                renderDims.canvasW = cw;
                renderDims.canvasH = ch;
                renderViewport(canvas, sceneCanvas, view, PREVIEW_STAGE_SIZE);
                updateSlotBar();
                badge.textContent = `${cw} × ${ch} · 视图 ${(view.zoom * 100).toFixed(0)}%`;
                const sel = sprites.find((s) => s.slotIndex === selectedSlot);
                if (sel) {
                    status.textContent = `${cfg.slotLabel(sel.slotIndex)} · ${Math.round(sel.offsetX)},${Math.round(sel.offsetY)} · 缩放 ${sel.scale.toFixed(2)} · 旋转 ${sel.rotation.toFixed(1)}°`;
                } else {
                    status.textContent =
                        "选择编辑按钮切换图层 · 滚轮缩放 · 中键/Alt 平移";
                }
            };

            const fetchLayers = async (force = false) => {
                const slots = collectSlots(node, cfg);
                const includeHidden = Boolean(
                    widgetValue(node, "include_hidden", true),
                );
                if (!slots.length) {
                    status.textContent = cfg.connectHint;
                    setPreviewVisible(false);
                    return;
                }
                const sig = layerSourceSignature(slots, includeHidden);
                if (
                    !force &&
                    layerCache.signature === sig &&
                    layerCache.images.length
                ) {
                    render();
                    return;
                }
                if (inflight) return;
                inflight = true;
                refreshBtn.disabled = true;
                status.textContent = "正在加载预览图层…";
                setPreviewVisible(false);
                try {
                    const layers = [];
                    for (const slot of slots) {
                        layers.push(
                            await resolveSourcePreview(slot.source, includeHidden),
                        );
                    }
                    layerCache.signature = sig;
                    layerCache.images = layers.map((l) => l.image);
                    layerCache.meta = layers.map((l) => ({
                        width: l.width,
                        height: l.height,
                        preview_width: l.preview_width || l.image?.naturalWidth,
                        preview_height:
                            l.preview_height || l.image?.naturalHeight,
                    }));
                    if (selectedSlot == null && slots.length) {
                        selectedSlot = slots[0].slotIndex;
                    }
                    render();
                } catch (err) {
                    console.warn("[PSD2Layer] merge flat layers:", err);
                    status.textContent = `预览失败: ${err.message || err}`;
                    setPreviewVisible(false);
                } finally {
                    inflight = false;
                    refreshBtn.disabled = false;
                }
            };

            const updateFromCanvas = (forceFetch = false) => {
                ensureNodeWidth(node);
                fetchLayers(forceFetch);
            };

            const onPointerDown = (e) => {
                if (!layerCache.images.length) return;

                const { sx, sy } = screenPointer(canvas, e.clientX, e.clientY);
                const { pw, ph, displayScale, canvasW, canvasH } = renderDims;

                if (e.button === 1 || e.altKey) {
                    e.preventDefault();
                    canvas.setPointerCapture(e.pointerId);
                    editor.mode = "viewpan";
                    editor.startPanX = view.panX;
                    editor.startPanY = view.panY;
                    editor.startSx = sx;
                    editor.startSy = sy;
                    return;
                }

                if (e.button !== 0) return;
                e.preventDefault();
                canvas.setPointerCapture(e.pointerId);

                const { x: px, y: py } = screenToScene(
                    sx,
                    sy,
                    pw,
                    ph,
                    view,
                    PREVIEW_STAGE_SIZE,
                );
                const sprites = buildSprites();

                let hit = null;
                let hitSprite = null;
                if (selectedSlot != null) {
                    const sel = sprites.find((s) => s.slotIndex === selectedSlot);
                    if (sel) {
                        hit = hitTestHandle(px, py, sel, canvasW, canvasH, displayScale);
                        if (hit) hitSprite = sel;
                    }
                }
                if (!hit) {
                    for (const sp of sprites) {
                        if (hitTestSprite(px, py, sp, canvasW, canvasH, displayScale)) {
                            hitSprite = sp;
                            selectedSlot = sp.slotIndex;
                            hit =
                                hitTestHandle(px, py, sp, canvasW, canvasH, displayScale) ||
                                "move";
                            break;
                        }
                    }
                }
                if (!hitSprite || !hit) return;

                selectedSlot = hitSprite.slotIndex;
                editor.mode = hit;
                editor.startPx = px;
                editor.startPy = py;
                editor.startSlot = hitSprite.slotIndex;
                editor.startOx = hitSprite.offsetX;
                editor.startOy = hitSprite.offsetY;
                editor.startScale = hitSprite.scale;
                editor.startRot = hitSprite.rotation;
                const { cx, cy } = spriteCenter(
                    hitSprite,
                    canvasW,
                    canvasH,
                    displayScale,
                );
                editor.startDist = Math.max(1, hitDist(px, py, cx, cy));
                editor.startAngle = Math.atan2(py - cy, px - cx);
                render();
            };

            const onPointerMove = (e) => {
                if (!editor.mode) return;
                const { sx, sy } = screenPointer(canvas, e.clientX, e.clientY);
                const { pw, ph, displayScale, canvasW, canvasH } = renderDims;

                if (editor.mode === "viewpan") {
                    view.panX = editor.startPanX + (sx - editor.startSx);
                    view.panY = editor.startPanY + (sy - editor.startSy);
                    render();
                    return;
                }

                const { x: px, y: py } = screenToScene(
                    sx,
                    sy,
                    pw,
                    ph,
                    view,
                    PREVIEW_STAGE_SIZE,
                );
                const slot = buildSprites().find(
                    (s) => s.slotIndex === editor.startSlot,
                );
                if (!slot) return;

                if (editor.mode === "move") {
                    slot.offsetX =
                        editor.startOx + (px - editor.startPx) / displayScale;
                    slot.offsetY =
                        editor.startOy + (py - editor.startPy) / displayScale;
                } else if (editor.mode === "rotate") {
                    const { cx, cy } = spriteCenter(
                        slot,
                        canvasW,
                        canvasH,
                        displayScale,
                    );
                    const angle = Math.atan2(py - cy, px - cx);
                    slot.rotation =
                        editor.startRot +
                        ((angle - editor.startAngle) * 180) / Math.PI;
                } else if (editor.mode === "scale") {
                    const { cx, cy } = spriteCenter(
                        slot,
                        canvasW,
                        canvasH,
                        displayScale,
                    );
                    const dist = Math.max(1, hitDist(px, py, cx, cy));
                    slot.scale = clampSpriteScale(
                        editor.startScale * (dist / editor.startDist),
                    );
                }

                syncSlotWidgets(node, slot);
                render();
            };

            const onPointerUp = (e) => {
                if (editor.mode) {
                    editor.mode = null;
                    canvas.releasePointerCapture(e.pointerId);
                }
            };

            const onWheel = (e) => {
                if (!layerCache.images.length) return;
                e.preventDefault();
                const factor = 1 - e.deltaY * 0.002;
                view.zoom = clampViewZoom(view.zoom * factor);
                render();
            };

            canvas.addEventListener("pointerdown", onPointerDown);
            canvas.addEventListener("pointermove", onPointerMove);
            canvas.addEventListener("pointerup", onPointerUp);
            canvas.addEventListener("pointercancel", onPointerUp);
            canvas.addEventListener("wheel", onWheel, { passive: false });

            refreshBtn.addEventListener("click", () => updateFromCanvas(true));

            const onExecuted = ({ detail }) => {
                const executedId = detail?.node;
                if (executedId == null) return;
                const slots = collectSlots(node, cfg);
                const hit = slots.some(
                    (s) =>
                        s.source.kind === "node" &&
                        String(s.source.nodeId) === String(executedId),
                );
                if (hit) updateFromCanvas(true);
            };
            api.addEventListener("executed", onExecuted);

            const onConnectionsChange = node.onConnectionsChange;
            node.onConnectionsChange = function (...args) {
                onConnectionsChange?.apply(this, args);
                selectedSlot = null;
                view.zoom = 1;
                view.panX = 0;
                view.panY = 0;
                updateFromCanvas(true);
            };

            setTimeout(() => updateFromCanvas(true), 600);
            node.psd2layerFetchMergePreview = () => updateFromCanvas(true);

            return ret;
        };
    },
});
