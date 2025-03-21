import os

from .. import const
from ..render import AERenderSubprocess
from .core import Task, SyncTask, fit


class AERenderFailed(Exception):
    pass


class AERenderComp(SyncTask):
    step = const.Rendering

    def __init__(
        self,
        project,
        comp,
        output_module,
        render_settings,
        output_path,
        *args,
        **kwargs,
    ):
        self.project = project
        self.comp = comp
        self.output_module = output_module
        self.render_settings = render_settings
        self.output_path = output_path
        self.output_folder = os.path.dirname(output_path)
        super(AERenderComp, self).__init__(*args, **kwargs)

    def execute(self):
        # Get required context data
        app = self.context["app"]

        self.log.debug("Preparing output path...")
        # Create output module for comp
        comp_item = app.engine.get_comp(self.comp)
        rq_item = app.engine.enqueue_comp(comp_item)
        om = rq_item.outputModule(1)
        self.set_status(const.Running, 10)

        # Ensure output folder exists
        try:
            os.makedirs(self.output_folder, exist_ok=True)
        except Exception:
            raise RuntimeError("Failed to create output folder %s" % self.output_folder)

        # Apply render setting template
        self.log.debug("Applying Render Setting [%s]", self.render_settings)
        rq_item.applyTemplate(self.render_settings)
        self.set_status(const.Running, 20)

        # Apply output module template
        self.log.debug("Applying Output Module [%s]", self.output_module)
        om.applyTemplate(self.output_module)
        self.set_status(const.Running, 40)

        # Apply output path
        self.log.debug("Setting Full Flat Path: %s" % self.output_path)
        app.engine.set_file_info(om, {"Full Flat Path": self.output_path})
        self.log.debug("Output File Info: %s", om.getSetting("Output File Info"))
        self.set_status(const.Running, 60)

        # Check for cancelled before rendering - once started we can't cancel.
        if self.status_request == const.Cancelled:
            return self.accept(const.Cancelled)

        success = app.engine.render_queue_item(rq_item)
        if not success:
            raise AERenderFailed("Failed to render queue item: %s" % self.comp)

        self.set_status(const.Running, 100)
        return self.output_path


class BackgroundAERenderComp(Task):
    step = const.Rendering

    def __init__(
        self,
        project,
        comp,
        output_module,
        render_settings,
        output_path,
        *args,
        **kwargs,
    ):
        self.project = project
        self.comp = comp
        self.output_module = output_module
        self.render_settings = render_settings
        self.output_path = output_path
        self.output_folder = os.path.dirname(output_path)
        super(BackgroundAERenderComp, self).__init__(*args, **kwargs)

    def on_render_status_changed(self, event):
        self.set_status(event["status"])

    def on_render_progress_changed(self, event):
        self.set_status(const.Running, fit(event["progress"], 0, 100, 20, 100))

    def request(self, status):
        self.log.debug("%s requested..." % status.upper())
        self.status_request = status
        if self.render:
            self.render.status_request = status

    def execute(self):
        # Get required context data
        app = self.context["app"]

        self.log.debug("Rendering AEComp...")

        # Ensure output folder exists
        try:
            os.makedirs(self.output_folder, exist_ok=True)
        except Exception:
            raise RuntimeError("Failed to create output folder %s" % self.output_folder)
        self.set_status(const.Running, 10)

        # Cancel check
        if self.status_request == const.Cancelled:
            return self.accept(const.Cancelled)

        self.render = AERenderSubprocess(
            project=self.project,
            comp=self.comp,
            omtemplate=self.output_module,
            rstemplate=self.render_settings,
            output=os.path.normpath(self.output_path),
            version=self.context["host_version"],
        )
        self.log.debug(
            "Render Arguments: %s" % ([self.render.executable] + self.render.arguments)
        )
        self.render.status_changed.connect(self.on_render_status_changed)
        self.render.progress_changed.connect(self.on_render_progress_changed)
        self.render.start()
        self.set_status(const.Running, 20)

        # AERenderSubprocess - uses subprocess.Popen
        status = self.render.wait()
        if status == const.Cancelled:
            return self.accept(const.Cancelled)

        # # AERenderProcess - uses QProcess
        # # Check for cancel request while waiting for render to finish.
        # while not self.render.wait(1000):
        #     if self.status_request == const.Cancelled:
        #         self.render.kill()
        #         return self.accept(const.Cancelled)

        # Raise Error if render process failed.
        state = self.render.finished_state()
        if state["status"] == const.Failed:
            raise RuntimeError(state["message"])

        # Ensure progress reaches 100
        self.set_status(const.Success, 100)

        return self.output_path


def backup(file, is_sequence=False):
    backup = file + ".tmp"
    shutil.move(file, file + ".bak")
