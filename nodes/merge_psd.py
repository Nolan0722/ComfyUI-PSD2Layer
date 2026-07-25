"""节点3：PSDMerger — 多个 PSD 文件合并到一个统一画布的 PSD。

各 PSD 的顶层图层按各自原始 xy 偏移贴到统一画布；按输入顺序叠加
（首个 PSD 在最底）。组图层按整体合成处理。
"""
from __future__ import annotations

import os
import time

from psd_tools import PSDImage

from ..utils import psd_io


class PSDMerger:
    """把多个 PSD 文件合并到统一画布的单一 PSD。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "psd_files": ("STRING", {"default": "", "multiline": True}),
                "canvas_width": (
                    "INT",
                    {"default": 0, "min": 0, "max": 65536, "step": 1},
                ),
                "canvas_height": (
                    "INT",
                    {"default": 0, "min": 0, "max": 65536, "step": 1},
                ),
                "filename_prefix": ("STRING", {"default": "PSD2Layer_merged"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("psd_path",)
    FUNCTION = "merge"
    CATEGORY = "PSD2Layer"

    def merge(self, psd_files, canvas_width, canvas_height, filename_prefix):
        paths = [p.strip() for p in str(psd_files).splitlines() if p.strip()]
        if not paths:
            raise ValueError("未提供任何 PSD 文件路径（每行一个）")
        paths = [self._resolve(p) for p in paths]
        psds = [PSDImage.open(p) for p in paths]

        # 画布：用户指定优先；否则扫描所有图层 bbox 取最大外包
        if canvas_width and canvas_height:
            W, H = int(canvas_width), int(canvas_height)
        else:
            max_r, max_b = 0, 0
            for psd in psds:
                for layer in psd:
                    if not layer.visible:
                        continue
                    max_r = max(max_r, layer.right)
                    max_b = max(max_b, layer.bottom)
            W = int(canvas_width) if canvas_width else max(1, max_r)
            H = int(canvas_height) if canvas_height else max(1, max_b)

        # 收集图层：每个 PSD 顶层（bottom→top），组按整体合成
        layers = []
        for psd in psds:
            for layer in psd:
                if not layer.visible:
                    continue
                pil = psd_io.rasterize_layer(layer)
                if pil is None:
                    continue
                layers.append(
                    {
                        "image": pil,
                        "left": layer.left,
                        "top": layer.top,
                        "opacity": layer.opacity,
                        "blend_mode": psd_io.blend_mode_to_str(layer.blend_mode),
                        "name": layer.name,
                        "visible": layer.visible,
                    }
                )

        psd = psd_io.build_psd(layers, W, H)
        path = self._output_path(str(filename_prefix))
        psd_io.save_psd(psd, path)
        return (path,)

    @staticmethod
    def _resolve(psd_file: str) -> str:
        psd_file = str(psd_file).strip().strip('"').strip("'")
        if psd_file and os.path.isfile(psd_file):
            return os.path.abspath(psd_file)
        try:
            from folder_paths import get_input_directory

            cand = os.path.join(get_input_directory(), psd_file)
            if os.path.isfile(cand):
                return os.path.abspath(cand)
        except Exception:
            pass
        raise FileNotFoundError(f"PSD file not found: {psd_file!r}")

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
