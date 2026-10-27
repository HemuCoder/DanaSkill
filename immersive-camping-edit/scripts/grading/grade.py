"""Validated shot-local SDR grading; numeric values map to FFmpeg filters."""
import json
from pathlib import Path

from timeline import fields, number

EQ = {'brightness': (-1, 1), 'contrast': (0, 3), 'saturation': (0, 3),
      'gamma': (0.1, 3), 'gamma_weight': (0, 1)}
BALANCE = {key: (-1, 1) for key in ('rs', 'gs', 'bs', 'rm', 'gm', 'bm', 'rh', 'gh', 'bh')}


def numeric_group(value, limits, label):
    fields(value, limits, set(), label)
    return {key: number(item, f'{label}.{key}', *limits[key]) for key, item in value.items()}


def balance(value):
    fields(value, set(BALANCE) | {'pl'}, set(), 'colorbalance')
    result = numeric_group({k: v for k, v in value.items() if k != 'pl'}, BALANCE, 'colorbalance')
    if 'pl' in value:
        if type(value['pl']) is not bool:
            raise ValueError('colorbalance.pl must be a boolean')
        result['pl'] = int(value['pl'])
    return result


def curve_points(value, label):
    if not isinstance(value, list) or not 2 <= len(value) <= 17:
        raise ValueError(f'{label}: expected 2..17 control points')
    points = []
    for pair in value:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError(f'{label}: each control point must be [x,y]')
        points.append([number(v, label, 0, 1) for v in pair])
    if any(b[0] <= a[0] for a, b in zip(points, points[1:])):
        raise ValueError(f'{label}: x coordinates must be strictly increasing')
    return points


def curves(value):
    fields(value, {'master', 'red', 'green', 'blue'}, set(), 'curves')
    return {key: curve_points(points, f'curves.{key}') for key, points in value.items()}


def unsharp(value):
    fields(value, {'amount', 'size'}, {'amount'}, 'unsharp')
    size = value.get('size', 5)
    if type(size) is not int or size % 2 != 1 or not 3 <= size <= 23:
        raise ValueError('unsharp.size must be an odd integer from 3 to 23')
    return {'amount': number(value['amount'], 'unsharp.amount', 0, 0.5), 'size': size}


def parameters(value):
    handlers = {'eq': lambda x: numeric_group(x, EQ, 'eq'), 'colorbalance': balance,
                'curves': curves, 'unsharp': unsharp,
                'clarity': lambda x: number(x, 'clarity', 0, 0.1)}
    fields(value, handlers, set(), 'params')
    return {key: handlers[key](item) for key, item in value.items()}


def load_plan(path, timeline_hash, clip_count):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    fields(value, {'version', 'timeline_sha256', 'clips', 'notes'},
           {'version', 'timeline_sha256', 'clips'}, 'grade plan')
    if type(value['version']) is not int or value['version'] != 1:
        raise ValueError('Only grade plan version 1 is supported')
    if value['timeline_sha256'] != timeline_hash:
        raise ValueError('Grade plan is bound to a different timeline SHA256')
    if not isinstance(value['clips'], list):
        raise ValueError('grade plan clips must be an array')
    result = {}
    for row in value['clips']:
        index, entry = plan_row(row, clip_count)
        if index in result:
            raise ValueError(f'Duplicate grade for clip_index {index}')
        result[index] = entry
    return result


def plan_row(row, clip_count):
    fields(row, {'clip_index', 'clip_id', 'params', 'notes'}, {'clip_index', 'params'}, 'grade clip')
    index = row['clip_index']
    if type(index) is not int or not 0 <= index < clip_count:
        raise ValueError(f'clip_index must be in 0..{clip_count-1}')
    if 'clip_id' in row and not isinstance(row['clip_id'], str):
        raise ValueError('clip_id must be a string')
    return index, {**row, 'params': parameters(row['params'])}


def options(value):
    return ':'.join(f'{key}={number:.8g}' for key, number in value.items())


def color_filters(clip):
    params, result = clip.get('_grade', {}), []
    for key in ('colorbalance', 'eq'):
        if params.get(key):
            result.append(f'{key}={options(params[key])}')
    if params.get('curves'):
        values = [f"{key}='" + ' '.join(f'{x:.8f}/{y:.8f}' for x, y in points) + "'"
                  for key, points in params['curves'].items()]
        result.append('curves=' + ':'.join(values))
    return result


def detail_filters(clip):
    params, result = clip.get('_grade', {}), []
    if params.get('clarity', 0):
        result.append(f'unsharp=13:13:{params["clarity"]:.8f}:3:3:0')
    sharp = params.get('unsharp', {})
    if sharp.get('amount', 0):
        result.append(f'unsharp={sharp["size"]}:{sharp["size"]}:{sharp["amount"]:.8f}:3:3:0')
    return result
