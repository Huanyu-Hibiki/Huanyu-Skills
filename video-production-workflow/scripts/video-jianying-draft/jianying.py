#!/usr/bin/env python3
"""
jianying.py — CLI for creating 剪映 draft files. No server, no ports.

Commands: create_draft, add_video, add_audio, add_text, add_subtitle,
          add_image, add_effect, add_sticker, save_draft
"""
import argparse, json, os, pickle, sys, time, uuid, shutil, subprocess, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import load_skill_env

load_skill_env()

SCRIPT_DIR = Path(__file__).resolve().parent
CAPCUT_MCP_DIR = os.environ.get("CAPCUT_MCP_DIR") or str(SCRIPT_DIR / "vendor")

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
                            material_name=os.path.basename(a.file),
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
                            material_name=os.path.basename(a.file), duration=dur)
    sc.add_material(mat)
    tn = a.track_name or "audio_main"
    sc.add_track(dy.Track_type.audio, tn)
    seg = dy.Audio_segment(mat, _tr(ts, ts + (end - start) / a.speed),
                           source_timerange=_tr(start, end), volume=a.volume)
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
                            material_name=os.path.basename(a.file),
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
    tmpl = os.path.join(CAPCUT_MCP_DIR, "template_jianying")
    if not os.path.exists(tmpl): tmpl = os.path.join(CAPCUT_MCP_DIR, "template")
    out = os.path.join(a.output, a.draft_id)
    if os.path.exists(out): shutil.rmtree(out)
    shutil.copytree(tmpl, out)
    sc.dump(os.path.join(out, "draft_content.json"))
    # Copy referenced media to draft assets/
    assets = os.path.join(out, "assets"); os.makedirs(assets, exist_ok=True)
    for mat in sc.materials.videos:
        lp = getattr(mat, 'local_path', '')
        if lp and os.path.exists(lp):
            dest = os.path.join(assets, os.path.basename(lp))
            if not os.path.exists(dest): shutil.copy2(lp, dest)
    for mat in sc.materials.audios:
        lp = getattr(mat, 'local_path', '')
        if lp and os.path.exists(lp):
            dest = os.path.join(assets, os.path.basename(lp))
            if not os.path.exists(dest): shutil.copy2(lp, dest)
    print(json.dumps({"success": True, "output": out,
        "message": f"草稿已保存。打开剪映专业版即可看到 {a.draft_id}"}))

# ─── CLI ──────────────────────────────────────────────────────────────

def main():
    pa = argparse.ArgumentParser(description="剪映 draft toolkit")
    sub = pa.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('create_draft'); p.add_argument('--width', type=int, default=1920); p.add_argument('--height', type=int, default=1080); p.add_argument('--cache-dir', required=True); p.set_defaults(fn=cmd_create_draft)
    p = sub.add_parser('add_video'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--file', required=True); p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--target-start', type=float); p.add_argument('--speed', type=float, default=1.0); p.add_argument('--track-name'); p.set_defaults(fn=cmd_add_video)
    p = sub.add_parser('add_audio'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--file', required=True); p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--target-start', type=float); p.add_argument('--volume', type=float, default=1.0); p.add_argument('--speed', type=float, default=1.0); p.add_argument('--track-name'); p.set_defaults(fn=cmd_add_audio)
    p = sub.add_parser('add_text'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--text', required=True); p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--font-size', type=float); p.add_argument('--font-color'); p.add_argument('--track-name'); p.set_defaults(fn=cmd_add_text)
    p = sub.add_parser('add_subtitle'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--srt', required=True); p.add_argument('--time-offset', type=float); p.add_argument('--font-size', type=float, default=5.0); p.add_argument('--font-color', default='#FFFFFF'); p.add_argument('--track-name'); p.add_argument('--max-chars', type=float, default=18, dest='max_chars', help='max display units per cue (CJK=1, ASCII=0.5)'); p.add_argument('--min-chars', type=float, default=6, dest='min_chars'); p.add_argument('--no-split', action='store_true', dest='no_split', help='import the SRT as-is without splitting'); p.set_defaults(fn=cmd_add_subtitle)
    p = sub.add_parser('add_image'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--file', required=True); p.add_argument('--width', type=int); p.add_argument('--height', type=int); p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--track-name'); p.set_defaults(fn=cmd_add_image)
    p = sub.add_parser('add_effect'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--effect', required=True); p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--track-name'); p.set_defaults(fn=cmd_add_effect)
    p = sub.add_parser('add_sticker'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--sticker-id', required=True); p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--width', type=int, default=1080); p.add_argument('--height', type=int, default=1920); p.add_argument('--track-name'); p.set_defaults(fn=cmd_add_sticker)
    p = sub.add_parser('save_draft'); p.add_argument('--draft-id', required=True); p.add_argument('--cache-dir', required=True); p.add_argument('--output', required=True); p.set_defaults(fn=cmd_save_draft)

    a = pa.parse_args(); a.fn(a)

if __name__ == '__main__': main()
