"""节点：Merge Layer Images — 将处理后的 RGB 与旁路 alpha 按索引匹配合并。

按每张图处理后尺寸 vs layer_info 原始 width/height 缩放 alpha，再可选叠背景输出。
"""
from __future__ import annotations

import torch

from ..utils import layer_info as li
from ..utils import psd_io


def _as_list(x):
    if isinstance(x, list) and len(x) == 1 and isinstance(x[0], list):
        return x[0]
    return x if isinstance(x, list) else [x]
        

def _scalar(x):
    return x[0] if isinstance(x, list) and x else x


class PSDLayerImageJoiner:
    """自动匹配 images 与 layer_info，合并 alpha 并输出 layer_image 列表。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "layer_info": (li.LAYER_INFO_TYPE, {"forceInput": True}),
                "background": (list(psd_io.BACKGROUND_CHOICES), {"default": "none"}),
                "restore_original_scale": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("layer_image",)
    FUNCTION = "join"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    CATEGORY = "PSD2Layer"

    def join(self, images, layer_info, background, restore_original_scale):
        imgs = _as_list(images)
        infos = _as_list(layer_info)
        background = _scalar(background)
        restore_original_scale = _scalar(restore_original_scale)

        if len(imgs) != len(infos):
            raise ValueError(
                f"图像数量({len(imgs)})与图层元数据数量({len(infos)})不一致，需按索引一一对应"
            )

        out = []
        for img, info in zip(imgs, infos):
            t = psd_io._drop_batch(img)
            th, tw = t.shape[0], t.shape[1]

            if t.shape[-1] >= 3:
                rgb = t[..., :3]
            else:
                rgb = t.unsqueeze(-1).expand(th, tw, 3)

            ow, oh = int(info.get("width", 0)), int(info.get("height", 0))
            if restore_original_scale and ow > 0 and oh > 0:
                # 图像缩回原始图层尺寸，蒙版保持原比例（不放大到超分尺寸）
                rgb = psd_io.resize_image_rgb(rgb, oh, ow)
                if info.get("alpha") is not None:
                    alpha = psd_io.resize_alpha(info["alpha"], oh, ow)
                elif t.shape[-1] == 4:
                    alpha = psd_io.resize_alpha(t[..., 3], oh, ow)
                else:
                    alpha = torch.ones(oh, ow, dtype=t.dtype)
            else:
                # 默认：蒙版缩放到处理后图像尺寸
                if info.get("alpha") is not None:
                    alpha = psd_io.resize_alpha(info["alpha"], th, tw)
                elif t.shape[-1] == 4:
                    alpha = t[..., 3]
                else:
                    alpha = torch.ones(th, tw, dtype=t.dtype)

            rgba = torch.cat([rgb, alpha.unsqueeze(-1)], dim=-1)
            out.append(psd_io.apply_background(rgba.unsqueeze(0), background))

        return (out,)
