from random import uniform

from .. import const, resources
from ..widgets import Window
from ..vendor.qtpy import QtCore


def toast_action(ui, item, action):
    def execute_toast_action():
        r = uniform(0, 1)
        if r < 0.334:
            ui.show_info('%s: executing action "%s"' % (item, action))
        elif r < 0.667:
            ui.show_error('%s: executing action "%s"' % (item, action))
        else:
            ui.show_warning('%s: executing action "%s"' % (item, action))
    return execute_toast_action


class TestApplication(QtCore.QObject):

    def __init__(self, nitems, parent=None):
        super(TestApplication, self).__init__(parent)

        self.items = ['Comp {:0>2d}'.format(i) for i in range(nitems)]
        self.ui = Window()
        self.load_queue()

    def show(self):
        self.ui.show()

    def load_queue(self):
        self.ui.queue.clear()
        for item in self.items:
            self.ui.queue.add_item(item, const.Done, 100)
            actions = int(uniform(0, 6))
            if not actions:
                continue
            for i in range(int(uniform(1, 6))):
                label = 'Action {:0>2d}'.format(i)
                self.ui.queue.add_item_action(
                    item,
                    action_label=label,
                    action_callback=toast_action(self.ui, item, label),
                    action_icon=(None, resources.get_path('info.png'))[int(uniform(0, 1.999))],
                )
