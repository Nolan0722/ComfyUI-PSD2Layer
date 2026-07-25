"""节点：Layers to PSD — 按 layer_info 将图层归位并输出 PSD。

输入可为放大后的图层：按相对 layer_info 的缩放比同比例调整位置与画布尺寸。
"""
from __future__ import annotations

from ..utils import layer_info as li
from ..utils import psd_io
from ..utils.merge_preview import save_node_flat_preview_ui


def _as_list(x):
    if isinstance(x, list) and len(x) == 1 and isinstance(x[0], list):
        return x[0]
    return x if isinstance(x, list) else [x]


def _scalar(x, default=0):
    if isinstance(x, list):
        return x[0] if x else default
    return x if x is not None else default


class LayersToPSD:
    """按 layer_info 归位写入 PSD；放大图层时同步缩放位置与画布。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "layer_info": (li.LAYER_INFO_TYPE, {"forceInput": True}),
                "canvas_width": (
                    "INT",
                    {"default": 0, "min": 0, "max": 65536, "step": 1},
                ),
                "canvas_height": (
                    "INT",
                    {"default": 0, "min": 0, "max": 65536, "step": 1},
                ),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = (psd_io.PSD_TYPE, "IMAGE")
    RETURN_NAMES = ("psd", "flat_preview")
    FUNCTION = "rebuild"
    INPUT_IS_LIST = True
    CATEGORY = "PSD2Layer"

    def rebuild(self, images, layer_info, canvas_width, canvas_height, unique_id=None):
        imgs = _as_list(images)
        infos = _as_list(layer_info)

        if not imgs:
            raise ValueError("未提供任何图层图像")
        if not infos:
            raise ValueError("未提供 layer_info，请从 Load PSD Layers 旁路接入")
        if len(imgs) != len(infos):
            raise ValueError(
                f"图像数量({len(imgs)})与 layer_info 数量({len(infos)})不一致，需一一对应"
            )

        c0 = infos[0]
        user_cw = int(_scalar(canvas_width, 0))
        user_ch = int(_scalar(canvas_height, 0))
        base_cw = max(1, int(c0["canvas_w"]))
        base_ch = max(1, int(c0["canvas_h"]))

        placements: list[tuple] = []
        max_sx = 1.0
        max_sy = 1.0

        for img, info in zip(imgs, infos):
            pil = psd_io.tensor_to_pil_rgba(psd_io._drop_batch(img))
            left, top, sx, sy = psd_io.scaled_layer_placement(pil, info)
            max_sx = max(max_sx, sx)
            max_sy = max(max_sy, sy)
            placements.append((pil, info, left, top))

        canvas_placements = [(pil, left, top) for pil, _, left, top in placements]
        W, H = psd_io.compute_rebuild_canvas_size(
            canvas_placements,
            base_cw,
            base_ch,
            max_sx,
            max_sy,
            user_canvas_w=user_cw,
            user_canvas_h=user_ch,
        )

        layers = []
        for pil, info, left, top in placements:
            layers.append(
                {
                    "image": pil,
                    "left": left,
                    "top": top,
                    "opacity": info["opacity"],
                    "blend_mode": info["blend_mode"],
                    "name": info["name"],
                    "visible": info["visible"],
                    "group_meta": info.get("group_meta"),
                    "group_indices": info.get("group_indices"),
                }
            )

        psd = psd_io.build_psd_hierarchical(layers, W, H)
        flat = psd_io.flatten_layers_on_canvas(layers, W, H)
        ui_img = save_node_flat_preview_ui(_scalar(unique_id, None), flat)
        preview = psd_io.pil_rgba_to_tensor(flat)
        result = (psd_io.make_psd_data_ref(psd), preview)
        if ui_img:
            return {"ui": {"images": [ui_img]}, "result": result}
        return result
