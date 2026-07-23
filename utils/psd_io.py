"""PSD 读写与张量/PIL 转换封装。

主用 psd_tools（create_pixel_layer 的 top/left 直接支持偏移定位）。
若未来需更高兼容性，可在 build_psd 内切换到 pytoshop 实现，节点接口不变。
"""
from __future__ import annotations

import os

import numpy as np
import torch
from PIL import Image

from psd_tools import PSDImage
from psd_tools.constants import BlendMode


# ---------------------------------------------------------------------------
# BlendMode 枚举转换
# ---------------------------------------------------------------------------
def blend_mode_to_str(mode) -> str:
    """BlendMode 枚举 → 字符串名（如 'NORMAL'）。"""
    if hasattr(mode, "name"):
        return mode.name
    return str(mode)


def parse_blend_mode(mode) -> BlendMode:
    """字符串名 → BlendMode 枚举；未知则回退 NORMAL。"""
    if isinstance(mode, BlendMode):
        return mode
    if isinstance(mode, str):
        try:
            return BlendMode[mode.upper()]
        except KeyError:
            return BlendMode.NORMAL
    return BlendMode.NORMAL


# ---------------------------------------------------------------------------
# 张量 ↔ PIL
# ---------------------------------------------------------------------------
def _drop_batch(t: torch.Tensor) -> torch.Tensor:
    """去掉 batch 维 [1,H,W,C] → [H,W,C]，并转到 CPU float。"""
    t = t.detach().cpu()
    if t.ndim == 4 and t.shape[0] == 1:
        t = t[0]
    return t.float()


def pil_rgba_to_tensor(pil: Image.Image) -> torch.Tensor:
    """PIL（任意模式）→ [H,W,4] float 0-1（统一为 RGBA）。"""
    if pil.mode != "RGBA":
        pil = pil.convert("RGBA")
    arr = np.asarray(pil, dtype=np.float32) / 255.0
    return torch.from_numpy(arr)


def tensor_to_pil_rgba(t: torch.Tensor) -> Image.Image:
    """[H,W,{3,4}] float → PIL RGBA。"""
    t = _drop_batch(t)
    arr = np.clip(t.numpy() * 255.0, 0, 255).astype(np.uint8)
    if arr.ndim == 2:  # 灰度
        arr = np.stack([arr] * 3, axis=-1)
    if arr.shape[-1] == 3:  # 无 alpha → 不透明
        alpha = np.full(arr.shape[:2] + (1,), 255, dtype=np.uint8)
        arr = np.concatenate([arr, alpha], axis=-1)
    return Image.fromarray(arr, mode="RGBA")


def tensor_to_alpha(t: torch.Tensor) -> torch.Tensor:
    """提取 alpha 通道 → [H,W] float 0-1；无 alpha 通道则返回全不透明。"""
    t = _drop_batch(t)
    if t.shape[-1] == 4:
        return t[..., 3]
    return torch.ones(t.shape[:2], dtype=t.dtype)


def apply_alpha(color_tensor: torch.Tensor, alpha: torch.Tensor) -> torch.Tensor:
    """用给定 alpha 替换图像的第 4 通道（用于 alpha_source='original'）。"""
    t = _drop_batch(color_tensor)
    rgb = t[..., :3]
    a = _drop_batch(alpha)
    if a.shape[:2] != rgb.shape[:2]:
        return t  # 尺寸不匹配则原样返回，避免错位
    return torch.cat([rgb, a.unsqueeze(-1)], dim=-1)


# ---------------------------------------------------------------------------
# PSD 写入
# ---------------------------------------------------------------------------
def build_psd(layers: list[dict], canvas_w: int, canvas_h: int) -> PSDImage:
    """根据图层列表构建分层 PSD。

    layers: list of dict，每项含 image(PIL RGBA)、left、top、opacity、
            blend_mode、name、visible。
    顺序约定：按 bottom→top 依次调用。create_pixel_layer 把新层加到栈顶，
    因此首个图层最终位于最底层（与 psd_tools 的 for-layer 顺序一致）。
    """
    psd = PSDImage.new(
        mode="RGBA", size=(int(canvas_w), int(canvas_h)), depth=8, color=0
    )
    for L in layers:
        blend = parse_blend_mode(L.get("blend_mode", "NORMAL"))
        layer = psd.create_pixel_layer(
            L["image"],
            name=str(L.get("name", "Layer")),
            top=int(L.get("top", 0)),
            left=int(L.get("left", 0)),
            opacity=int(L.get("opacity", 255)),
            blend_mode=blend,
        )
        layer.visible = bool(L.get("visible", True))
    return psd


def psd_to_flat_tensor(psd: PSDImage) -> torch.Tensor:
    """整张 PSD 合成 → [1,H,W,4] 张量（还原后的预览）。"""
    pil = psd.composite()
    if pil is None:
        pil = Image.new("RGBA", psd.size)
    return pil_rgba_to_tensor(pil).unsqueeze(0)


def save_psd(psd: PSDImage, path: str) -> str:
    """保存 PSD 到指定路径，自动创建目录。"""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    psd.save(path)
    return path
