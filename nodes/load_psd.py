"""节点1：PSDLayerExtractor — 读取 PSD，按图层拆分为图像管线 + LAYER_INFO 旁路。

输出 N 个独立 IMAGE（不同尺寸可逐张流过下游任意插件）+ 一一对应的 LAYER_INFO
（承载每层位置/尺寸/属性，绕过用户的处理黑盒）。
"""
from __future__ import annotations

import os

import torch
from psd_tools import PSDImage

from ..utils import layer_info, psd_io


class PSDLayerExtractor:
    """读取 PSD 文件，把每个图层作为图像输出，并旁路图层元数据。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "psd_file": ("STRING", {"default": "", "multiline": False}),
                "include_hidden": ("BOOLEAN", {"default": False}),
                "flatten_groups": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", layer_info.LAYER_INFO_TYPE)
    RETURN_NAMES = ("layer_image", "layer_info")
    FUNCTION = "extract"
    OUTPUT_IS_LIST = (True, True)
    CATEGORY = "PSD2Layer"

    def extract(self, psd_file, include_hidden=False, flatten_groups=True):
        psd_file = self._resolve_path(psd_file)
        psd = PSDImage.open(psd_file)
        canvas_w, canvas_h = psd.width, psd.height

        # 收集 (layer, pil_rgba)，顺序 bottom→top
        collected: list = []
        for layer in psd:
            self._walk(layer, collected, include_hidden, flatten_groups)

        if not collected:
            # PSD 无可栅格化图层时，输出一个 1x1 透明占位，避免空 list 报错
            empty = torch.zeros(1, 1, 4, dtype=torch.float32)
            empty_info = layer_info.make_layer_info(
                left=0, top=0, width=1, height=1, opacity=255,
                blend_mode="NORMAL", name="empty", visible=True,
                alpha=None, canvas_w=canvas_w, canvas_h=canvas_h,
            )
            return ([empty], [empty_info])

        images, infos = [], []
        for layer, pil in collected:
            tensor = psd_io.pil_rgba_to_tensor(pil)  # [H,W,4]
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
                    alpha=psd_io.tensor_to_alpha(tensor),
                    canvas_w=canvas_w,
                    canvas_h=canvas_h,
                )
            )
        return (images, infos)

    @staticmethod
    def _resolve_path(psd_file: str) -> str:
        if psd_file and os.path.isfile(psd_file):
            return os.path.abspath(psd_file)
        # 尝试相对 ComfyUI input 目录
        try:
            from folder_paths import get_input_directory

            cand = os.path.join(get_input_directory(), psd_file)
            if os.path.isfile(cand):
                return os.path.abspath(cand)
        except Exception:
            pass
        raise FileNotFoundError(f"PSD file not found: {psd_file!r}")

    @staticmethod
    def _walk(layer, out, include_hidden, flatten_groups):
        """递归收集图层。组图层按 flatten_groups 决定合成或展平。"""
        if not layer.visible and not include_hidden:
            return
        if layer.is_group():
            if flatten_groups:
                # 组作为单张合成图（含子层视觉效果）
                pil = layer.composite()
                if pil is not None:
                    out.append((layer, pil))
            else:
                # 展平：组内每个子层独立输出
                for child in layer:
                    PSDLayerExtractor._walk(child, out, include_hidden, flatten_groups)
        else:
            # 像素 / 文字 / 形状 / 智能对象等：栅格化为 RGBA
            pil = layer.composite()
            if pil is not None:
                out.append((layer, pil))
