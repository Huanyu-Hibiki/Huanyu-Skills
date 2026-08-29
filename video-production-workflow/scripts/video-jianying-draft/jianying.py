#!/usr/bin/env python3
"""
jianying.py — CLI for creating 剪映 draft files. No server, no ports.

Commands: create_draft, add_video, add_audio, add_text, add_subtitle,
          add_image, add_effect, add_sticker, save_draft
"""
import argparse, json, os, pickle, sys, time, uuid, shutil, subprocess, re, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import load_skill_env

load_skill_env()

SCRIPT_DIR = Path(__file__).resolve().parent
# env 覆盖仅在确实指向含 pyJianYingDraft 的目录时生效；失效路径
# （如旧机器迁移残留）自动回退到随 skill 附带的 vendor，避免静默断链
_env_mcp = os.environ.get("CAPCUT_MCP_DIR")
CAPCUT_MCP_DIR = _env_mcp if _env_mcp and os.path.isdir(
    os.path.join(_env_mcp, "pyJianYingDraft")) else str(SCRIPT_DIR / "vendor")

def _bootstrap():
    import types
    s = types.ModuleType('settings'); s.__path__=[]
    s.IS_CAPCUT_ENV = False; s.IS_UPLOAD_DRAFT = False
    sl = types.ModuleType('settings.local')
    sl.IS_CAPCUT_ENV = False; sl.IS_UPLOAD_DRAFT = False
    s.local = sl
    sys.modules['settings'] = s; sys.modules['settings.local'] = sl
    if CAPCUT_MCP_DIR not in sys.path:
        sys.path.insert(0, CAPCUT_MCP_DIR)

_bootstrap()
import pyJianYingDraft as dy

# ─── persistence ──────────────────────────────────────────────────────

def _save(cache_dir, draft_id, script):
    p = Path(cache_dir) / f"{draft_id}.pkl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'wb') as f: pickle.dump(script, f)

def _load(cache_dir, draft_id):
    p = Path(cache_dir) / f"{draft_id}.pkl"
    if not p.exists():
        print(f"ERROR: Draft {draft_id} not found", file=sys.stderr); sys.exit(1)
    with open(p, 'rb') as f: return pickle.load(f)

# ─── helpers ──────────────────────────────────────────────────────────

def _dur(path):
    r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',path], capture_output=True, text=True)
    return float(r.stdout.strip())

def _video_info(path):
    r1 = subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','csv=p=0:s=x',path], capture_output=True, text=True)
    parts = [p for p in r1.stdout.strip().split('x') if p]
    return int(parts[0]), int(parts[1]), _dur(path)

def _tr(start, end):
    """Create Timerange from start/end seconds. trange takes (start, duration).
    Must pass as strings like "851.9s" because tim() treats raw floats as microseconds."""
    return dy.trange(f"{start}s", f"{end - start}s")

def _hex_to_rgb_tuple(hex_color):
    """Convert '#FFFFFF' to (1.0, 1.0, 1.0) normalized RGB."""
    h = hex_color.lstrip('#')
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return (r, g, b)

def _name_key(name):
    """文件名占用键：Unicode NFC + casefold。NTFS 不区分大小写，
    clip.mp4 与 CLIP.mp4 是同一个文件。"""
    return unicodedata.normalize("NFC", name).casefold()

def _unique_name(name, used_keys):
    """生成占用键唯一的文件名（循环递增后缀，不会二次碰撞）。"""
    if _name_key(name) not in used_keys:
        return name
    stem, ext = os.path.splitext(name)
    i = 2
    while _name_key(f"{stem}-{i}{ext}") in used_keys:
        i += 1
    return f"{stem}-{i}{ext}"

def _trash_dir(root):
    """替换/卸载的待删目录统一放这里。剪映按 <草稿根>/<目录>/
    draft_content.json 识别草稿，嵌套一层不会被扫成幽灵草稿；
    同一文件系统内 rename 保持原子。"""
    d = os.path.join(root, ".jianying-trash")
    os.makedirs(d, exist_ok=True)
    return d

def _audio_lane(sc, base_name, seg):
    """贪心分道：剪映同轨音频段不可重叠。请求轨道装不下时按
    base-2/base-3... 顺序找第一个不重叠的空位，必要时开新轨。"""
    def fits(name):
        t = sc.tracks.get(name)
        return t is None or not any(s.overlaps(seg) for s in t.segments)
    name, i = base_name, 2
    while not fits(name):
        name = f"{base_name}-{i}"
        i += 1
    if name not in sc.tracks:
        sc.add_track(dy.Track_type.audio, name)
    return name

def _material_name_for(sc, kind, path):
    """素材表按 material_name 去重（uuid3(name) 作 id），同名不同文件会被
    静默合并成第一个素材——错链。这里给不同源文件返回不冲突的名称；
    同一源文件保持原名，让 add_material 正确复用。"""
    path = os.path.realpath(os.path.abspath(path))
    base = os.path.basename(path)
    existing = {getattr(m, 'material_name', ''): getattr(m, 'path', '')
                for m in getattr(sc.materials, kind)}
    if existing.get(base) == path:
        return base
    stem, ext = os.path.splitext(base)
    name, i = base, 2
    while existing.get(name) not in (None, '', path):
        name = f"{stem}-{i}{ext}"
        i += 1
    return name

def _jianying_running():
    """剪映专业版进程检测：save_draft 写盘前剪映必须完全退出。
    tasklist 在中文 Windows 输出 GBK，按 bytes 捕获再 errors='ignore'
    解码（JianyingPro 是 ASCII，不受非 ASCII 丢弃影响）。"""
    if sys.platform == 'win32':
        r = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq JianyingPro.exe', '/NH'],
            capture_output=True)
        return 'JianyingPro' in r.stdout.decode('utf-8', errors='ignore')
    try:
        out = subprocess.run(['pgrep', '-fl', '-i', 'JianyingPro'],
                             capture_output=True, text=True).stdout or ''
    except FileNotFoundError:
        return False
    return bool(out.strip())

def _default_draft_root():
    """剪映草稿根候选探测。只接受「存在且含至少一个真草稿子目录」
    的候选（子目录里有 draft_content.json 或 draft_info.json）——目录存在
    且被剪映用过才可信；候选都不满足时返回 None，不猜。"""
    cands = []
    if sys.platform == 'darwin':
        cands.append(os.path.expanduser(
            r"~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft"))
    cands += [
        os.path.expandvars(r'%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft'),
        os.path.expanduser(r'~\JianyingPro Drafts'),
    ]
    for c in cands:
        if not os.path.isdir(c):
            continue
        try:
            subs = os.listdir(c)
        except OSError:
            continue
        for sub in subs:
            d = os.path.join(c, sub)
            if os.path.isfile(os.path.join(d, 'draft_content.json')) or \
               os.path.isfile(os.path.join(d, 'draft_info.json')):
                return c
    return None

def _validate_draft_name(draft_id, root):
    """校验草稿名并返回目标路径。save 会对目标 rename/rmtree，
    名字含路径分隔符、盘符或 .. 时会逃逸草稿根（任意目录删除），必须拒绝。"""
    if (not draft_id or draft_id in ('.', '..')
            or '/' in draft_id or '\\' in draft_id or ':' in draft_id
            or os.path.isabs(draft_id)):
        print(f"ERROR: 非法草稿名 {draft_id!r}：不能为空、含路径分隔符或为绝对路径",
              file=sys.stderr)
        sys.exit(1)
    target = os.path.realpath(os.path.join(root, draft_id))
    if os.path.dirname(target) != os.path.realpath(root):
        print(f"ERROR: 草稿名 {draft_id!r} 解析后逃逸草稿根目录：{target}",
              file=sys.stderr)
        sys.exit(1)
    return os.path.join(root, draft_id)

# ─── Mac 支持（移植自 video-shotcraft mac_draft.py，Mac 剪映 11.2 实测） ──

def _write_json_atomic(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)

def _load_platform(draft_dir):
    """从一个明文草稿读 platform 机器指纹；读不到返回 None。"""
    try:
        with open(os.path.join(draft_dir, "draft_info.json"),
                  encoding="utf-8") as f:
            platform = json.load(f).get("platform", {})
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if isinstance(platform, dict) and platform.get("device_id") \
            and platform.get("os") == "mac":
        return {k: platform[k] for k in
                ("os", "app_version", "device_id", "hard_disk_id",
                 "mac_address") if k in platform}
    return None

def _mac_platform(root, donor_draft=None, allow_missing_fingerprint=False,
                  skip_names=()):
    """取 Mac 平台指纹：显式 donor > 自动扫描草稿库里仍为明文的老草稿。
    剪映 6+ 保存后加密，更早创建未再打开过的草稿仍是明文，可抄本机指纹。
    skip_names 排除本次正在创建的草稿——它含 vendor 模板自带的他人指纹，
    不排除会在全新机器上静默冒用模板作者的指纹而不是明确失败。"""
    if donor_draft:
        platform = _load_platform(donor_draft)
        if platform is None:
            print(f"ERROR: 指定的 donor 草稿不可用（非明文或缺 device_id）：{donor_draft}",
                  file=sys.stderr)
            sys.exit(1)
        return platform
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        entries = []
    for name in entries:
        if name in skip_names or name.startswith('.'):
            continue
        platform = _load_platform(os.path.join(root, name))
        if platform:
            return platform
    if not allow_missing_fingerprint:
        print("ERROR: 草稿库中未找到可抄设备指纹的明文老草稿（无指纹草稿未经实测，已中止）。"
              "可选项：① 剪映里新建任意草稿后立即退出，若其仍为明文即可被自动扫描；"
              "② 用 --donor-draft 指定一个明文草稿路径；"
              "③ --allow-missing-fingerprint 实验性安装（结果自负）",
              file=sys.stderr)
        sys.exit(1)
    print("[warn] 实验模式：platform 缺少机器指纹（device_id 等），剪映可能拒载")
    return {"os": "mac", "app_version": "5.4.0"}

def _material_records(content, now_us):
    """从 draft_content 的 materials 反推 Mac 版媒体池登记记录。
    缺登记时打开草稿会弹「媒体丢失，请重新链接」。"""
    records = []
    for kind, metetype in (("videos", None), ("audios", "music")):
        for m in content["materials"].get(kind, []):
            records.append({
                "create_time": now_us // 1_000_000,
                "duration": m["duration"],
                "extra_info": (m.get("material_name") or m.get("name")
                               or os.path.basename(m["path"])),
                "file_Path": m["path"],
                "height": m.get("height", 0),
                "id": str(uuid.uuid4()),
                "import_time": now_us // 1_000_000,
                "import_time_ms": now_us,
                "item_source": 1,
                "md5": "",
                # 图片素材在 videos 组里 type=photo，登记也要跟着标 photo
                "metetype": metetype or ("photo" if m.get("type") == "photo"
                                         else "video"),
                "roughcut_time_range": {"duration": -1, "start": -1},
                "sub_time_range": {"duration": -1, "start": -1},
                "type": 0,
                "width": m.get("width", 0),
            })
    return records

def _macify(out, draft_name, root, donor_draft=None, allow_missing=False):
    """把 Windows 5.9 格式草稿补成 Mac 版认识的样子，返回注册所需信息。
    Mac 三坑（均为逆向实测）：入口文件名 draft_info.json；platform 要带
    机器指纹；draft_materials(type 0) 必须登记全部媒体。"""
    platform = _mac_platform(root, donor_draft, allow_missing,
                             skip_names={draft_name})
    content_path = os.path.join(out, "draft_content.json")
    meta_path = os.path.join(out, "draft_meta_info.json")
    with open(content_path, encoding="utf-8") as f:
        content = json.load(f)
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    for key in ("platform", "last_modified_platform"):
        content[key] = {**content.get(key, {}), **platform}

    now_us = int(time.time() * 1_000_000)
    records = _material_records(content, now_us)
    assets_dir = os.path.join(out, "assets")
    materials_size = sum(
        os.path.getsize(os.path.join(assets_dir, n))
        for n in os.listdir(assets_dir)) if os.path.isdir(assets_dir) else 0

    fold_path = os.path.join(root, draft_name)
    meta.update({
        "draft_fold_path": fold_path,
        "draft_root_path": root,
        "draft_name": draft_name,
        "tm_draft_create": now_us,
        "tm_draft_modified": now_us,
        "tm_duration": content["duration"],
        "draft_timeline_materials_size_": materials_size,
    })
    meta.pop("draft_is_ai_translate", None)
    for group in meta.get("draft_materials", []):
        if group.get("type") == 0:
            group["value"] = records

    # 封面：从第一个视频素材抽首帧（缺封面时草稿列表显示异常）
    videos = content["materials"].get("videos", [])
    if videos:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                        "-i", videos[0]["path"], "-frames:v", "1",
                        os.path.join(out, "draft_cover.jpg")], check=False)

    _write_json_atomic(content_path, content)
    # Mac 入口文件名是 draft_info.json；draft_content.json 留给 Windows 工具
    _write_json_atomic(os.path.join(out, "draft_info.json"), content)
    _write_json_atomic(meta_path, meta)
    return {"draft_id": meta.get("draft_id") or str(uuid.uuid4()).upper(),
            "fold_path": fold_path, "duration": content["duration"],
            "materials_size": materials_size, "tm": now_us}

def _registry_entry(info, draft_name, root):
    """按 root_meta_info.json 实测 schema 构造注册条目。"""
    return {
        "cloud_draft_cover": False,
        "cloud_draft_sync": False,
        "draft_cloud_last_action_download": False,
        "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_cover": os.path.join(info["fold_path"], "draft_cover.jpg"),
        "draft_fold_path": info["fold_path"],
        "draft_id": info["draft_id"],
        "draft_is_ai_shorts": False,
        "draft_is_cloud_temp_draft": False,
        "draft_is_invisible": False,
        "draft_is_pippit_draft": False,
        "draft_is_web_article_video": False,
        "draft_json_file": os.path.join(info["fold_path"], "draft_info.json"),
        "draft_name": draft_name,
        "draft_new_version": "",
        "draft_root_path": root,
        "draft_timeline_materials_size": info["materials_size"],
        "draft_type": "",
        "draft_web_article_video_enter_from": "",
        "pippit_avatar_url": "",
        "pippit_extra_info": "",
        "pippit_id": "",
        "pippit_user_name": "",
        "streaming_edit_draft_ready": True,
        "tm_draft_cloud_completed": "",
        "tm_draft_cloud_entry_id": -1,
        "tm_draft_cloud_modified": 0,
        "tm_draft_cloud_parent_entry_id": -1,
        "tm_draft_cloud_space_id": -1,
        "tm_draft_cloud_user_id": -1,
        "tm_draft_create": info["tm"],
        "tm_draft_modified": info["tm"],
        "tm_draft_removed": 0,
        "tm_duration": info["duration"],
    }

def _mac_install_registry(draft_name, info, root):
    """把草稿注册进 root_meta_info.json（先备份，原子写入），返回备份路径。"""
    rm = os.path.join(root, "root_meta_info.json")
    with open(rm, encoding="utf-8") as f:
        reg = json.load(f)
    bak = rm + time.strftime(".%Y%m%d-%H%M%S.bak")
    shutil.copy2(rm, bak)
    reg["all_draft_store"] = [e for e in reg["all_draft_store"]
                              if e.get("draft_name") != draft_name]
    reg["all_draft_store"].insert(0, _registry_entry(info, draft_name, root))
    _write_json_atomic(rm, reg)
    return bak

# ─── commands ─────────────────────────────────────────────────────────

def cmd_create_draft(a):
    sc = dy.Script_file(a.width, a.height)
    did = f"dfd_jy_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    _save(a.cache_dir, did, sc)
    print(json.dumps({"draft_id": did, "width": a.width, "height": a.height}))

def cmd_add_video(a):
    sc = _load(a.cache_dir, a.draft_id)
    w, h, dur = _video_info(a.file)
    start = a.start if a.start is not None else 0
    end = a.end if a.end is not None else dur
    ts = a.target_start if a.target_start is not None else 0
    # Video_material needs the raw local path (it validates existence)
    mat = dy.Video_material(material_type='video', path=os.path.abspath(a.file),
                            material_name=_material_name_for(sc, 'videos', a.file),
                            duration=dur, width=w, height=h)
    sc.add_material(mat)
    tn = a.track_name or "main"
    sc.add_track(dy.Track_type.video, tn)
    seg = dy.Video_segment(mat, _tr(ts, ts + (end - start) / a.speed),
                           source_timerange=_tr(start, end), speed=a.speed)
    sc.add_segment(seg, tn)
    _save(a.cache_dir, a.draft_id, sc)
    print(json.dumps({"success": True, "file": os.path.basename(a.file), "track": tn}))

def cmd_add_audio(a):
    sc = _load(a.cache_dir, a.draft_id)
    dur = _dur(a.file)
    start = a.start if a.start is not None else 0
    end = a.end if a.end is not None else dur
    ts = a.target_start if a.target_start is not None else 0
    mat = dy.Audio_material(path=os.path.abspath(a.file),
                            material_name=_material_name_for(sc, 'audios', a.file), duration=dur)
    sc.add_material(mat)
    tn = a.track_name or "audio_main"
    seg = dy.Audio_segment(mat, _tr(ts, ts + (end - start) / a.speed),
                           source_timerange=_tr(start, end), volume=a.volume)
    if a.no_lane_split:
        # 严格模式：同轨重叠直接抛 SegmentOverlap（旧行为）
        sc.add_track(dy.Track_type.audio, tn)
        sc.add_segment(seg, tn)
    else:
        # 贪心分道：重叠音频自动溢出到同名前缀的新轨（如 BGM-2）
        tn = _audio_lane(sc, tn, seg)
        sc.add_segment(seg, tn)
    _save(a.cache_dir, a.draft_id, sc)
    print(json.dumps({"success": True, "file": os.path.basename(a.file), "track": tn}))

def cmd_add_text(a):
    sc = _load(a.cache_dir, a.draft_id)
    ts = a.start if a.start is not None else 0
    te = a.end if a.end is not None else ts + 3
    tn = a.track_name or "text_main"
    sc.add_track(dy.Track_type.text, tn)
    style = dy.Text_style(size=a.font_size or 20.0,
                          color=_hex_to_rgb_tuple(a.font_color or "#FFFFFF"))
    seg = dy.Text_segment(a.text, _tr(ts, te), style=style)
    sc.add_segment(seg, tn)
    _save(a.cache_dir, a.draft_id, sc)
    print(json.dumps({"success": True, "text": a.text[:50], "start": ts, "end": te}))

def cmd_add_subtitle(a):
    sc = _load(a.cache_dir, a.draft_id)
    srt = Path(a.srt).read_text(encoding='utf-8-sig')
    # Split long cues into JianYing-native short chunks before import —
    # sentence-level blocks would land as one oversized text box each.
    if not a.no_split:
        from subtitle_split import split_srt
        srt, _stats = split_srt(srt, a.max_chars, a.min_chars)
        split_path = Path(a.srt).with_suffix('.split.srt')
        split_path.write_text(srt, encoding='utf-8')
        print(json.dumps({"success": True, "stage": "split", "output": str(split_path)}))
    tn = a.track_name or "subtitle"
    style = dy.Text_style(size=a.font_size, color=_hex_to_rgb_tuple(a.font_color), align=1)
    sc.import_srt(srt, tn, time_offset=a.time_offset or 0, text_style=style)
    _save(a.cache_dir, a.draft_id, sc)
    blocks = [b for b in re.split(r'\n\s*\n', srt.strip()) if b.strip()]
    print(json.dumps({"success": True, "srt": a.srt, "count": len(blocks)}))

def cmd_add_image(a):
    sc = _load(a.cache_dir, a.draft_id)
    w = a.width or 1920; h = a.height or 1080
    ts = a.start if a.start is not None else 0
    te = a.end if a.end is not None else ts + 5
    mat = dy.Video_material(material_type='photo', path=os.path.abspath(a.file),
                            material_name=_material_name_for(sc, 'videos', a.file),
                            duration=te-ts, width=w, height=h)
    sc.add_material(mat)
    tn = a.track_name or "image_main"
    sc.add_track(dy.Track_type.video, tn)
    seg = dy.Video_segment(mat, _tr(ts, te))
    sc.add_segment(seg, tn)
    _save(a.cache_dir, a.draft_id, sc)
    print(json.dumps({"success": True, "file": os.path.basename(a.file)}))

def cmd_add_effect(a):
    sc = _load(a.cache_dir, a.draft_id)
    ts = a.start if a.start is not None else 0
    te = a.end if a.end is not None else ts + 5
    tn = a.track_name or "effect_01"
    sc.add_track(dy.Track_type.effect, tn)
    seg = dy.Effect_segment(a.effect, _tr(ts, te), width=1920, height=1080)
    sc.add_segment(seg, tn)
    _save(a.cache_dir, a.draft_id, sc)
    print(json.dumps({"success": True, "effect": a.effect}))

def cmd_add_sticker(a):
    sc = _load(a.cache_dir, a.draft_id)
    ts = a.start if a.start is not None else 0
    te = a.end if a.end is not None else ts + 3
    tn = a.track_name or "sticker_main"
    sc.add_track(dy.Track_type.sticker, tn)
    seg = dy.Sticker_segment(a.sticker_id, _tr(ts, te), width=a.width, height=a.height)
    sc.add_segment(seg, tn)
    _save(a.cache_dir, a.draft_id, sc)
    print(json.dumps({"success": True, "sticker": a.sticker_id}))

def cmd_save_draft(a):
    sc = _load(a.cache_dir, a.draft_id)
    if _jianying_running():
        print("ERROR: 剪映专业版正在运行——完全退出后再 save_draft（写盘时草稿打开会导致损坏）",
              file=sys.stderr)
        sys.exit(1)
    root, root_source = a.output, "explicit"
    if not root:
        root = _default_draft_root()
        if not root:
            print("ERROR: 未指定 --output 且未能探测到剪映草稿根。"
                  "请在剪映「全局设置→草稿位置」复制真实路径后用 --output 传入",
                  file=sys.stderr)
            sys.exit(1)
        root_source = "auto-detected"
    tmpl = os.path.join(CAPCUT_MCP_DIR, "template_jianying")
    if not os.path.exists(tmpl): tmpl = os.path.join(CAPCUT_MCP_DIR, "template")
    out = _validate_draft_name(a.draft_id, root)
    # 旧草稿先移入回收目录（嵌套一层，剪映不会扫成幽灵草稿），
    # 全部成功后才清理；中途失败自动回滚复位
    old = None
    if os.path.exists(out):
        old = os.path.join(_trash_dir(root),
                           f"{a.draft_id}.replaced-{time.strftime('%Y%m%d-%H%M%S')}")
        os.rename(out, old)
    missing = []
    mac_bak = None
    try:
        shutil.copytree(tmpl, out)
        # 媒体拷进 assets/ 并改写 replace_path → 草稿自包含：
        # 原素材被移动/删除不影响草稿；同名碰撞自动加后缀，绝不静默错链。
        # replace_path 必须在 dump 之前设置（dump 直接序列化它）
        assets = os.path.join(out, "assets"); os.makedirs(assets, exist_ok=True)
        used_keys, mapped = set(), {}
        for mat in list(sc.materials.videos) + list(sc.materials.audios):
            lp = getattr(mat, 'path', '')
            if not lp:
                continue
            key = os.path.realpath(lp)
            if not os.path.exists(lp):
                missing.append(lp)
                continue
            if key not in mapped:
                name = _unique_name(os.path.basename(lp), used_keys)
                used_keys.add(_name_key(name))
                shutil.copy2(lp, os.path.join(assets, name))
                mapped[key] = os.path.join(assets, name)
            mat.replace_path = mapped[key]
        # 原子落盘：先写 tmp 再 os.replace，中途崩溃不留半截 JSON
        content_tmp = os.path.join(out, 'draft_content.json.tmp')
        sc.dump(content_tmp)
        os.replace(content_tmp, os.path.join(out, 'draft_content.json'))
        # Mac：补 draft_info.json 入口/platform 指纹/媒体登记并注册草稿库
        if sys.platform == 'darwin':
            info = _macify(out, a.draft_id, root,
                           donor_draft=getattr(a, 'donor_draft', None),
                           allow_missing=getattr(a, 'allow_missing_fingerprint', False))
            mac_bak = _mac_install_registry(a.draft_id, info, root)
    except BaseException:
        if os.path.exists(out):
            shutil.rmtree(out, ignore_errors=True)
        if mac_bak and os.path.exists(mac_bak):
            shutil.copy2(mac_bak, os.path.join(root, "root_meta_info.json"))
        if old and os.path.exists(old):
            os.rename(old, out)
        raise
    if old:
        try:
            shutil.rmtree(old)
        except OSError as e:
            print(f"[warn] 旧草稿副本删除失败（位于回收目录，剪映不会扫描到），"
                  f"请手动清理：{old}（{e}）")
    print(json.dumps({"success": True, "output": out,
        "draft_root_source": root_source, "media_copied": len(mapped),
        "missing_media": missing,
        "message": f"草稿已保存。打开剪映专业版即可看到 {a.draft_id}"}))

# ─── CLI ──────────────────────────────────────────────────────────────

def main():
    pa = argparse.ArgumentParser(description="剪映 draft toolkit")
    sub = pa.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('create_draft'); p.add_argument('--width', type=int, default=1920); p.add_argument('--height', type=int, default=1080); p.add_argument('--cache-dir', required=True); p.set_defaults(fn=cmd_create_draft)
    p = sub.add_parser('add_video'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--file', required=True); p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--target-start', type=float); p.add_argument('--speed', type=float, default=1.0); p.add_argument('--track-name'); p.set_defaults(fn=cmd_add_video)
    p = sub.add_parser('add_audio'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--file', required=True); p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--target-start', type=float); p.add_argument('--volume', type=float, default=1.0); p.add_argument('--speed', type=float, default=1.0); p.add_argument('--track-name'); p.add_argument('--no-lane-split', action='store_true', dest='no_lane_split', help='disable greedy lane split; overlapping audio raises SegmentOverlap'); p.set_defaults(fn=cmd_add_audio)
    p = sub.add_parser('add_text'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--text', required=True); p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--font-size', type=float); p.add_argument('--font-color'); p.add_argument('--track-name'); p.set_defaults(fn=cmd_add_text)
    p = sub.add_parser('add_subtitle'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--srt', required=True); p.add_argument('--time-offset', type=float); p.add_argument('--font-size', type=float, default=5.0); p.add_argument('--font-color', default='#FFFFFF'); p.add_argument('--track-name'); p.add_argument('--max-chars', type=float, default=18, dest='max_chars', help='max display units per cue (CJK=1, ASCII=0.5)'); p.add_argument('--min-chars', type=float, default=6, dest='min_chars'); p.add_argument('--no-split', action='store_true', dest='no_split', help='import the SRT as-is without splitting'); p.set_defaults(fn=cmd_add_subtitle)
    p = sub.add_parser('add_image'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--file', required=True); p.add_argument('--width', type=int); p.add_argument('--height', type=int); p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--track-name'); p.set_defaults(fn=cmd_add_image)
    p = sub.add_parser('add_effect'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--effect', required=True); p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--track-name'); p.set_defaults(fn=cmd_add_effect)
    p = sub.add_parser('add_sticker'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--sticker-id', required=True); p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--width', type=int, default=1080); p.add_argument('--height', type=int, default=1920); p.add_argument('--track-name'); p.set_defaults(fn=cmd_add_sticker)
    p = sub.add_parser('save_draft'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--output', help='剪映真实草稿根；缺省时自动探测已验证的默认候选，探测不到必须显式传入'); p.add_argument('--donor-draft', dest='donor_draft', help='Mac: 从指定明文草稿抄 platform 设备指纹'); p.add_argument('--allow-missing-fingerprint', action='store_true', dest='allow_missing_fingerprint', help='Mac: 无指纹实验性安装（未经实测，结果自负）'); p.set_defaults(fn=cmd_save_draft)

    a = pa.parse_args(); a.fn(a)

if __name__ == '__main__': main()
