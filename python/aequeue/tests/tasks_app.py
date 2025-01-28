from ..vendor.qtpy import QtWidgets, QtCore

from .. import const, resources
from ..options import RenderOptions
from ..widgets import Window
from ..tasks.core import Runner, Flow, generate_report, generate_html_report
from ..tasks.generic import LongRunningTask, ErrorTask


def new_flow(item, options):
    with Flow(item) as flow:
        LongRunningTask(steps=10, step=const.Rendering)
        if options.mp4:
            LongRunningTask(steps=10, step=const.Encoding + ' MP4')
            LongRunningTask(steps=10, step=const.Copying + ' MP4')

        if options.gif:
            LongRunningTask(steps=10, step=const.Encoding + ' GIF')
            LongRunningTask(steps=10, step=const.Copying + ' GIF')

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
        self.ui.reset_button.clicked.connect(self.reset_queue)
        self.ui.render_button.clicked.connect(self.render)
        self.ui.closeEvent = self.closeEvent

    def closeEvent(self, event):
        if self.runner and self.runner.status == const.Running:
            self.ui.show_error("Can't close while rendering.")
            event.ignore()
        else:
            return QtWidgets.QWidget.closeEvent(self.ui, event)

    def show(self):
        self.ui.show()

    def reset_queue(self):
        self.ui.queue.clear()
        self.set_render_status(const.Waiting)

    def load_queue(self):
        self.ui.queue.clear()
        for item in self.items:
            self.ui.queue.add_item(item, const.Queued, 0)
        self.set_render_status(const.Waiting)

    def render(self):
        if not self.ui.queue.count():
            self.ui.show_error('Load items into the queue first.')
            return

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
        if status in const.DoneList:
            self.ui.report.setText(generate_html_report(self.runner))
        self.ui.set_status(status)
