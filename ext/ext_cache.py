# -*- coding: utf-8 -*-
# 恋与临空 后端插件：静态图片缓存头（图片7天缓存，不再重复下载，缓解卡顿）
from fastapi import Request

def setup(app, data, helpers):
    @app.middleware("http")
    async def _cache_headers(request: Request, call_next):
        resp = await call_next(request)
        try:
            p = request.url.path
            if p.startswith('/images/') or p == '/api/avatar':
                resp.headers['Cache-Control'] = 'public, max-age=604800'
        except Exception:
            pass
        return resp
    print('[ext_cache] 静态图片缓存头（7天）已注册', flush=True)
