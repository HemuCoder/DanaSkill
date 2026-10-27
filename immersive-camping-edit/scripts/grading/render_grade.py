#!/usr/bin/env python3
"""Apply a validated shot-specific grade without editing the source timeline."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grading import grade
import render
from timeline import load, number


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configure_grading_runtime():
    render.FILTERS.update({'eq', 'colorbalance', 'curves', 'unsharp'})
    original = render.input_args
    execute = render.execute

    def limited_decode(clip, sources, settings):
        args, audio_index, caption_index = original(clip, sources, settings)
        if not clip.get('black'):
            args[args.index('-t') + 1] = str(clip['_decode_read_out'] - clip['in'])
        return (['-threads', '2', *args] if not clip.get('black') else args), audio_index, caption_index

    render.input_args = limited_decode
    render.execute = lambda binary, args, folder, log: execute(
        binary, ['-filter_complex_threads', '2', *args], folder, log)


def indices(value, count):
    selected = list(range(count)) if value is None else [int(v) for v in value.split(',')]
    if not selected or len(set(selected)) != len(selected) or any(i < 0 or i >= count for i in selected):
        raise ValueError(f'--indices needs unique clip indices in 0..{count-1}')
    return selected


def sample_clip(clip, settings, seconds):
    result = copy.deepcopy(clip)
    if seconds is None or clip['duration'] <= seconds:
        return result
    frames = max(1, round(seconds * settings['fps']))
    duration = float(frames / settings['fps'])
    if not clip.get('black'):
        span = duration * clip['speed']
        start = (clip['in'] + clip['out'] - span) / 2
        result.update({'in': start, 'out': start + span})
    result.update(frames=frames, duration=duration, fade_in=0, fade_out=0)
    return result


def attach_grades(timeline, selected, plan, sample_seconds, bypass):
    clips, records, offset = [], [], 0.0
    for index in selected:
        clip = sample_clip(timeline['clips'][index], timeline['output'], sample_seconds)
        entry = plan.get(index)
        if entry is None and not clip.get('black'):
            raise ValueError(f'clip_index {index} has no explicit grade; use params={{}} for reviewed identity')
        params = {} if bypass or clip.get('black') else entry['params']
        clip['_grade'] = params
        if not clip.get('black'):
            clip['_decode_read_out'] = min(timeline['sources'][clip['source']]['duration'],
                                          clip['out'] + 2 / float(timeline['output']['fps']) * clip['speed'])
        records.append(grade_record(index, entry, clip, offset))
        clips.append(clip)
        offset += clip['duration']
    return clips, records, offset


def grade_record(index, entry, clip, offset):
    return {'clip_index': index, 'clip_id': (entry or {}).get('clip_id', f'clip-{index:03d}'),
            'source': clip.get('source'), 'source_in': clip.get('in'), 'source_out': clip.get('out'),
            'decode_read_out': clip.get('_decode_read_out'),
            'decode_extra_seconds': clip.get('_decode_read_out', 0) - clip.get('out', 0),
            'target_in': offset, 'duration': clip['duration'], 'frames': clip['frames'],
            'params': clip['_grade'], 'color_filters': grade.color_filters(clip),
            'detail_filters': grade.detail_filters(clip)}


def prepare(args):
    source, config = args.timeline.resolve(), args.grade.resolve()
    timeline = load(source)
    original_duration, count = timeline['duration'], len(timeline['clips'])
    selected = indices(args.indices, count)
    plan = grade.load_plan(config, digest(source), count)
    if args.sample_seconds is not None:
        number(args.sample_seconds, '--sample-seconds', 0.04)
    if (args.indices is not None or args.sample_seconds is not None) and timeline['music']:
        raise ValueError('Subset previews with a music track need an explicit remapped music timeline')
    clips, records, duration = attach_grades(timeline, selected, plan, args.sample_seconds, args.bypass_grade)
    timeline.update(clips=clips, duration=duration)
    timeline['grade_manifest'] = manifest(args, source, config, original_duration, count, records)
    return source, timeline


def manifest(args, source, config, duration, count, records):
    return {'plan_path': str(config), 'plan_sha256': digest(config), 'timeline_sha256': digest(source),
            'driver_sha256': digest(Path(__file__)), 'grade_module_sha256': digest(Path(grade.__file__)),
            'original_duration': duration, 'original_clip_count': count,
            'subset': args.indices is not None, 'sample_seconds': args.sample_seconds,
            'bypass_grade': args.bypass_grade, 'decode_encode_filter_threads': 2, 'serial_segments': True,
            'decode_lookahead': 'Up to 2 output frames in source time, capped at source duration; output video/audio retain requested trims',
            'color_position': 'after source transfer-function conversion, before crop/pad and captions',
            'detail_position': 'at final output resolution, after crop/pad, before captions and fades',
            'clips': records}


def run(args):
    started = time.monotonic()
    configure_grading_runtime()
    source, timeline = prepare(args)
    output = render.destination(args.output, timeline, source)
    binary = render.choose_ffmpeg(args.ffmpeg)
    if args.check:
        print(json.dumps({'valid': True, 'duration': timeline['duration'], 'output': timeline['output'] | {'fps': str(timeline['output']['fps'])},
                          'grade': timeline['grade_manifest']}, ensure_ascii=False, indent=2))
        return
    render.render_all(args, timeline, output, source, binary, started)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('timeline', type=Path)
    parser.add_argument('--grade', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--work', type=Path, default=Path('work/render-grade'))
    parser.add_argument('--ffmpeg')
    parser.add_argument('--indices', help='Comma-separated original zero-based clip indices')
    parser.add_argument('--sample-seconds', type=float, help='Use central excerpt of each selected clip')
    parser.add_argument('--bypass-grade', action='store_true', help='Same source edit and conversion, neutral grading')
    parser.add_argument('--check', action='store_true')
    try:
        run(parser.parse_args())
    except (ValueError, KeyError, OSError, StopIteration, subprocess.CalledProcessError) as error:
        print(f'Grade render failed: {error}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
