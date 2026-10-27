#!/usr/bin/env python3
"""Render an explicit camping edit timeline to SDR H.264/AAC MP4."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageDraw, ImageFont
from timeline import load, probe
from grading.grade import color_filters, detail_filters

FILTERS = {'scale', 'pad', 'crop', 'fps', 'overlay', 'fade', 'afade', 'amix',
           'atempo', 'volume', 'alimiter', 'apad', 'trim', 'atrim', 'adelay',
           'tpad', 'setsar', 'setpts', 'asetpts', 'aresample', 'aformat', 'color',
           'anullsrc', 'setparams', 'colorspace', 'format', 'null'}

IEC_TO_709 = ('colorspace=ispace=bt709:iprimaries=bt709:itrc=iec61966-2-4:irange=tv:'
              'space=bt709:primaries=bt709:trc=bt709:range=tv:format=yuv420p:fast=0')


def choose_ffmpeg(explicit):
    candidates = [explicit, os.environ.get('FFMPEG_BIN'), shutil.which('ffmpeg')]
    try:
        import imageio_ffmpeg
        candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
    except ImportError:
        pass
    for candidate in filter(None, candidates):
        if supports(candidate):
            return candidate
        if explicit:
            raise ValueError('Specified FFmpeg lacks required filters or encoders')
    raise ValueError('Full FFmpeg unavailable; install imageio-ffmpeg in this Python environment')


def supports(binary):
    try:
        output = subprocess.check_output([binary, '-hide_banner', '-filters'], stderr=subprocess.STDOUT, text=True)
        filters = {line.split()[1] for line in output.splitlines() if len(line.split()) > 1}
        encoders = subprocess.check_output([binary, '-hide_banner', '-encoders'], stderr=subprocess.STDOUT, text=True)
        return FILTERS <= filters and 'libx264' in encoders and 'pcm_s16le' in encoders and ' aac ' in encoders
    except (OSError, subprocess.CalledProcessError):
        return False


def execute(binary, args, folder, log):
    command = [binary, '-hide_banner', '-nostdin', '-y', *args]
    with log.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(command, ensure_ascii=False) + '\n')
        stream.flush()
        subprocess.run(command, cwd=folder, stdout=stream, stderr=stream, check=True)


def font_path(settings):
    mac_fonts = sorted(Path('/System/Library/AssetsV2').glob(
        'com_apple_MobileAsset_Font*/*.asset/AssetData/PingFang.ttc'))
    paths = [settings.get('font'), '/System/Library/Fonts/PingFang.ttc', *mac_fonts,
             '/System/Library/Fonts/STHeiti Medium.ttc',
             '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
             'C:/Windows/Fonts/msyh.ttc']
    path = next((p for p in paths if p and Path(p).is_file()), None)
    if not path:
        raise ValueError('Chinese captions require output.font pointing to a suitable font')
    return str(path)


def caption_font(settings, size):
    path = font_path(settings)
    index = {'PingFang.ttc': 3, 'STHeiti Light.ttc': 1,
             'STHeiti Medium.ttc': 1}.get(Path(path).name, 0)
    font = ImageFont.truetype(path, size, index=index)
    if Path(path).name == 'PingFang.ttc' and font.getname() != ('PingFang SC', 'Regular'):
        raise ValueError('Verify this system PingFang collection has SC Regular at index 3')
    return font


def text_lines(text, draw, font, width):
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for char in paragraph:
            if line and draw.textlength(line + char, font=font) > width:
                lines.append(line)
                line = ''
            line += char
        lines.append(line)
    if len(lines) > 2:
        raise ValueError('Caption exceeds 2 lines; shorten it or split the clip')
    return lines


def paint_caption_line(draw, line, font, width, y, row_height, padding, background):
    left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
    length = right-left
    x = round((width-length)/2)
    if background:
        draw.rectangle((x-padding, y, x+length+padding-1, y+row_height-1),
                       fill=(0, 0, 0, 135))
    draw.text((x-left, y+(row_height-(bottom-top))/2-top), line,
              font=font, fill='white', stroke_width=0)


def draw_caption(value, settings, path):
    width, height = settings['width'], settings['height']
    canvas = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(canvas)
    diary = value['style'] == 'diary'
    size = max(1, round(height * (0.024 if diary else 0.028)))
    font = caption_font(settings, size)
    lines = text_lines(value['text'], draw, font, width * 0.72)
    _, top, _, bottom = draw.textbbox((0, 0), '国Ag', font=font)
    row_height = bottom-top+2*max(1, round(size*0.16))
    gap = max(1, round(size*0.12))
    block = len(lines)*row_height+(len(lines)-1)*gap
    y = round({'top': height*0.07, 'center': (height-block)/2,
               'bottom': height*0.91-block}[value['position']])
    for line in lines:
        paint_caption_line(draw, line, font, width, y, row_height,
                           max(1, round(size*0.35)), diary)
        y += row_height+gap
    canvas.save(path)


def check_overlay_bounds(bounds, value, settings):
    left, top, right, bottom = bounds
    moving_bottom = bottom + value['move_y'] * settings['height']
    if left < 0 or top < 0 or right > settings['width'] or moving_bottom > settings['height']:
        raise ValueError(f'Overlay {value["id"]!r}: content or entry movement leaves the canvas')


def overlay_text_layout(value, settings, draw):
    size = max(1, round(settings['height'] * value['size']))
    font = caption_font(settings, size)
    lines = text_lines(value['text'], draw, font, settings['width'] * value['max_width'])
    bounds = [draw.textbbox((0, 0), line, font=font) for line in lines]
    padding = (round(size * 0.35), round(size * 0.16)) if value['background_alpha'] else (0, 0)
    row_height = max(bottom-top for _, top, _, bottom in bounds) + 2 * padding[1]
    return font, lines, bounds, padding, max(1, row_height), max(1, round(size * 0.18))


def paint_overlay_text(draw, value, settings):
    font, lines, boxes, (px, py), row_height, gap = overlay_text_layout(value, settings, draw)
    anchor = {'left': 0, 'center': 0.5, 'right': 1}[value['align']]
    y = round(value['y'] * settings['height'])
    for line, (left, top, right, bottom) in zip(lines, boxes):
        length = right-left
        if length > settings['width'] * value['max_width']:
            raise ValueError(f'Overlay {value["id"]!r}: glyph exceeds max_width')
        x = round(value['x'] * settings['width'] - anchor * length)
        check_overlay_bounds((x-px, y, x+length+px, y+row_height), value, settings)
        if value['background_alpha'] and length:
            draw.rectangle((x-px, y, x+length+px-1, y+row_height-1),
                           fill=(0, 0, 0, round(255 * value['background_alpha'])))
        draw.text((x-left, y+py-top), line, font=font, fill='white')
        y += row_height+gap


def paint_overlay_line(draw, value, settings):
    width, height = settings['width'], settings['height']
    points = [(round(value[x] * width), round(value[y] * height))
              for x, y in [('x', 'y'), ('x2', 'y2')]]
    stroke = max(1, round(value['stroke'] * height))
    radius = (stroke + 1) // 2
    xs, ys = zip(*points)
    check_overlay_bounds((min(xs)-radius, min(ys)-radius, max(xs)+radius+1,
                          max(ys)+radius+1), value, settings)
    draw.line(points, fill='white', width=stroke)


def overlay_image(value, settings):
    canvas = Image.new('RGBA', (settings['width'], settings['height']))
    painter = {'text': paint_overlay_text, 'line': paint_overlay_line}[value['type']]
    painter(ImageDraw.Draw(canvas), value, settings)
    return canvas


def tempo(speed):
    factors = []
    while speed > 2:
        factors.append(2)
        speed /= 2
    while speed < 0.5:
        factors.append(0.5)
        speed /= 0.5
    return ','.join(f'atempo={value:.9f}' for value in [*factors, speed])


def fade_filters(clip, audio=False):
    prefix = 'afade' if audio else 'fade'
    fades = []
    if clip['fade_in']:
        fades.append(f'{prefix}=t=in:st=0:d={clip["fade_in"]:.9f}')
    if clip['fade_out']:
        fades.append(f'{prefix}=t=out:st={clip["duration"]-clip["fade_out"]:.9f}:d={clip["fade_out"]:.9f}')
    return fades


def input_args(clip, sources, settings):
    if clip.get('black'):
        video = f'color=c=black:s={settings["width"]}x{settings["height"]}:r={settings["fps"]}'
        return ['-f', 'lavfi', '-i', video, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo'], 1, 2
    source = sources[clip['source']]
    seek = clip['in'] + source['video_start'] - source['container_start']
    args = ['-ss', str(seek), '-t', str(clip['out']-clip['in']), '-noautorotate', '-i', source['path']]
    if source['audio']:
        return args, 0, 1
    return [*args, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo'], 1, 2


def video_filters(clip, settings, color_metadata=None):
    width, height = settings['width'], settings['height']
    mode = 'increase' if clip.get('fit') == 'cover' else 'decrease'
    fit = (f'crop={width}:{height}:(iw-ow)*{clip.get("crop_x",0.5)}:(ih-oh)/2'
           if mode == 'increase' else f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black')
    conversion = [IEC_TO_709] if color_metadata == [1, 11, 1] else []
    return [f'setpts=(PTS-STARTPTS)/{clip.get("speed",1)}',
            f'scale={width}:{height}:flags=lanczos:force_original_aspect_ratio={mode}:force_divisible_by=2:out_color_matrix=bt709:out_range=tv',
            *conversion, *color_filters(clip),
            fit, 'setsar=1', f'fps={settings["fps"]}', 'format=yuv420p',
            *detail_filters(clip),
            'setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709',
            f'tpad=stop_mode=clone:stop_duration={1/float(settings["fps"]):.9f}',
            f'trim=end_frame={clip["frames"]}']


def segment_graph(clip, settings, audio_index, caption_index, color_metadata=None):
    video = ','.join(video_filters(clip, settings, color_metadata))
    graph = [f'[0:v:0]{video}[picture]']
    last = 'picture'
    if 'caption' in clip:
        graph.append(f'[picture][{caption_index}:v]overlay=0:0:shortest=1[captioned]')
        last = 'captioned'
    graph.append(f'[{last}]' + ','.join(fade_filters(clip) or ['null']) + '[v]')
    gain = 'volume=0' if clip.get('mute') else f'volume={clip.get("gain_db",0)}dB'
    audio = ['aresample=48000:async=1:first_pts=0', 'asetpts=PTS-STARTPTS', tempo(clip.get('speed', 1)), gain,
             'aformat=channel_layouts=stereo', 'apad', f'atrim=duration={clip["duration"]:.9f}']
    edge = min(0.01, clip['duration']/2)
    declick = [f'afade=t=in:st=0:d={edge:.9f}',
               f'afade=t=out:st={clip["duration"]-edge:.9f}:d={edge:.9f}']
    graph.append(f'[{audio_index}:a:0]' + ','.join(audio + fade_filters(clip, True) + declick) + '[a]')
    return ';'.join(graph)


def render_segment(binary, clip, timeline, index, folder, log):
    settings = timeline['output']
    args, audio_index, caption_index = input_args(clip, timeline['sources'], settings)
    if 'caption' in clip:
        caption_file = folder / f'caption-{index:05d}.png'
        draw_caption(clip['caption'], settings, caption_file)
        args += ['-loop', '1', '-framerate', str(settings['fps']), '-i', caption_file.name]
    name = f'segment-{index:05d}.mkv'
    color = None if clip.get('black') else timeline['sources'][clip['source']]['color_metadata']
    args += ['-filter_complex_threads', '2', '-filter_complex', segment_graph(clip, settings, audio_index, caption_index, color),
             '-map', '[v]', '-map', '[a]', '-t', str(clip['duration']), '-map_metadata', '-1',
             '-c:v', 'libx264', '-threads', '2', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
             '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv',
             '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', name]
    execute(binary, args, folder, log)
    return name


def music_graph(timeline):
    graph, args, labels = [], [], ['[0:a]']
    for index, track in enumerate(timeline['music'], 1):
        source = timeline['sources'][track['source']]
        seek = track['in'] + source['audio_start'] - source['container_start']
        args += ['-ss', str(seek), '-t', str(track['out']-track['in']), '-i', source['path']]
        settings = dict(track, duration=track['out']-track['in'])
        filters = ['asetpts=PTS-STARTPTS', 'aresample=48000', 'aformat=channel_layouts=stereo',
                   f'volume={track["gain_db"]}dB', *fade_filters(settings, True),
                   f'adelay={round(track["at"]*48000)}S:all=1']
        graph.append(f'[{index}:a:0]' + ','.join(filters) + f'[m{index}]')
        labels.append(f'[m{index}]')
    graph.append(''.join(labels) + f'amix=inputs={len(labels)}:duration=first:normalize=0,'
                 f'alimiter=limit=0.95:level=false:latency=true,atrim=duration={timeline["duration"]:.9f}[a]')
    return args, ';'.join(graph)


def overlay_filters(value):
    filters = ['format=rgba', 'setpts=PTS-STARTPTS']
    if value['fade_in']:
        filters.append(f'fade=t=in:st=0:d={value["fade_in"]:.9f}:alpha=1')
    if value['fade_out']:
        start = value['duration'] - value['fade_out']
        filters.append(f'fade=t=out:st={start:.9f}:d={value["fade_out"]:.9f}:alpha=1')
    filters.append(f'setpts=PTS+{value["at"]:.9f}/TB')
    return ','.join(filters)


def overlay_position(value, height):
    if not value['move_y']:
        return '0'
    return (f'{value["move_y"] * height:.9f}*'
            f'max(0,1-(t-{value["at"]:.9f})/{value["fade_in"]:.9f})')


def overlay_graph(timeline, folder):
    args, graph, picture = [], [], '0:v:0'
    settings = timeline['output']
    for index, layer in enumerate(timeline['overlays']):
        name = f'overlay-{index:05d}.png'
        overlay_image(layer, settings).save(folder / name)
        args += ['-loop', '1', '-framerate', str(settings['fps']),
                 '-t', str(layer['duration']), '-i', name]
        source = 1 + len(timeline['music']) + index
        graph.append(f'[{source}:v:0]{overlay_filters(layer)}[o{index}]')
        end = layer['at'] + layer['duration']
        active = f'gte(t,{layer["at"]:.9f})*lt(t,{end:.9f})'
        y = overlay_position(layer, settings['height'])
        graph.append(f'[{picture}][o{index}]overlay=x=0:y=\'{y}\':'
                     f'enable=\'{active}\':eof_action=pass:repeatlast=0[v{index}]')
        picture = f'v{index}'
    return args, graph, f'[{picture}]'


def final_video(timeline, folder):
    if not timeline['overlays']:
        return [], [], ['-map', '0:v:0', '-c:v', 'copy']
    args, graph, picture = overlay_graph(timeline, folder)
    encoding = ['-map', picture, '-c:v', 'libx264', '-threads', '2', '-preset', 'fast',
                '-crf', '18', '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709',
                '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv']
    return args, graph, encoding


def final_encode(binary, timeline, segments, folder, log):
    (folder / 'concat.txt').write_text(''.join(f"file '{name}'\n" for name in segments), encoding='utf-8')
    args = ['-f', 'concat', '-safe', '1', '-i', 'concat.txt']
    music_args, audio = music_graph(timeline)
    video_args, graphics, encoding = final_video(timeline, folder)
    args += [*music_args, *video_args, '-filter_complex_threads', '2',
             '-filter_complex', ';'.join([audio, *graphics]), *encoding, '-map', '[a]',
             '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
             '-t', str(timeline['duration']), '-movflags', '+faststart', 'render.mp4']
    execute(binary, args, folder, log)
    return folder / 'render.mp4'


def publish(source, target):
    handle, path = tempfile.mkstemp(prefix='.camping-render-', dir=target.parent)
    temporary = Path(path)
    try:
        with os.fdopen(handle, 'wb') as stream, source.open('rb') as input_file:
            shutil.copyfileobj(input_file, stream)
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def destination(path, timeline, input_file):
    path = path.resolve()
    if path.suffix.lower() != '.mp4':
        raise ValueError('Output must end in .mp4')
    occupied = {Path(value['path']) for value in timeline['sources'].values()} | {input_file}
    if path in occupied or path.exists() or path.with_suffix('.render.json').exists():
        raise ValueError('Output or render report already exists, or conflicts with an input')
    return path


def run(args):
    started = time.monotonic()
    source = args.timeline.resolve()
    timeline = load(source)
    for layer in timeline['overlays']:
        overlay_image(layer, timeline['output'])
    output = destination(args.output, timeline, source)
    binary = choose_ffmpeg(args.ffmpeg)
    if args.check:
        print(json.dumps({'valid': True, 'duration': timeline['duration'],
                          'clips': len(timeline['clips']), 'overlays': len(timeline['overlays']),
                          'ffmpeg': binary}))
        return
    render_all(args, timeline, output, source, binary, started)


def render_all(args, timeline, output, source, binary, started):
    args.work.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='camping-render-', dir=args.work)).resolve()
    log = folder / 'ffmpeg.log'
    print(f'Work directory: {folder}', flush=True)
    segments = []
    for index, clip in enumerate(timeline['clips']):
        segments.append(render_segment(binary, clip, timeline, index, folder, log))
        print(f'Rendered {index+1}/{len(timeline["clips"])} clips', flush=True)
    result = final_encode(binary, timeline, segments, folder, log)
    finish(result, output, source, timeline, folder, started)


def finish(result, output, source, timeline, folder, started):
    actual = probe(result)
    expected_size = timeline['output']['width'], timeline['output']['height']
    if not actual['video'] or (actual.get('width'), actual.get('height')) != expected_size:
        raise ValueError(f'Render is missing video or has wrong dimensions: {actual}')
    tolerance = max(0.1, 2/float(timeline['output']['fps']))
    if abs(actual['duration']-timeline['duration']) > tolerance:
        raise ValueError(f'Render duration mismatch: expected {timeline["duration"]}, got {actual["duration"]}')
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {'timeline': str(source), 'timeline_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'renderer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'timeline_module_sha256': hashlib.sha256(Path(__file__).with_name('timeline.py').read_bytes()).hexdigest(),
              'timeline_extension': 'Version 1 supports crop_x for fit=cover and independently timed text/line overlays',
              'color_conversion': {'source_metadata': [1, 11, 1], 'filter': IEC_TO_709,
                                   'applied_to': [key for key, value in timeline['sources'].items()
                                                  if value.get('color_metadata') == [1, 11, 1]]},
              'output': str(output), 'expected_duration': timeline['duration'], 'actual': actual,
              'elapsed_seconds': round(time.monotonic()-started, 2), 'work': str(folder),
              'sources': timeline['sources'],
              'overlays': timeline['overlays'],
              'grade': timeline.get('grade_manifest'),
              'audio': 'Original audio plus explicit music; 48 kHz stereo, 10ms audio-only clip edge fades, peak limiter 0.95, AAC 192k',
              'review': 'Technical render only; visual continuity and listening review remain separate'}
    report_source = folder / 'render.json'
    report_source.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    publish(result, output)
    publish(report_source, output.with_suffix('.render.json'))
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('timeline', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--work', type=Path, default=Path('work/render'))
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--ffmpeg')
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, KeyError, OSError, StopIteration, subprocess.CalledProcessError) as error:
        print(f'Render failed: {error}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
