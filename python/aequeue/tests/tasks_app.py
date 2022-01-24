from ..vendor.Qt import QtWidgets, QtCore

from .. import const, resources
from ..options import RenderOptions
from ..widgets import Window
from ..tasks.core import Runner, Flow
from ..tasks.generic import LongRunningTask


def new_flow(item, options):
    with Flow(item) as flow:
        LongRunningTask(steps=10, step=const.Rendering)

        if options.mp4:
            LongRunningTask(steps=10, step=const.Encoding + ' MP4')
            LongRunningTask(steps=10, step=const.Copying)

        if options.gif:
            LongRunningTask(steps=10, step=const.Encoding + ' GIF')
            LongRunningTask(steps=10, step=const.Copying)

        if options.sg:
            LongRunningTask(steps=10, step=const.Uploading)

    return flow


class TestApplication(QtCore.QObject):

    def __init__(self, nitems, parent=None):
        super(TestApplication, self).__init__(parent)

        self.items = ['Comp {:0>2d}'.format(i) for i in range(nitems)]
        self.runner = None

        # Create UI
        self.ui = Window()
        self.ui.queue_button.clicked.connect(self.load_queue)
        self.ui.render.clicked.connect(self.render)
        self.ui.closeEvent = self.closeEvent

    def closeEvent(self, event):
        if self.runner and self.runner.status == const.Running:
            self.ui.show_error("Can't close while rendering.")
            event.ignore()
        else:
            return QtWidgets.QWidget.closeEvent(self.ui, event)

    def show(self):
        self.ui.show()

    def load_queue(self):
        self.ui.queue.clear()
        for item in self.items:
            self.ui.queue.add_item(item, const.Queued, 0)
        self.set_render_status(const.Waiting)

    def render(self):

        options = RenderOptions(**self.ui.options.get())

        with Runner('Render and Review') as runner:
            prev_flow = None
            for item in self.items:
                flow = new_flow(item, options)
                if prev_flow:
                    flow.depends_on(prev_flow.tasks[0])
                prev_flow = flow

        self.runner = runner
        self.runner.step_changed.connect(self.step_changed)
        self.runner.status_changed.connect(self.set_render_status)
        self.runner.start()

    def step_changed(self, event):
        self.ui.queue.update_item(
            label=event['flow'],
            status=event['step'],
            percent=event['progress'],
        )

    def set_render_status(self, status):
        if status == const.Waiting:
            self.ui.options_header.label.setText('OPTIONS')
            self.ui.options.setEnabled(True)
            self.ui.render.setEnabled(True)
            self.ui.queue_button.setVisible(True)

            self.ui.render.enable_movie(False)
            self.ui.render.set_height(36)
        if status == const.Running:
            self.ui.options_header.label.setText('STATUS')
            self.ui.options.setEnabled(False)
            self.ui.render.setEnabled(False)
            self.ui.queue_button.setVisible(False)

            movie = resources.get_path(const.Running.title() + '.gif')
            self.ui.render.set_movie(movie)
            self.ui.render.enable_movie(True)
            self.ui.render.set_height(
                self.ui.options_header.height()
                + self.ui.options.height()
            )
        if status in [const.Failed, const.Success]:
            self.ui.options_header.label.setText('STATUS')
            self.ui.options.setEnabled(False)
            self.ui.render.setEnabled(False)
            self.ui.queue_button.setVisible(True)

            movie = resources.get_path(status.title() + '.gif')
            self.ui.render.add_movie_to_queue(movie)
