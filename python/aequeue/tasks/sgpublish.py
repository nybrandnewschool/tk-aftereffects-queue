import os
import tempfile

from .. import const
from ..vendor import ffmpeg_lib
from .core import Task


def get_shotgun():
    from sgtk.util.shotgun import create_sg_connection

    return create_sg_connection()


def register_publish(*args, **kwargs):
    from sgtk.util import register_publish

    return register_publish(*args, **kwargs)


class SGPublish(Task):
    step = const.Publishing

    def __init__(self, file, sg_ctx, version_task, *args, **kwargs):
        self.file = file
        self.thumbnail_src_file = kwargs.pop("thumbnail_src_file", None)
        self.sg_ctx = sg_ctx
        self.version_task = version_task
        super(SGPublish, self).__init__(*args, **kwargs)

    def execute(self):
        # Get necessary data from task context
        app = self.context["app"]
        options = self.context["options"]
        version = self.version_task.result

        file = self.file
        file_info = app.engine.get_ae_path_info(file)
        if file_info["is_sequence"]:
            file = file.replace(
                file_info["padding_str"], "%{:0>2}d".format(file_info["padding"])
            )

        self.log.debug("Preparing publish data for ShotGrid...")
        dirname, basename = os.path.split(file)
        filename, ext = os.path.splitext(basename)
        code = filename.split(".")[0]
        if file_info["version"]:
            name = code.split(file_info["version"])[0].rstrip("._-") + ext
        else:
            name = code + ext

        publish_data = {
            "tk": app.engine.sgtk,
            "context": self.sg_ctx,
            "path": file,
            "name": name,
            "version_number": file_info["version_number"],
            "version_entity": version,
            "comment": version["description"],
            "published_file_type": file_info["published_file_type"],
        }
        self.set_status(const.Running, 25)

        # Check for cancelled before publshing.
        if self.status_request == const.Cancelled:
            return self.accept(const.Cancelled)

        # Get an instance of SG for this thread
        sg = get_shotgun()

        publish = self.create_publish(sg, publish_data)
        self.set_status(const.Running, 50)

        self.upload_thumbnail_and_filmstrip(
            sg,
            publish,
            self.thumbnail_src_file or file,
        )
        self.set_status(const.Running, 100)

        return version

    def create_publish(self, sg, publish_data):
        """Get existing version or create a new one."""

        self.log.debug("Checking if Publish already exists...")
        return_fields = [
            "id",
            "code",
            "project",
            "task",
            "entity",
            "version_number",
            "path",
        ]
        prepublish_data = register_publish(**dict(dry_run=True, **publish_data))
        publish = sg.find_one(
            "PublishedFile",
            filters=[
                ["project", "is", prepublish_data["project"]],
                ["code", "is", prepublish_data["code"]],
                ["version_number", "is", prepublish_data["version_number"]],
                ["task", "is", prepublish_data["task"]],
                ["entity", "is", prepublish_data["entity"]],
            ],
            fields=return_fields,
        )

        if not publish:
            self.log.debug("Creating new Publish in ShotGrid...")
            app = self.context["app"]
            publish = register_publish(**publish_data)
        else:
            self.log.debug("Updated existing Publish in ShotGrid...")
            sg.update(
                "PublishedFile",
                publish["id"],
                {"version": publish_data["version_entity"]},
            )

        return publish

    def upload_thumbnail_and_filmstrip(self, sg, publish, in_file):
        name = os.path.splitext(os.path.basename(in_file))[0]

        with tempfile.TemporaryDirectory() as tempdir:
            self.log.debug("Creating and uploading thumbnail...")
            thumbnail = os.path.join(tempdir, name + ".jpeg")
            ffmpeg_lib.create_thumbnail(in_file, thumbnail, frame="middle")
            sg.upload_thumbnail(
                "PublishedFile",
                publish["id"],
                thumbnail,
            )
            self.set_status(const.Running, 70)

            self.log.debug("Creating and uploading filmstrip...")
            filmstrip = os.path.join(tempdir, name + "_filmstrip.jpeg")
            ffmpeg_lib.create_filmstrip(in_file, filmstrip)
            sg.upload_filmstrip_thumbnail(
                "PublishedFile",
                publish["id"],
                filmstrip,
            )
            self.set_status(const.Running, 90)
