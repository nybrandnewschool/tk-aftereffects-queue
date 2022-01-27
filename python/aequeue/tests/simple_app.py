from math import floor
from random import uniform

from ..vendor.Qt import QtCore

from .. import const, resources
from ..widgets import Window
from ..options import RenderOptions


def clamp(value, mn, mx):
    return min(max(value, mn), mx)


def fit(value, omin, omax, nmin, nmax):
    nvalue = (((value - omin) * (nmax - nmin)) / (omax - omin)) + nmin
    return clamp(nvalue, nmin, nmax)


def fit100(value, mn, mx):
    return fit(value, mn, mx, 0, 100)


def percent_to_status(percent, statuses):
    index = int(floor((percent / 100.0) * (len(statuses) - 1)))
    return statuses[index]


def statuses_for_options(options):
    check_statuses = [
        (bool(False), const.Queued),
        (bool(options.module), const.Rendering),
        (bool(options.mp4), const.Encoding),
        (bool(options.gif), const.Encoding),
        (bool(const.Copying), const.Copying),
        (bool(options.sg), const.Uploading),
        (bool(const.Done), const.Done),
    ]
    return [status for has_status, status in check_statuses if has_status]


class MockRenderPipeline(QtCore.QObject):

    status_changed = QtCore.Signal(str)
    item_status_changed = QtCore.Signal([str, str, int])
    done = QtCore.Signal()
    interval = 50

    def __init__(self, items, options, parent=None):
        super(MockRenderPipeline, self).__init__(parent)
        self.statuses = statuses_for_options(options)
        self.items = items
        self.options = options
        self.states = {
            item: {
                'start': int(uniform(1, 20)),
                'duration': int(uniform(100, 200)),
                'status': 'queued',
                'percent': 0,
            } for item in self.items
        }
        self._time = 0
        self._timer = None
        self._done = False
        self.set_status(const.Waiting)

    def __call__(self):
        self._time += 1
        unfinished_items = []
        for item in self.items:
            state = self.states[item]
            state['percent'] = fit100(
                self._time,
                state['start'],
                state['start'] + state['duration'],
            )
            state['status'] = percent_to_status(
                state['percent'],
                self.statuses,
            )
            self.item_status_changed.emit(
                item, state['status'], state['percent']
            )
            if state['status'] != const.Done:
                unfinished_items.append(item)

        if not unfinished_items:
            self._done = True
            self.done.emit()

    def set_status(self, status):
        self.status = status
        self.status_changed.emit(status)

    def run(self):
        if self._timer and self._timer.isActive():
            return

        # Create QTimer
        # Simulates multiple items executing and emits their changing statuses
        self._timer = None
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(self.interval)
        self._timer.timeout.connect(self)
        self.done.connect(self._timer.stop)
        self.done.connect(lambda: self.set_status(const.Success))

        # Start Timer
        self._timer.start()
        self.set_status(const.Running)


class TestApplication(QtCore.QObject):

    def __init__(self, nitems, parent=None):
        super(TestApplication, self).__init__(parent)

        self.items = ['Comp {:0>2d}'.format(i) for i in range(nitems)]
        self.pipeline = None

        # Create UI
        self.ui = Window()
        self.ui.queue_button.clicked.connect(self.load_queue)
        self.ui.render_button.clicked.connect(self.render)
        self.ui.reset_button.clicked.connect(self.reset_queue)

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
        # Create and connect render pipeline
        self.pipeline = MockRenderPipeline(
            items=self.items,
            options=RenderOptions(**self.ui.options.get()),
            parent=self,
        )
        self.pipeline.item_status_changed.connect(self.ui.queue.update_item)
        self.pipeline.status_changed.connect(self.set_render_status)

        # Simulate Render Pipeline
        self.pipeline.run()

    def set_render_status(self, status):
        self.ui.set_status(status)

