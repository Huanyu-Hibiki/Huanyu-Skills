"""Subtitle and preview consumers of the canonical frame timeline."""
import json
from pathlib import Path
import subprocess
from .edit_plan import probe


def keeps(plan):
    return [item for item in plan['timeline'] if item['op'] in ('keep', 'insert_screen_demo', 'insert_broll_packaging', 'insert_broll_ai_visual')]


def micros(frames, fps):
    return (frames * 1000000 + fps // 2) // fps


def captions(plan):
    return [dict(id=item['id'], text=item['text'], start=item['targetStartFrame'],
                 end=item['targetStartFrame'] + item['durationFrames'])
            for item in keeps(plan) if item.get('text') and item.get('track', 'A-roll Final') == 'A-roll Final']


def subtitles(plan, output):
    output = Path(output)
    def stamp(frames):
        milliseconds = (frames * 1000 + plan['fps'] // 2) // plan['fps']
        seconds, ms = divmod(milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'
    text = '\n\n'.join(f"{index}\n{stamp(cue['start'])} --> {stamp(cue['end'])}\n{cue['text']}"
                       for index, cue in enumerate(captions(plan), 1))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text + '\n', encoding='utf-8')
    output.with_suffix('.json').write_text(json.dumps(dict(planHash=plan['planHash'],
                                                          cues=captions(plan)), ensure_ascii=False), encoding='utf-8')


def preview(plan, output):
    output = Path(output)
    items = keeps(plan)
    a_roll_items = [item for item in items if item.get('track', 'A-roll Final') == 'A-roll Final']
    overlay_items = [item for item in items if item.get('track') in ('Screen Demo', 'B-roll Packaging', 'B-roll AI Visual')]
    if any(item.get('track') not in ('A-roll Final', 'Screen Demo', 'B-roll Packaging', 'B-roll AI Visual') for item in items):
        raise ValueError('preview currently supports A-roll Final, Screen Demo, B-roll Packaging, and B-roll AI Visual tracks only; cross-track plans validate but need a later compositor')
    if not a_roll_items:
        raise ValueError('preview requires at least one keep on A-roll Final')
    fps = plan['fps']
    unique_sources = []
    source_to_input_idx = {}
    for sid, s in plan['sources'].items():
        source_path = s['path']
        if source_path not in source_to_input_idx:
            source_to_input_idx[source_path] = len(unique_sources)
            unique_sources.append(source_path)
            is_aroll_source = any(it['sourceId'] == sid for it in a_roll_items)
            if is_aroll_source:
                info = probe(source_path)
                if not any(stream['codec_type'] == 'audio' for stream in info['streams']):
                    raise ValueError('A-roll source must contain audio')
    inputs = []
    for src in unique_sources:
        inputs += ['-i', src]
    cursor = 0
    filters, labels = [], []
    for index, item in enumerate(a_roll_items):
        if item['targetStartFrame'] > cursor:
            gap_frames = item['targetStartFrame'] - cursor
            gap_dur = gap_frames / fps
            gap_idx = f"gap_{index}"
            filters += [
                f'color=c=black:s=640x360:r={fps}:d={gap_dur}[v_{gap_idx}]',
                f'anullsrc=r=48000:cl=stereo,atrim=duration={gap_dur}[a_{gap_idx}]'
            ]
            labels.append(f'[v_{gap_idx}][a_{gap_idx}]')
            cursor += gap_frames
        elif item['targetStartFrame'] < cursor:
            raise ValueError('overlapping items on A-roll Final timeline')

        cursor += item['durationFrames']
        source = plan['sources'][item['sourceId']]['path']
        input_idx = source_to_input_idx[source]
        start = item['sourceStartFrame'] / fps
        end = item['sourceEndFrame'] / fps
        filters += [f'[{input_idx}:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,fps={fps},scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,setsar=1[v{index}]',
                    f'[{input_idx}:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo:sample_fmts=fltp[a{index}]']
        labels.append(f'[v{index}][a{index}]')
    concat_v_label = '[v_base]' if overlay_items else '[v]'
    filters.append(''.join(labels) + f'concat=n={len(labels)}:v=1:a=1{concat_v_label}[a]')

    if overlay_items:
        curr_v = "[v_base]"
        for s_idx, s_item in enumerate(overlay_items):
            s_src = plan['sources'][s_item['sourceId']]['path']
            s_input_idx = source_to_input_idx[s_src]
            s_start = s_item['sourceStartFrame'] / fps
            s_end = s_item['sourceEndFrame'] / fps
            t_start = s_item['targetStartFrame'] / fps
            t_end = t_start + (s_item['durationFrames'] / fps)
            s_label = f"over_{s_idx}"
            filters.append(
                f"[{s_input_idx}:v]trim=start={s_start}:end={s_end},setpts=PTS-STARTPTS+{t_start:.4f}/TB,fps={fps},"
                f"scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,setsar=1[{s_label}]"
            )
            next_v = f"[v_over_{s_idx}]" if s_idx < len(overlay_items) - 1 else "[v]"
            filters.append(
                f"{curr_v}[{s_label}]overlay=0:0:enable='between(t,{t_start:.4f},{t_end:.4f})'{next_v}"
            )
            curr_v = next_v

    output.parent.mkdir(parents=True, exist_ok=True)
    filter_script = output.with_suffix('.filter.txt')
    filter_script.write_text(';\n'.join(filters), encoding='utf-8')
    try:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex_script', str(filter_script),
                        '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-t', str(cursor/fps), str(output)], check=True, capture_output=True, timeout=300)
    finally:
        if filter_script.is_file():
            try:
                filter_script.unlink()
            except OSError:
                pass
    duration = float(probe(output)['format']['duration'])
    if abs(duration - cursor/fps) > 1/fps:
        raise ValueError('preview duration differs from plan by more than one frame')
    output.with_suffix('.json').write_text(json.dumps(dict(planHash=plan['planHash'], duration=duration)), encoding='utf-8')


def verify_draft(plan, path):
    draft = json.loads(Path(path).read_text(encoding='utf-8'))
    expected = keeps(plan)
    main_actual_by_id = {}
    track_attributes = {track['name']: track.get('attribute', 0) for track in draft['tracks'] if 'name' in track}
    for track in draft['tracks']:
        if track['type'] == 'video' and track['name'] != 'A-roll Recovery':
            for segment in track['segments']:
                if segment['id'] in main_actual_by_id:
                    raise ValueError(f"duplicate segment ID in draft: {segment['id']}")
                main_actual_by_id[segment['id']] = (track['name'], segment)
    if len(main_actual_by_id) != len(expected):
        raise ValueError('draft segment count mismatch')
    materials = {item['id']: item['path'] for item in draft['materials']['videos']}
    for item in expected:
        if item['id'] not in main_actual_by_id:
            raise ValueError('draft segment ID mismatch')
        track, segment = main_actual_by_id[item['id']]
        source = segment['source_timerange']
        target = segment['target_timerange']
        fps = plan['fps']
        if item.get('track') in ('Screen Demo', 'B-roll Packaging', 'B-roll AI Visual') and track_attributes.get(item['track']) != 1:
            raise ValueError(f"{item['track']} track must be muted (attribute=1)")
        if (track != item['track'] or Path(materials[segment['material_id']]).resolve() != Path(plan['sources'][item['sourceId']]['path']).resolve()
                or source['start'] != micros(item['sourceStartFrame'], fps)
                or source['duration'] != micros(item['durationFrames'], fps)
                or target['start'] != micros(item['targetStartFrame'], fps)
                or target['duration'] != micros(item['durationFrames'], fps)):
            raise ValueError(f"draft mapping mismatch: {item['id']}")
    expected_cues = captions(plan)
    text_materials = {item['id']: item for item in draft['materials']['texts']}
    actual_cues = [segment for track in draft['tracks'] if track['type'] == 'text' for segment in track['segments']]
    if len(actual_cues) != len(expected_cues):
        raise ValueError('draft subtitle count mismatch')
    for cue, segment in zip(expected_cues, actual_cues):
        content = json.loads(text_materials[segment['material_id']]['content'])
        if (content['text'] != cue['text'] or segment['target_timerange'] !=
                dict(start=micros(cue['start'], plan['fps']), duration=micros(cue['end']-cue['start'], plan['fps']))):
            raise ValueError('draft subtitle mismatch')
    return {'status': 'ok', 'planHash': plan['planHash'], 'segments': len(main_actual_by_id), 'guiVerified': False}
