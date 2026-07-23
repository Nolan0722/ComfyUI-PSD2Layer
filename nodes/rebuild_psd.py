"""节点2：PSDRebuilder — 把处理后的图层图像按原始位置/顺序还原成分层 PSD。

同时接收「处理后的 IMAGE 列表」与「旁路的 LAYER_INFO 列表」，按索引一一对应，
按原始 xy 偏移（可选自动缩放）把每张图贴回画布，输出 PSD。
"""
from __future__ import annotations

import os
import time

import numpy as np
import torch
from PIL import Image

from ..utils import layer_info, psd_io


def _as_list(x):
    """INPUT_IS_LIST 下输入应为 list；兼容被包成 [[...]] 的情况。"""
    if isinstance(x, list) and len(x) == 1 and isinstance(x[0], list):
        return x[0]
    return x if isinstance(x, list) else [x]


def _scalar(x):
    """widget 标量在 INPUT_IS_LIST 下可能被广播成 list，取单值。"""
    return x[0] if isinstance(x, list) and x else x


def _resize_alpha(alpha_tensor: torch.Tensor, target_h: int, target_w: int) -> torch.Tensor:
    """把原始 alpha 缩放到处理后图像的目标尺寸（alpha_source='original' 时用）。"""
    a = psd_io._drop_batch(alpha_tensor)
    if a.shape[0] == target_h and a.shape[1] == target_w:
        return a
    pil = Image.fromarray(
        np.clip(a.numpy() * 255.0, 0, 255).astype(np.uint8), mode="L"
    )
    pil = pil.resize((target_w, target_h), Image.LANCZOS)
    return torch.from_numpy(np.asarray(pil, dtype=np.float32) / 255.0)


class PSDRebuilder:
    """把处理后的图层图像按原始位置/顺序还原成分层 PSD。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "layer_info": (layer_info.LAYER_INFO_TYPE, {"forceInput": True}),
                "canvas_width": (
                    "INT",
                    {"default": 0, "min": 0, "max": 65536, "step": 1},
                ),
                "canvas_height": (
                    "INT",
                    {"default": 0, "min": 0, "max": 65536, "step": 1},
                ),
                "scale": (
                    "FLOAT",
                    {"default": 0.0, "min": 0.0, "max": 100.0, "step": 0.01},
                ),
                "alpha_source": (["original", "processed"],),
                "filename_prefix": ("STRING", {"default": "PSD2Layer"}),
            }
        }

    RETURN_TYPES = ("STRING", "IMAGE")
    RETURN_NAMES = ("psd_path", "flat_preview")
    FUNCTION = "rebuild"
    INPUT_IS_LIST = True
    CATEGORY = "PSD2Layer"

    def rebuild(
        self,
        images,
        layer_info,
        canvas_width,
        canvas_height,
        scale,
        alpha_source,
        filename_prefix,
    ):
        imgs = _as_list(images)
        infos = _as_list(layer_info)
        canvas_width = _scalar(canvas_width)
        canvas_height = _scalar(canvas_height)
        scale = _scalar(scale)
        alpha_source = _scalar(alpha_source)
        filename_prefix = _scalar(filename_prefix)

        if len(imgs) != len(infos):
            raise ValueError(
                f"图像数量({len(imgs)})与图层数量({len(infos)})不一致，需一一对应"
            )

        # 缩放系数：scale>0 用手动值，否则按首图比例自动推算
        if scale and float(scale) > 0:
            sx = sy = float(scale)
        else:
            sx, sy = layer_info.estimate_scale(imgs, infos)

        # 画布：用户指定优先；否则按原画布 × 缩放自动跟随
        c0 = infos[0]
        W = int(canvas_width) if canvas_width else max(1, round(c0["canvas_w"] * sx))
        H = int(canvas_height) if canvas_height else max(1, round(c0["canvas_h"] * sy))

        layers = []
        for img, info in zip(imgs, infos):
            t = psd_io._drop_batch(img)  # [H,W,C]
            th, tw = t.shape[0], t.shape[1]

            # alpha 来源：original=用旁路原始 alpha（缩放到当前尺寸），processed=用图像自带
            if alpha_source == "original" and info.get("alpha") is not None:
                alpha = _resize_alpha(info["alpha"], th, tw)
                t = torch.cat([t[..., :3], alpha.unsqueeze(-1)], dim=-1)
            elif t.shape[-1] == 3:
                t = torch.cat(
                    [t, torch.ones(th, tw, 1, dtype=t.dtype)], dim=-1
                )

            layers.append(
                {
                    "image": psd_io.tensor_to_pil_rgba(t),
                    "left": round(info["left"] * sx),
                    "top": round(info["top"] * sy),
                    "opacity": info["opacity"],
                    "blend_mode": info["blend_mode"],
                    "name": info["name"],
                    "visible": info["visible"],
                }
            )

        psd = psd_io.build_psd(layers, W, H)
        path = self._output_path(str(filename_prefix))
        psd_io.save_psd(psd, path)
        preview = psd_io.psd_to_flat_tensor(psd)
        return (path, preview)

    @staticmethod
    def _output_path(prefix: str) -> str:
        try:
            from folder_paths import get_output_directory

            out_dir = get_output_directory()
        except Exception:
            out_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output"
            )
        sub = os.path.join(out_dir, "PSD2Layer")
        os.makedirs(sub, exist_ok=True)
        fname = f"{prefix}_{int(time.time() * 1000)}.psd"
        return os.path.join(sub, fname)
