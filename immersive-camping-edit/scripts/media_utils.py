"""Shared local media helpers. Never modify source media."""
import json
from pathlib import Path


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def outside_source(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output == source or (source.is_dir() and source in output.parents):
        raise ValueError('输出不能覆盖源文件或写入正在递归扫描的素材目录。')


def seconds(value, time_base):
    return float(value * time_base) if value is not None else None


def stream_duration(stream, container):
    duration = seconds(stream.duration, stream.time_base)
    return duration if duration is not None else (container.duration / 1_000_000 if container.duration else None)


def orientation(frame, metadata):
    try:
        has_matrix = any(getattr(side, 'name', '') == 'DISPLAYMATRIX' for side in frame.side_data.keys())
        if has_matrix:
            return int(frame.rotation), 'decoded_display_matrix'
    except (AttributeError, TypeError, ValueError):
        pass
    try:
        return -float(metadata['rotate']), 'stream_rotate_tag'
    except (KeyError, TypeError, ValueError):
        return (0, 'no_rotation_metadata') if hasattr(frame, 'rotation') else (None, 'unknown')


def displayed_image(frame, metadata, sample_aspect_ratio=None):
    image = frame.to_image()
    if sample_aspect_ratio and sample_aspect_ratio != 1:
        image = image.resize((max(1, round(image.width * sample_aspect_ratio)), image.height))
    angle, status = orientation(frame, metadata)
    if angle:
        image = image.rotate(angle, expand=True)
    return image, angle, status


def timestamp(value):
    value = max(0, value)
    hours, rest = divmod(value, 3600)
    minutes, sec = divmod(rest, 60)
    return f'{int(hours):02d}:{int(minutes):02d}:{sec:06.3f}'
