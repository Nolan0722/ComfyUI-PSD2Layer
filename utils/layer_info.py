"""LAYER_INFO 图层元数据结构。

LAYER_INFO 是 ComfyUI 自定义数据类型（任意 Python 对象），承载单个 PSD 图层的
几何与属性信息，用于在节点间旁路传递——绕过用户中间的处理步骤，保证还原时
位置/顺序/属性不丢失。
"""
from __future__ import annotations

from typing import Any

import torch

# ComfyUI 自定义类型名（节点 RETURN_TYPES / INPUT_TYPES 中使用）
LAYER_INFO_TYPE = "LAYER_INFO"


def make_layer_info(
    *,
    left: int,
    top: int,
    width: int,
    height: int,
    opacity: int,
    blend_mode: str,
    name: str,
    visible: bool,
    alpha: torch.Tensor | None,
    canvas_w: int,
    canvas_h: int,
    group_path: list[str] | None = None,
    group_meta: list[dict[str, Any]] | None = None,
    group_indices: list[int] | None = None,
) -> dict[str, Any]:
    """构造单层 LAYER_INFO 字典。

    alpha: 该图层原始 alpha 张量 [H,W]（float 0-1），供还原节点在
           alpha_source='original' 时还原图层形状。可为 None。
    canvas_w/canvas_h: 原 PSD 画布尺寸，冗余编码以便还原节点取默认画布。
    group_path: 自外到内的父组名称链。
    group_meta: 与组链一一对应的组属性。
    group_indices: 自外到内各父组在兄弟中的序号（唯一定位同名组）。
    """
    return {
        "left": int(left),
        "top": int(top),
        "width": int(width),
        "height": int(height),
        "opacity": int(opacity),
        "blend_mode": str(blend_mode),
        "name": str(name),
        "visible": bool(visible),
        "alpha": alpha,
        "canvas_w": int(canvas_w),
        "canvas_h": int(canvas_h),
        "group_path": list(group_path or []),
        "group_meta": list(group_meta or []),
        "group_indices": list(group_indices or []),
    }


def is_layer_info(obj: Any) -> bool:
    """判断对象是否为合法的 LAYER_INFO 字典。"""
    return isinstance(obj, dict) and "left" in obj and "top" in obj and "width" in obj
