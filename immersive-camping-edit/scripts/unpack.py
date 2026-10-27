#!/usr/bin/env python3
"""Extract ZIP or tar archives into a fresh task-owned directory."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tarfile
import unicodedata
import zipfile


def safe_name(name):
    name = name.rstrip('/')
    path = PurePosixPath(name)
    if not name or '\\' in name or '\0' in name or re.match(r'^[A-Za-z]:', name):
        raise ValueError(f'不支持的包内路径：{name!r}')
    if path.is_absolute() or '..' in path.parts or str(path) == '.':
        raise ValueError(f'包内路径越界：{name!r}')
    return path


def zip_entries(archive):
    rows = []
    for member in archive.infolist():
        mode = stat.S_IFMT(member.external_attr >> 16)
        if mode not in (0, stat.S_IFREG, stat.S_IFDIR) or member.flag_bits & 1:
            raise ValueError(f'拒绝符号链接、特殊文件或加密文件：{member.filename}')
        rows.append((safe_name(member.filename), member.is_dir(), member.file_size, member))
    return rows


def tar_entries(archive):
    rows = []
    for member in archive.getmembers():
        if member.name in ('.', './') and member.isdir():
            continue
        if not (member.isdir() or member.isfile()):
            raise ValueError(f'拒绝链接或特殊文件：{member.name}')
        rows.append((safe_name(member.name), member.isdir(), member.size, member))
    return rows


def canonical(path):
    return unicodedata.normalize('NFC', str(path)).casefold()


def validate_paths(rows):
    names = {}
    for path, directory, size, member in rows:
        key = canonical(path)
        if key in names:
            raise ValueError(f'包内含重复或大小写冲突的目标：{path}')
        names[key] = directory
        if size < 0:
            raise ValueError(f'无效文件长度：{path}')
    for path, directory, size, member in rows:
        for parent in path.parents:
            if canonical(parent) in names and not names[canonical(parent)]:
                raise ValueError(f'文件和目录发生冲突：{parent}')


def disk_preflight(output, total, maximum):
    if total > maximum:
        raise ValueError(f'展开量 {total} 超过 --max-bytes {maximum}')
    ancestor = output.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    free = shutil.disk_usage(ancestor).free
    if free < total * 1.05 + 64 * 1024 * 1024:
        raise ValueError(f'磁盘空间不足：展开需 {total} 字节，剩余 {free} 字节')


def copy_checked(reader, destination, expected):
    copied = 0
    with reader, destination.open('xb') as target:
        while chunk := reader.read(1024 * 1024):
            copied += len(chunk)
            if copied > expected:
                raise ValueError(f'展开文件超过声明长度：{destination.name}')
            target.write(chunk)
    if copied != expected:
        raise ValueError(f'展开文件长度不符：{destination.name}')


def extract(archive, rows, output, opener):
    output.mkdir(parents=True, exist_ok=False)
    try:
        for path, directory, size, member in rows:
            destination = output / str(path)
            if directory:
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            copy_checked(opener(member), destination, size)
    except BaseException:
        shutil.rmtree(output)
        raise


def open_archive(path):
    if zipfile.is_zipfile(path):
        archive = zipfile.ZipFile(path)
        return archive, zip_entries, archive.open
    if tarfile.is_tarfile(path):
        archive = tarfile.open(path, 'r:*')
        return archive, tar_entries, archive.extractfile
    raise ValueError('仅支持 ZIP 与 tar/tar.gz/tar.bz2/tar.xz；RAR/7z 请先在本机展开。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-bytes', type=int, default=250 * 1024 ** 3)
    args = parser.parse_args()
    source = args.archive.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f'目标已存在，请提供新目录：{output}')
    archive, entries, opener = open_archive(source)
    with archive:
        rows = entries(archive)
        validate_paths(rows)
        total = sum(size for path, directory, size, member in rows if not directory)
        disk_preflight(output, total, args.max_bytes)
        extract(archive, rows, output, opener)
    print(json.dumps({'source': str(source), 'output': str(output), 'files': sum(not r[1] for r in rows),
                      'expanded_bytes': total}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, tarfile.TarError, zipfile.BadZipFile) as error:
        print(f'解包失败：{error}', file=sys.stderr)
        sys.exit(2)
