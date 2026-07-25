"""Merge PSD Files 合成逻辑（节点执行与预览 API 共用）。"""
from __future__ import annotations

import os

from . import psd_io

DEFAULT_MERGE_CANVAS_W = 3000
DEFAULT_MERGE_CANVAS_H = 6000

# (psd_ref, offset_x, offset_y, scale, rotation_deg)
MergeSlot = tuple[dict, int, int, float, float]


def ref_group_label(ref: dict, index: int) -> str:
    """从 PSD 引用取组名：文件路径 basename，或 label / PSD_N。"""
    if ref.get("label"):
        return str(ref["label"])
    path = ref.get("path")
    if path:
        return os.path.splitext(os.path.basename(str(path)))[0] or "PSD"
    return f"PSD_{index}"


def unique_group_names_from_refs(refs: list[dict]) -> list[str]:
    names: list[str] = []
    seen: dict[str, int] = {}
    for i, ref in enumerate(refs):
        base = ref_group_label(ref, i + 1)
        count = seen.get(base, 0) + 1
        seen[base] = count
        names.append(base if count == 1 else f"{base}_{count}")
    return names


def merge_canvas_size(canvas_width: int, canvas_height: int) -> tuple[int, int]:
    """解析合并画布尺寸；0 表示使用默认 3000×6000。"""
    w = int(canvas_width) if canvas_width else DEFAULT_MERGE_CANVAS_W
    h = int(canvas_height) if canvas_height else DEFAULT_MERGE_CANVAS_H
    return max(1, w), max(1, h)


def slot_placement_on_canvas(
    psd_w: int,
    psd_h: int,
    canvas_w: int,
    canvas_h: int,
    scale: float,
    offset_x: int,
    offset_y: int,
) -> tuple[int, int]:
    """PSD 在画布上居中，再叠加用户 offset。"""
    sc = float(scale) if scale > 0 else 1.0
    sw = max(1, int(round(psd_w * sc)))
    sh = max(1, int(round(psd_h * sc)))
    base_x = (canvas_w - sw) // 2 + int(offset_x)
    base_y = (canvas_h - sh) // 2 + int(offset_y)
    return base_x, base_y


def compose_merged_psd(
    slots: list[MergeSlot],
    *,
    include_hidden: bool = True,
    canvas_width: int = 0,
    canvas_height: int = 0,
) -> PSDImage:
    """按 PSD 引用（文件路径或内存）与变换合成 PSD。

    叠放顺序：psd_5 最底，psd_1 最顶（后写入的图层在上层）。
    """
    if not slots:
        raise ValueError("未提供任何 PSD 输入")

    W, H = merge_canvas_size(canvas_width, canvas_height)

    refs = [ref for ref, _, _, _, _ in slots]
    group_names = unique_group_names_from_refs(refs)

    # 自底向上：先 psd_5，最后 psd_1
    ordered = list(reversed(list(zip(slots, group_names))))

    all_layers: list[dict] = []
    for group_index, ((ref, ox, oy, slot_scale, rotation), group_name) in enumerate(
        ordered
    ):
        psd = psd_io.resolve_psd_image(ref)
        pw, ph = psd.size
        sc = float(slot_scale) if slot_scale > 0 else 1.0
        base_x, base_y = slot_placement_on_canvas(pw, ph, W, H, sc, ox, oy)
        group_layers = psd_io.collect_psd_layers_for_merge(
            psd,
            offset_x=base_x,
            offset_y=base_y,
            group_name=group_name,
            group_index=group_index,
            include_hidden=include_hidden,
            scale=sc,
        )
        rcx = W / 2 + int(ox)
        rcy = H / 2 + int(oy)
        psd_io.rotate_layer_entries(group_layers, rcx, rcy, rotation)
        all_layers.extend(group_layers)

    if not all_layers:
        raise ValueError("所选 PSD 中未找到可栅格化的图层")

    return psd_io.build_psd_hierarchical(all_layers, W, H)
