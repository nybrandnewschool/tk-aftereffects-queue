from ..vendor.qtpy import QtCore

from ..widgets import Window


class TestApplication(QtCore.QObject):

    def __init__(self, nitems, parent=None):
        super(TestApplication, self).__init__(parent)

        self.ui = Window()
        self.ui.queue_button.clicked.connect(self.load_queue)
        self.ui.render_button.clicked.connect(self.render)

    def show(self):
        self.ui.show()

    def load_queue(self):
        self.ui.show_error('Select some Comps to queue...')

    def render(self):
        self.ui.show_info('Render something...')
