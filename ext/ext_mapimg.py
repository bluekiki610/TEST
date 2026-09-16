# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：地图图片管理（站长上传主图/分区图，存持久卷 /app/data/images）
# 附带：启动时把仓库 images/ 里的图片自动复制到卷（弥补骨架早期 migrate 只复制子目录的问题）
import base64
import re
import hashlib
import shutil


def setup(app, data, helpers):
    import main as m
    from main import is_admin, DATA_ROOT, save_data

    # ---- 补充迁移：仓库 images/ 根目录 + 子目录 → 卷（map_main.jpg 等） ----
    try:
        repo_img = m.BASE_DIR / "images"
        if repo_img.exists():
            img_root = DATA_ROOT / "images"
            img_root.mkdir(parents=True, exist_ok=True)
            for f in repo_img.iterdir():
                if f.is_file():
                    d = img_root / f.name
                    if not d.exists():
                        d.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, d)
                        print(f"[ext_mapimg] 仓库图片 → 卷: {f.name}", flush=True)
            for sub in repo_img.iterdir():
                if sub.is_dir():
                    for f in sub.iterdir():
                        if f.is_file():
                            d = img_root / sub.name / f.name
                            if not d.exists():
                                d.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(f, d)
                                print(f"[ext_mapimg] 仓库图片 → 卷: {sub.name}/{f.name}", flush=True)
    except Exception:
        pass

    def save_as(data_url, base_name):
        mm = re.match(r'data:image/(png|jpeg|jpg|webp);base64,(.+)', data_url or '', re.S)
        if not mm:
            return None
        ext = mm.group(1)
        if ext == "jpeg":
            ext = "jpg"
        raw = base64.b64decode(mm.group(2))
        if len(raw) > 5 * 1024 * 1024:
            return None
        filename = base_name + "." + ext
        (DATA_ROOT / "images" / filename).write_bytes(raw)
        return "/images/" + filename

    @app.get("/api/mapimg/status")
    async def mapimg_status(user: str = ""):
        img_root = DATA_ROOT / "images"
        def has(n):
            return (img_root / n).exists()
        regions_info = {}
        for label, r in data.get("regions", {}).items():
            regions_info[label] = bool(r.get("image"))
        return {
            "can_upload": is_admin(user),
            "main": has("map_main.png") or has("map_main.jpg") or has("map_main.jpeg"),
            "regions": regions_info,
        }

    @app.post("/api/mapimg/upload")
    async def mapimg_upload(bb: dict):
        user = (bb.get("user") or "").strip()
        if not is_admin(user):
            return {"ok": False, "msg": "🔒 只有站长可以上传世界地图"}
        kind = (bb.get("kind") or "main").strip()
        img = bb.get("image") or ""
        label = (bb.get("label") or "").strip()
        if kind == "main":
            p = save_as(img, "map_main")
            if not p:
                return {"ok": False, "msg": "保存失败（图片可能太大或格式不对）"}
            return {"ok": True, "msg": "✅ 世界地图主图已上传！请强刷页面（Ctrl+F5）", "url": p}
        if kind == "region":
            if not label:
                return {"ok": False, "msg": "缺少分区名"}
            if label not in data.get("regions", {}):
                return {"ok": False, "msg": f"分区「{label}」不存在，请先在地图上创建区域"}
            safe = "map_reg_" + hashlib.md5(label.encode()).hexdigest()[:8]
            p = save_as(img, safe)
            if not p:
                return {"ok": False, "msg": "保存失败（图片可能太大或格式不对）"}
            data.setdefault("regions", {}).setdefault(label, {})["image"] = p
            save_data()
            return {"ok": True, "msg": f"✅ 分区「{label}」地图已上传！请强刷页面", "url": p}
        return {"ok": False, "msg": "未知类型"}

    print("[ext_mapimg] 地图图片管理 + 仓库图片自动迁移 已注册", flush=True)
