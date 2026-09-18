#!/usr/bin/env python3
"""Explicit edit-plan workflow; no automatic speech decisions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.edit_plan import load_plan, frame, probe
from lib.edit_outputs import preview, verify_draft
from lib.boundary_protect import analyze_cut_boundary, generate_boundary_report
from lib.pause_tighten import tighten_pauses, generate_pauses_report
from lib.take_selection import convert_takes_to_plan, evaluate_circuit_breaker, restore_take_in_plan
from lib.screen_demo import match_screen_anchors
from lib.broll_registry import get_template, validate_shot_brief


def _is_link_like(path: Path) -> bool:
    if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
        return True
    try:
        return bool(getattr(path.lstat(), 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))
    except OSError:
        return False


def _assert_safe_write_target(path: Path) -> None:
    if _is_link_like(path):
        raise ValueError(f'symlinked write target: {path}')
    current = path.parent
    while True:
        if _is_link_like(current):
            raise ValueError(f'symlinked write parent: {current}')
        if current.parent == current:
            break
        current = current.parent


def load_broll_manifest(path):
    """Read the canonical manifest without silently replacing corrupt data."""
    if not path.exists():
        return {'version': '1', 'items': [], 'summary': {}}
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot safely read B-roll manifest: {error}") from error
    if not isinstance(value, dict) or not isinstance(value.get('items'), list):
        raise ValueError('cannot safely read B-roll manifest: invalid schema')
    return value


def write_broll_manifest(path, manifest):
    """Atomically publish a complete manifest after every item state change."""
    path = Path(path)
    _assert_safe_write_target(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=f'.{path.name}.', suffix='.tmp', delete=False) as handle:
            handle.write(json.dumps(manifest, indent=2, ensure_ascii=False))
            tmp = Path(handle.name)
        os.replace(tmp, path)
    finally:
        if tmp and tmp.exists():
            tmp.unlink()


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Write a file through a same-directory temp and atomic replace."""
    path = Path(path)
    _assert_safe_write_target(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent,
                                         prefix=f'.{path.name}.', suffix='.tmp', delete=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            tmp = Path(handle.name)
        os.replace(tmp, path)
    finally:
        if tmp and tmp.exists():
            tmp.unlink()


def _safe_write_text(path: Path, text: str) -> None:
    _atomic_write_bytes(Path(path), text.encode('utf-8'))


def _transaction_journal_path(plan_path: Path) -> Path:
    return plan_path.with_name(f'.{plan_path.name}.broll-journal.json')


def _publish_plan_and_manifest(plan_path: Path, plan: dict, manifest_path: Path, manifest: dict) -> dict:
    """Publish normalized plan + manifest as one recoverable state transition."""
    previous_plan = plan_path.read_bytes() if plan_path.exists() else None
    previous_manifest = manifest_path.read_bytes() if manifest_path.exists() else None
    journal_path = _transaction_journal_path(plan_path)
    _atomic_write_bytes(journal_path, json.dumps({
        'version': 1,
        'plan_path': str(plan_path),
        'manifest_path': str(manifest_path),
        'previous_plan_sha256': hashlib.sha256(previous_plan or b'').hexdigest(),
        'previous_manifest_sha256': hashlib.sha256(previous_manifest or b'').hexdigest(),
    }, ensure_ascii=False).encode('utf-8'))
    try:
        _atomic_write_bytes(plan_path, json.dumps(plan, indent=2, ensure_ascii=False).encode('utf-8'))
        normalized = load_plan(plan_path)
        _atomic_write_bytes(plan_path, json.dumps(normalized, indent=2, ensure_ascii=False).encode('utf-8'))
        manifest['planHash'] = normalized['planHash']
        write_broll_manifest(manifest_path, manifest)
        if journal_path.exists():
            journal_path.unlink()
        return normalized
    except Exception:
        if previous_plan is not None:
            _atomic_write_bytes(plan_path, previous_plan)
        elif plan_path.exists():
            plan_path.unlink()
        if previous_manifest is not None:
            _atomic_write_bytes(manifest_path, previous_manifest)
        elif manifest_path.exists():
            manifest_path.unlink()
        if journal_path.exists():
            journal_path.unlink()
        raise


def summarize_broll_manifest(items):
    """Recompute manifest counters after any targeted state transition."""
    return {
        'total_items': len(items),
        'packaging_count': sum(1 for item in items if item.get('route') == 'packaging'),
        'screen_demo_count': sum(1 for item in items if item.get('route') == 'screen_demo'),
        'approved_count': sum(1 for item in items if item.get('status') == 'approved'),
    }


def run_boundary_check(plan):
    decisions = []
    keeps = [item for item in plan['timeline'] if item['op'] == 'keep']
    source_keeps = {}
    for item in keeps:
        source_keeps.setdefault(item['sourceId'], []).append(item)

    for item in keeps:
        src = plan['sources'].get(item['sourceId'])
        if src and Path(src['path']).is_file():
            text = item.get('text', '')
            ms = item.get('manuscript', text)
            siblings = source_keeps[item['sourceId']]
            curr_idx = siblings.index(item)
            next_start = siblings[curr_idx + 1]['sourceStart'] if curr_idx + 1 < len(siblings) else None
            dec = analyze_cut_boundary(
                audio_path=Path(src['path']),
                candidate_end=item['sourceEnd'],
                sentence_text=text,
                manuscript_text=ms,
                next_speech_start=next_start,
                source_duration=src.get('duration'),
                segment_id=item['id'],
                source_id=item['sourceId'],
            )
            decisions.append(dec)
    return decisions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'validate', 'subtitles', 'preview', 'verify-draft', 'boundary-check', 'tighten', 'select-takes', 'restore', 'insert-screen-demo', 'insert-broll-packaging', 'retry-broll-item', 'insert-broll-ai-visual', 'reconcile'])
    parser.add_argument('project', type=Path)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--draft', type=Path)
    parser.add_argument('--takes', type=Path, help='path to takes_decision.json or raw takes candidates')
    parser.add_argument('--screen', type=Path, help='path to screen recording video file')
    parser.add_argument('--markers', type=Path, help='path to screen recording markers json file')
    parser.add_argument('--sentence', type=str, help='target sentence ID for B-roll packaging')
    parser.add_argument('--style-pack', type=str, default='vox_explainer', help='B-roll style pack')
    parser.add_argument('--template', type=str, help='Remotion template ID')
    parser.add_argument('--engine', choices=['remotion', 'hyperframes'], default='remotion', help='local packaging renderer')
    parser.add_argument('--brief', type=Path, help='pre-authored shot brief JSON')
    parser.add_argument('--item', type=str, help='item ID to restore')
    parser.add_argument('--retry-item', type=str, help='failed B-roll item ID to retry')
    parser.add_argument('--undo-group', type=str, help='undoGroup to restore')
    parser.add_argument('--apply', action='store_true', help='apply safe boundaries, tightened pauses, or selected/restored takes into edit-plan.v1.json')
    parser.add_argument('--strict', action='store_true', help='fail validate if any boundary requires review or circuit breaker triggered')
    parser.add_argument('--threshold', type=float, default=0.35, help='pause detection threshold in seconds')
    parser.add_argument('--keep', type=float, default=0.25, help='pause duration to keep in seconds')
    parser.add_argument('--min-gain', type=float, default=0.10, help='minimum gain to perform pause cut')
    args = parser.parse_args()
    try:
        plan_path = args.input or args.plan or args.project / 'Rough/edit-plan.v1.json'
        plan = None
        if args.command != 'select-takes':
            journal_path = _transaction_journal_path(Path(plan_path))
            if journal_path.exists():
                raise ValueError(f'incomplete B-roll plan/manifest transaction: {journal_path}')
            plan = load_plan(plan_path)
        if args.command == 'plan':
            output = args.project / 'Rough/edit-plan.v1.json'
            output.parent.mkdir(parents=True, exist_ok=True)
            _safe_write_text(output, json.dumps(plan, ensure_ascii=False, indent=2))
        elif args.command == 'boundary-check':
            decisions = run_boundary_check(plan)
            rep_path = args.project / 'Rough/cut-boundary-report.json'
            rep = generate_boundary_report(decisions, rep_path)
            b_summary = rep['summary']
            if args.apply:
                # Apply safe_end with frame-level ripple shift and route reviewQueueItems
                modified = False
                fps = plan['fps']
                # 1. Update sourceEnd and reviewQueue
                for dec in decisions:
                    for item in plan['timeline']:
                        if item.get('id') == dec.get('id') and item['op'] == 'keep':
                            if dec['safe_end'] > item['sourceEnd']:
                                item['sourceEnd'] = dec['safe_end']
                                modified = True
                            if dec.get('reviewQueueItem'):
                                rq = plan.setdefault('reviewQueue', [])
                                if not any(x.get('id') == dec['id'] for x in rq):
                                    rq.append(dec['reviewQueueItem'])
                                modified = True
                # 2. Ripple shift on each track using frame-level discrete mathematics
                if modified:
                    tracks = set(item.get('track', 'A-roll Final') for item in plan['timeline'] if item['op'] == 'keep')
                    for track in tracks:
                        track_cursor_frames = 0
                        for item in plan['timeline']:
                            if item['op'] == 'keep' and item.get('track', 'A-roll Final') == track:
                                s_frame = frame(item['sourceStart'], fps)
                                e_frame = frame(item['sourceEnd'], fps)
                                dur_frames = e_frame - s_frame
                                t_frame = frame(item['targetStart'], fps)
                                if t_frame < track_cursor_frames:
                                    t_frame = track_cursor_frames
                                    item['targetStart'] = round(float(t_frame) / fps, 6)
                                track_cursor_frames = t_frame + dur_frames

                    # Save and reload to recalculate frames and planHash
                    out_plan = args.project / 'Rough/edit-plan.v1.json'
                    _safe_write_text(out_plan, json.dumps(plan, ensure_ascii=False, indent=2))
                    plan = load_plan(out_plan)
                    _safe_write_text(out_plan, json.dumps(plan, ensure_ascii=False, indent=2))
            review_req = b_summary.get('review_required', 0)
            status = 'review_required' if review_req > 0 else 'ok'
            print(json.dumps({'status': status, 'report': str(rep_path), 'summary': b_summary}))
            if review_req > 0 and not args.apply:
                return 1
            return 0
        elif args.command == 'tighten':
            words_file = args.project / 'Rough/subtitles_words.json'
            words_per_seg = {}
            if words_file.is_file():
                try:
                    words_data = json.loads(words_file.read_text(encoding='utf-8'))
                    speech_words = [w for w in words_data if not w.get('isGap')]
                    for item in plan['timeline']:
                        if item['op'] == 'keep':
                            s, e = item['sourceStart'], item['sourceEnd']
                            inside = [w for w in speech_words if w['start'] >= s - 1e-4 and w['end'] <= e + 1e-4]
                            if inside:
                                words_per_seg[item['id']] = inside
                except Exception:
                    pass

            tightened_plan, p_report = tighten_pauses(
                plan,
                threshold=args.threshold,
                keep=args.keep,
                min_gain=args.min_gain,
                words_per_segment=words_per_seg,
            )
            rep_path = args.project / 'Rough/pauses-report.json'
            generate_pauses_report(p_report, rep_path)
            if args.apply:
                out_plan = args.project / 'Rough/edit-plan.v1.json'
                _safe_write_text(out_plan, json.dumps(tightened_plan, ensure_ascii=False, indent=2))
                plan = load_plan(out_plan)
                _safe_write_text(out_plan, json.dumps(plan, ensure_ascii=False, indent=2))
            print(json.dumps({'status': 'ok', 'report': str(rep_path), 'summary': p_report['summary']}))
            return 0
        elif args.command == 'select-takes':
            takes_path = args.takes or (args.project / 'Rough/takes_decision.json')
            if not takes_path.is_file():
                raise ValueError(f"takes decision file not found: {takes_path}")
            takes_data = json.loads(takes_path.read_text(encoding='utf-8'))

            sources = {}
            fps = 25
            if plan_path.is_file():
                try:
                    existing_plan = load_plan(plan_path)
                    sources = existing_plan.get('sources', {})
                    fps = existing_plan.get('fps', 25)
                except Exception:
                    pass
            if not sources and 'sources' in takes_data:
                sources = takes_data['sources']
            if not sources:
                raw_files = list((args.project / 'Raw').glob('*.mp4')) + list((args.project / 'Raw').glob('*.mov')) + list(args.project.glob('*.mp4'))
                if raw_files:
                    sources = {'raw': {'path': str(raw_files[0].resolve()), 'duration': 1000.0}}
                else:
                    sources = {'raw': {'path': 'raw.mp4', 'duration': 1000.0}}

            new_plan, report = convert_takes_to_plan(takes_data, sources, fps=fps, project_root=str(args.project))
            rep_path = args.project / 'Rough/takes-selection-report.json'
            rep_path.parent.mkdir(parents=True, exist_ok=True)
            _safe_write_text(rep_path, json.dumps(report, indent=2, ensure_ascii=False))

            cb_result = evaluate_circuit_breaker(
                new_plan,
                total_sentences=report['summary']['total_sentences'],
                unmatched_sentences=report['summary']['unmatched_sentences']
            )
            cb_path = args.project / 'Rough/circuit-breaker.json'
            _safe_write_text(cb_path, json.dumps(cb_result, indent=2, ensure_ascii=False))

            if args.apply:
                out_plan = args.project / 'Rough/edit-plan.v1.json'
                out_plan.parent.mkdir(parents=True, exist_ok=True)
                _safe_write_text(out_plan, json.dumps(new_plan, indent=2, ensure_ascii=False))
                plan = load_plan(out_plan)
                _safe_write_text(out_plan, json.dumps(plan, indent=2, ensure_ascii=False))
            else:
                plan = new_plan

            if args.strict and cb_result['circuit_broken']:
                print(json.dumps({'status': 'circuit_broken', 'triggers': cb_result['triggers'], 'metrics': cb_result['metrics']}), file=sys.stderr)
                return 1

            print(json.dumps({
                'status': 'ok',
                'report': str(rep_path),
                'circuit_broken': cb_result['circuit_broken'],
                'summary': report['summary'],
                'planHash': plan.get('planHash')
            }))
            return 0
        elif args.command == 'restore':
            if not args.item and not args.undo_group:
                raise ValueError("either --item or --undo-group is required for restore")
            restored_plan, receipt = restore_take_in_plan(
                plan,
                item_id=args.item,
                undo_group=args.undo_group,
            )
            if args.apply:
                out_plan = args.project / 'Rough/edit-plan.v1.json'
                _safe_write_text(out_plan, json.dumps(restored_plan, indent=2, ensure_ascii=False))
                plan = load_plan(out_plan)
                _safe_write_text(out_plan, json.dumps(plan, indent=2, ensure_ascii=False))
                cb_path = args.project / 'Rough/circuit-breaker.json'
                if cb_path.is_file():
                    cb_path.unlink()
            else:
                plan = restored_plan
            print(json.dumps({
                'status': 'ok',
                'receipt': receipt,
                'durationFrames': plan['durationFrames'],
                'planHash': plan['planHash'],
            }))
            return 0
        elif args.command == 'insert-screen-demo':
            screen_path = args.screen or (args.project / 'Raw/obs-demo.mp4')
            if not screen_path.is_file():
                found = list((args.project / 'Raw').glob('*screen*.mp4')) + list((args.project / 'Raw').glob('*obs*.mp4'))
                if found:
                    screen_path = found[0]
                else:
                    raise ValueError(f"screen recording file not found: {screen_path}")
            markers_path = args.markers or (args.project / 'Rough/screen_markers.json')
            if not markers_path.is_file():
                raise ValueError(f"screen markers file not found: {markers_path}")
            markers = json.loads(markers_path.read_text(encoding='utf-8'))

            info = probe(screen_path)
            if not any(stream.get('codec_type') == 'video' for stream in info.get('streams', [])):
                raise ValueError(f"screen recording has no video stream: {screen_path}")

            screen_sid = "screen_demo_source"
            for sid, s in plan['sources'].items():
                if Path(s['path']).resolve() == screen_path.resolve():
                    screen_sid = sid
                    break
            else:
                plan['sources'][screen_sid] = {
                    'path': str(screen_path.resolve()),
                    'duration': float(info['format']['duration'])
                }

            # Auto-load words for word-level anchor alignment if available
            words_file = args.project / 'Rough/subtitles_words.json'
            words_per_seg = None
            if words_file.exists():
                try:
                    w_data = json.loads(words_file.read_text(encoding='utf-8'))
                    if isinstance(w_data, dict):
                        words_per_seg = w_data
                    elif isinstance(w_data, list):
                        words_per_seg = {}
                        for w in w_data:
                            sid = w.get('segment_id') or w.get('id')
                            if sid:
                                words_per_seg.setdefault(sid, []).append(w)
                except Exception:
                    pass

            updated_plan, manifest = match_screen_anchors(
                plan=plan,
                screen_source_id=screen_sid,
                markers=markers,
                words_per_segment=words_per_seg,
            )

            manifest_path = args.project / 'Polished/broll-manifest.v1.json'
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            _safe_write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))

            if args.apply:
                out_plan = args.project / 'Rough/edit-plan.v1.json'
                _safe_write_text(out_plan, json.dumps(updated_plan, indent=2, ensure_ascii=False))
                plan = load_plan(out_plan)
                _safe_write_text(out_plan, json.dumps(plan, indent=2, ensure_ascii=False))
            else:
                plan = updated_plan

            print(json.dumps({
                'status': 'ok',
                'manifest': str(manifest_path),
                'approved_demos': manifest['summary']['approved_count'],
                'pending_markers': manifest['summary']['pending_count'],
                'planHash': plan['planHash'],
            }))
            return 0
        elif args.command in ('insert-broll-packaging', 'retry-broll-item'):
            from lib.broll_narrative import generate_shot_brief

            manifest_path = args.project / 'Polished/broll-manifest.v1.json'
            manifest = load_broll_manifest(manifest_path)
            if manifest.get('planHash') not in (None, plan.get('planHash')):
                raise ValueError('B-roll manifest planHash does not match edit plan; reconcile before retrying')
            manifest['planHash'] = plan.get('planHash')

            # Locate target sentence in plan['timeline']
            target_sent = None
            if args.sentence:
                for it in plan['timeline']:
                    if it.get('id') == args.sentence:
                        if it.get('op') != 'keep':
                            raise ValueError(f"sentence '{args.sentence}' is not an active keep item (op={it.get('op')})")
                        target_sent = it
                        break
                if not target_sent:
                    raise ValueError(f"sentence '{args.sentence}' not found in plan timeline")
            else:
                keeps_items = [it for it in plan['timeline'] if it.get('op') == 'keep']
                if keeps_items:
                    target_sent = keeps_items[0]
                else:
                    raise ValueError("no keep sentence available in timeline")

            # Generate or load shot brief
            if args.command == 'retry-broll-item':
                if not args.retry_item:
                    raise ValueError('--retry-item is required')
                prior = next((entry for entry in manifest['items'] if entry.get('id') == args.retry_item), None)
                if not prior or prior.get('status') != 'failed' or not isinstance(prior.get('shot_brief'), dict):
                    raise ValueError('retry item must be a failed manifest item with a shot brief')
                brief = dict(prior['shot_brief'])
                args.engine = brief.get('engine')
            elif args.brief and args.brief.is_file():
                brief = json.loads(args.brief.read_text(encoding='utf-8'))
            else:
                brief = generate_shot_brief(
                    sentence=target_sent,
                    style_pack=args.style_pack,
                    template_id=args.template,
                    engine=args.engine,
                )

            # SEC-01 Sanitize brief ID
            raw_id = str(brief.get('id', ''))
            clean_id = Path(raw_id).name
            if not clean_id or not re.match(r'^[a-zA-Z0-9_-]+$', clean_id) or '..' in raw_id:
                raise ValueError(f"invalid or unsafe brief id: {raw_id}")
            brief['id'] = clean_id

            # Normalize the shared shot-brief contract for authored briefs as
            # well as generated ones.  Existing callers may provide only the
            # minimum renderer fields; these defaults preserve their timing
            # while making placement and provenance explicit in the manifest.
            sentence_id = brief.get('sentence_id') or (target_sent or {}).get('id')
            start = float(brief.get('target_start', (target_sent or {}).get('targetStart', 0.0)))
            duration = float(brief.get('duration', 0.0))
            brief.setdefault('anchor', (target_sent or {}).get('text', '')[:30])
            brief.setdefault('main_visual', {'type': 'narrative_process', 'description': brief.get('visual_intent', '')})
            brief.setdefault('composition', {'layout': 'split_frame_editorial', 'face_avoidance_zone': brief.get('face_avoidance_zone')})
            brief.setdefault('entrance', {'semantic': 'attention_reveal', 'duration': 0.45})
            brief.setdefault('exit', {'semantic': 'make_room', 'duration': 0.35})
            brief.setdefault('acceptance_frames', [0.0, 0.5, 0.96])
            brief.setdefault('source', {'type': 'a_roll_sentence', 'id': sentence_id})
            brief.setdefault('provenance', {'generator': 'authored_shot_brief', 'sentence_id': sentence_id})
            brief.setdefault('layer', 'B-roll Packaging')
            brief.setdefault('start', start)
            brief.setdefault('end', round(start + duration, 6))
            brief.setdefault('stylePack', brief.get('style_pack'))
            contract_template = get_template(str(brief.get('template_id', '')))
            if contract_template:
                brief.setdefault('transparency', contract_template['transparency'])
                brief.setdefault('overlay_mode', contract_template['overlay_mode'])

            if brief.get('engine') != args.engine:
                raise ValueError('brief engine does not match --engine')
            validate_shot_brief(brief, engine=args.engine)
            engine_out = args.project / 'Polished' / args.engine
            try:
                if args.engine == 'hyperframes':
                    from lib.broll_hyperframes import render_hyperframes_shot, verify_hyperframes_shot
                    render_res = render_hyperframes_shot(brief, out_dir=engine_out)
                    qa_res = verify_hyperframes_shot(render_res, brief)
                else:
                    from lib.broll_remotion import render_remotion_shot, verify_broll_shot
                    render_res = render_remotion_shot(brief, out_dir=engine_out)
                    qa_res = verify_broll_shot(render_res, brief)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                failure = {'id': f"{brief['id']}-render-failed", 'type': 'broll_render_failed', 'engine': args.engine,
                           'reason': str(error), 'shot_brief': brief, 'action': 'retry_this_item_only'}
                plan['reviewQueue'] = [item for item in plan.get('reviewQueue', []) if item.get('id') != failure['id']] + [failure]
                old = next((entry for entry in manifest['items'] if entry.get('id') == brief['id']), {})
                failed_entry = {
                    'id': brief['id'], 'route': 'packaging', 'engine': args.engine,
                    'template_id': brief.get('template_id'), 'style_pack': brief.get('style_pack'),
                    'stylePack': brief.get('stylePack', brief.get('style_pack')), 'anchor': brief.get('anchor'),
                    'start': brief.get('start'), 'end': brief.get('end'), 'layer': brief.get('layer'),
                    'source': brief.get('source'), 'provenance': brief.get('provenance'),
                    'main_visual': brief.get('main_visual'), 'composition': brief.get('composition'),
                    'entrance': brief.get('entrance'), 'exit': brief.get('exit'),
                    'acceptance_frames': brief.get('acceptance_frames'),
                    'transparency': brief.get('transparency'), 'overlay_mode': brief.get('overlay_mode'),
                    'shot_brief': brief, 'status': 'failed', 'attempt': int(old.get('attempt', 0)) + 1,
                    'error': str(error), 'action': 'retry_this_item_only',
                }
                prior_video = old.get('video_path')
                if old and prior_video and Path(prior_video).is_file():
                    # Preserve the last known-good segment in sync with the
                    # edit plan and append the failed attempt separately.
                    failed_entry['id'] = f"{brief['id']}-attempt-{failed_entry['attempt']}"
                    preserved = dict(old, last_error=str(error), last_failed_attempt=failed_entry['id'])
                    manifest['items'] = [entry for entry in manifest['items'] if entry.get('id') != brief['id']] + [preserved, failed_entry]
                else:
                    manifest['items'] = [entry for entry in manifest['items'] if entry.get('id') != brief['id']] + [failed_entry]
                manifest['summary'] = summarize_broll_manifest(manifest['items'])
                if args.apply:
                    out_plan = args.project / 'Rough/edit-plan.v1.json'
                    plan = _publish_plan_and_manifest(out_plan, plan, manifest_path, manifest)
                else:
                    write_broll_manifest(manifest_path, manifest)
                print(json.dumps({'status': 'render_failed', 'engine': args.engine, 'reason': str(error)}))
                return 0
            rq_fail_id = f"{brief['id']}-qa-failed"
            if qa_res.get('status') != 'passed':
                rq_item = {
                    'id': rq_fail_id,
                    'type': 'broll_qa_rejected',
                    'reason': qa_res.get('reason', 'unknown_qa_failure'),
                    'shot_brief': brief,
                    'action': 'hold_and_review'
                }
                # STATE-01 Clean existing and recalculate hash
                plan['reviewQueue'] = [rq for rq in plan.get('reviewQueue', []) if rq.get('id') != rq_fail_id]
                plan['reviewQueue'].append(rq_item)
                old = next((entry for entry in manifest['items'] if entry.get('id') == brief['id']), {})
                failed_item = {
                    'id': brief['id'], 'route': 'packaging', 'engine': args.engine,
                    'template_id': brief.get('template_id'), 'style_pack': brief.get('style_pack'),
                    'stylePack': brief.get('stylePack', brief.get('style_pack')), 'anchor': brief.get('anchor'),
                    'start': brief.get('start'), 'end': brief.get('end'), 'layer': brief.get('layer'),
                    'source': brief.get('source'), 'provenance': brief.get('provenance'),
                    'main_visual': brief.get('main_visual'), 'composition': brief.get('composition'),
                    'entrance': brief.get('entrance'), 'exit': brief.get('exit'),
                    'acceptance_frames': brief.get('acceptance_frames'),
                    'transparency': brief.get('transparency'), 'overlay_mode': brief.get('overlay_mode'),
                    'shot_brief': brief, 'status': 'failed',
                    'attempt': int(old.get('attempt', 0)) + 1,
                    'error': qa_res.get('reason', 'qa_rejected'), 'action': 'retry_this_item_only',
                }
                manifest['items'] = [entry for entry in manifest['items'] if entry.get('id') != brief['id']] + [failed_item]
                manifest['summary'] = summarize_broll_manifest(manifest['items'])
                if args.apply:
                    out_plan = args.project / 'Rough/edit-plan.v1.json'
                    plan = _publish_plan_and_manifest(out_plan, plan, manifest_path, manifest)
                else:
                    write_broll_manifest(manifest_path, manifest)
                print(json.dumps({'status': 'qa_rejected', 'reason': qa_res.get('reason')}))
                return 0

            # STATE-01 On success, clean up prior QA failure entry for this shot
            plan['reviewQueue'] = [rq for rq in plan.get('reviewQueue', []) if rq.get('id') != rq_fail_id]

            # Register source in plan['sources']
            broll_video = Path(render_res['video_path']).resolve()
            source_id = f"broll_src_{brief['id']}"
            plan['sources'][source_id] = {
                'path': str(broll_video),
                'duration': float(render_res['duration'])
            }

            # Compute discrete frames
            fps = plan['fps']
            s_dur = float(render_res['duration'])
            t_start_f = frame(float(brief['target_start']), fps)
            dur_f = frame(s_dur, fps)

            # Remove prior packaging items on this shot id if any (idempotence)
            updated_timeline = [
                it for it in plan['timeline']
                if not (it.get('op') == 'insert_broll_packaging' and it.get('id') == brief['id'])
            ]

            broll_timeline_item = {
                'id': brief['id'],
                'op': 'insert_broll_packaging',
                'sourceId': source_id,
                'sourceStart': 0.0,
                'sourceEnd': round(dur_f / fps, 6),
                'targetStart': round(t_start_f / fps, 6),
                'track': 'B-roll Packaging',
                'stylePack': brief['style_pack'],
                'overlayMode': brief.get('overlay_mode', 'full_frame'),
                'engine': args.engine,
                'sourceStartFrame': 0,
                'sourceEndFrame': dur_f,
                'durationFrames': dur_f,
                'targetStartFrame': t_start_f,
            }
            updated_timeline.append(broll_timeline_item)

            # VIS-01 Stacking order: B-roll Packaging overlays on top of Screen Demo
            def _timeline_sort(it):
                t_name = it.get('track', 'A-roll Final')
                order = {'A-roll Final': 0, 'Screen Demo': 1, 'B-roll Packaging': 2, 'A-roll Recovery': 3}
                return (order.get(t_name, 9), it.get('targetStartFrame', 0))
            updated_timeline.sort(key=_timeline_sort)
            plan['timeline'] = updated_timeline

            # Update or create broll-manifest
            manifest_items = [it for it in manifest.get('items', []) if it.get('id') != brief['id']]
            prior_item = next((it for it in manifest.get('items', []) if it.get('id') == brief['id']), None)
            engine_change = None
            if prior_item and prior_item.get('engine') != args.engine:
                engine_change = {
                    'from_engine': prior_item.get('engine'), 'to_engine': args.engine,
                    'from_template': prior_item.get('template_id'), 'to_template': brief['template_id'],
                    'reason': 'explicit packaging engine replacement; visual output requires review',
                    'capability_delta': {
                        'transparency': [prior_item.get('transparency'), brief.get('transparency')],
                        'overlay_mode': [prior_item.get('overlay_mode'), brief.get('overlay_mode')],
                        'renderer': [prior_item.get('engine'), args.engine],
                    },
                }
                plan['reviewQueue'] = [rq for rq in plan.get('reviewQueue', []) if rq.get('id') != f"{brief['id']}-engine-change"]
                plan['reviewQueue'].append({
                    'id': f"{brief['id']}-engine-change", 'type': 'broll_engine_change',
                    'engine_change': engine_change, 'action': 'hold_and_review',
                })
            manifest_items.append({
                'id': brief['id'],
                'route': 'packaging',
                'engine': args.engine,
                'template_id': brief['template_id'],
                'style_pack': brief['style_pack'],
                'stylePack': brief.get('stylePack', brief['style_pack']),
                'anchor': brief.get('anchor'),
                'start': broll_timeline_item['targetStart'],
                'end': round(broll_timeline_item['targetStart'] + broll_timeline_item['durationFrames'] / fps, 6),
                'layer': brief.get('layer', 'B-roll Packaging'),
                'source': brief.get('source'),
                'provenance': brief.get('provenance'),
                'main_visual': brief.get('main_visual'),
                'composition': brief.get('composition'),
                'entrance': brief.get('entrance'),
                'exit': brief.get('exit'),
                'acceptance_frames': brief.get('acceptance_frames'),
                'target_start': broll_timeline_item['targetStart'],
                'duration': s_dur,
                'status': 'needs_review' if engine_change else 'approved',
                'video_path': str(broll_video),
                'source_path': render_res.get('source_path'),
                'engine_change': engine_change,
                'transparency': brief.get('transparency'),
                'overlay_mode': brief.get('overlay_mode'),
                'receipt_path': render_res.get('receipt_path'),
                'shot_brief': brief,
                'attempt': int((prior_item or {}).get('attempt', 0)) + 1,
                'error': None,
            })
            manifest['items'] = manifest_items
            manifest['summary'] = summarize_broll_manifest(manifest_items)
            if args.apply:
                out_plan = args.project / 'Rough/edit-plan.v1.json'
                plan = _publish_plan_and_manifest(out_plan, plan, manifest_path, manifest)
            else:
                write_broll_manifest(manifest_path, manifest)

            print(json.dumps({
                'status': 'ok',
                'shot_id': brief['id'],
                'video_path': str(broll_video),
                'manifest': str(manifest_path),
                'planHash': plan['planHash'],
            }))
            return 0
        elif args.command == 'insert-broll-ai-visual':
            from lib.broll_ai_visual import generate_ai_visual_shot, resolve_ai_visual_budget, verify_ai_visual_shot

            manifest_path = args.project / 'Polished/broll-manifest.v1.json'
            manifest = load_broll_manifest(manifest_path)
            if manifest.get('planHash') not in (None, plan.get('planHash')):
                raise ValueError('B-roll manifest planHash does not match edit plan; reconcile before retrying')
            manifest['planHash'] = plan.get('planHash')

            # Locate target sentence in plan['timeline']
            target_sent = None
            if args.sentence:
                for it in plan['timeline']:
                    if it.get('id') == args.sentence:
                        if it.get('op') != 'keep':
                            raise ValueError(f"sentence '{args.sentence}' is not an active keep item (op={it.get('op')})")
                        target_sent = it
                        break
                if not target_sent:
                    raise ValueError(f"sentence '{args.sentence}' not found in plan timeline")
            else:
                keeps_items = [it for it in plan['timeline'] if it.get('op') == 'keep']
                if keeps_items:
                    target_sent = keeps_items[0]
                else:
                    raise ValueError("no keep sentence available in timeline")

            if args.brief and args.brief.is_file():
                brief = json.loads(args.brief.read_text(encoding='utf-8'))
            else:
                # Default AI Visual brief based on target sentence
                sent_text = (target_sent or {}).get('text', '')
                sent_dur = float((target_sent or {}).get('durationFrames', 75)) / plan['fps']
                shot_dur = round(max(2.0, min(8.0, sent_dur)), 2)
                brief = {
                    'id': f"ai_shot_{target_sent['id']}",
                    'engine': 'ai_visual',
                    'template_id': args.template or 'ai-visual-vox-metaphor',
                    'style_pack': args.style_pack,
                    'prompt': f"Conceptual visual metaphor for: {sent_text}",
                    'target_start': float(target_sent.get('targetStart', 0.0)),
                    'duration': shot_dur,
                    'fps': plan['fps'],
                    'transparency': 'opaque',
                    'overlay_mode': 'full_frame',
                    'props': {
                        'prompt': f"Conceptual visual metaphor for: {sent_text}",
                        'provider': 'gemini',
                    }
                }

            # Sanitize brief ID
            raw_id = str(brief.get('id', ''))
            clean_id = Path(raw_id).name
            if not clean_id or not re.match(r'^[a-zA-Z0-9_-]+$', clean_id) or '..' in raw_id:
                raise ValueError(f"invalid or unsafe brief id: {raw_id}")
            brief['id'] = clean_id

            # Parse budget & check credentials
            budget = resolve_ai_visual_budget(brief)
            ai_out = args.project / 'Polished/ai_visual'
            gen_res = generate_ai_visual_shot(brief, out_dir=ai_out, budget_spec=budget)

            if gen_res.get('status') == 'pending_credentials':
                # Route to reviewQueue
                rq_item = {
                    'id': f"{brief['id']}-pending-credentials",
                    'type': 'ai_visual_pending_credentials',
                    'reason': gen_res.get('reason'),
                    'shot_brief': brief,
                    'prompt_package': gen_res.get('prompt_package'),
                    'action': 'provide_api_key_or_skip'
                }
                plan['reviewQueue'] = [rq for rq in plan.get('reviewQueue', []) if rq.get('id') != rq_item['id']]
                plan['reviewQueue'].append(rq_item)
                if args.apply:
                    out_plan = args.project / 'Rough/edit-plan.v1.json'
                    plan = _publish_plan_and_manifest(out_plan, plan, manifest_path, manifest)
                print(json.dumps({'status': 'pending_credentials', 'reason': gen_res.get('reason')}))
                return 0

            # QA Verification
            qa_res = verify_ai_visual_shot(gen_res, brief)
            rq_fail_id = f"{brief['id']}-qa-failed"
            if qa_res.get('status') != 'passed':
                rq_item = {
                    'id': rq_fail_id,
                    'type': 'ai_visual_qa_rejected',
                    'reason': qa_res.get('reason', 'unknown_qa_failure'),
                    'shot_brief': brief,
                    'action': 'hold_and_review'
                }
                plan['reviewQueue'] = [rq for rq in plan.get('reviewQueue', []) if rq.get('id') != rq_fail_id]
                plan['reviewQueue'].append(rq_item)
                if args.apply:
                    out_plan = args.project / 'Rough/edit-plan.v1.json'
                    plan = _publish_plan_and_manifest(out_plan, plan, manifest_path, manifest)
                print(json.dumps({'status': 'qa_rejected', 'reason': qa_res.get('reason')}))
                return 0

            # Register source and timeline item
            ai_video = Path(gen_res['video_path']).resolve()
            source_id = f"ai_visual_src_{brief['id']}"
            plan['sources'][source_id] = {
                'path': str(ai_video),
                'duration': float(gen_res['duration'])
            }

            fps = plan['fps']
            s_dur = float(gen_res['duration'])
            t_start_f = frame(float(brief['target_start']), fps)
            dur_f = frame(s_dur, fps)

            updated_timeline = [
                it for it in plan['timeline']
                if not (it.get('op') == 'insert_broll_ai_visual' and it.get('id') == brief['id'])
            ]
            ai_timeline_item = {
                'id': brief['id'],
                'op': 'insert_broll_ai_visual',
                'sourceId': source_id,
                'sourceStart': 0.0,
                'sourceEnd': round(dur_f / fps, 6),
                'targetStart': round(t_start_f / fps, 6),
                'track': 'B-roll AI Visual',
                'stylePack': brief['style_pack'],
                'overlayMode': brief.get('overlay_mode', 'full_frame'),
                'engine': 'ai_visual',
                'sourceStartFrame': 0,
                'sourceEndFrame': dur_f,
                'durationFrames': dur_f,
                'targetStartFrame': t_start_f,
            }
            updated_timeline.append(ai_timeline_item)

            def _timeline_sort(it):
                t_name = it.get('track', 'A-roll Final')
                order = {'A-roll Final': 0, 'Screen Demo': 1, 'B-roll Packaging': 2, 'B-roll AI Visual': 3, 'A-roll Recovery': 4}
                return (order.get(t_name, 9), it.get('targetStartFrame', 0))
            updated_timeline.sort(key=_timeline_sort)
            plan['timeline'] = updated_timeline

            manifest_items = [it for it in manifest.get('items', []) if it.get('id') != brief['id']]
            manifest_items.append({
                'id': brief['id'],
                'route': 'ai_visual',
                'engine': 'ai_visual',
                'template_id': brief.get('template_id', 'ai-visual-vox-metaphor'),
                'style_pack': brief['style_pack'],
                'target_start': ai_timeline_item['targetStart'],
                'duration': s_dur,
                'status': 'approved',
                'video_path': str(ai_video),
                'receipt_path': gen_res.get('receipt_path'),
                'shot_brief': brief,
            })
            manifest['items'] = manifest_items
            manifest['summary'] = summarize_broll_manifest(manifest_items)

            if args.apply:
                out_plan = args.project / 'Rough/edit-plan.v1.json'
                plan = _publish_plan_and_manifest(out_plan, plan, manifest_path, manifest)
            else:
                write_broll_manifest(manifest_path, manifest)

            print(json.dumps({
                'status': 'ok',
                'shot_id': brief['id'],
                'video_path': str(ai_video),
                'manifest': str(manifest_path),
                'planHash': plan['planHash'],
            }))
            return 0
        elif args.command == 'validate':
            decisions = run_boundary_check(plan)
            rep_path = args.project / 'Rough/cut-boundary-report.json'
            b_summary = {}
            review_req = 0
            if decisions:
                rep = generate_boundary_report(decisions, rep_path)
                b_summary = rep['summary']
                review_req = b_summary.get('review_required', 0)
            pauses_summary = {}
            p_rep_path = args.project / 'Rough/pauses-report.json'
            if p_rep_path.is_file():
                try:
                    pauses_summary = json.loads(p_rep_path.read_text(encoding='utf-8')).get('summary', {})
                except Exception:
                    pass

            cb_summary = {}
            cb_path = args.project / 'Rough/circuit-breaker.json'
            if cb_path.is_file():
                try:
                    loaded_cb = json.loads(cb_path.read_text(encoding='utf-8'))
                    if loaded_cb.get('planHash') == plan.get('planHash'):
                        cb_summary = loaded_cb
                except Exception:
                    pass
            if not cb_summary:
                total_s = None
                unmatched_s = None
                rep_sel_path = args.project / 'Rough/takes-selection-report.json'
                if rep_sel_path.is_file():
                    try:
                        rep_sel_data = json.loads(rep_sel_path.read_text(encoding='utf-8'))
                        total_s = rep_sel_data.get('summary', {}).get('total_sentences')
                        unmatched_s = rep_sel_data.get('summary', {}).get('unmatched_sentences')
                    except Exception:
                        pass
                cb_summary = evaluate_circuit_breaker(plan, total_sentences=total_s, unmatched_sentences=unmatched_s)
                cb_path.parent.mkdir(parents=True, exist_ok=True)
                _safe_write_text(cb_path, json.dumps(cb_summary, indent=2, ensure_ascii=False))

            has_rq = len(plan.get('reviewQueue', [])) > 0
            circuit_broken = cb_summary.get('circuit_broken', False)
            status = 'circuit_broken' if circuit_broken else ('review_required' if (review_req > 0 or pauses_summary.get('pauses_flagged_review', 0) > 0 or has_rq) else 'ok')
            val_result = {
                'status': status,
                'planHash': plan['planHash'],
                'durationFrames': plan['durationFrames'],
                'boundaryCheck': b_summary,
                'pausesCheck': pauses_summary,
                'circuitBreaker': cb_summary,
            }
            val_file = args.project / 'Rough/auto-cut-validation.json'
            val_file.parent.mkdir(parents=True, exist_ok=True)
            _safe_write_text(val_file, json.dumps(val_result, indent=2, ensure_ascii=False))
            report_file = args.project / 'Rough/auto-cut-report.md'
            keeps_count = len([x for x in plan['timeline'] if x.get('op') == 'keep'])
            removes_count = len([x for x in plan['timeline'] if x.get('op') == 'remove'])
            p_line = (
                f"- Pause Tightening: {pauses_summary.get('total_pauses_cut', 0)} cut "
                f"({pauses_summary.get('seconds_removed', 0.0):.2f}s removed), "
                f"{pauses_summary.get('pauses_flagged_review', 0)} review required\n"
                if pauses_summary else ""
            )
            cb_line = ""
            if cb_summary:
                m = cb_summary.get('metrics', {})
                del_m = m.get('deletion', {})
                unm_m = m.get('unmatched_manuscript', {})
                hr_m = m.get('high_risk', {})
                cb_line = (
                    f"- Circuit Breaker: {'TRIGGERED' if circuit_broken else 'OK'}\n"
                    f"  - Deletion: {del_m.get('actual', 0.0)*100:.1f}% (threshold {del_m.get('threshold', 0.35)*100:.1f}%, "
                    f"removed {del_m.get('removed_s', 0.0)}s / source {del_m.get('source_s', 0.0)}s)\n"
                    f"  - Unmatched Manuscript: {unm_m.get('actual', 0.0)*100:.1f}% (threshold {unm_m.get('threshold', 0.05)*100:.1f}%, "
                    f"unmatched {unm_m.get('unmatched', 0)} / total {unm_m.get('total', 0)})\n"
                    f"  - High Risk Items: {hr_m.get('actual', 0)} (threshold {hr_m.get('threshold', 3)})\n"
                )
            report_content = (
                f"# Auto-Cut Report\n\n"
                f"- Plan Hash: `{plan['planHash']}`\n"
                f"- Duration: {plan['durationFrames']} frames ({plan['durationFrames']/plan['fps']:.2f}s)\n"
                f"- Keeps: {keeps_count}\n"
                f"- Removes: {removes_count}\n"
                f"- Review Queue: {len(plan.get('reviewQueue', []))}\n"
                f"- Boundary Protection: {b_summary.get('approved', 0)} approved, {review_req} review required\n"
                f"{p_line}"
                f"{cb_line}"
            )
            _safe_write_text(report_file, report_content)
            if (circuit_broken or review_req > 0 or pauses_summary.get('pauses_flagged_review', 0) > 0 or has_rq) and args.strict:
                print(json.dumps(val_result), file=sys.stderr)
                return 1
        elif args.command == 'subtitles':
            from lib.draft_reconcile import rebuild_subtitles_for_plan
            rebuild_subtitles_for_plan(plan, args.project / 'Rough/auto-cut.srt')
        elif args.command == 'preview':
            preview(plan, args.project / 'Rough/auto-cut-preview.mp4')
        elif args.command == 'verify-draft':
            if not args.draft:
                raise ValueError('--draft is required')
            print(json.dumps(verify_draft(plan, args.draft)))
            return 0
        elif args.command == 'reconcile':
            if not args.draft:
                raise ValueError('--draft is required for reconcile')
            from lib.draft_reconcile import (
                reconcile_plan_from_draft,
                realign_broll_manifest,
                rebuild_subtitles_for_plan,
                check_subtitles_compatible,
                audit_broll_manifest,
            )
            reconciled_plan = reconcile_plan_from_draft(plan, args.draft)
            manifest_path = args.project / 'Polished/broll-manifest.v1.json'
            if not manifest_path.is_file():
                alt = args.project / 'Rough/broll-manifest.json'
                if alt.is_file():
                    manifest_path = alt
            realigned_manifest = None
            audit_issues = []
            if manifest_path.is_file():
                manifest = load_broll_manifest(manifest_path)
                realigned_manifest, reconciled_plan = realign_broll_manifest(manifest, reconciled_plan)
                realigned_manifest, audit_issues = audit_broll_manifest(realigned_manifest)

            if args.apply:
                out_plan = args.project / 'Rough/edit-plan.v1.json'
                if realigned_manifest is not None:
                    reconciled_plan = _publish_plan_and_manifest(out_plan, reconciled_plan, manifest_path, realigned_manifest)
                else:
                    _safe_write_text(out_plan, json.dumps(reconciled_plan, indent=2, ensure_ascii=False))
                    reconciled_plan = load_plan(out_plan)
                    _safe_write_text(out_plan, json.dumps(reconciled_plan, indent=2, ensure_ascii=False))

            srt_path = args.project / 'Rough/auto-cut.srt'
            is_compat = False
            if srt_path.is_file():
                is_compat, _ = check_subtitles_compatible(srt_path, reconciled_plan)
            if not is_compat:
                rebuild_subtitles_for_plan(reconciled_plan, srt_path)

            orphaned_count = len([x for x in reconciled_plan.get('reviewQueue', []) if x.get('type') == 'broll_anchor_orphaned'])
            res = {
                'status': 'ok',
                'planHash': reconciled_plan['planHash'],
                'durationFrames': reconciled_plan['durationFrames'],
                'orphaned_broll_count': orphaned_count,
                'audit_issues': audit_issues,
            }
            print(json.dumps(res))
            return 0
        print(json.dumps({'status': 'ok', 'planHash': plan['planHash'], 'durationFrames': plan['durationFrames']}))
    except subprocess.CalledProcessError as error:
        err = error.stderr.decode('utf-8', errors='replace') if isinstance(error.stderr, bytes) else (error.stderr or str(error))
        print(json.dumps({'status': 'error', 'error': err.strip()}), file=sys.stderr)
        return 1
    except (ValueError, KeyError, TypeError, OSError, AttributeError) as error:
        print(json.dumps({'status': 'error', 'error': str(error)}), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
