from .. import const
from ..vendor import ffmpeg_lib
from .core import Task


class EncodeError(Exception):
    pass


class EncodeMP4(Task):
    step = const.Encoding + " MP4"

    def __init__(self, src_file, dst_file, quality, resolution, framerate, *args, **kwargs):
        self.src_file = src_file
        self.dst_file = dst_file
        self.quality = quality
        self.resolution = resolution
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
        elif self.quality == "Low Quality":
            crf = "26"
            preset = "veryfast"
        else:
            crf = "30"
            preset = "veryfast"

        scale_filter = get_scale_filter(self.resolution)
        if scale_filter:
            scale = ("-vf", scale_filter)
        else:
            scale = ("",)

        if src_file_info["is_sequence"]:
            padding = "%0{}d".format(src_file_info["padding"])
            src_file = src_file.replace(src_file_info["padding_str"], padding)
            start_number = ffmpeg_lib.get_frame_range(src_file)[0]
            proc = ffmpeg_lib.encode(
                '-y',
                '-start_number', str(start_number),
                '-r', str(self.framerate),
                '-f', 'image2',
                '-i', src_file,
                '-vcodec', 'libx264',
                '-pix_fmt', 'yuv420p',
                *scale,
                "-profile:v", "main",
                "-g", "1",
                "-vendor", "apl0",
                "-tune", "stillimage",
                '-crf', crf,
                '-preset', preset,
                self.dst_file
            )
        else:
            proc = ffmpeg_lib.encode(
                "-y",
                "-i", src_file,
                "-acodec", "aac",
                "-vcodec", "libx264",
                "-pix_fmt", "yuv420p",
                *scale,
                "-profile:v", "main",
                "-g", "1",
                "-vendor", "apl0",
                "-tune", "stillimage",
                "-crf", crf,
                "-preset", preset,
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

    def __init__(self, src_file, dst_file, quality, resolution, framerate, *args, **kwargs):
        self.src_file = src_file
        self.dst_file = dst_file
        self.quality = quality
        self.resolution = resolution
        self.framerate = int(framerate)
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
        fps = self.framerate
        scale_filter = get_scale_filter(self.resolution)
        scale = ("", f"{scale_filter}:flags=lanczos,")[bool(scale_filter)]
        colors = {
            "High Quality": 256,
            "Medium Quality": 128,
            "Low Quality": 64,
            "Min Quality": 32,
        }.get(self.quality)
        dither = ""  # 'dither=bayer:bayer_scale=3:'
        filters = [
            f"[0:v] fps={fps},{scale}split [a][b]",
            f"[a] palettegen=max_colors={colors}:stats_mode=diff [p]",
            f"[b][p] paletteuse={dither}diff_mode=rectangle",
        ]
        proc = ffmpeg_lib.encode(
            "-y",
            "-i", src_file,
            "-filter_complex", ";".join(filters),
            "-loop", "0",
            "-gifflags", "+transdiff",
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


def get_scale_filter(resolution="Full"):
    if resolution == "Full":
        return ""
    if resolution == "Half":
        return "scale='iw/2:ih/2'"
    if resolution == "Quarter":
        return "scale='iw/4:ih/4'"

    rint = int(resolution)
    return f"scale='if(gte(iw,ih),{rint},-2)':'if(gte(iw,ih),-2,{rint})'"
