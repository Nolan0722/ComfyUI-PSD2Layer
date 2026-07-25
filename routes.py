"""ComfyUI HTTP 路由：Merge PSD 节点内预览（不重跑整条管线）。"""

from __future__ import annotations

from aiohttp import web

from .utils.merge_preview import flatten_paths_for_preview, flatten_sources_for_preview


def _register():
    try:
        from server import PromptServer
    except ImportError:
        return

    routes = web.RouteTableDef()

    @routes.post("/psd2layer/merge_flat_layers")
    async def merge_flat_layers(request: web.Request) -> web.Response:
        """每个 PSD 压平为一张图；offset 由前端本地合成。"""
        try:
            data = await request.json()
        except Exception as e:
            return web.json_response({"error": f"无效 JSON: {e}"}, status=400)

        include_hidden = bool(data.get("include_hidden", True))

        sources = data.get("sources")
        if sources:
            try:
                layers = flatten_sources_for_preview(sources, include_hidden=include_hidden)
                return web.json_response({"layers": layers})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        paths = data.get("paths") or []
        if not paths:
            return web.json_response({"error": "未提供 PSD 路径或 sources"}, status=400)

        try:
            layers = flatten_paths_for_preview(
                [str(p) for p in paths],
                include_hidden=include_hidden,
            )
            return web.json_response({"layers": layers})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    PromptServer.instance.app.add_routes(routes)


_register()
