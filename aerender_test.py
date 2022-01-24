import os
import re
import sys
import subprocess
import time

sys.path.insert(1, os.path.abspath('python'))

from aequeue.vendor.Qt import QtCore, QtWidgets
from aequeue import const


class AERenderProcess(QtCore.QProcess):

    patterns = {
        'start': re.compile(r'PROGRESS:  Start: (\d:\d\d:\d\d:\d\d)'),
        'end': re.compile(r'PROGRESS:  End: (\d:\d\d:\d\d:\d\d)'),
        'duration': re.compile(r'PROGRESS:  Duration: (\d:\d\d:\d\d:\d\d)'),
        'framerate': re.compile(r'PROGRESS:  Frame Rate: (\d+.\d+)'),
        'progress': re.compile(r'PROGRESS:  (\d:\d\d:\d\d:\d\d) \((\d+)\): \d+ Seconds')
    }
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
        self.executable = self.get_executable(version)

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
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._close_windows_alerts)

    def _close_windows_alerts(self):
        if sys.platform != 'win32':
            return

        proc = subprocess.Popen([
            'powershell.exe',
            '-C',
            r"& {$wshell = New-Object -ComObject 'wscript.shell'; $alert_visible = $wshell.AppActivate('Script Alert'); if ($alert_visible) {$wshell.SendKeys('{ENTER}');};}"
        ], shell=True)
        proc.communicate()

    def get_executable(self, version=None):
        sg_version = None
        try:
            import sgtk
            host_info = sgtk.platform.current_engine().host_info
            if host_info['name'] == 'AfterFX':
                sg_version = '20' + host_info['version'].split('.')[0]
        except ImportError:
            pass

        if not version and sg_version:
            version = sg_version

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
                    self.version = version
                    return path

        raise RuntimeError('Could not find path to aerender executable...')

    def get_arguments(self):
        return [
            '-project', f"{self.project}",
            '-comp', f"{self.comp}",
            '-OMtemplate', f"{self.omtemplate}",
            '-output', f"{self.output}",
        ]

    def handle_stderr(self):
        data = self.readAllStandardError()
        stderr = bytes(data).decode("utf8")

    def handle_stdout(self):
        data = self.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        for line in stdout.splitlines():
            self.parse_line(line)

    def parse_line(self, text):
        for name, pattern in self.patterns.items():
            match = pattern.search(text)
            if not match:
                continue
            if name in ['start', 'end', 'duration', 'framerate']:
                self.render_state[name] = match.group(1)
                if name == 'framerate':
                    framerate = float(match.group(1))
                    duration = self.render_state['duration']
                    hours, minutes, seconds, frames = duration.split(':')
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
        self._timer.stop()

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
        self._timer.start()
        super(AERenderProcess, self).start(
            self.executable,
            self.get_arguments(),
        )


def on_progress(event):
    print(f'{event["progress"]:>3d}% - {event["message"]}')


def on_status(event):
    print(f'{event["status"]} - {event["message"]}')


def main():
    app = QtWidgets.QApplication([])
    proc = AERenderProcess(
        project='G:/Shared drives/22-XXX-TestA/animation/shots/seqA/seqa_031/animation/work/ae/anim_seqa_031_v014.aep',
        comp='anim_seqa_031_A_v014',
        omtemplate='BNS - ProRes 4444+',
        output='G:/Shared drives/22-XXX-TestA/animation/shots/seqA/seqa_031/animation/work/ae/tmp.mov',
    )
    proc.status_changed.connect(on_status)
    proc.progress_changed.connect(on_progress)
    proc.finished.connect(app.exit())
    proc.start()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
