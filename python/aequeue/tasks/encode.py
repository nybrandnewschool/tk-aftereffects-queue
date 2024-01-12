import os
import shutil

from .. import const
from ..vendor import ffmpeg_lib
from .core import Task


class EncodeError(Exception):
    pass


class EncodeMP4(Task):
    step = const.Encoding + " MP4"

    def __init__(self, src_file, dst_file, quality, framerate, *args, **kwargs):
        self.src_file = src_file
        self.dst_file = dst_file
        self.quality = quality
        self.framerate = framerate
        super(EncodeMP4, self).__init__(*args, **kwargs)

    def on_start(self, proc):
        self.log.debug("Encoding MP4 [%s]", self.quality)
        self.log.debug(" ".join(proc.args))

    def on_frame(self, proc):
        self.set_status(const.Running, proc.progress)
        self.log.debug(f"Frame {proc.frame:>4d} of {proc.num_frames + 1:>4d}.")

    def on_error(self, proc):
        raise EncodeError("Failed to encode mp4...\n" + proc.error)

    def on_done(self, proc):
        self.log.debug("Finished encoding mp4!")

    def execute(self):
        app = self.context["app"]

        src_file = self.src_file
        src_file_info = app.engine.get_ae_path_info(src_file)

        if self.quality == "High Quality":
            crf = "18"
            preset = "veryslow"
        elif self.quality == "Medium Quality":
            crf = "22"
            preset = "medium"
        else:
            crf = "26"
            preset = "veryfast"

        if src_file_info["is_sequence"]:
            padding = "%0{}d".format(src_file_info["padding"])
            src_file = src_file.replace(src_file_info["padding_str"], padding)
            proc = ffmpeg_lib.encode_sequence(
                in_file=src_file,
                out_file=self.dst_file,
                framerate=self.framerate,
                crf=crf,
                preset=preset,
            )
        else:
            proc = ffmpeg_lib.encode(
                "-y",
                "-i",
                src_file,
                "-acodec",
                "aac",
                "-vcodec",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-profile:v",
                "main",
                "-vendor",
                "apl0",
                "-tune",
                "stillimage",
                "-crf",
                crf,
                "-preset",
                preset,
                self.dst_file,
            )
        ffmpeg_lib.watch(
            proc,
            on_start=self.on_start,
            on_frame=self.on_frame,
            on_error=self.on_error,
            on_done=self.on_done,
        )
        return self.dst_file


class EncodeGIF(Task):
    step = const.Encoding + " GIF"

    def __init__(self, src_file, dst_file, quality, framerate, *args, **kwargs):
        self.src_file = src_file
        self.dst_file = dst_file
        self.quality = quality
        self.framerate = framerate
        super(EncodeGIF, self).__init__(*args, **kwargs)

    def on_start(self, proc):
        self.log.debug("Encoding GIF [%s]", self.quality)
        self.log.debug(" ".join(proc.args))

    def on_frame(self, proc):
        self.set_status(const.Running, proc.progress)
        self.log.debug(f"Frame {proc.frame:>4d} of {proc.num_frames + 1:>4d}.")

    def on_error(self, proc):
        self.set_status(const.Failed, proc.progress)
        raise EncodeError("Failed to encode mp4...\n" + proc.error)

    def on_done(self, proc):
        self.log.debug("Finished encoding mp4!")

    def execute(self):
        app = self.context["app"]

        src_file = self.src_file
        src_file_info = app.engine.get_ae_path_info(src_file)
        if src_file_info["is_sequence"]:
            padding = "%0{}d".format(src_file_info["padding"])
            src_file = src_file.replace(src_file_info["padding_str"], padding)

        # Prepare cli arguments
        width = None
        resolution = ffmpeg_lib.get_resolution(src_file)
        if resolution:
            width = resolution[0]
        if width:
            max_width = min(width, 2160)
            if self.quality == "Low Quality":
                width = int(max_width * 0.25)
            elif self.quality == "Medium Quality":
                width = int(max_width * 0.5)
            else:
                width = max_width

        fps = self.framerate
        scale = ("", f"scale={width}:-1:flags=lanczos,")[bool(width)]
        colors = 128
        dither = ""  # 'dither=bayer:bayer_scale=3:'
        filters = [
            f"[0:v] fps={fps},{scale}split [a][b]",
            f"[a] palettegen=max_colors={colors}:stats_mode=diff [p]",
            f"[b][p] paletteuse={dither}diff_mode=rectangle",
        ]
        proc = ffmpeg_lib.encode(
            "-i",
            src_file,
            "-filter_complex",
            ";".join(filters),
            "-loop",
            "0",
            "-gifflags",
            "+transdiff",
            "-y",
            self.dst_file,
        )
        ffmpeg_lib.watch(
            proc,
            on_start=self.on_start,
            on_frame=self.on_frame,
            on_error=self.on_error,
            on_done=self.on_done,
        )
        return self.dst_file
