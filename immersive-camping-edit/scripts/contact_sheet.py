#!/usr/bin/env python3
"""Sample a video across its duration and label decoded source timestamps."""
import argparse
import math
from pathlib import Path
import sys

import av
from PIL import Image, ImageDraw, ImageFont, ImageOps
from media_utils import displayed_image, outside_source, seconds, stream_duration, timestamp, write_json


def font(size):
    candidates = ['/System/Library/Fonts/STHeiti Medium.ttc',
                  '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def video_details(container):
    if not container.streams.video:
        raise ValueError('输入文件没有视频轨')
    stream = container.streams.video[0]
    duration = stream_duration(stream, container)
    if duration is None or duration <= 0:
        raise ValueError('无法确定可采样时长；请先检查/修复媒体容器')
    first = next(container.decode(stream))
    origin = seconds(stream.start_time, stream.time_base)
    return stream, duration, origin if origin is not None else first.time or 0


def sample_times(start, end, interval, maximum, fps):
    if start < 0 or end <= start or interval <= 0 or maximum < 1:
        raise ValueError('要求 0 <= start < end，interval > 0，max-frames >= 1')
    last = max(start, end - min(0.05, 1 / fps if fps else 0.05))
    count = min(maximum, max(1, math.ceil((last - start) / interval) + 1))
    return [start + (last - start) * i / (count - 1) for i in range(count)] if count > 1 else [start]


def read_frame(container, stream, target, origin):
    container.seek(int((target + origin) / stream.time_base), stream=stream, backward=True)
    last = None
    for frame in container.decode(stream):
        if frame.time is None:
            continue
        last = frame
        if frame.time - origin >= target - 0.000001:
            return frame
    if last is None:
        raise ValueError('该时间点没有可解码画面')
    return last


def save_sheet(output, page, tiles):
    canvas = Image.new('RGB', (1280, 16 + 4 * 270), '#171b19')
    draw = ImageDraw.Draw(canvas)
    for index, (image, label) in enumerate(tiles):
        x, y = index % 4 * 320, 16 + index // 4 * 270
        draw.text((x + 8, y), label, font=font(18), fill='white')
        fitted = ImageOps.pad(image.convert('RGB'), (312, 234), color='#080a09')
        canvas.paste(fitted, (x + 4, y + 27))
    relative = Path('sheets') / f'{page // 8 + 1:03d}' / f'{page + 1:04d}.jpg'
    (output / relative.parent).mkdir(parents=True, exist_ok=True)
    canvas.save(output / relative, quality=88)
    return str(relative)


def sample_frame(container, stream, origin, target):
    row = {'requested_seconds': target, 'actual_seconds': None, 'error': None}
    try:
        frame = read_frame(container, stream, target, origin)
        picture, angle, status = displayed_image(frame, stream.metadata, stream.sample_aspect_ratio)
        row.update(actual_seconds=frame.time - origin, raw_pts_seconds=frame.time,
                   pts=frame.pts, rotation=angle, rotation_status=status)
        return row, (picture, timestamp(row['actual_seconds']))
    except Exception as error:
        row['error'] = str(error)
        return row, (Image.new('RGB', (320, 240), '#481c1c'), f'ERROR {timestamp(target)}')


def sample(container, stream, origin, targets, output):
    rows = []
    for page_start in range(0, len(targets), 16):
        page = [sample_frame(container, stream, origin, t) for t in targets[page_start:page_start + 16]]
        sheet = save_sheet(output, page_start // 16, [tile for row, tile in page])
        for cell, (row, tile) in enumerate(page):
            row.update(sheet=sheet, cell=cell)
            rows.append(row)
    return rows, []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--interval', type=float, default=20)
    parser.add_argument('--start', type=float, default=0)
    parser.add_argument('--end', type=float)
    parser.add_argument('--max-frames', type=int, default=160)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    outside_source(source, args.output)
    with av.open(str(source)) as container:
        stream, duration, origin = video_details(container)
        end = min(args.end, duration) if args.end is not None else duration
        targets = sample_times(args.start, end, args.interval, args.max_frames, float(stream.average_rate or 0))
        args.output.mkdir(parents=True, exist_ok=False)
        rows, warnings = sample(container, stream, origin, targets, args.output)
        if int(stream.codec_context.color_trc) in (16, 18):
            warnings.append('源视频带 HDR 传递特性；这些抽帧未做显式 HDR→SDR 色调映射，只用于内容索引。')
    errors = [row for row in rows if row['error']]
    unknown = [row for row in rows if row.get('rotation_status') == 'unknown']
    if unknown:
        warnings.append('部分画面旋转信息未知；请用可播放的原片核对显示方向。')
    write_json(args.output / 'frames.json', {'source': str(source), 'duration': duration,
               'source_pts_origin': origin, 'start': args.start, 'end': end, 'frames': rows,
               'warnings': warnings, 'note': '时间码为解码帧相对视频轨起点的秒数；抽帧只用于索引，不能证明动作完整。'})
    print(f'{len(rows)} 次采样，{len(errors)} 个错误，{len(warnings)} 个警告 → {args.output}')
    return 1 if errors or warnings else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, av.error.FFmpegError) as error:
        print(f'抽帧失败：{error}', file=sys.stderr)
        sys.exit(2)
