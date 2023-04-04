from collections import namedtuple


RenderOptionsType = namedtuple(
    "RenderOptions",
    [
        "settings",
        "module",
        "keep_original",
        "mp4",
        "mp4_quality",
        "gif",
        "gif_quality",
        "sg",
        "sg_comment",
        "bg",
        "bg_threads",
    ],
)


class RenderOptions(RenderOptionsType):
    """A dataclass holding all of the options required for rendering."""

    def dict(self):
        return self._asdict()
