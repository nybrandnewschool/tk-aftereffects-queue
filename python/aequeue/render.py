import io
import os
import re
import subprocess
import sys
import time

from .vendor.Qt import QtCore
from . import const


AERENDER_PATTERNS = {
    'start': re.compile(r'PROGRESS:  Start: (\d[:;]\d\d[:;]\d\d[:;]\d\d)'),
    'end': re.compile(r'PROGRESS:  End: (\d[:;]\d\d[:;]\d\d[:;]\d\d)'),
    'duration': re.compile(r'PROGRESS:  Duration: (\d[:;]\d\d[:;]\d\d[:;]\d\d)'),
    'framerate': re.compile(r'PROGRESS:  Frame Rate: (\d+.\d+)'),
    'progress': re.compile(r'PROGRESS:  (\d[:;]\d\d[:;]\d\d[:;]\d\d) \((\d+)\): \d+ Seconds'),
    'error': re.compile(r'aerender Error:\s*(.*)$'),
}


class AERenderProcess(QtCore.QProcess):

    status_changed = QtCore.Signal(object)
    progress_changed = QtCore.Signal(object)

    def __init__(self, project, comp, omtemplate, output, version=None, parent=None):
        super(AERenderProcess, self).__init__(parent=parent)

        # Process start arguments
        self.project = os.path.normpath(project)
        self.comp = comp
        self.omtemplate = omtemplate
        self.output = os.path.normpath(output)
        self.version = version
        self.executable = get_executable(version)
        self.arguments = get_arguments(project, comp, omtemplate, output)

        # Process handlers
        self._finished = False
        self._finished_state = {}
        self.readyReadStandardOutput.connect(self.handle_stdout)
        self.readyReadStandardError.connect(self.handle_stderr)
        self.stateChanged.connect(self.handle_state)
        self.finished.connect(self.handle_finish)

        self.render_state = {
            'progress': 0,
            'start': '',
            'end': '',
            'duration': '',
            'framerate': '',
            'frame_duration': 0,
            'status': const.Waiting,
        }

    def handle_stderr(self):
        data = self.readAllStandardError()
        stderr = bytes(data).decode("utf8")

    def handle_stdout(self):
        data = self.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        for line in stdout.splitlines():
            self.parse_line(line)

    def parse_line(self, text):
        for name, pattern in AERENDER_PATTERNS.items():
            match = pattern.search(text)
            if not match:
                continue
            if name == 'error':
                self.render_state['status'] = const.Failed
                self.status_changed.emit({
                    'status': const.Failed,
                    'message': match.group(1),
                })
                raise RuntimeError('Failed to render: %s' % match.group(1))
            elif name in ['start', 'end', 'duration', 'framerate']:
                self.render_state[name] = match.group(1)
                if name == 'framerate':
                    framerate = float(match.group(1))
                    duration = self.render_state['duration']
                    hours, minutes, seconds, frames = re.split(r'[:;]', duration)
                    seconds = int(seconds) + int(hours) * 3600 + int(minutes) * 60
                    frame_duration = int(frames) + int(framerate * seconds) - 1
                    self.render_state['frame_duration'] = frame_duration
            else:
                frame_duration = self.render_state['frame_duration']
                frame_number = int(match.group(2))
                progress = int((frame_number / frame_duration) * 100)
                self.progress_changed.emit({
                    'progress': progress,
                    'message': f'Frame {frame_number} of {frame_duration}.',
                })
                self.render_state['progress'] = progress

    def handle_state(self, state):
        status = {
            self.NotRunning: const.Waiting,
            self.Starting: const.Queued,
            self.Running: const.Running,
        }[state]
        self.status_changed.emit({
            'status': status,
            'message': f'Status changed to {status}',
        })
        self.render_state['status'] = status

    def handle_finish(self, exit_code, exit_status):
        self._finished = True
        if exit_code < 0 or exit_status == self.CrashExit:
            self._finished_state = {
                'status': const.Failed,
                'message': self.error_message(self.error()),
            }
            self.render_state['status'] = const.Failed
            self.status_changed.emit(self._finished_state)
        else:
            self._finished_state = {
                'status': const.Success,
                'message': 'Render completed successfully.',
            }
            self.render_state['status'] = const.Success
            self.status_changed.emit(self._finished_state)

    def is_finished(self):
        return self._finished

    def finished_state(self):
        return self._finished_state

    def error_message(self, error):
        return {  # Messages taken from Qt QProcess documentation.
            self.FailedToStart: 'The process failed to start. Either the invoked program is missing, or you may have insufficient permissions to invoke the program.',
            self.Crashed: 'The process crashed some time after starting successfully.',
            self.Timedout: 'The last waitFor...() function timed out. The state of QProcess is unchanged, and you can try calling waitFor...() again.',
            self.WriteError: 'An error occurred when attempting to write to the process. For example, the process may not be running, or it may have closed its input channel.',
            self.ReadError: 'An error occurred when attempting to read from the process. For example, the process may not be running.',
            self.UnknownError: 'An unknown error occurred. This is the default return value of error().',
        }[error]

    def start(self):
        super(AERenderProcess, self).start(
            self.executable,
            self.arguments,
        )

    def wait(self, msecs=-1):
        return self.waitForFinished(msecs)


class AERenderSignals(QtCore.QObject):

    status_changed = QtCore.Signal(object)
    progress_changed = QtCore.Signal(object)
    started = QtCore.Signal()
    finished = QtCore.Signal()


class AERenderSubprocess:

    def __init__(self, project, comp, omtemplate, output, version=None):

        # Process start arguments
        self.project = os.path.normpath(project)
        self.comp = comp
        self.omtemplate = omtemplate
        self.output = os.path.normpath(output)
        self.version = version
        self.executable = get_executable(version)
        self.arguments = get_arguments(project, comp, omtemplate, output)

        self.signals = AERenderSignals()
        self.status_changed = self.signals.status_changed
        self.progress_changed = self.signals.progress_changed
        self.started = self.signals.started
        self.finished = self.signals.finished

        self.proc = None
        self._finished = False
        self._finished_state = {}
        self.render_state = {
            'progress': 0,
            'start': '',
            'end': '',
            'duration': '',
            'framerate': '',
            'frame_duration': 0,
            'status': const.Waiting,
        }

    def parse_line(self, text):
        for name, pattern in AERENDER_PATTERNS.items():
            match = pattern.search(text)
            if not match:
                continue
            if name == 'error':
                self.render_state['status'] = const.Failed
                self.status_changed.emit({
                    'status': const.Failed,
                    'message': match.group(1),
                })
                raise RuntimeError('Failed to render: %s' % match.group(1))
            elif name in ['start', 'end', 'duration', 'framerate']:
                self.render_state[name] = match.group(1)
                if name == 'framerate':
                    framerate = float(match.group(1))
                    duration = self.render_state['duration']
                    hours, minutes, seconds, frames = re.split(r'[:;]', duration)
                    seconds = int(seconds) + int(hours) * 3600 + int(minutes) * 60
                    frame_duration = int(frames) + int(framerate * seconds) - 1
                    self.render_state['frame_duration'] = frame_duration
            else:
                frame_duration = self.render_state['frame_duration']
                frame_number = int(match.group(2))
                progress = int((frame_number / frame_duration) * 100)
                self.progress_changed.emit({
                    'progress': progress,
                    'message': f'Frame {frame_number} of {frame_duration}.',
                })
                self.render_state['progress'] = progress

    def is_finished(self):
        return self._finished

    def finished_state(self):
        return self._finished_state

    def start(self):
        # Platform specific kwargs
        platform_kwargs = {}

        if sys.platform == 'win32':
            CREATE_NO_WINDOW = 0x08000000
            platform_kwargs['creationflags'] = CREATE_NO_WINDOW

        self.started.emit()
        self.status_changed.emit({
            'status': const.Running,
            'message': 'Starting subprocess'
        })

        self.proc = subprocess.Popen(
            [self.executable] + self.arguments,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            **platform_kwargs
        )

    def wait(self, check_cancel=None):
        capture = []
        self.render_state['output'] = capture
        cancelled = False
        for line in io.TextIOWrapper(self.proc.stdout, encoding='utf-8'):
            capture.append(line)
            self.parse_line(line)
            if check_cancel and check_cancel():
                cancelled = True
                break
            time.sleep(0.01)

        if cancelled:
            self.proc.terminate()
            self.proc.wait()
            self.finished.emit()
            return const.Cancelled

        if self.proc.wait() != 0:
            self.render_state['status'] = const.Failed
            self._finished_state = {
                'status': const.Failed,
                'message': '\n'.join(capture),
            }
            self.status_changed.emit(self._finished_state)
            self._finished = True
            self.finished.emit()
            return const.Failed
        else:
            self.render_state['status'] = const.Success
            self._finished_state = {
                'status': const.Success,
                'message': 'Render completed successfully.',
            }
            self.status_changed.emit(self._finished_state)
            self._finished = True
            self.finished.emit()
            return const.Success


def get_executable(version=None):
    if version:
        versions = [version]
    else:
        versions = [str(i) for i in reversed(range(2015, 2030))]

    application_templates = {
        'darwin': [
            '/Applications/Adobe After Effects {version}/aerender',
            '/Applications/Adobe After Effects CC {version}/aerender',
        ],
        'win32': [
            'C:/Program Files/Adobe/Adobe After Effects {version}/Support Files/aerender.exe',
            'C:/Program Files/Adobe/Adobe After Effects CC {version}/Support Files/aerender.exe',
        ]
    }[sys.platform]
    for application_template in application_templates:
        for version in versions:
            path = application_template.format(version=version)
            if os.path.exists(path):
                return path

    raise RuntimeError('Could not find path to aerender executable...')


def get_arguments(project, comp, omtemplate, output):
    return [
        '-mem_usage', '50', '50',
        '-continueOnMissingFootage',
        '-project', project,
        '-comp', comp,
        '-OMtemplate', omtemplate,
        '-output', output,
    ]


class AERenderPopupMonitor(QtCore.QThread):
    '''Monitors for and closes popup windows from aerender processes that prevent
    the aerender from progressing.
    '''

    def __init__(self, interval=2, *args, **kwargs):
        super(AERenderPopupMonitor, self).__init__(*args, **kwargs)
        self._interval = interval
        self._stopRequested = False

    def stop(self):
        self._stopRequested = True

    def run(self):
        if sys.platform != 'win32':
            return

        from . import winapi

        while not self._stopRequested:

            for window in winapi.get_windows():

                # Locate and close all Script Alert windows...
                if window.title == 'Script Alert':
                    button = winapi.find_child(
                        window.hwnd,
                        title='OK',
                        cls='Button',
                    )
                    if button:
                        winapi.click(button.hwnd)
                        winapi.click(button.hwnd)

            self.sleep(self._interval)
