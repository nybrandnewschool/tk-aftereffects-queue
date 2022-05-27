import os
import re
import sys
import subprocess
import time

sys.path.insert(1, os.path.abspath('python'))

from aequeue.vendor.Qt import QtCore, QtWidgets
from aequeue.render import AERenderProcess, AERenderProcess


def on_progress(event):
    print(f'{event["progress"]:>3d}% - {event["message"]}')


def on_status(event):
    print(f'{event["status"]} - {event["message"]}')


def on_finished():
    print('FINISHED!!')


def main():
    app = QtWidgets.QApplication([])
    proc = AERenderProcess(
        project='G:/Shared drives/22-XXX-TestA/animation/shots/seqA/seqa_031/animation/work/ae/anim_seqa_031_v043.aep',
        comp='anim_seqa_031_v043',
        omtemplate='BNS - ProRes 4444+',
        output='G:/Shared drives/22-XXX-TestA/animation/shots/seqA/seqa_031/animation/work/ae/tmp.mov',
    )
    proc.status_changed.connect(on_status)
    proc.progress_changed.connect(on_progress)
    proc.finished.connect(on_finished)
    proc.finished.connect(app.quit)
    proc.start()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
