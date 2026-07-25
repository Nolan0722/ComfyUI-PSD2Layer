"""节点1：PSDLayerExtractor — 读取 PSD，按图层拆分为图像管线 + LAYER_INFO 旁路。

输出 N 个独立 IMAGE（不同尺寸可逐张流过下游任意插件）+ 一一对应的 LAYER_INFO
（承载每层位置/尺寸/属性及组层级，绕过用户的处理黑盒）。
"""
from __future__ import annotations

import torch

from ..utils import layer_info, psd_io


class PSDLayerExtractor:
    """读取 PSD，把每个图层作为图像输出，并旁路图层元数据。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "psd": (psd_io.PSD_TYPE, {"forceInput": True}),
                "include_hidden": ("BOOLEAN", {"default": True}),
                "background": (list(psd_io.BACKGROUND_CHOICES), {"default": "none"}),
            }
        }

    RETURN_TYPES = ("IMAGE", layer_info.LAYER_INFO_TYPE)
    RETURN_NAMES = ("layer_image", "layer_info")
    FUNCTION = "extract"
    OUTPUT_IS_LIST = (True, True)
    CATEGORY = "PSD2Layer"

    def extract(self, psd, include_hidden=True, background="none"):
        psd = psd_io.resolve_psd_image(psd)
        canvas_w, canvas_h = psd.width, psd.height

        collected: list = []
        for layer in psd:
            self._walk(layer, psd, collected, include_hidden, [], [])

        if not collected:
            ch = 4 if psd_io.background_rgb(background) is None else 3
            empty = torch.zeros(1, 1, 1, ch, dtype=torch.float32)
            empty_info = layer_info.make_layer_info(
                left=0, top=0, width=1, height=1, opacity=255,
                blend_mode="NORMAL", name="empty", visible=True,
                alpha=None, canvas_w=canvas_w, canvas_h=canvas_h,
            )
            return ([empty], [empty_info])

        images, infos = [], []
        for layer, pil, group_chain, index_chain in collected:
            tensor_rgba = psd_io.pil_rgba_to_tensor(pil)
            alpha = psd_io.tensor_to_alpha(tensor_rgba)
            tensor = psd_io.apply_background(tensor_rgba, background)
            group_meta = [
                {
                    "name": g.name,
                    "visible": g.visible,
                    "opacity": g.opacity,
                    "blend_mode": psd_io.blend_mode_to_str(g.blend_mode),
                    "open_folder": g.open_folder,
                }
                for g in group_chain
            ]
            images.append(tensor)
            infos.append(
                layer_info.make_layer_info(
                    left=layer.left,
                    top=layer.top,
                    width=layer.width,
                    height=layer.height,
                    opacity=layer.opacity,
                    blend_mode=psd_io.blend_mode_to_str(layer.blend_mode),
                    name=layer.name,
                    visible=layer.visible,
                    alpha=alpha,
                    canvas_w=canvas_w,
                    canvas_h=canvas_h,
                    group_path=[m["name"] for m in group_meta],
                    group_meta=group_meta,
                    group_indices=list(index_chain),
                )
            )
        return (images, infos)

    @staticmethod
    def _walk(layer, parent, out, include_hidden, group_chain, index_chain):
        """递归收集像素图层；组仅记录层级，不合成输出。"""
        if not include_hidden:
            if hasattr(layer, "is_visible") and not layer.is_visible():
                return
            if not getattr(layer, "visible", True):
                return
        if layer.is_group():
            my_index = _sibling_index(layer, parent)
            for child in layer:
                PSDLayerExtractor._walk(
                    child,
                    layer,
                    out,
                    include_hidden,
                    group_chain + [layer],
                    index_chain + [my_index],
                )
        else:
            pil = psd_io.rasterize_layer(layer, include_hidden=include_hidden)
            if pil is not None:
                out.append((layer, pil, group_chain, index_chain))


def _sibling_index(layer, parent) -> int:
    for i, sibling in enumerate(parent):
        if sibling is layer:
            return i
    return 0
