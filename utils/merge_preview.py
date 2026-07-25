"""Merge PSD 预览：每源文件压平为单张 RGBA，避免重建 PSD 后再 composite。"""
from __future__ import annotations

import base64
import io
import os

from PIL import Image
from psd_tools import PSDImage

from . import psd_io

_PREVIEW_MAX = 1200

# (abs_path, include_hidden) -> (mtime, PIL.Image)
_flat_cache: dict[tuple[str, bool], tuple[float, Image.Image]] = {}

# 节点执行后注册的内存 PSD 预览（node_id -> encoded preview dict）
_node_psd_preview: dict[str, dict] = {}


def normalize_node_id(node_id) -> str | None:
    """ComfyUI UNIQUE_ID；INPUT_IS_LIST 节点可能收到 list。"""
    if node_id is None:
        return None
    if isinstance(node_id, list):
        node_id = node_id[0] if node_id else None
    if node_id is None or node_id == "":
        return None
    return str(node_id)


def register_flat_preview(node_id, flat: Image.Image) -> None:
    """注册已压平的 RGBA 预览图（Merge 交互画布用）。"""
    nid = normalize_node_id(node_id)
    if not nid:
        return
    _node_psd_preview[nid] = encode_layer_preview(flat)


def save_node_flat_preview_ui(node_id, flat: Image.Image) -> dict | None:
    """保存压平预览到 temp，供 UI /view 与 Merge 前端读取；同时写入服务端缓存。"""
    nid = normalize_node_id(node_id)
    if flat.mode != "RGBA":
        flat = flat.convert("RGBA")
    if nid:
        register_flat_preview(nid, flat)

    try:
        from folder_paths import get_temp_directory
    except ImportError:
        return None

    temp_dir = get_temp_directory()
    os.makedirs(temp_dir, exist_ok=True)
    filename = f"psd2layer_flat_{nid or 'x'}.png"
    flat.save(os.path.join(temp_dir, filename), format="PNG")
    return {"filename": filename, "subfolder": "", "type": "temp"}


def get_flattened_psd(path: str, include_hidden: bool) -> Image.Image:
    """读取并压平单个 PSD；按路径+mtime 缓存。"""
    abs_path = psd_io.resolve_psd_path(path)
    mtime = os.path.getmtime(abs_path)
    key = (abs_path, include_hidden)
    cached = _flat_cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]

    psd = PSDImage.open(abs_path)
    flat = psd_io.flatten_psd_to_rgba(psd, include_hidden=include_hidden)
    _flat_cache[key] = (mtime, flat)
    return flat


def encode_layer_preview(flat: Image.Image) -> dict:
    """压平图 → 预览 PNG base64 + 尺寸元数据（严格保持宽高比）。"""
    full_w, full_h = flat.size
    scale = min(_PREVIEW_MAX / full_w, _PREVIEW_MAX / full_h, 1.0)
    preview_w = max(1, int(round(full_w * scale)))
    preview_h = max(1, int(round(full_h * scale)))
    preview = flat.resize((preview_w, preview_h), Image.LANCZOS)
    buf = io.BytesIO()
    preview.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {
        "image": b64,
        "width": full_w,
        "height": full_h,
        "preview_width": preview.width,
        "preview_height": preview.height,
    }


def register_node_psd_preview(node_id, psd: PSDImage) -> None:
    """节点执行后注册内存 PSD，供 Merge 交互预览使用。"""
    nid = normalize_node_id(node_id)
    if not nid:
        return
    flat = psd_io.flatten_psd_to_rgba(psd, include_hidden=True)
    _node_psd_preview[nid] = encode_layer_preview(flat)


def get_node_psd_preview(node_id) -> dict | None:
    nid = normalize_node_id(node_id)
    if not nid:
        return None
    return _node_psd_preview.get(nid)


def flatten_sources_for_preview(
    sources: list[dict],
    include_hidden: bool,
) -> list[dict]:
    """为每个预览源生成压平图层数据（文件路径或已执行节点的内存 PSD）。"""
    layers: list[dict] = []
    for src in sources:
        if not isinstance(src, dict):
            continue
        if src.get("path"):
            flat = get_flattened_psd(str(src["path"]), include_hidden)
            layers.append(encode_layer_preview(flat))
            continue
        node_id = src.get("node_id")
        if node_id is not None:
            cached = get_node_psd_preview(node_id)
            if cached is None:
                nid = normalize_node_id(node_id)
                raise ValueError(
                    f"节点 {nid or node_id} 的 PSD 预览不可用，请先 Queue 运行上游节点后再点「刷新图层」"
                )
            layers.append(dict(cached))
    return layers


def flatten_paths_for_preview(
    paths: list[str],
    include_hidden: bool,
) -> list[dict]:
    """为每个 PSD 路径生成预览层数据（每文件一张压平图）。"""
    return flatten_sources_for_preview(
        [{"path": p} for p in paths],
        include_hidden,
    )
