"""Generate a Wondershare Filmora project file from EDL.

Reads an EDL (Edit Decision List) and generates a .wfpx project file
that can be opened directly in Wondershare Filmora.

Usage:
    python scripts/video-rough-cut/generate_filmora_project.py <edl.json> -o project.wfpx
    python scripts/video-rough-cut/generate_filmora_project.py <edl.json> -o project.wfpx --name "My Project"
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any


TIME_UNIT = 10_000_000  # 100 nanoseconds per second
FALLBACK_TEMPLATE_FOLDER = Path(__file__).resolve().parent / "templates" / "filmora" / "ProjectFolder"


def generate_uuid() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


def seconds_to_100ns(seconds: float) -> int:
    return int(seconds * TIME_UNIT)


def resolve_template_folder(edl_path: Path, template_folder: Path | None) -> Path:
    if template_folder:
        return template_folder.resolve()

    for candidate_root in [edl_path.parent, *edl_path.parents]:
        candidate = candidate_root / "ProjectFolder"
        if candidate.is_dir():
            return candidate.resolve()

    return FALLBACK_TEMPLATE_FOLDER


def resolve_source_path(source_path: str, edl_dir: Path) -> Path:
    """Resolve EDL sources relative to Rough/ or the project root."""
    path = Path(source_path)
    if path.is_absolute():
        return path.resolve()

    candidates = [edl_dir / path, edl_dir.parent / path, Path.cwd() / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def get_video_info(video_path: Path) -> dict:
    import subprocess
    
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    info = json.loads(result.stdout)
    
    video_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    
    duration = float(info.get("format", {}).get("duration", 0))
    
    width = int(video_stream.get("width", 1920)) if video_stream else 1920
    height = int(video_stream.get("height", 1080)) if video_stream else 1080
    
    fps_num = 30
    fps_den = 1
    if video_stream and "r_frame_rate" in video_stream:
        fps_str = video_stream["r_frame_rate"]
        if "/" in fps_str:
            parts = fps_str.split("/")
            fps_num = int(parts[0])
            fps_den = int(parts[1])
    
    sample_rate = int(audio_stream.get("sample_rate", 48000)) if audio_stream else 48000
    
    return {
        "duration": duration,
        "width": width,
        "height": height,
        "fps_num": fps_num,
        "fps_den": fps_den,
        "sample_rate": sample_rate,
    }


def build_resource_entry(video_path: Path, video_info: dict) -> dict:
    file_uri = f"file:/{video_path.as_posix()}"
    source_uuid = str(uuid.uuid4())
    
    duration_100ns = seconds_to_100ns(video_info["duration"])
    
    resource = {
        "AIGCMeta": {"data": "", "size": 0},
        "audStreamInfo": [{
            "audLang": "",
            "audStreamId": 0,
            "bitDepth": 16,
            "bitRate": 128000,
            "bytesPerSecond": 16000,
            "channels": 2,
            "description": "Advanced Audio Codec",
            "duration": video_info["duration"],
            "fourCC": 541278529,
            "layout": 0,
            "sampleRate": video_info["sample_rate"],
            "streamLength": duration_100ns,
        }],
        "audioStreamCount": 1,
        "bitRate": 5000000,
        "createDate": 0,
        "filename": file_uri,
        "fourCC": 540299341,
        "mediaLength": duration_100ns,
        "modifyDate": 0,
        "programCount": 1,
        "sourceUuid": source_uuid,
        "streamType": 2,
        "subPicStreamCount": 0,
        "videoStreamCount": 1,
        "vidStreamInfo": [{
            "ViewsCount": 0,
            "alphaChannel": 0,
            "bitRate": 5000000,
            "bitsDepth": 24,
            "cameraMaker": "None",
            "cameraModel": "None",
            "colorChromesubsampling": 0,
            "colorPrimary": 0,
            "colorRange": 0,
            "colorSpace": 0,
            "colorSpaceSource": 0,
            "exposureTime": 0.0,
            "flipType": 0,
            "fourCC": 875967048,
            "frameRate": {"den": video_info["fps_den"], "num": video_info["fps_num"]},
            "gpsLatitude": 0.0,
            "gpsLongitude": 0.0,
            "height": video_info["height"],
            "isDolbyVision": 0,
            "lastframeRate": {"den": video_info["fps_den"], "num": video_info["fps_num"]},
            "maxFrameRate": {"den": video_info["fps_den"] * 100, "num": video_info["fps_num"] * 100},
            "maxGopSize": 30,
            "premultiAlphaTypePhoto": -1,
            "rotation": 0,
            "startTimestamp": 0,
            "streamId": 0,
            "streamLength": duration_100ns,
            "timestampOffset": 0,
            "totalFrames": int(video_info["duration"] * video_info["fps_num"] / video_info["fps_den"]),
            "transferCharacteristics": 0,
            "videoScanType": 2,
            "width": video_info["width"],
            "xRatio": video_info["width"],
            "yRatio": video_info["height"],
        }],
    }
    
    return resource, source_uuid


def build_clip_entry(
    source_uuid: str,
    in_point: float,
    out_point: float,
    tl_begin: float,
    tl_end: float,
    clip_type: int = 2,
) -> dict:
    return {
        "CacheAlg": [
            {
                "cache_mode": 0,
                "id": "WindDenoiseCache",
                "params": [
                    {
                        "fxParam": {"paramType": 5, "unValue": 100},
                        "name": "WindDenoiseRatio"
                    }
                ],
                "status": 1,
                "version": 1
            }
        ],
        "audioDuckingframe": {
            "parameter": '{"Version": 2,"ParameterType": 0,"keyframeSets": [],"MD5":"d41d8cd98f00b204e9800998ecf8427e"}'
        },
        "audio_cloud_algorithm": {
            "info": [{"type": "audio"}],
            "version": 1
        },
        "denoiseV3Strength": 50.0,
        "effectChainList": [
            {"effectList": [], "name": "Basic"},
            {"effectList": [], "name": "Effect"},
            {"effectList": [], "name": "_wes_hold_effectchain_"}
        ],
        "filename": "",
        "inPoint": seconds_to_100ns(in_point),
        "outPoint": seconds_to_100ns(out_point),
        "sourceUuid": source_uuid,
        "speed": {
            "offset": 0.0,
            "offsetEnd": out_point - in_point,
            "reverse": False,
            "speedParam": '{"Version": 2,"ParameterType": 0,"keyframeSets": [{"_time": 0.0,"Interpolation": 6,"_value": 1.0}],"MD5": "71bd40df43914650e82f103348704572","_totalTime": ' + str(out_point - in_point) + '}'
        },
        "streamId": 0,
        "thisUId": generate_uuid(),
        "tlBegin": seconds_to_100ns(tl_begin),
        "tlEnd": seconds_to_100ns(tl_end),
        "type": clip_type,
        "userData": [
            {"data": "AAAAAA==", "key": 102, "size": 4},
            {"data": "JQAAAA==", "key": 6, "size": 4},
            {"data": "cXVpY2tNb2Rl", "key": 30304, "size": 9},
            {"data": "BAAAAA==", "key": 103, "size": 4},
            {"data": generate_uuid(), "key": 10, "size": 38},
            {"data": "AAAAAA==", "key": 2, "size": 4},
            {"data": generate_uuid(), "key": 3, "size": 64},
            {"data": "AgAAAA==", "key": 1, "size": 4},
            {"data": "8v///w==", "key": 30307, "size": 4}
        ],
        "volumeKeyframe": {
            "parameter": '{"Version": 2,"ParameterType": 0,"keyframeSets": [],"MD5":"d41d8cd98f00b204e9800998ecf8427e"}'
        },
    }


def build_timeline_wesproj(
    resources: list[dict],
    clip_lists: list[list[dict]],
    project_name: str,
    width: int,
    height: int,
    fps_num: int,
    fps_den: int,
    sample_rate: int,
) -> dict:
    timeline_id = 1
    
    track_infos = []
    # Filmora uses trackType=1 for video tracks and trackType=2 for audio tracks.
    track_type_map = {0: 1, 1: 2}
    for i, clips in enumerate(clip_lists):
        track_infos.append({
            "busUuids": [generate_uuid()],
            "clipList": clips,
            "trackType": track_type_map.get(i, 2),
            "userData": [
                {"data": "MAAAAA==", "key": 12000, "size": 4},
                {"data": "5Y+j5pKt", "key": 50, "size": 6}
            ],
            "uuid": generate_uuid(),
        })
    
    return {
        "currentTimelineId": timeline_id,
        "productName": "Filmora",
        "projectName": project_name,
        "projectVersion": "6, 8, 101, 2",
        "resources": resources,
        "serialNumber": 0,
        "serializationVersion": 1,
        "timelineInfos": [{
            "aspectRatioX": width,
            "aspectRatioY": height,
            "audioBusInfos": [{
                "busType": 0,
                "uuid": generate_uuid(),
            }],
            "channels": 2,
            "format": 0,
            "frameRate": {"den": fps_den, "num": fps_num},
            "hdrMode": 0,
            "hdrMode_force_16bit": False,
            "resolutionHeight": height,
            "resolutionWidth": width,
            "sampleRate": sample_rate,
            "timelineId": timeline_id,
            "trackInfos": track_infos,
            "type": 0,
            "userData": "",
        }],
    }


def build_project_info(
    project_name: str,
    width: int,
    height: int,
    fps_num: int,
    fps_den: int,
    sample_rate: int,
    timeline_media_id: str,
    total_duration: float,
) -> dict:
    from math import gcd
    g = gcd(width, height)
    ratio_x = width // g
    ratio_y = height // g
    
    return {
        "vbl_modify_version": "8.1.1.1",
        "vbl_create_version": "8.1.1.1",
        "project_os_name": "Windows",
        "project_os_version": "",
        "project_file_name": project_name,
        "project_file_suffix": ".wfpx",
        "project_editor_name": "MiaoYing",
        "project_editor_create_version": "15.1.2.17052",
        "project_editor_modify_version": "15.1.2.17052",
        "project_date_create": 0,
        "project_date_modify": 0,
        "project_timeline_duration": seconds_to_100ns(total_duration),
        "project_current_position": 0,
        "project_timeline_framerate": [fps_num, fps_den],
        "project_timeline_resolution": [width, height],
        "project_timeline_ratio": [ratio_x, ratio_y],
        "project_color_space": 0,
        "project_sample_rate": sample_rate,
        "project_audio_bitdepth": 1,
        "project_player_quality": 0,
        "project_player_zoom_level": 0,
        "project_player_safe_zone": False,
        "project_archive": False,
        "project_storage": True,
        "project_backup": False,
        "project_cover": False,
        "project_custom_cover": False,
        "project_type": 0,
        "project_template_name": "",
        "timeline_mediaId": timeline_media_id,
        "project_guid": generate_uuid(),
        "proj_zip_save_path": "",
        "proj_cover_proj_path": "",
        "nSizeRatioType": 0,
        "project_used_pack_list": [],
        "user_data": [{"key": 1, "data": "1"}, {"key": 2, "data": ""}],
    }


def build_medias_info(media_ids: list[str], timeline_media_id: str) -> str:
    entries = [f'"media_item":"{timeline_media_id}"']
    entries.extend(f'"media_item":"{mid}"' for mid in media_ids)
    joined_entries = ",".join(entries)
    return (
        '{"media_structure":{"visible":"true","SerializeDataOnlyProjectUsered":"false",'
        '"AutoEdit":{"visible":"true","SerializeDataOnlyProjectUsered":"false",'
        '"Folder":{"visible":"true","SerializeDataOnlyProjectUsered":"false"},'
        f'{joined_entries}'
        '}}}'
    )


def update_template_medias_info(
    medias_folder: Path,
    media_items: list[dict[str, Any]],
    timeline_media_id: str,
    total_duration: float,
) -> None:
    """Ensure Filmora's project media bin lists imported source files.

    Template projects already contain a timeline media item. We preserve that
    entry and append one media_item entry per source clip so the Project Media
    panel is populated instead of only the timeline tracks referencing files.
    """
    info_path = medias_folder / "medias_info.json"
    if info_path.exists():
        try:
            data = json.loads(info_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}

    data.setdefault("media_structure", {})
    structure = data["media_structure"]
    structure.setdefault("visible", "true")
    structure.setdefault("SerializeDataOnlyProjectUsered", "false")
    structure.setdefault("Folder", {"visible": "true", "SerializeDataOnlyProjectUsered": "false"})

    existing = structure.get("media_item")
    ordered_items: list[str] = []
    if isinstance(existing, list):
        ordered_items.extend(existing)
    elif isinstance(existing, str):
        ordered_items.append(existing)
    if timeline_media_id not in ordered_items:
        ordered_items.insert(0, timeline_media_id)
    for item in media_items:
        if item["id"] not in ordered_items:
            ordered_items.append(item["id"])
    structure["media_item"] = ordered_items

    data.setdefault("media_items", {})
    now = int(time.time())
    if timeline_media_id not in data["media_items"]:
        data["media_items"][timeline_media_id] = {
            "name": "Timeline",
            "download_url": "",
            "id": timeline_media_id,
            "timeline_uuid": generate_uuid(),
            "media_type": 1048576,
            "create_time": now,
            "duration": seconds_to_100ns(total_duration),
            "enable_modify_mediaId": 0,
            "mark_info_list": [{"mark_in": -1, "mark_out": -1}],
        }

    for item in media_items:
        data["media_items"][item["id"]] = {
            "name": item["name"],
            "download_url": "",
            "id": item["id"],
            "media_type": 2,
            "create_time": now,
            "duration": seconds_to_100ns(item["duration"]),
            "enable_modify_mediaId": 0,
            "mark_info_list": [{"mark_in": -1, "mark_out": -1}],
        }

    info_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def find_clip_prototype(timeline_data: dict, track_type: int, clip_type: int) -> dict | None:
    for timeline in timeline_data.get("timelineInfos", []):
        for track in timeline.get("trackInfos", []):
            if track.get("trackType") != track_type:
                continue
            for clip in track.get("clipList", []):
                if clip.get("type") == clip_type and clip.get("sourceUuid"):
                    return clip
    return None


def build_clip_from_prototype(
    prototype: dict,
    source_uuid: str,
    source_path: str,
    in_point: float,
    out_point: float,
    tl_begin: float,
    tl_end: float,
) -> dict:
    clip = copy.deepcopy(prototype)
    clip["sourceUuid"] = source_uuid
    clip["filename"] = f"file:/{Path(source_path).as_posix()}"
    clip["inPoint"] = seconds_to_100ns(in_point)
    clip["outPoint"] = seconds_to_100ns(out_point)
    clip["tlBegin"] = seconds_to_100ns(tl_begin)
    clip["tlEnd"] = seconds_to_100ns(tl_end)
    clip["thisUId"] = generate_uuid()
    duration = out_point - in_point
    if isinstance(clip.get("speed"), dict):
        clip["speed"]["offset"] = 0.0
        clip["speed"]["offsetEnd"] = duration
        if "speedParam" in clip["speed"]:
            clip["speed"]["speedParam"] = (
                '{"Version": 2,"ParameterType": 0,"keyframeSets": '
                '[{"_time": 0.0,"Interpolation": 6,"_value": 1.0}],'
                '"MD5": "71bd40df43914650e82f103348704572","_totalTime": '
                + str(duration)
                + "}"
            )
    return clip


def generate_project(
    edl: dict,
    output_path: Path,
    project_name: str = "VideoUse Project",
    template_folder: Path | None = None,
    edl_dir: Path | None = None,
) -> None:
    sources = edl.get("sources", {})
    ranges = edl.get("ranges", [])
    source_base = edl_dir or output_path.parent
    sources = {
        source_name: str(resolve_source_path(source_path, source_base))
        for source_name, source_path in sources.items()
    }
    
    if not sources or not ranges:
        print("Error: EDL must contain 'sources' and 'ranges'")
        sys.exit(1)
    
    resources = []
    source_uuid_map = {}
    
    for source_name, source_path in sources.items():
        video_path = Path(source_path)
        if not video_path.exists():
            print(f"Warning: Source file not found: {video_path}")
            continue
        
        video_info = get_video_info(video_path)
        resource, source_uuid = build_resource_entry(video_path, video_info)
        resources.append(resource)
        source_uuid_map[source_name] = {
            "uuid": source_uuid,
            "info": video_info,
        }
    
    if not resources:
        print("Error: No valid source files found")
        sys.exit(1)
    
    first_source = list(source_uuid_map.values())[0]
    width = first_source["info"]["width"]
    height = first_source["info"]["height"]
    fps_num = first_source["info"]["fps_num"]
    fps_den = first_source["info"]["fps_den"]
    sample_rate = first_source["info"]["sample_rate"]
    
    video_clips = []
    audio_clips = []
    
    tl_offset = 0.0
    for r in ranges:
        source_name = r["source"]
        if source_name not in source_uuid_map:
            continue
        
        source_uuid = source_uuid_map[source_name]["uuid"]
        start = float(r["start"])
        end = float(r["end"])
        duration = end - start
        
        video_clip = build_clip_entry(
            source_uuid=source_uuid,
            in_point=start,
            out_point=end,
            tl_begin=tl_offset,
            tl_end=tl_offset + duration,
            clip_type=1,
        )
        audio_clip = build_clip_entry(
            source_uuid=source_uuid,
            in_point=start,
            out_point=end,
            tl_begin=tl_offset,
            tl_end=tl_offset + duration,
            clip_type=2,
        )
        
        video_clips.append(video_clip)
        audio_clips.append(audio_clip)
        
        tl_offset += duration
    
    project_folder = output_path.parent / "ProjectFolder"
    if project_folder.exists():
        shutil.rmtree(project_folder)

    use_template = bool(template_folder and template_folder.exists())

    if use_template:
        shutil.copytree(template_folder, project_folder)
    else:
        project_folder.mkdir(parents=True, exist_ok=True)

    medias_folder = project_folder / "Medias"
    medias_folder.mkdir(exist_ok=True)
    
    template_project_info_path = project_folder / "project_info.json"
    if template_project_info_path.exists():
        try:
            template_project_info = json.loads(template_project_info_path.read_text(encoding="utf-8"))
            timeline_uuid = template_project_info.get("timeline_mediaId") or generate_uuid()
        except Exception:
            timeline_uuid = generate_uuid()
    else:
        timeline_uuid = generate_uuid()

    if use_template and template_project_info_path.exists():
        project_info = json.loads(template_project_info_path.read_text(encoding="utf-8"))
        project_info["project_file_name"] = project_name
        project_info["project_timeline_duration"] = seconds_to_100ns(tl_offset)
        project_info["project_current_position"] = 0
        project_info["timeline_mediaId"] = timeline_uuid
        project_info["project_timeline_framerate"] = [fps_num, fps_den]
        project_info["project_timeline_resolution"] = [width, height]
        project_info["project_sample_rate"] = sample_rate
    else:
        project_info = build_project_info(
            project_name=project_name,
            width=width,
            height=height,
            fps_num=fps_num,
            fps_den=fps_den,
            sample_rate=sample_rate,
            timeline_media_id=timeline_uuid,
            total_duration=tl_offset,
        )

    with open(project_folder / "project_info.json", "w", encoding="utf-8") as f:
        json.dump(project_info, f, indent=2, ensure_ascii=False)

    timeline_folder = medias_folder / timeline_uuid
    timeline_folder.mkdir(exist_ok=True)

    template_timeline_path = timeline_folder / "timeline.wesproj"
    if use_template and template_timeline_path.exists():
        timeline_data = json.loads(template_timeline_path.read_text(encoding="utf-8"))
        timeline_data["projectName"] = project_name
        timeline_data["resources"].extend(resources)

        proto_video = find_clip_prototype(timeline_data, track_type=1, clip_type=1)
        proto_audio = find_clip_prototype(timeline_data, track_type=2, clip_type=2)
        if proto_video is not None:
            video_clips = []
            audio_clips = []
            tl_offset = 0.0
            for r in ranges:
                source_name = r["source"]
                if source_name not in source_uuid_map:
                    continue
                source_uuid = source_uuid_map[source_name]["uuid"]
                source_path = sources[source_name]
                start = float(r["start"])
                end = float(r["end"])
                duration = end - start
                video_clips.append(build_clip_from_prototype(
                    proto_video, source_uuid, source_path, start, end, tl_offset, tl_offset + duration
                ))
                if proto_audio is not None:
                    audio_clips.append(build_clip_from_prototype(
                        proto_audio, source_uuid, source_path, start, end, tl_offset, tl_offset + duration
                    ))
                tl_offset += duration

        tracks = timeline_data["timelineInfos"][0]["trackInfos"]
        timeline_info = timeline_data["timelineInfos"][0]
        timeline_info["frameRate"] = {"den": fps_den, "num": fps_num}
        timeline_info["resolutionHeight"] = height
        timeline_info["resolutionWidth"] = width
        timeline_info["aspectRatioX"] = 16
        timeline_info["aspectRatioY"] = 9
        timeline_info["sampleRate"] = sample_rate
        video_track = next((track for track in tracks if track.get("trackType") == 1), tracks[0])
        audio_track = next((track for track in tracks if track.get("trackType") == 2), None)
        video_track["clipList"] = video_clips
        if audio_track is not None:
            audio_track["clipList"] = audio_clips
        for track in tracks:
            if track is not video_track and track is not audio_track:
                track["clipList"] = []
    else:
        timeline_data = build_timeline_wesproj(
            resources=resources,
            clip_lists=[video_clips, audio_clips],
            project_name=project_name,
            width=width,
            height=height,
            fps_num=fps_num,
            fps_den=fps_den,
            sample_rate=sample_rate,
        )
    
    with open(timeline_folder / "timeline.wesproj", "w", encoding="utf-8") as f:
        json.dump(timeline_data, f, indent=2, ensure_ascii=False)
    
    if not use_template:
        extra_data = {
            "fontNameInfo": [],
            "usedBizFont": [],
            "usedTemplateResInfo": {},
            "mediaClipsMapInfo": {},
            "allMarkersInfo": {},
            "pendingMarkersInfo": {},
            "highlightInfo": {},
            "TextSentence": [],
        }
        with open(timeline_folder / "extra.json", "w", encoding="utf-8") as f:
            json.dump(extra_data, f, indent=2, ensure_ascii=False)
    
    media_ids = []
    media_items = []
    for source_name, source_info in source_uuid_map.items():
        media_id = generate_uuid()
        media_ids.append(media_id)
        media_folder = medias_folder / media_id
        media_folder.mkdir(exist_ok=True)
        
        video_path = Path(sources[source_name])
        media_items.append({
            "id": media_id,
            "name": video_path.name,
            "duration": source_info["info"]["duration"],
        })
        media_json = {
            "version": "1.1.7",
            "file_name": video_path.as_posix(),
            "sourceInfo": {
                "basicInfo": {
                    "streamType": 2,
                    "fourCC": 540299341,
                    "mediaLength": seconds_to_100ns(source_info["info"]["duration"]),
                    "programCount": 1,
                    "videoStreamCount": 1,
                    "audioStreamCount": 1,
                    "subPicStreamCount": 0,
                    "bitRate": 5000000,
                    "createDate": 0,
                },
                "vidStreamInfos": [{
                    "vidStreamId": 0,
                    "fourCC": 875967048,
                    "streamLength": seconds_to_100ns(source_info["info"]["duration"]),
                    "bitRate": 5000000,
                    "startTimestamp": 0,
                    "timestampOffset": 0,
                    "videoScanType": 2,
                    "width": source_info["info"]["width"],
                    "height": source_info["info"]["height"],
                    "frameRate": {"den": fps_den, "num": fps_num},
                    "maxFrameRate": {"den": fps_den * 100, "num": fps_num * 100},
                    "totalFrames": int(source_info["info"]["duration"] * fps_num / fps_den),
                    "xRatio": source_info["info"]["width"],
                    "yRatio": source_info["info"]["height"],
                    "rotation": 0,
                    "flipType": 0,
                    "gpsLatitude": 0.0,
                    "gpsLongitude": 0.0,
                    "cameraMaker": "None",
                    "cameraModel": "None",
                    "exposureTime": 0.0,
                    "premultiAlphaTypePhoto": -1,
                    "transferCharacteristics": 0,
                    "maxGopSize": 30,
                    "lastframeRate": {"den": fps_den, "num": fps_num},
                    "alphaChannel": 0,
                    "isDolbyVision": 0,
                    "colorSpaceSource": 1,
                }],
                "audStreamInfos": [{
                    "audStreamId": 0,
                    "sampleRate": source_info["info"].get("sample_rate", sample_rate),
                    "channels": 2,
                    "bitDepth": 16,
                    "streamLength": seconds_to_100ns(source_info["info"]["duration"]),
                    "duration": source_info["info"]["duration"],
                    "fourCC": 541278529,
                }],
                "recordInfos": {},
            },
        }
        
        with open(media_folder / "media.json", "w", encoding="utf-8") as f:
            json.dump(media_json, f, indent=2, ensure_ascii=False)
    
    if use_template:
        update_template_medias_info(medias_folder, media_items, timeline_uuid, tl_offset)
    else:
        medias_info = build_medias_info(media_ids, timeline_uuid)
        with open(medias_folder / "medias_info.json", "w", encoding="utf-8") as f:
            f.write(medias_info)
    
    if not use_template:
        anon_folder = project_folder / "Anon" / "AppData" / "Windows"
        anon_folder.mkdir(parents=True, exist_ok=True)
        with open(anon_folder / "functionExtraData.json", "w", encoding="utf-8") as f:
            json.dump({"9": "2"}, f)
    
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_folder):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(project_folder.parent)
                zf.write(file_path, arcname)
    
    shutil.rmtree(project_folder)
    
    print(f"Generated: {output_path}")
    print(f"  Sources: {len(resources)}")
    print(f"  Clips: {len(video_clips)}")
    print(f"  Duration: {tl_offset:.2f}s")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate Wondershare Filmora project from EDL")
    ap.add_argument("edl", type=Path, help="Path to edl.json")
    ap.add_argument("-o", "--output", type=Path, required=True, help="Output .wfpx file path")
    ap.add_argument("--name", type=str, default="VideoUse Project", help="Project name")
    ap.add_argument(
        "--template-folder",
        type=Path,
        default=None,
        help="Existing Filmora ProjectFolder to use as a template. Defaults to the nearest ProjectFolder beside the EDL.",
    )
    args = ap.parse_args()
    
    edl_path = args.edl.resolve()
    if not edl_path.exists():
        sys.exit(f"EDL not found: {edl_path}")
    
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    output_path = args.output.resolve()
    template_folder = resolve_template_folder(edl_path, args.template_folder)
    
    generate_project(edl, output_path, args.name, template_folder, edl_path.parent)


if __name__ == "__main__":
    main()
