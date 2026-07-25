"""PSD 读写与张量/PIL 转换封装。

主用 psd_tools（create_pixel_layer 的 top/left 直接支持偏移定位）。
若未来需更高兼容性，可在 build_psd 内切换到 pytoshop 实现，节点接口不变。
"""
from __future__ import annotations

import math
import os

import numpy as np
import torch
from PIL import Image

from psd_tools import PSDImage
from psd_tools.api.layers import Group, PixelLayer
from psd_tools.constants import BlendMode, ChannelID

# ComfyUI 自定义类型：已解析的 PSD 文件引用（节点间传递）
PSD_TYPE = "PSD"


def make_psd_ref(path: str) -> dict:
    """构造 PSD 引用对象（供 Load PSD File → 下游节点）。"""
    return {"path": os.path.abspath(path)}


def make_psd_data_ref(psd: PSDImage) -> dict:
    """构造内存 PSD 引用（Rebuild / Merge 输出 → Save PSD File）。"""
    return {"psd": psd}


def resolve_psd_ref(ref) -> str:
    """从 PSD 引用对象取绝对路径（仅文件引用）。"""
    if isinstance(ref, dict) and ref.get("path"):
        path = os.path.abspath(str(ref["path"]))
        if os.path.isfile(path):
            return path
        raise FileNotFoundError(f"PSD file not found: {path!r}")
    raise TypeError(f"Invalid PSD file reference: {ref!r}")


def resolve_psd_image(ref) -> PSDImage:
    """从 PSD 引用取 PSDImage（内存引用或按路径打开）。"""
    if not isinstance(ref, dict):
        raise TypeError(f"Invalid PSD reference: {ref!r}")
    if ref.get("psd") is not None:
        return ref["psd"]
    if ref.get("path"):
        return PSDImage.open(resolve_psd_ref(ref))
    raise TypeError(f"Invalid PSD reference: {ref!r}")


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


def pil_rgba_to_tensor(pil: Image.Image, batch: bool = True) -> torch.Tensor:
    """PIL（任意模式）→ ComfyUI IMAGE 张量。

    默认返回 [1,H,W,4] float 0-1（ComfyUI IMAGE 约定带 batch 维）。
    batch=False 时返回 [H,W,4]。
    """
    if pil.mode != "RGBA":
        pil = pil.convert("RGBA")
    arr = np.asarray(pil, dtype=np.float32) / 255.0
    t = torch.from_numpy(arr)
    return t.unsqueeze(0) if batch else t


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


BACKGROUND_CHOICES = ("none", "black", "white", "gray")


def background_rgb(name: str) -> tuple[float, float, float] | None:
    """背景选项 → RGB 0-1；none 表示保留透明通道。"""
    key = str(name).lower().strip()
    if key in ("none", "transparent", ""):
        return None
    if key == "black":
        return (0.0, 0.0, 0.0)
    if key == "white":
        return (1.0, 1.0, 1.0)
    if key == "gray":
        return (0.5, 0.5, 0.5)
    return None


def resize_alpha(
    alpha_tensor: torch.Tensor, target_h: int, target_w: int
) -> torch.Tensor:
    """将 alpha [H,W] 缩放到目标尺寸（LANCZOS）。"""
    a = _drop_batch(alpha_tensor)
    if a.ndim == 3:
        a = a[..., 0]
    if a.shape[0] == target_h and a.shape[1] == target_w:
        return a
    pil = Image.fromarray(
        np.clip(a.numpy() * 255.0, 0, 255).astype(np.uint8), mode="L"
    )
    pil = pil.resize((target_w, target_h), Image.LANCZOS)
    return torch.from_numpy(np.asarray(pil, dtype=np.float32) / 255.0)


def resize_image_rgb(
    rgb_tensor: torch.Tensor, target_h: int, target_w: int
) -> torch.Tensor:
    """将 RGB [H,W,3] 缩放到目标尺寸（LANCZOS）。"""
    t = _drop_batch(rgb_tensor)
    rgb = t[..., :3]
    if rgb.shape[0] == target_h and rgb.shape[1] == target_w:
        return rgb
    arr = np.clip(rgb.numpy() * 255.0, 0, 255).astype(np.uint8)
    pil = Image.fromarray(arr, mode="RGB")
    pil = pil.resize((target_w, target_h), Image.LANCZOS)
    return torch.from_numpy(np.asarray(pil, dtype=np.float32) / 255.0)


def apply_background(t: torch.Tensor, background: str) -> torch.Tensor:
    """按背景选项输出 IMAGE 张量。

    none → RGBA [1,H,W,4]（保留透明）
    black/white/gray → 叠到纯色底后输出 RGB [1,H,W,3]
    """
    hwc = _drop_batch(t)
    channels = hwc.shape[-1]
    if channels == 3:
        rgb = hwc[..., :3]
        alpha = torch.ones(hwc.shape[0], hwc.shape[1], 1, dtype=hwc.dtype)
    else:
        rgb = hwc[..., :3]
        alpha = hwc[..., 3:4]

    bg = background_rgb(background)
    if bg is None:
        out = torch.cat([rgb, alpha], dim=-1)
    else:
        bg_t = torch.tensor(bg, dtype=rgb.dtype)
        out = rgb * alpha + bg_t * (1.0 - alpha)

    return out.unsqueeze(0)


# ---------------------------------------------------------------------------
# PSD 写入
# ---------------------------------------------------------------------------
def _apply_layer_transparency(layer: PixelLayer, alpha: Image.Image) -> None:
    """将 alpha 写入图层透明度通道（-1），而非用户图层蒙版。"""
    if alpha.mode != "L":
        alpha = alpha.convert("L")
    w, h = alpha.size
    version = layer._psd._record.header.version
    depth = layer._psd._record.header.depth
    data = alpha.tobytes()
    for i, ci in enumerate(layer._record.channel_info):
        if ci.id == ChannelID.TRANSPARENCY_MASK:
            layer._channels[i].set_data(data, w, h, depth, version)
            return


def _strip_user_layer_mask(layer: PixelLayer) -> None:
    """移除用户图层蒙版（USER_LAYER_MASK），保留透明度通道。"""
    if layer.has_mask():
        layer.remove_mask()


def add_pixel_layer(
    parent,
    pil: Image.Image,
    *,
    top: int = 0,
    left: int = 0,
    opacity: int = 255,
    blend_mode: str | BlendMode = "NORMAL",
    name: str = "Layer",
    visible: bool = True,
) -> PixelLayer:
    """添加像素图层：RGB 像素 + 透明度通道存 alpha，不创建用户图层蒙版。"""
    if pil.mode != "RGBA":
        pil = pil.convert("RGBA")
    rgb = pil.convert("RGB")
    alpha = pil.getchannel("A")
    blend = parse_blend_mode(blend_mode)

    if isinstance(parent, PSDImage):
        layer = parent.create_pixel_layer(
            rgb,
            name="Layer",
            top=int(top),
            left=int(left),
            opacity=int(opacity),
            blend_mode=blend,
        )
    else:
        layer = PixelLayer.frompil(
            rgb,
            parent=parent,
            name="Layer",
            top=int(top),
            left=int(left),
        )
        layer.opacity = int(opacity)
        layer.blend_mode = blend

    _apply_layer_transparency(layer, alpha)
    _strip_user_layer_mask(layer)
    layer.name = str(name)
    layer.visible = bool(visible)
    return layer


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
        add_pixel_layer(
            psd,
            L["image"],
            top=int(L.get("top", 0)),
            left=int(L.get("left", 0)),
            opacity=int(L.get("opacity", 255)),
            blend_mode=L.get("blend_mode", "NORMAL"),
            name=str(L.get("name", "Layer")),
            visible=bool(L.get("visible", True)),
        )
    return psd


def build_psd_hierarchical(layers: list[dict], canvas_w: int, canvas_h: int) -> PSDImage:
    """按 group_meta / group_indices 重建嵌套组结构并写入像素图层。"""
    psd = PSDImage.new(
        mode="RGBA", size=(int(canvas_w), int(canvas_h)), depth=8, color=0
    )
    group_cache: dict[tuple, Group] = {}

    for L in layers:
        group_meta = L.get("group_meta") or []
        group_indices = L.get("group_indices") or []
        parent = psd

        for depth, meta in enumerate(group_meta):
            key = tuple(group_indices[: depth + 1])
            if key not in group_cache:
                if parent is psd:
                    g = psd.create_group(
                        name="Group",
                        opacity=int(meta.get("opacity", 255)),
                        blend_mode=parse_blend_mode(
                            meta.get("blend_mode", "PASS_THROUGH")
                        ),
                        open_folder=bool(meta.get("open_folder", True)),
                    )
                else:
                    g = Group.new(
                        parent=parent,
                        name="Group",
                        open_folder=bool(meta.get("open_folder", True)),
                    )
                    g.opacity = int(meta.get("opacity", 255))
                    g.blend_mode = parse_blend_mode(
                        meta.get("blend_mode", "PASS_THROUGH")
                    )
                g.name = str(meta.get("name", "Group"))
                g.visible = bool(meta.get("visible", True))
                group_cache[key] = g
            parent = group_cache[key]

        blend = parse_blend_mode(L.get("blend_mode", "NORMAL"))
        raw_name = str(L.get("name", "Layer"))
        pil = L["image"]
        add_pixel_layer(
            parent,
            pil,
            top=int(L.get("top", 0)),
            left=int(L.get("left", 0)),
            opacity=int(L.get("opacity", 255)),
            blend_mode=blend,
            name=raw_name,
            visible=bool(L.get("visible", True)),
        )

    return psd


def _force_visible_chain(layer) -> list[tuple]:
    """临时将图层及其祖先组设为 visible，返回需恢复的 (layer, was_visible) 列表。"""
    restore: list[tuple] = []
    cur = layer
    while cur is not None and hasattr(cur, "visible"):
        was = cur.visible
        if not was:
            cur.visible = True
            restore.append((cur, was))
        cur = getattr(cur, "parent", None)
    return restore


def rasterize_layer(layer, include_hidden: bool = False) -> Image.Image | None:
    """将 psd_tools 图层栅格化为 PIL RGBA。

    include_hidden=True 时强制祖先组可见，并用 layer_filter 绕过 is_visible 过滤。
    """
    if not include_hidden:
        if hasattr(layer, "is_visible") and not layer.is_visible():
            return None
        if not getattr(layer, "visible", True):
            return None

    restore_chain = _force_visible_chain(layer) if include_hidden else []
    pil = None
    try:
        if include_hidden:
            pil = layer.composite(layer_filter=lambda l: True, force=True)
        else:
            pil = layer.composite()
        if pil is None and hasattr(layer, "topil"):
            pil = layer.topil()
    finally:
        for cur, was in restore_chain:
            cur.visible = was

    if pil is None:
        return None
    if pil.mode != "RGBA":
        pil = pil.convert("RGBA")
    return pil


def make_root_group_meta(name: str) -> dict:
    """合并 PSD 时，为每个源文件创建的根组元数据。"""
    return {
        "name": str(name),
        "visible": True,
        "opacity": 255,
        "blend_mode": "PASS_THROUGH",
        "open_folder": True,
    }


def collect_psd_layers_for_merge(
    psd: PSDImage,
    *,
    offset_x: int = 0,
    offset_y: int = 0,
    group_name: str,
    group_index: int,
    include_hidden: bool = True,
    scale: float = 1.0,
) -> list[dict]:
    """递归收集 PSD 像素图层，包入指定根组并施加整体偏移与缩放。"""
    layers: list[dict] = []
    group_meta = [make_root_group_meta(group_name)]
    group_indices = [int(group_index)]
    ox, oy = int(offset_x), int(offset_y)
    sc = float(scale)
    if sc <= 0:
        sc = 1.0

    def walk(layer, parent):
        if not include_hidden:
            if hasattr(layer, "is_visible") and not layer.is_visible():
                return
            if not getattr(layer, "visible", True):
                return
        if layer.is_group():
            for child in layer:
                walk(child, layer)
        else:
            pil = rasterize_layer(layer, include_hidden=include_hidden)
            if pil is None:
                return
            left = int(layer.left)
            top = int(layer.top)
            if sc != 1.0:
                nw = max(1, int(round(pil.width * sc)))
                nh = max(1, int(round(pil.height * sc)))
                pil = pil.resize((nw, nh), Image.LANCZOS)
                left = int(round(left * sc))
                top = int(round(top * sc))
            layers.append(
                {
                    "image": pil,
                    "left": left + ox,
                    "top": top + oy,
                    "opacity": layer.opacity,
                    "blend_mode": blend_mode_to_str(layer.blend_mode),
                    "name": layer.name,
                    "visible": layer.visible,
                    "group_meta": group_meta,
                    "group_indices": group_indices,
                }
            )

    for layer in psd:
        walk(layer, psd)
    return layers


def rotate_layer_entries(
    layers: list[dict],
    rcx: float,
    rcy: float,
    angle_deg: float,
) -> None:
    """绕画布点 (rcx, rcy) 旋转已定位图层（用于 Merge 整文件旋转）。"""
    if not angle_deg:
        return
    angle = math.radians(float(angle_deg))
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    for L in layers:
        pil = L["image"]
        lw, lh = pil.size
        lc_x = L["left"] + lw / 2
        lc_y = L["top"] + lh / 2
        dx, dy = lc_x - rcx, lc_y - rcy
        new_cx = rcx + dx * cos_a - dy * sin_a
        new_cy = rcy + dx * sin_a + dy * cos_a
        pil = pil.rotate(-angle_deg, expand=True, resample=Image.LANCZOS)
        nlw, nlh = pil.size
        L["image"] = pil
        L["left"] = int(round(new_cx - nlw / 2))
        L["top"] = int(round(new_cy - nlh / 2))


def canvas_bbox_from_layers(layers: list[dict]) -> tuple[int, int]:
    """根据图层列表计算最小外包画布 (W, H)。"""
    max_r, max_b = 0, 0
    for L in layers:
        w, h = L["image"].size
        max_r = max(max_r, int(L["left"]) + w)
        max_b = max(max_b, int(L["top"]) + h)
    return max(1, max_r), max(1, max_b)


def flatten_psd_to_rgba(psd: PSDImage, include_hidden: bool = True) -> Image.Image:
    """将 PSD 所有像素图层压平到透明 RGBA（避免 composite() 白底）。"""
    canvas = Image.new("RGBA", psd.size, (0, 0, 0, 0))

    def walk(layer) -> None:
        if not include_hidden:
            if hasattr(layer, "is_visible") and not layer.is_visible():
                return
            if not getattr(layer, "visible", True):
                return
        if layer.is_group():
            for child in layer:
                walk(child)
        else:
            pil = rasterize_layer(layer, include_hidden=include_hidden)
            if pil is None:
                return
            tmp = Image.new("RGBA", psd.size, (0, 0, 0, 0))
            tmp.paste(pil, (int(layer.left), int(layer.top)), pil)
            canvas.alpha_composite(tmp)

    for layer in psd:
        walk(layer)
    return canvas


def resize_pil_rgba(pil: Image.Image, width: int, height: int) -> Image.Image:
    """RGBA PIL 缩放到目标尺寸。"""
    w, h = int(width), int(height)
    if pil.size == (w, h):
        return pil
    if pil.mode != "RGBA":
        pil = pil.convert("RGBA")
    return pil.resize((w, h), Image.LANCZOS)


def fit_layer_image_to_info(pil: Image.Image, info: dict) -> Image.Image:
    """将图层图像缩放到 layer_info 记录的原始宽高。"""
    ow = int(info.get("width", 0))
    oh = int(info.get("height", 0))
    if ow > 0 and oh > 0 and pil.size != (ow, oh):
        return resize_pil_rgba(pil, ow, oh)
    return pil


def layer_scale_factors(pil: Image.Image, info: dict) -> tuple[float, float]:
    """根据输入图像与 layer_info 原始尺寸计算缩放比。"""
    ow = int(info.get("width", 0))
    oh = int(info.get("height", 0))
    if ow > 0 and oh > 0:
        return pil.width / ow, pil.height / oh
    return 1.0, 1.0


def scaled_layer_placement(pil: Image.Image, info: dict) -> tuple[int, int, float, float]:
    """按缩放比计算放大后图层的 left/top（保持图像当前尺寸）。"""
    sx, sy = layer_scale_factors(pil, info)
    left = int(round(int(info["left"]) * sx))
    top = int(round(int(info["top"]) * sy))
    return left, top, sx, sy


def compute_rebuild_canvas_size(
    placements: list[tuple[Image.Image, int, int]],
    base_canvas_w: int,
    base_canvas_h: int,
    max_scale_x: float,
    max_scale_y: float,
    user_canvas_w: int = 0,
    user_canvas_h: int = 0,
) -> tuple[int, int]:
    """根据缩放比与图层外包框计算重建画布尺寸。"""
    if user_canvas_w > 0:
        w = user_canvas_w
    else:
        w = max(1, int(round(base_canvas_w * max_scale_x)))
    if user_canvas_h > 0:
        h = user_canvas_h
    else:
        h = max(1, int(round(base_canvas_h * max_scale_y)))
    for pil, left, top in placements:
        w = max(w, left + pil.width)
        h = max(h, top + pil.height)
    return w, h


def flatten_layers_on_canvas(
    layers: list[dict],
    canvas_w: int,
    canvas_h: int,
) -> Image.Image:
    """将图层列表压平到透明 RGBA 画布（与写入 PSD 的图像一致）。"""
    W, H = max(1, int(canvas_w)), max(1, int(canvas_h))
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for L in layers:
        if not bool(L.get("visible", True)):
            continue
        pil = L["image"]
        if pil.mode != "RGBA":
            pil = pil.convert("RGBA")
        tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        tmp.paste(pil, (int(L["left"]), int(L["top"])), pil)
        canvas.alpha_composite(tmp)
    return canvas


def psd_to_flat_tensor(psd: PSDImage) -> torch.Tensor:
    """整张 PSD 压平 → [1,H,W,4] 张量（透明底 RGBA）。"""
    pil = flatten_psd_to_rgba(psd, include_hidden=True)
    return pil_rgba_to_tensor(pil)


def save_psd(psd: PSDImage, path: str) -> str:
    """保存 PSD 到指定路径，自动创建目录。"""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    psd.save(path)
    return path


def resolve_psd_path(psd_file: str) -> str:
    """解析 PSD 输入路径：绝对路径，或相对 ComfyUI input 目录。"""
    psd_file = str(psd_file).strip().strip('"').strip("'")
    if not psd_file:
        raise FileNotFoundError("PSD path is empty")
    if os.path.isfile(psd_file):
        return os.path.abspath(psd_file)
    try:
        from folder_paths import get_input_directory

        cand = os.path.join(get_input_directory(), psd_file)
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    except Exception:
        pass
    raise FileNotFoundError(f"PSD file not found: {psd_file!r}")


def resolve_save_path(
    output_dir: str,
    filename: str,
    default_stem: str = "output",
) -> str:
    """解析保存路径：output_dir + filename，空目录时落到 ComfyUI output/PSD2Layer。"""
    import time

    output_dir = str(output_dir).strip().strip('"').strip("'")
    filename = str(filename).strip().strip('"').strip("'")

    if not filename:
        filename = f"{default_stem}_{int(time.time() * 1000)}.psd"
    elif not filename.lower().endswith(".psd"):
        filename += ".psd"

    if output_dir:
        if not os.path.isabs(output_dir):
            try:
                from folder_paths import get_output_directory

                output_dir = os.path.join(get_output_directory(), output_dir)
            except Exception:
                pass
        dest_dir = output_dir
    else:
        try:
            from folder_paths import get_output_directory

            dest_dir = os.path.join(get_output_directory(), "PSD2Layer")
        except Exception:
            dest_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "output",
                "PSD2Layer",
            )

    os.makedirs(dest_dir, exist_ok=True)
    return os.path.abspath(os.path.join(dest_dir, filename))
