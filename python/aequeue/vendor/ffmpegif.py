# -*- coding: utf-8 -*-

from __future__ import print_function
import subprocess
import argparse
import tempfile
import io

import ffmpeg_lib


def get_palette_path(fn):
    '''Get the path to a temporary palette file.'''

    with tempfile.NamedTemporaryFile(prefix='palette', suffix='.png') as tmp:
        palette_path = tmp.name
    return palette_path


def parser():
    parser = argparse.ArgumentParser(prog='ffmpegif')
    parser.add_argument(
        '-i',
        dest='in_file',
        help='Input video to convert to gif',
        required=True,
    )
    parser.add_argument(
        '-fps',
        dest='fps',
        help='Output fps',
        default='',
    )
    parser.add_argument(
        '-width',
        dest='width',
        help='Output width',
        default='',
    )
    parser.add_argument(
        '-max_colors',
        dest='max_colors',
        help='Output max_colors',
        default='',
    )
    parser.add_argument(
        '-filter',
        dest='filter',
        help='Output Scale filter: bilinear, lanczos, sinc, gauss, bicubic',
        default='bicubic'
    )
    parser.add_argument(
        '-transpose',
        dest='transpose',
        help='1:rotate clockwise / 2:rotate counterclockwise',
        default='',
    )
    parser.add_argument(
        '-loop',
        dest='loop',
        help='-1:no_loop / 0:loop / 1:loop_once / n:loop_n_times'
    )
    parser.add_argument(
        '-start_time',
        dest='start_time',
        help='Timecode to start rendering from.',
        default='',
    )
    parser.add_argument(
        '-frames',
        dest='frames',
        help='Number of frames after start_time to render.',
        default='',
    )
    parser.add_argument(
        'out_file',
        help='Output gif file',
        nargs=1,
    )
    return parser


def encode(
    in_file,
    out_file,
    loop='0',
    framerate=None,
    width=None,
    filter=None,
    transpose=None,
    max_colors=None,
    start_time=None,
    frames=None,
):
    # Build timecode_args
    timecode_args = []
    if start_time:
        timecode_args.extend(['-ss', start_time])
    if frames:
        timecode_args.extend(['-vframes', frames])

    # Build filter graph
    filter_graph = (
        '[0:v] %s%s%ssplit [a][b];'
        '[a] palettegen%s [p];'
        '[b][p] paletteuse'
    ) % (
        ('', 'fps=%s,' % framerate)[bool(framerate)],
        ('', 'scale=%s:-1:flags=%s,' % (width, filter or 'bicubic'))[bool(width)],
        ('', 'transpose=%s,' % transpose)[bool(transpose)],
        ('', '=max_colors=%s' % max_colors)[bool(max_colors)],
    )

    # Build ffmpeg args
    ffmpeg_args = [
        '-i', in_file,
        '-filter_complex', filter_graph,
        '-loop', loop,
    ]
    ffmpeg_args += timecode_args
    ffmpeg_args += [
        '-y',
        out_file,
    ]

    # Start and watch process
    return ffmpeg_lib.encode(*ffmpeg_args)


def watch(*args, **kwargs):
    return ffmpeg_lib.watch(*args, **kwargs)


def main():
    '''CLI Entry Point...'''
    args = parser().parse_args()
    proc = encode(
        args.in_file,
        args.out_file[0],
        args.loop,
        args.fps,
        args.width,
        args.filter,
        args.transpose,
        args.max_colors,
        args.start_time,
        args.frames,
    )
    watch(proc)


if __name__ == '__main__':
    main()
