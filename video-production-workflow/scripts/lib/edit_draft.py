"""Build a fresh native draft from JSON, without loading pickle state."""
import hashlib
import json
from pathlib import Path
import shutil
import time
import uuid
from .edit_plan import load_plan, probe
from .edit_outputs import captions, keeps, micros, verify_draft


def apply_edit_plan(plan_path, output_dir, dy, draft_id=None):
    plan = load_plan(plan_path)
    output_dir = Path(output_dir)
    if draft_id:
        clean_name = Path(draft_id).name
        if not clean_name or clean_name in ('.', '..') or '/' in str(draft_id) or '\\' in str(draft_id):
            raise ValueError(f'invalid draft_id: {draft_id}')
        folder_name = clean_name
    else:
        folder_name = 'auto-' + plan['planHash'][:16]
    folder = output_dir / folder_name
    draft_path = folder / 'draft_content.json'
    receipt = folder / 'edit-plan-receipt.json'
    if draft_path.exists() and receipt.exists():
        recorded = json.loads(receipt.read_text(encoding='utf-8'))
        if (recorded.get('planHash') == plan['planHash'] and
                recorded.get('draftHash') == hashlib.sha256(draft_path.read_bytes()).hexdigest()):
            verify_draft(plan, draft_path)
            return str(draft_path)
    if folder.exists():
        folder = output_dir / (folder.name + '-' + uuid.uuid4().hex[:8])
        draft_path = folder / 'draft_content.json'
        receipt = folder / 'edit-plan-receipt.json'
    items = keeps(plan)
    if not items:
        raise ValueError('draft requires at least one keep')
    source_meta = {}
    for sid, s in plan['sources'].items():
        info = probe(s['path'])
        video = next((stream for stream in info['streams'] if stream['codec_type'] == 'video'), None)
        if not video:
            raise ValueError(f'source {sid} has no video stream')
        source_meta[sid] = {'info': info, 'video': video}
    first_video = source_meta[items[0]['sourceId']]['video']
    script = dy.Script_file(first_video['width'], first_video['height'], fps=plan['fps'])
    fps = plan['fps']
    for item in items:
        source = plan['sources'][item['sourceId']]
        meta = source_meta[item['sourceId']]
        video = meta['video']
        material = dy.Video_material(material_type='video', path=source['path'],
                                     material_name=item['sourceId'], duration=source['duration'],
                                     width=video['width'], height=video['height'])
        if item['track'] not in script.tracks:
            is_muted = (item['track'] in ('Screen Demo', 'B-roll Packaging', 'B-roll AI Visual'))
            script.add_track(dy.Track_type.video, item['track'], mute=is_muted)
        seg_volume = 0.0 if item['track'] in ('Screen Demo', 'B-roll Packaging', 'B-roll AI Visual') else 1.0
        clip_settings = None
        zoom_val = item.get('zoom')
        if zoom_val is not None:
            try:
                scale = float(zoom_val)
                if abs(scale - 1.0) > 1e-4:
                    clip_settings = dy.Clip_settings(scale_x=scale, scale_y=scale)
            except (ValueError, TypeError):
                pass
        segment = dy.Video_segment(material,
                                   dy.Timerange(micros(item['targetStartFrame'], fps), micros(item['durationFrames'], fps)),
                                   source_timerange=dy.Timerange(micros(item['sourceStartFrame'], fps), micros(item['durationFrames'], fps)),
                                   volume=seg_volume,
                                   clip_settings=clip_settings)
        segment.segment_id = item['id']
        script.add_segment(segment, item['track'])
    for cue in captions(plan):
        if 'Subtitles' not in script.tracks:
            script.add_track(dy.Track_type.text, 'Subtitles')
        segment = dy.Text_segment(cue['text'], dy.Timerange(micros(cue['start'], fps), micros(cue['end']-cue['start'], fps)))
        script.add_segment(segment, 'Subtitles')

    removes = [item for item in plan['timeline'] if item['op'] == 'remove']
    if removes:
        script.add_track(dy.Track_type.video, 'A-roll Recovery', mute=True)
        final_dur_micros = micros(plan['durationFrames'], fps)
        rec_cursor = 0
        for r_item in removes:
            meta = source_meta.get(r_item['sourceId'])
            if not meta:
                continue
            source = plan['sources'][r_item['sourceId']]
            video = meta['video']
            material = dy.Video_material(material_type='video', path=source['path'],
                                         material_name=r_item['sourceId'], duration=source['duration'],
                                         width=video['width'], height=video['height'])
            dur_frames = r_item.get('durationFrames', r_item.get('sourceEndFrame', 0) - r_item.get('sourceStartFrame', 0))
            dur_micros = micros(dur_frames, fps)
            if dur_micros <= 0:
                continue
            target_start = rec_cursor
            if target_start >= final_dur_micros:
                break
            target_dur = dur_micros
            if target_start + target_dur > final_dur_micros:
                target_dur = final_dur_micros - target_start
            if target_dur < 1000:
                break
            clip_settings = dy.Clip_settings(alpha=0.0)
            segment = dy.Video_segment(material,
                                       dy.Timerange(target_start, target_dur),
                                       source_timerange=dy.Timerange(micros(r_item['sourceStartFrame'], fps), target_dur),
                                       volume=0.0,
                                       clip_settings=clip_settings)
            segment.segment_id = r_item['id']
            script.add_segment(segment, 'A-roll Recovery')
            rec_cursor += target_dur

    folder.mkdir(parents=True, exist_ok=True)
    tmpl = Path(__file__).resolve().parents[1] / 'video-jianying-draft/vendor/template_jianying'
    if not tmpl.exists():
        tmpl = Path(__file__).resolve().parents[1] / 'video-jianying-draft/vendor/template'
    now_us = int(time.time() * 1_000_000)
    if tmpl.exists():
        for f in tmpl.iterdir():
            if f.is_file() and f.name != 'draft_content.json':
                shutil.copy2(f, folder / f.name)
        meta_path = folder / 'draft_meta_info.json'
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
                meta.update({
                    "draft_fold_path": str(folder),
                    "draft_root_path": str(output_dir),
                    "draft_name": folder.name,
                    "draft_id": str(uuid.uuid4()).upper(),
                    "tm_draft_create": now_us,
                    "tm_draft_modified": now_us,
                    "tm_duration": micros(plan['durationFrames'], fps),
                })
                meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
            except Exception:
                pass
    script.dump(str(draft_path))

    # Build independent recovery draft
    if removes:
        rec_folder = output_dir / f"{folder.name}-recovery"
        rec_folder.mkdir(parents=True, exist_ok=True)
        rec_script = dy.Script_file(first_video['width'], first_video['height'], fps=plan['fps'])
        rec_script.add_track(dy.Track_type.video, 'A-roll Recovery Full')
        rec_t_cursor = 0
        for r_item in removes:
            meta = source_meta.get(r_item['sourceId'])
            if not meta:
                continue
            source = plan['sources'][r_item['sourceId']]
            video = meta['video']
            material = dy.Video_material(material_type='video', path=source['path'],
                                         material_name=r_item['sourceId'], duration=source['duration'],
                                         width=video['width'], height=video['height'])
            dur_frames = r_item.get('durationFrames', r_item.get('sourceEndFrame', 0) - r_item.get('sourceStartFrame', 0))
            dur_micros = micros(dur_frames, fps)
            segment = dy.Video_segment(material,
                                       dy.Timerange(rec_t_cursor, dur_micros),
                                       source_timerange=dy.Timerange(micros(r_item['sourceStartFrame'], fps), dur_micros))
            segment.segment_id = r_item['id']
            rec_script.add_segment(segment, 'A-roll Recovery Full')
            rec_t_cursor += dur_micros

        if tmpl.exists():
            for f in tmpl.iterdir():
                if f.is_file() and f.name != 'draft_content.json':
                    shutil.copy2(f, rec_folder / f.name)
            rec_meta_path = rec_folder / 'draft_meta_info.json'
            if rec_meta_path.exists():
                try:
                    rmeta = json.loads(rec_meta_path.read_text(encoding='utf-8'))
                    rmeta.update({
                        "draft_fold_path": str(rec_folder),
                        "draft_root_path": str(output_dir),
                        "draft_name": rec_folder.name,
                        "draft_id": str(uuid.uuid4()).upper(),
                        "tm_draft_create": now_us,
                        "tm_draft_modified": now_us,
                        "tm_duration": rec_t_cursor,
                    })
                    rec_meta_path.write_text(json.dumps(rmeta, ensure_ascii=False), encoding='utf-8')
                except Exception:
                    pass
        rec_script.dump(str(rec_folder / 'draft_content.json'))

    verify_draft(plan, draft_path)
    receipt.write_text(json.dumps(dict(planHash=plan['planHash'],
                                      draftHash=hashlib.sha256(draft_path.read_bytes()).hexdigest(),
                                      guiVerified=False)), encoding='utf-8')
    return str(draft_path)
