from collections import namedtuple

RenderOptionsType = namedtuple(
    "RenderOptions",
    [
        "settings",
        "module",
        "keep_original",
        "mp4",
        "mp4_quality",
        "mp4_resolution",
        "gif",
        "gif_quality",
        "gif_resolution",
        "sg",
        "sg_comment",
        "bg",
        "bg_threads",
        "async_render",
    ],
)


class RenderOptions(RenderOptionsType):
    """A dataclass holding all of the options required for rendering."""

    def dict(self):
        return self._asdict()
