# -*- coding: utf-8 -*-
# Standard library imports
import os

# Local imports
from . import icon, watch

# Third party imports
from ..Qt import QtCore, QtWidgets, QtGui


class FfmpegErrorDialog(QtWidgets.QDialog):

    def __init__(self, message, parent):
        super(FfmpegErrorDialog, self).__init__(parent)

        self.setWindowTitle('Error')
        self.setWindowIcon(QtGui.QIcon(icon))
        self.setWindowFlags(
            self.windowFlags() |
            QtCore.Qt.WindowStaysOnTopHint
        )

        self.label = QtWidgets.QLabel('Failed to encode!')
        self.text = QtWidgets.QPlainTextEdit(message)
        self.text.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)

        self.button = QtWidgets.QPushButton('Dismiss')
        self.button.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum,
        )
        self.button.clicked.connect(self.accept)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setStretch(1, 1)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.text)
        self.layout.addWidget(self.button)
        self.layout.setAlignment(self.button, QtCore.Qt.AlignRight)
        self.setLayout(self.layout)


class FfmpegWatchDialog(QtWidgets.QDialog):

    def __init__(self, args, kwargs, parent):
        super(FfmpegWatchDialog, self).__init__(parent)

        # Window options
        self.setWindowTitle('Progress')
        self.setWindowIcon(QtGui.QIcon(icon))
        self.setWindowFlags(
            self.windowFlags() |
            QtCore.Qt.WindowStaysOnTopHint
        )

        # Layout widgets
        self.label = QtWidgets.QLabel('Starting...')
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        self.progress.setAlignment(QtCore.Qt.AlignCenter)
        self.progress.setFormat('starting')
        self.frame = QtWidgets.QLabel()
        self.button = QtWidgets.QPushButton('Cancel')
        self.button.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum,
        )
        self.button.clicked.connect(self.on_cancel)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.progress)
        self.layout.addWidget(self.frame)
        self.layout.addWidget(self.button)
        self.layout.setAlignment(self.button, QtCore.Qt.AlignRight)
        self.setLayout(self.layout)

        # Start thread
        self.thread = WatchThread(args, kwargs)
        self.thread.on_start.connect(self.on_start)
        self.thread.on_frame.connect(self.on_frame)
        self.thread.on_done.connect(self.on_done)
        self.thread.on_error.connect(self.on_error)
        self.thread.start()

    def on_start(self, proc):
        self.proc = proc
        self.label.setText('Encoding ' + os.path.basename(proc.out_file))

    def on_frame(self, proc):
        percent = '{:0.0f}%'.format(proc.progress)
        self.progress.setValue(proc.progress)
        self.progress.setFormat(percent)
        text = 'frame {:0.0f} of {:0.0f}'.format(
            proc.frame,
            proc.num_frames + 1
        )
        self.frame.setText(text)

    def on_done(self, proc):
        self.label.setText('Encoding complete!')
        QtCore.QTimer.singleShot(2000, self.accept)

    def on_error(self, proc):
        self.label.setText('Failed to encode!')
        QtCore.QTimer.singleShot(1000, self.reject)
        error_message = FfmpegErrorDialog(proc.error, self.parent())
        error_message.exec_()

    def on_cancel(self):
        self.label.setText('Cancelling...')
        self.proc.kill()
        self.proc.wait()
        try:
            if os.path.isfile(self.proc.out_file):
                os.remove(self.proc.out_file)
        except OSError:
            pass
        self.reject()


class WatchThread(QtCore.QThread):

    on_start = QtCore.Signal(object)
    on_frame = QtCore.Signal(object)
    on_done = QtCore.Signal(object)
    on_error = QtCore.Signal(object)

    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs
        super(WatchThread, self).__init__()

    def run(self):
        self.kwargs['on_start'] = self.on_start.emit
        self.kwargs['on_frame'] = self.on_frame.emit
        self.kwargs['on_done'] = self.on_done.emit
        self.kwargs['on_error'] = self.on_error.emit
        watch(*self.args, **self.kwargs)
