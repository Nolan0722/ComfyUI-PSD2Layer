"""Merge PSD Files / Merge Layer Images 合成逻辑。

每个输入按槽位序号合成：序号小的在上层，大的在下层。输入居中放置到画布。
画布尺寸：宽/高 <=0 时取所有输入对应维的最大值，否则用设定值。
"""
from __future__ import annotations

from PIL import Image
from psd_tools import PSDImage

from . import psd_io

DEFAULT_MERGE_CANVAS_W = 3000
DEFAULT_MERGE_CANVAS_H = 6000


def compute_merge_canvas(
    sizes: list[tuple[int, int]],
    user_w: int,
    user_h: int,
) -> tuple[int, int]:
    """合并画布尺寸：某维 <=0 时取所有输入该维最大值，否则用设定值。

    无任何输入尺寸时回退默认 3000×6000。
    """
    max_w = max((w for w, _h in sizes), default=0)
    max_h = max((h for _w, h in sizes), default=0)
    W = int(user_w) if user_w and user_w > 0 else max(1, max_w)
    H = int(user_h) if user_h and user_h > 0 else max(1, max_h)
    if W <= 0:
        W = DEFAULT_MERGE_CANVAS_W
    if H <= 0:
        H = DEFAULT_MERGE_CANVAS_H
    return W, H


def compose_merged_psd(
    slots: list[tuple[dict, str]],
    *,
    include_hidden: bool = True,
    canvas_width: int = 0,
    canvas_height: int = 0,
) -> PSDImage:
    """按 PSD 引用合成 PSD。

    slots: (psd_ref, group_name) 列表，group_name 为该源根组名（用户可自定义）。
    每个源居中放置到画布；组内保留源 PSD 的完整嵌套组结构与原始命名。
    叠放顺序：序号最大的最底，psd_1 最顶（后写入的在上层）。
    """
    if not slots:
        raise ValueError("未提供任何 PSD 输入")

    psd_images = [psd_io.resolve_psd_image(ref) for ref, _name in slots]
    names = [str(name) for _ref, name in slots]
    W, H = compute_merge_canvas(
        [(psd.width, psd.height) for psd in psd_images],
        canvas_width,
        canvas_height,
    )

    # 自底向上：先序号最大，最后 psd_1
    ordered = list(reversed(list(zip(psd_images, names))))

    all_layers: list[dict] = []
    for group_index, (psd, group_name) in enumerate(ordered):
        pw, ph = psd.size
        cx = (W - pw) // 2
        cy = (H - ph) // 2
        group_layers = psd_io.collect_psd_layers_for_merge(
            psd,
            offset_x=cx,
            offset_y=cy,
            group_name=group_name,
            group_index=group_index,
            include_hidden=include_hidden,
        )
        all_layers.extend(group_layers)

    if not all_layers:
        raise ValueError("所选 PSD 中未找到可栅格化的图层")

    return psd_io.build_psd_hierarchical(all_layers, W, H)


def compose_merged_images(
    slots: list[tuple[Image.Image, str]],
    *,
    canvas_width: int = 0,
    canvas_height: int = 0,
) -> PSDImage:
    """将多张图像合成 PSD。

    每张图居中放置，作为根组内单层。叠放顺序：编号最大的最底，image_1 最顶。
    画布尺寸：宽/高 <=0 时取所有输入对应维最大值，否则用设定值。
    """
    if not slots:
        raise ValueError("未提供任何图像输入")

    pils = []
    for pil, _name in slots:
        if pil.mode != "RGBA":
            pil = pil.convert("RGBA")
        pils.append(pil)

    W, H = compute_merge_canvas(
        [pil.size for pil in pils], canvas_width, canvas_height
    )

    names = [str(name) for _pil, name in slots]
    ordered = list(reversed(list(zip(pils, names))))

    all_layers: list[dict] = []
    for group_index, (pil, group_name) in enumerate(ordered):
        w, h = pil.size
        all_layers.append(
            {
                "image": pil,
                "left": (W - w) // 2,
                "top": (H - h) // 2,
                "opacity": 255,
                "blend_mode": "NORMAL",
                "name": group_name,
                "visible": True,
                "group_meta": [psd_io.make_root_group_meta(group_name)],
                "group_indices": [int(group_index)],
            }
        )

    return psd_io.build_psd_hierarchical(all_layers, W, H)
