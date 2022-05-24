'''
ffmpeg_lib
==========
Small ffmpeg library to facilitate progress reporting.

'''

# Standard library imports
import glob
import io
import os
import random
import re
import subprocess
import sys
import tempfile
import time


__title__ = 'ffmpeg_lib'
__version__ = '0.1.0'
__author__ = 'Dan Bradham'
__email__ = 'danbradham@gmail.com'
__url__ = 'https://github.com/danbradham/ffmpeg_lib'
__all__ = [
    'encode',
    'encode_sequence',
    'FfmpegProcess',
    'get_ffmpeg',
    'get_resolution',
    'get_frame_range',
    'icon',
    'is_ffmpeg_available',
    'watch',
    'watch_qt',
]

icon = os.path.join(os.path.dirname(__file__), 'ffmpeg.png')


class FfmpegProcess(object):

    def __init__(self, proc):
        self.proc = proc
        self.in_file = proc.args[proc.args.index('-i') + 1]
        self.out_file = proc.args[-1]
        self.frame = 0
        self.num_frames = 1
        self.progress = 0.0
        self.capture = []
        self.result = None
        self.error = None

    def __getattr__(self, attr):
        return getattr(self.proc, attr)

    def set_frame(self, frame):
        self.frame = frame
        self.progress = self.frame / (self.num_frames + 1) * 100


def get_ffmpeg():
    '''Get ffmpeg executable...'''

    return os.environ.get('FFMPEG_LOCATION', 'ffmpeg').replace('\\', '/')


def is_ffmpeg_available():
    '''Returns True if ffmpeg executable is available.'''

    ffmpeg = get_ffmpeg()
    if os.path.exists(ffmpeg):
        return True

    potential_files = ['ffmpeg', 'ffmpeg.exe']
    paths = os.environ['PATH'].split(os.pathsep)
    for path in paths:
        for file in potential_files:
            potential_path = os.path.join(path, file)
            if os.path.exists(potential_path):
                return True

    return False


def encode(*args, **kwargs):
    '''Use ffmpeg to encode a video.

    This function includes the -vstats_file flag which writes out frame by
    frame output. You can watch the vstats_file using the watch function and
    provide on_frame and on_done callbacks.

    .. seealso:: main() for a concrete example

    Arguments:
        *args: ffmpeg cli arguments

    Optional Keyword Arguments:
        ffmpeg (str): Path to ffmpeg executable
    '''

    if not is_ffmpeg_available():
        raise RuntimeError(
            'Could not find ffmpeg executable.\n\n'
            'Make sure ffmpeg is on your system PATH or set the '
            'FFMPEG_LOCATION environment variable to the ffmpeg executable.'
        )

    # Get defaults
    ffmpeg = kwargs.get('ffmpeg', get_ffmpeg())

    # Platform specific kwargs
    platform_kwargs = {}

    if sys.platform == 'win32':
        CREATE_NO_WINDOW = 0x08000000
        platform_kwargs['creationflags'] = CREATE_NO_WINDOW

    # Fill cli arguments
    cmd = [ffmpeg] + list(args)

    # Create subprocess
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        **platform_kwargs
    )
    if not hasattr(proc, 'args'):
        proc.args = cmd
    return FfmpegProcess(proc)


def encode_sequence(in_file, out_file, **kwargs):
    '''Use ffmpeg to encode an image sequence to an mpeg4 video.

    Arguments:
        in_file (str): Input image sequence like my_seq.%04d.png
        out_file (str): Output filename like my_seq.mp4

    Optional Keyword Arguments:
        ffmpeg (str): Path to ffmpeg executable
        start_number (int): First frame of sequence - tries to lookup based on
            in_file if not provided.
        framerate (float): FPS - defaults to 24.0
        preset (str): libx264 preset [veryslow, slow, medium, fast, veryfast, ultrafast]
        crf (str): libx264 crf value 22 is a good default.
    '''

    preset = kwargs.pop('preset', 'slow')
    crf = kwargs.pop('crf', '22')
    start_number = kwargs.pop('start_number', None)
    if start_number is None:
        start_number = get_frame_range(in_file)[0]
    framerate = kwargs.pop('framerate', 24.0)

    return encode(
        '-y',
        '-start_number', str(start_number),
        '-r', str(framerate),
        '-f', 'image2',
        '-i', in_file,
        '-vcodec', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-preset', preset,
        '-crf', crf,
        out_file,
        **kwargs
    )


def modify_sequence(in_file, out_file, scale=1, **kwargs):
    '''Use ffmpeg to modify an image sequence.

    Arguments:
        in_file (str): Input image sequence like my_seq.%04d.png
        out_file (str): Output filename like my_seq.%04d.png

    Optional Keyword Arguments:
        ffmpeg (str): Path to ffmpeg executable
        start_number (int): First frame of sequence - tries to lookup based on
            in_file if not provided.
        framerate (float): FPS - defaults to 24.0
    '''

    start_number = kwargs.pop('start_number', None)
    if start_number is None:
        start_number = get_frame_range(in_file)[0]

    return encode(
        '-start_number', str(start_number),
        '-f', 'image2',
        '-i', in_file,
        '-vf', 'scale=iw*{0}:ih*{0}'.format(scale),
        out_file,
        **kwargs
    )


def create_thumbnail(in_file, out_file, frame="middle"):
    '''Grab a single frame from a video.

    Arguments:
        in_file (str): Path to input video or sequence.
        out_file (str): Path to output image.
        frame (int, str): Frame number as int or "start", "middle", "end", "random".
    '''

    start, end = get_frame_range(in_file)
    if frame == "start":
        frame = start
    elif frame == "middle":
        frame = start + int(((end - start) * 0.5))
    elif frame == "end":
        frame = end
    elif frame == "random":
        frame = random.choice(range(start, end))
    else:
        frame = frame

    proc = encode(
        "-i", in_file,
        "-vf", f"select=eq(n\\,{frame})",
        "-frames:v", "1",
        "-y",
        out_file,
    )
    success = watch(proc)
    if not success:
        raise RuntimeError(f'Failed to extract frame {frame} from {in_file}')

    return out_file


def create_filmstrip(in_file, out_file, frames=50, frame_width=240, tile="horizontal"):
    '''Convert a video to an image filmstrip.

    Arguments:
        in_file (str): Path to input video or sequence.
        out_file (str): Path to output image.
        frames (int): Number of frames to place in filmstrip. Defaults to 50.
        frame_width (int): Width of a single frame in the filmstrip. Defaults to 240.
        tile (str): "horizontal" or "vertical".
    '''

    start, end = get_frame_range(in_file)
    fps = get_fps(in_file)
    duration = end - start
    rate = (frames / (duration / fps))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_files = os.path.join(tmpdir, "tmp.%04d.jpeg")

        # Extract images
        proc = encode(
            "-i", in_file,
            "-r", f"{rate}",
            "-vf", f'scale={frame_width}:-1',
            "-frames:v", f"{frames}",
            "-f", "image2",
            tmp_files,
        )
        success = watch(proc)
        if not success:
            raise RuntimeError('Failed to extract frames for filmstrip.')

        # Create filmstrip
        num_images = len(os.listdir(tmpdir))
        proc = encode(
            "-i", tmp_files,
            "-vf", [f'tile=1x{num_images}', f'tile={num_images}x1'][tile=="horizontal"],
            "-an",
            "-vsync" ,"0",
            "-qscale:v", "2",
            "-pix_fmt", "yuvj420p",
            "-f", "image2",
            "-y",
            out_file,
        )
        success = watch(proc)
        if not success:
            raise RuntimeError('Failed to arrange frames in filmstrip.')

    return out_file


def watch(
    proc,
    num_frames=None,
    on_start=None,
    on_frame=None,
    on_done=None,
    on_error=None,
):
    '''Watch an FfmpegProcess until it exits. All on_* callbacks are
    passed the FfmpegProcess object that wraps a subprocess.Popen object
    and provides useful state information like the previously rendered frame,
    num_frames, progress, and captured output.

    Arguments:
        proc (FfmpegProcess): FfmpegProcess object returned by encode
        num_frames (int): Number of frames in sequence
        on_start (callable): Executed before reading from ffmpeg stdout
        on_frame (callable): Executed when a frame is reported
        on_done (callable): Executed when ffmpeg encoding succeeds
        on_error (callable): Executed when ffmpeg encoding fails

    Returns:
        True if encoding was successful
    '''

    if not num_frames:
        start_frame, end_frame = get_frame_range(proc.in_file)
        num_frames = end_frame - start_frame
        proc.num_frames = num_frames
        proc.frame = start_frame
    else:
        proc.num_frames = num_frames

    on_start = on_start or on_start_default
    on_frame = on_frame or on_frame_default
    on_done = on_done or on_done_default
    on_error = on_error or on_error_default

    on_start(proc)
    time.sleep(0.01)

    for line in io.TextIOWrapper(proc.stdout, encoding='utf-8'):
        proc.capture.append(line)
        frame = parse_frame(line)
        if frame:
            proc.set_frame(frame)
            on_frame(proc)
        time.sleep(0.01)

    if proc.wait() != 0:
        proc.error = '\n'.join(proc.capture)
        on_error(proc)
        return False
    else:
        proc.result = '\n'.join(proc.capture)
        on_done(proc)
        return True


def watch_qt(*args, **kwargs):
    '''Opens a Dialog with a progress bar for the provided FfmpegProcess.
    Similar to to the watch method but all on_* callbacks are handled by the
    Qt Dialog that this method creates.

    Only available when Qt.py and a Qt for Python binding are installed.

    Arguments:
        proc (FfmpegProcess): FfmpegProcess object returned by encode
        num_frames (int): Number of frames in sequence

    Returns:
        True if encoding was successful
    '''

    parent = kwargs.pop('parent', None)

    try:
        from Qt import QtCore
    except Exception as e:
        raise RuntimeError(
            'Qt.py and Qt for Python binding required...\n' + str(e)
        )

    from .qt import FfmpegWatchDialog
    dialog = FfmpegWatchDialog(args, kwargs, parent)
    return dialog.exec_()


def watch_tqdm(proc, *args, **kwargs):
    '''Opens a Dialog with a progress bar for the provided FfmpegProcess.
    Similar to to the watch method but all on_* callbacks are handled by the
    Qt Dialog that this method creates.

    Only available when Qt.py and a Qt for Python binding are installed.

    Arguments:
        proc (FfmpegProcess): FfmpegProcess object returned by encode
        num_frames (int): Number of frames in sequence

    Returns:
        True if encoding was successful
    '''

    try:
        from tqdm import tqdm
    except Exception as e:
        raise RuntimeError(
            'Python tqdm package is required...\n' + str(e)
        )

    return watch(
        *([proc] + list(args)),
        on_start=lambda proc: setattr(
            proc,
            'tqdm',
            tqdm(
                desc=os.path.basename(proc.out_file),
                bar_format='{desc} {bar} {n_fmt} of {total_fmt} frames',
                total=proc.num_frames,
                leave=False,
            ),
        ),
        on_frame=lambda proc: proc.tqdm.update(),
        on_done=lambda proc: proc.tqdm.close(),
        on_error=lambda proc: [proc.tqdm.close(), on_error_default(proc)]
    )


def get_resolution(in_file):
    '''Get the resolution of a file sequence or video file.'''

    # Probe resolution using ffmpeg
    cmd = [
        'ffmpeg',
        '-i', in_file,
        '-map', '0:v:0',
        '-c', 'copy',
        '-f', 'null',
        '-'
    ]
    p = subprocess.Popen(
        ['ffmpeg', '-i', in_file, '2>&1'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    out, _ = p.communicate()

    return parse_resolution(out)


def parse_resolution(string):
    '''Parses resolution from output of ffmpeg.'''

    for line in string.splitlines():
        if 'Video:' not in line:
            continue
        data = line.split('Video:')[-1]
        for chunk in data.split(','):
            match = re.match(r'\d+x\d+', chunk.strip())
            if not match:
                continue
            return [int(value) for value in match.group().split('x')]


def get_frame_range(in_file):
    '''Get the frame range of a file sequence or video file.

    Supported image sequence formats:
        extensions - .png, .jpeg, .tif, .exr
        % Tokens - my_image_sequence.%04d.png
        # Padded - my_image_sequence.####.png
        One file - my_image_sequence.0001.png

    Supported video codecs:
        Any supported ffmpeg codec
    '''

    name, ext = os.path.splitext(in_file)

    if ext in ['.png', '.jpeg', '.tif', '.exr', '.jpg', '.tiff', '.gif']:

        seq_text = None

        # Check for wildcard
        match = re.search(r'\*', in_file)
        if match:
            seq_text = match.group(0)

        # Check for % format token
        if not seq_text:
            match = re.search(r'%0\dd', in_file)
            seq_text = match.group(0)

        # Check for # frame padding
        if not seq_text:
            match = re.search(r'\#+', in_file)
            if match:
                seq_text = match.group(0)

        # Check for actual frame number
        if not seq_text:
            match = re.findall(r'\d+', in_file)
            if match:
                seq_text = match[-1]

        # Failed to detect frame number in input file
        if not seq_text:
            raise ValueError('in_file does not look like an image sequence.')

        pattern = in_file.replace(seq_text, '*')
        frame_numbers = sorted([
            int(re.findall(r'\d+', f)[-1])
            for f in glob.glob(pattern)
        ])
        return frame_numbers[0], frame_numbers[-1]

    # Probe framerange from video file using ffmpeg
    proc = subprocess.Popen(
        [
            'ffmpeg',
            '-i', in_file,
            '-map', '0:v:0',
            '-c', 'copy',
            '-f', 'null',
            '-'
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    out, _ = proc.communicate()

    frame = parse_frame(out)
    if not frame:
        raise RuntimeError('Could not probe framerange from "%s".' % in_file)

    return 1, frame


def parse_frame(string):
    '''Grab the frame number from a line of the ffmpeg log.

    Returns:
        int or None: The frame number or None when the last frame can not be determined
    '''

    matches = re.findall(r'frame=\s+(\d+)', string)
    if matches:
        return int(matches[-1])


def get_fps(in_file, default=24):
    '''Get the FPS of a video or image sequence.'''

    proc = subprocess.Popen(
        [
            'ffmpeg',
            '-i', in_file,
            '-map', '0:v:0',
            '-c', 'copy',
            '-f', 'null',
            '-'
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    out, _ = proc.communicate()
    return parse_fps(out) or default


def parse_fps(string):
    '''Grab FPS from a line in the ffmpeg log.'''

    match = re.search(r'Stream #0:0(.*)', string)
    if match:
        return int(match.group(1).split('fps,')[0].split(',')[-1].strip())


def on_start_default(proc):
    '''Default on_start callback'''

    print('Watching ffmpeg process: {}'.format(proc.pid))
    print('Input File: ' + proc.in_file)
    print('Output File: ' + proc.out_file)


def on_frame_default(proc):
    '''Default on_frame callback'''

    print('{:>8.2f}% - frame {:>4d} of {:<4d}'.format(
        proc.progress,
        proc.frame,
        proc.num_frames + 1
    ))


def on_done_default(proc):
    '''Default on_done callback'''

    print('Success!')


def on_error_default(proc):
    '''Default on_error callback'''

    print()
    print('************ ERROR ************')
    print(proc.error)
    print('*******************************')
