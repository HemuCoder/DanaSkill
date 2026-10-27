"""Validate an explicit edit decision timeline; never choose shots implicitly."""
import json
import math
from fractions import Fraction
from pathlib import Path

import av


def fields(value, allowed, required, label):
    if not isinstance(value, dict):
        raise ValueError(f'{label}: expected an object')
    unknown, missing = set(value) - set(allowed), set(required) - set(value)
    if unknown or missing:
        raise ValueError(f'{label}: unknown={sorted(unknown)}, missing={sorted(missing)}')


def number(value, label, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label}: expected a finite number')
    if not math.isfinite(value) or (low is not None and value < low):
        raise ValueError(f'{label}: invalid value {value}')
    if high is not None and value > high:
        raise ValueError(f'{label}: maximum is {high}')
    return float(value)


def stream_duration(stream, container):
    if stream.duration is not None:
        return float(stream.duration * stream.time_base)
    if container.duration is not None:
        return float(container.duration / av.time_base)
    raise ValueError('Media duration is unknown; remux/probe it before editing')


def check_video(stream, frame, path):
    codec = stream.codec_context
    if codec.color_trc in (16, 18) or codec.color_primaries == 9:
        raise ValueError(f'HDR/wide-gamut source needs an explicit SDR conversion: {path}')
    if frame.rotation or float(stream.metadata.get('rotate', '0')) % 360:
        raise ValueError(f'Rotated source needs an explicit orientation conversion: {path}')
    if any('DISPLAYMATRIX' in str(item) for item in frame.side_data):
        raise ValueError(f'Display matrix needs an explicit orientation conversion: {path}')
    if stream.sample_aspect_ratio and stream.sample_aspect_ratio != 1:
        raise ValueError(f'Non-square pixels need an explicit conversion: {path}')
    known = (codec.color_primaries, codec.color_trc, codec.colorspace)
    if known != (1, 11, 1) and any(value not in (0, 1, 2) for value in known):
        raise ValueError(f'Non-BT.709 color metadata {known} needs explicit conversion: {path}')


def stream_start(stream):
    return float(stream.start_time * stream.time_base) if stream.start_time is not None else 0.0


def probe(path):
    with av.open(str(path)) as container:
        videos, audios = container.streams.video, container.streams.audio
        stream = videos[0] if videos else audios[0] if audios else None
        if stream is None:
            raise ValueError(f'No video/audio stream: {path}')
        result = {'duration': stream_duration(stream, container), 'audio': bool(audios)}
        result['container_start'] = float(container.start_time / av.time_base) if container.start_time is not None else 0.0
        result['video_start'] = stream_start(videos[0]) if videos else None
        result['audio_start'] = stream_start(audios[0]) if audios else None
        result['audio_duration'] = stream_duration(audios[0], container) if audios else None
        result['video'] = bool(videos)
        if videos:
            frame = next(container.decode(videos[0]))
            check_video(videos[0], frame, path)
            result.update(width=frame.width, height=frame.height)
            result['color_metadata'] = [videos[0].codec_context.color_primaries,
                                        videos[0].codec_context.color_trc, videos[0].codec_context.colorspace]
        return result


def output_settings(value, root):
    fields(value, {'width', 'height', 'fps', 'font'}, {'width', 'height', 'fps'}, 'output')
    for key in ('width', 'height'):
        if type(value[key]) is not int or not 16 <= value[key] <= 7680 or value[key] % 2:
            raise ValueError(f'output.{key}: expected an even integer from 16 to 7680')
    fps = Fraction(str(value['fps']))
    if not 1 <= fps <= 120:
        raise ValueError('output.fps must be between 1 and 120')
    result = dict(value, fps=fps)
    if value.get('font'):
        result['font'] = str((root / value['font']).resolve())
        if not Path(result['font']).is_file():
            raise ValueError('output.font does not exist')
    return result


def interval(value, source, label):
    start = number(value['in'], f'{label}.in', 0)
    end = number(value['out'], f'{label}.out', 0)
    if end <= start or end > source['duration'] + 0.001:
        raise ValueError(f'{label}: interval {start}..{end} outside duration {source["duration"]}')
    return start, end


def caption(value):
    fields(value, {'text', 'position', 'style'}, {'text'}, 'caption')
    if not isinstance(value['text'], str) or not value['text'].strip():
        raise ValueError('caption.text must contain text')
    result = {'position': 'bottom', 'style': 'diary', **value}
    if result['position'] not in ('top', 'center', 'bottom'):
        raise ValueError('caption.position: top, center or bottom')
    if result['style'] not in ('diary', 'label'):
        raise ValueError('caption.style: diary or label')
    return result


def fades(value, duration, label):
    result = {key: number(value.get(key, 0), f'{label}.{key}', 0, duration)
              for key in ('fade_in', 'fade_out')}
    if sum(result.values()) > duration:
        raise ValueError(f'{label}: fades overlap')
    return result


def clip(value, sources, settings, index):
    label = f'clips[{index}]'
    if not isinstance(value, dict):
        raise ValueError(f'{label}: expected an object')
    common = {'fade_in', 'fade_out', 'caption'}
    is_black = value.get('black') is True
    required = {'black', 'duration'} if is_black else {'source', 'in', 'out'}
    allowed = required | common | (set() if is_black else {'speed', 'gain_db', 'fit', 'mute', 'crop_x'})
    fields(value, allowed, required, label)
    result = dict(value)
    if is_black:
        duration = number(value['duration'], label + '.duration', 0.001)
    else:
        result, duration = video_clip(value, sources, label)
    result['frames'] = max(1, round(duration * settings['fps']))
    result['duration'] = float(result['frames'] / settings['fps'])
    result.update(fades(value, result['duration'], label))
    if 'caption' in value:
        result['caption'] = caption(value['caption'])
    return result


def video_clip(value, sources, label):
    source = source_for(value, sources, label)
    if not source['video']:
        raise ValueError(f'{label}: source has no video')
    start, end = interval(value, source, label)
    speed = number(value.get('speed', 1), label + '.speed', 0.125, 8)
    gain = number(value.get('gain_db', 0), label + '.gain_db', -96, 24)
    fit = value.get('fit', 'contain')
    crop_x = number(value.get('crop_x', 0.5), label + '.crop_x', 0, 1)
    if fit not in ('contain', 'cover'):
        raise ValueError(f'{label}.fit: contain or cover')
    if 'mute' in value and type(value['mute']) is not bool:
        raise ValueError(f'{label}.mute: expected boolean')
    return dict(value, **{'in': start, 'out': end}, speed=speed, gain_db=gain,
                fit=fit, crop_x=crop_x), (end-start)/speed


def music_track(value, sources, duration, index):
    label = f'music[{index}]'
    keys = {'source', 'in', 'out', 'at', 'gain_db', 'fade_in', 'fade_out'}
    fields(value, keys, {'source', 'in', 'out', 'at', 'gain_db'}, label)
    source = source_for(value, sources, label)
    if not source['audio']:
        raise ValueError(f'{label}: source has no audio')
    start, end = interval(value, dict(source, duration=source['audio_duration']), label)
    at = number(value['at'], label + '.at', 0)
    if at + end - start > duration + 0.001:
        raise ValueError(f'{label}: extends beyond timeline end')
    gain = number(value['gain_db'], label + '.gain_db', -96, 24)
    return dict(value, **{'in': start, 'out': end}, at=at, gain_db=gain,
                **fades(value, end-start, label))


def overlay_timing(value, settings, duration, label):
    fps = settings['fps']
    at = number(value['at'], label + '.at', 0)
    length = number(value['duration'], label + '.duration', 0.001)
    start_frame, frames = round(at * fps), max(1, round(length * fps))
    if start_frame + frames > round(duration * fps):
        raise ValueError(f'{label}: extends beyond timeline end after frame quantization')
    length = float(frames / fps)
    result = dict(at=float(start_frame / fps), duration=length,
                  **fades(value, length, label))
    result['move_y'] = number(value.get('move_y', 0), label + '.move_y', 0, 1)
    if result['move_y'] and not result['fade_in']:
        raise ValueError(f'{label}: move_y requires fade_in > 0')
    return result


def overlay_text(value, label):
    if not isinstance(value['text'], str) or not value['text'].strip():
        raise ValueError(f'{label}.text must contain text')
    align = value.get('align', 'left')
    if align not in ('left', 'center', 'right'):
        raise ValueError(f'{label}.align: left, center or right')
    return dict(text=value['text'], align=align,
                size=number(value['size'], label + '.size', 0.001, 1),
                max_width=number(value.get('max_width', 0.72), label + '.max_width', 0.001, 1),
                background_alpha=number(value.get('background_alpha', 0),
                                        label + '.background_alpha', 0, 1))


def overlay_line(value, label):
    result = {key: number(value[key], f'{label}.{key}', 0, 1) for key in ('x2', 'y2')}
    if value['x'] == result['x2'] and value['y'] == result['y2']:
        raise ValueError(f'{label}: line endpoints must differ')
    result['stroke'] = number(value.get('stroke', 0.0015), label + '.stroke', 0.0001, 1)
    return result


def overlay(value, settings, duration, index):
    label = f'overlays[{index}]'
    if not isinstance(value, dict) or value.get('type') not in ('text', 'line'):
        raise ValueError(f'{label}.type: text or line')
    common = {'id', 'type', 'at', 'duration', 'x', 'y'}
    required = {'text', 'size'} if value['type'] == 'text' else {'x2', 'y2'}
    optional = {'align', 'max_width', 'background_alpha'} if value['type'] == 'text' else {'stroke'}
    fields(value, common | required | optional | {'fade_in', 'fade_out', 'move_y'},
           common | required, label)
    if not isinstance(value['id'], str) or not value['id'].strip():
        raise ValueError(f'{label}.id must contain a unique name')
    position = {key: number(value[key], f'{label}.{key}', 0, 1) for key in ('x', 'y')}
    content = {'text': overlay_text, 'line': overlay_line}[value['type']](value, label)
    return dict(id=value['id'], type=value['type'], **position, **content,
                **overlay_timing(value, settings, duration, label))


def overlays(values, settings, duration):
    if not isinstance(values, list):
        raise ValueError('overlays must be an array')
    result = [overlay(value, settings, duration, i) for i, value in enumerate(values)]
    if len({item['id'] for item in result}) != len(result):
        raise ValueError('overlays.id values must be unique')
    return result


def load(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    fields(data, {'version', 'sources', 'output', 'clips', 'music', 'overlays'},
           {'version', 'sources', 'output', 'clips'}, 'timeline')
    if type(data['version']) is not int or data['version'] != 1:
        raise ValueError('Only timeline version 1 is supported')
    if not isinstance(data['sources'], dict) or not isinstance(data['clips'], list) or not data['clips']:
        raise ValueError('sources must be an object and clips a nonempty array')
    if not isinstance(data.get('music', []), list):
        raise ValueError('music must be an array')
    settings = output_settings(data['output'], path.parent)
    sources = read_sources(data['sources'], path.parent)
    clips = [clip(value, sources, settings, i) for i, value in enumerate(data['clips'])]
    total = sum(item['frames'] for item in clips) / float(settings['fps'])
    music = [music_track(v, sources, total, i) for i, v in enumerate(data.get('music', []))]
    layers = overlays(data.get('overlays', []), settings, total)
    return {'sources': sources, 'output': settings, 'clips': clips, 'music': music,
            'overlays': layers, 'duration': total}


def source_for(value, sources, label):
    key = value['source']
    if not isinstance(key, str) or key not in sources:
        raise ValueError(f'{label}: unknown source ID {key!r}')
    return sources[key]


def read_sources(values, root):
    sources = {}
    for key, value in values.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError('Source IDs and paths must be strings')
        path = (root / value).resolve()
        if not path.is_file():
            raise ValueError(f'Source file missing: {path}')
        sources[key] = dict(probe(path), path=str(path))
    return sources
