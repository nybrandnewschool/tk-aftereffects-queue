import sys


# Various Test Methods
def requires_event_loop(fn):
    def call_fn(*args, **kwargs):
        from ..vendor.Qt import QtWidgets

        if QtWidgets.QApplication.instance():
            return fn(*args, **kwargs)

        event_loop = QtWidgets.QApplication([])
        obj = fn(*args, **kwargs)
        sys.exit(event_loop.exec_())

    return call_fn


@requires_event_loop
def show_test_ui():
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

@requires_event_loop
def show_simple_app():
    from .simple_app import TestApplication

    app = TestApplication(nitems=5)
    app.show()
    return app


@requires_event_loop
def show_tasks_app():
    from .tasks_app import TestApplication

    app = TestApplication(nitems=5)
    app.show()
    return app


@requires_event_loop
def show_toast_app():
    from .toast_app import TestApplication

    app = TestApplication(nitems=5)
    app.show()
    return app


@requires_event_loop
def show_item_menus_app():
    from .item_menus_app import TestApplication

    app = TestApplication(nitems=4)
    app.show()
    return app
