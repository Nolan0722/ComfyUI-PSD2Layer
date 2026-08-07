"""PSD 压平预览工具。

为 Load PSD File / Layers to PSD 的 flat_preview 输出引脚提供压平图与
临时 PNG 写入支持（按路径+mtime 缓存）。
"""
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


def normalize_node_id(node_id) -> str | None:
    """ComfyUI UNIQUE_ID；INPUT_IS_LIST 节点可能收到 list。"""
    if node_id is None:
        return None
    if isinstance(node_id, list):
        node_id = node_id[0] if node_id else None
    if node_id is None or node_id == "":
        return None
    return str(node_id)


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


def save_node_flat_preview_ui(node_id, flat: Image.Image) -> dict | None:
    """保存压平预览到 temp，供 UI /view 读取；返回 ui 图元数据或 None。"""
    nid = normalize_node_id(node_id)
    if flat.mode != "RGBA":
        flat = flat.convert("RGBA")

    try:
        from folder_paths import get_temp_directory
    except ImportError:
        return None

    temp_dir = get_temp_directory()
    os.makedirs(temp_dir, exist_ok=True)
    filename = f"psd2layer_flat_{nid or 'x'}.png"
    flat.save(os.path.join(temp_dir, filename), format="PNG")
    return {"filename": filename, "subfolder": "", "type": "temp"}
