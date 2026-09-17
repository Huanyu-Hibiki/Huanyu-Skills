"""Frame-based, half-open edit plan shared by all timeline consumers."""
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import subprocess


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams',
                             '-of', 'json', str(path)], capture_output=True, text=True, check=True, timeout=30)
    return json.loads(result.stdout)


def frame(value, fps):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('time must be a finite number')
    number = Decimal(str(value))
    if not number.is_finite() or number < 0:
        raise ValueError('time must be finite and nonnegative')
    return int((number * fps).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def load_plan(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding='utf-8'))
    base = Path(data.get('projectRoot', path.parent)).resolve()
    fps = data.get('fps')
    if data.get('version') != '1' or type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError('version must be 1 and fps an integer from 1 to 120')
    sources = {}
    for key, value in data['sources'].items():
        source = (base / (value['path'] if isinstance(value, dict) else value)).resolve()
        if not source.is_file():
            raise ValueError(f'missing source: {source}')
        info = probe(source)
        sources[key] = {'path': str(source), 'duration': float(info['format']['duration'])}
    timeline = []
    seen = set()
    ends = {}
    for item in data['timeline']:
        identifier = item['id']
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError('segment IDs must be unique nonempty strings')
        seen.add(identifier)
        if item['op'] not in ('keep', 'remove', 'insert_screen_demo', 'insert_broll_packaging'):
            raise ValueError('this version supports explicit keep, remove, insert_screen_demo, or insert_broll_packaging only')
        source = sources.get(item['sourceId'])
        if source is None:
            raise ValueError('unknown sourceId')
        start = frame(item['sourceStart'], fps)
        end = frame(item['sourceEnd'], fps)
        if item['sourceEnd'] <= item['sourceStart'] or end <= start:
            raise ValueError('source interval must have positive duration')
        if item['sourceEnd'] > source['duration'] or end / fps > source['duration'] + 1e-6:
            raise ValueError('source interval out of bounds')
        normalized = dict(item, sourceStartFrame=start, sourceEndFrame=end, durationFrames=end-start)
        if item['op'] in ('keep', 'insert_screen_demo', 'insert_broll_packaging'):
            target = frame(item['targetStart'], fps)
            if item['op'] == 'insert_screen_demo':
                default_track = 'Screen Demo'
            elif item['op'] == 'insert_broll_packaging':
                default_track = 'B-roll Packaging'
            else:
                default_track = 'A-roll Final'
            track = item.get('track', default_track)
            if target < ends.get(track, 0):
                raise ValueError(f'overlap or nonmonotonic timeline on {track}')
            ends[track] = target + end - start
            normalized.update(track=track, targetStartFrame=target)
        timeline.append(normalized)
    result = dict(version='1', fps=fps, projectRoot=str(base), sources=sources,
                  timeline=timeline, durationFrames=ends.get('A-roll Final', 0),
                  reviewQueue=data.get('reviewQueue', []))
    result['planHash'] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return result
