#!/usr/bin/env python3
"""Read-only inventory of video, audio and still images."""
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sys

import av
from PIL import Image, ImageOps
from media_utils import orientation, outside_source, seconds, stream_duration, write_json

VIDEO = set('.mov .mp4 .m4v .mkv .avi .mxf .mts .m2ts .webm'.split())
AUDIO = set('.wav .mp3 .aac .m4a .flac .aif .aiff .ogg .opus'.split())
IMAGE = set('.jpg .jpeg .png .tif .tiff .webp .heic .heif .bmp'.split())
PRIMARIES = {1: 'bt709', 2: 'unspecified', 9: 'bt2020', 12: 'smpte432'}
TRANSFER = {1: 'bt709', 2: 'unspecified', 16: 'smpte2084', 18: 'arib-std-b67'}
SPACE = {1: 'bt709', 2: 'unspecified', 9: 'bt2020nc', 10: 'bt2020c'}


def field_number(obj, name):
    value = getattr(obj, name, None)
    return int(value) if value is not None else None


def color_fields(context):
    transfer = field_number(context, 'color_trc')
    return {
        'color_range': field_number(context, 'color_range'),
        'color_space': SPACE.get(field_number(context, 'colorspace'), field_number(context, 'colorspace')),
        'color_transfer': TRANSFER.get(transfer, transfer),
        'color_primaries': PRIMARIES.get(field_number(context, 'color_primaries'), field_number(context, 'color_primaries')),
        'hdr': True if transfer in (16, 18) else (None if transfer in (None, 2) else False),
    }


def video_info(stream, container):
    context = stream.codec_context
    row = {'index': stream.index, 'codec': context.name, 'width': context.width, 'height': context.height,
           'fps': float(stream.average_rate) if stream.average_rate else None,
           'time_base': str(stream.time_base), 'start_time': seconds(stream.start_time, stream.time_base),
           'sample_aspect_ratio': str(stream.sample_aspect_ratio) if stream.sample_aspect_ratio else None,
           'duration': stream_duration(stream, container), 'rotation': None, 'rotation_status': 'unknown',
           'pixel_format': context.format.name if context.format else None, 'metadata': dict(stream.metadata)}
    row.update(color_fields(context))
    return row


def audio_info(stream, container):
    context = stream.codec_context
    return {'index': stream.index, 'codec': context.name, 'sample_rate': context.sample_rate,
            'channels': context.channels, 'layout': context.layout.name if context.layout else None,
            'duration': stream_duration(stream, container), 'start_time': seconds(stream.start_time, stream.time_base)}


def check_orientation(path, videos, warnings):
    for video in videos:
        try:
            with av.open(str(path)) as container:
                stream = container.streams[video['index']]
                frame = next(container.decode(stream))
                video['rotation'], video['rotation_status'] = orientation(frame, stream.metadata)
        except Exception as error:
            warnings.append(f'首帧解码失败，旋转未知（流{video["index"]}）：{error}')


def inspect_container(path, row):
    with av.open(str(path)) as container:
        row['container_duration'] = container.duration / 1_000_000 if container.duration is not None else None
        row['creation_time'] = container.metadata.get('creation_time')
        row['metadata'] = dict(container.metadata)
        row['video'] = [video_info(s, container) for s in container.streams.video]
        row['audio'] = [audio_info(s, container) for s in container.streams.audio]
    if not row['video'] and not row['audio']:
        raise ValueError('没有可识别的视频或音频流')
    streams = row['video'] or row['audio']
    row['duration'] = streams[0]['duration']
    check_orientation(path, row['video'], row['warnings'])


def inspect_image(path, row):
    with Image.open(path) as image:
        image.load()
        exif = image.getexif()
        displayed = ImageOps.exif_transpose(image)
        row['image'] = {'width': image.width, 'height': image.height, 'mode': image.mode,
                        'display_width': displayed.width, 'display_height': displayed.height,
                        'exif_orientation': exif.get(274, 1), 'format': image.format,
                        'has_icc_profile': bool(image.info.get('icc_profile'))}
        row['creation_time'] = exif.get(36867) or exif.get(306)


def kind(path):
    suffix = path.suffix.lower()
    return 'video' if suffix in VIDEO else 'audio' if suffix in AUDIO else 'image'


def inspect(path, root):
    stat = path.stat()
    relative = str(path.relative_to(root))
    identity = f'{relative}\0{stat.st_size}\0{stat.st_mtime_ns}'.encode()
    row = {'id': hashlib.sha256(identity).hexdigest()[:16], 'path': str(path.resolve()),
           'relative_path': relative, 'kind': kind(path), 'size_bytes': stat.st_size,
           'mtime_ns': stat.st_mtime_ns, 'duration': None, 'video': [], 'audio': [],
           'creation_time': None, 'warnings': [], 'error': None}
    try:
        (inspect_image if row['kind'] == 'image' else inspect_container)(path, row)
    except Exception as error:
        row['error'] = str(error)
    return row


def collect(source):
    paths = [source] if source.is_file() else sorted(source.rglob('*'))
    files, skipped = [], []
    for path in paths:
        if path.is_symlink():
            skipped.append({'path': str(path), 'reason': 'symbolic_link'})
        elif path.is_file():
            (files if path.suffix.lower() in VIDEO | AUDIO | IMAGE else skipped).append(
                path if path.suffix.lower() in VIDEO | AUDIO | IMAGE else {'path': str(path), 'reason': 'unsupported_extension'})
    return files, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    outside_source(source, args.output)
    files, skipped = collect(source)
    root = source if source.is_dir() else source.parent
    rows = [inspect(path, root) for path in files]
    errors = [{'path': row['path'], 'error': row['error']} for row in rows if row['error']]
    warnings = [{'path': row['path'], 'messages': row['warnings']} for row in rows if row['warnings']]
    result = {'schema_version': 1, 'source_root': str(root), 'generated_at': datetime.now(timezone.utc).isoformat(),
              'id_method': 'relative_path + size + mtime_ns; not a content hash', 'files': rows,
              'skipped': skipped, 'warnings': warnings, 'errors': errors}
    write_json(args.output, result)
    print(f'{len(rows)} 个素材，{len(errors)} 个错误，{len(warnings)} 个警告，{len(skipped)} 个跳过项 → {args.output}')
    return 1 if errors or warnings or not rows else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(f'素材扫描失败：{error}', file=sys.stderr)
        sys.exit(2)
