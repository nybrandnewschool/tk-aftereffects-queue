import sys
from functools import wraps


apps = {}


def application(name):
    def wrap_fn(fn):
        @wraps(fn)
        def call_fn(*args, **kwargs):
            from ..vendor.Qt import QtWidgets

            if QtWidgets.QApplication.instance():
                return fn(*args, **kwargs)

            event_loop = QtWidgets.QApplication([])
            obj = fn(*args, **kwargs)
            sys.exit(event_loop.exec_())

        apps[name] = call_fn
        return call_fn
    return wrap_fn

# Test Applications

@application('test_ui')
def show_test_ui():
    '''Basic UI for viewing styling.'''

    from random import choice
    from ..widgets import Window

    win = Window()
    win.show()

    statuses = [
        ('queued', range(0, 20)),
        ('rendering', range(20, 40)),
        ('encoding', range(40, 60)),
        ('copying', range(60, 80)),
        ('uploading', range(80, 100)),
        ('done', range(99, 100)),
    ]
    for i in range(10):
        status, values = choice(statuses)
        win.queue.add_item(f'Comp {i+1:0>2d}', status, choice(values))
    return win

@application('simple_app')
def show_simple_app():
    '''Simple render test using Mock tasks.'''

    from .simple_app import TestApplication

    app = TestApplication(nitems=5)
    app.show()
    return app


@application('tasks_app')
def show_tasks_app():
    '''Advanced render test using Flow and Task objects.'''

    from .tasks_app import TestApplication

    app = TestApplication(nitems=4)
    app.show()
    return app


@application('toast_app')
def show_toast_app():
    '''Test Toast popups when buttons are pressed.'''

    from .toast_app import TestApplication

    app = TestApplication(nitems=5)
    app.show()
    return app


@application('item_menus_app')
def show_item_menus_app():
    '''Test Kebab Menus for each render item.'''

    from .item_menus_app import TestApplication

    app = TestApplication(nitems=4)
    app.show()
    return app


@application('ae_dragndrop')
def show_ae_dragndrop():
    '''Debug drag and drop of CompItems from AE.'''

    from .ae_dragndrop import TestApplication

    app = TestApplication()
    app.show()
    return app
