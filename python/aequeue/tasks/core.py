import logging
import re
import sys
import time
import threading
import traceback
import uuid
from collections import defaultdict, deque
from queue import Queue

from .. import const
from ..vendor.Qt import QtCore, QtWidgets


__all__ = [
    'call_in_main',
    'clamp',
    'current',
    'fit',
    'fit100',
    'Flow',
    'generate_report',
    'generate_html_report',
    'LogFormatter',
    'LogStreamReporter',
    'Runner',
    'Task',
]


_stack = defaultdict(deque)


def push(stack, obj):
    _stack[stack].append(obj)


def pop(stack, obj):
    if _stack[stack] and _stack[stack][-1] == obj:
        _stack[stack].pop()
    else:
        return


def current(stack):
    if _stack[stack]:
        return _stack[stack][-1]


class LogHandler(logging.Handler):

    def __init__(self, signals, record_type):
        super(LogHandler, self).__init__()
        self.signals = signals
        self.record_type = record_type

    def filter(self, record):
        record.type = self.record_type
        self.signals.prepare_record.emit(record)
        return super(LogHandler, self).filter(record)

    def emit(self, record):
        self.signals.emit_record.emit(record)


class LogFormatter(logging.Formatter):

    default_format = (
        '%(context)s - %(message)s'
    )

    def __init__(self, format=None):
        super(LogFormatter, self).__init__(format or self.default_format)

    def format(self, record):
        # Add special token to record with as much context as possible.
        runner_name = getattr(record, 'runner_name', None)
        flow_name = getattr(record, 'flow_name', None)
        flow_progress = getattr(record, 'flow_progress', None)
        flow_step = getattr(record, 'flow_step', None)
        task_progress = getattr(record, 'task_progress', None)

        context = []
        if runner_name is not None:
            context.append(runner_name)
        if flow_name is not None:
            context.append(flow_name)
        if flow_progress is not None:
            context.append('{:>3d}%'.format(int(flow_progress)))
        if flow_step is not None:
            context.append(flow_step)
        if task_progress is not None:
            context.append('{:>3d}%'.format(int(task_progress)))
        record.context = ' - '.join(context)

        return super(LogFormatter, self).format(record)


class LogStreamReporter(QtCore.QObject):

    emit_record = QtCore.Signal(object)

    def __init__(self, log, parent=None):
        super(LogStreamReporter, self).__init__(parent)

        self.formatter = LogFormatter()
        self.log = log
        self.log.emit_record.connect(self.emit_record)
        self.emit_record.connect(self.report)

    def report(self, record):
        sys.stdout.write(self.formatter.format(record) + '\n')
        sys.stdout.flush()


class Log(QtCore.QObject):

    prepare_record = QtCore.Signal(object)
    emit_record = QtCore.Signal(object)

    def __init__(self, name, record_type, parent=None):
        super(Log, self).__init__(parent)

        self.handler = LogHandler(self, record_type)
        self.logger = logging.getLogger(name)
        self.logger.addFilter(self.handler)
        self.logger.addHandler(self.handler)
        self.setLevel(logging.DEBUG)

    def setLevel(self, level):
        self.logger.setLevel(level)
        self.handler.setLevel(level)

    def __getattr__(self, attr):
        return getattr(self.logger, attr)


class TaskSignals(QtCore.QObject):

    status_changed = QtCore.Signal(dict)


class Task(QtCore.QRunnable):
    '''A single chunk of work.'''

    step = 'Task'
    execute_in_main = False

    def __init__(self, step=None, flow=None, parent=None):
        super(Task, self).__init__(parent)
        self.setAutoDelete(False)
        self.signals = TaskSignals()

        self.id = uuid.uuid4().hex
        self.status = const.Waiting
        self.status_request = None
        self.result = None
        self.error = None
        self.progress = 0
        self.step = step or self.step
        self.context = {}

        self.log = Log(str(self), record_type='task')
        self.log.prepare_record.connect(self.prepare_record)

        self.flow = flow or current('flow')
        if self.flow:
            self.flow.add_task(self)

        self.log.debug(f'{self.step} initialized...')

    def __repr__(self):
        return '<{}:{}>'.format(self.__class__.__name__, self.id)

    def prepare_record(self, record):
        record.task = self
        record.task_id = self.id
        record.task_status = self.status
        record.task_status_request = self.status_request
        record.task_progress = self.progress
        record.task_result = self.result
        record.task_error = self.error
        record.task_step = self.step

    def set_context(self, context):
        self.context = context

    def set_status(self, status, progress=None):
        event = {
            'type': 'status_changed',
            'task': self.id,
            'step': self.step,
            'prev_status': self.status,
            'status': status,
            'progress': progress or self.progress,
        }
        self.status = event['status']
        self.progress = event['progress']
        self.signals.status_changed.emit(event)
        if event['status'] != event['prev_status']:
            self.log.debug(
                'Status changed from %s to %s.'
                % (event['prev_status'].upper(), event['status'].upper())
            )

    def request(self, status):
        self.log.debug('%s requested...' % status.upper())
        self.status_request = const.Cancelled

    def accept(self, status):
        self.log.debug('%s accepted...' % status.upper())
        self.set_status(status)

    def wait(self):
        while True:
            if self.status in const.DoneList:
                return self.status
            time.sleep(1)

    def run(self):
        self.set_status(const.Running)
        try:
            if self.execute_in_main:
                self.result = call_in_main(self.execute)
            else:
                self.result = self.execute()
            if self.status_request == const.Cancelled:
                return self.accept(const.Cancelled)
            self.set_status(const.Success)
        except Exception:
            self.error = sys.exc_info()
            self.log.exception('Task failed to execute...')
            self.set_status(const.Failed)

    def execute(self):
        return NotImplemented


class SyncTask(Task):

    execute_in_main = True


class FlowSignals(QtCore.QObject):

    status_changed = QtCore.Signal(str)
    step_changed = QtCore.Signal(dict)


class Flow(QtCore.QRunnable):
    '''An object used to sequentially execute a list of tasks.'''

    def __init__(self, name, runner=None, parent=None):
        super(Flow, self).__init__(parent)
        self.id = uuid.uuid4().hex
        self.name = name
        self.status = const.Waiting
        self.status_request = None
        self.step = const.Queued
        self.progress = 0
        self.context = self.default_context()
        self.dependencies = []
        self.tasks = []
        self.tasks_by_id = {}
        self.current_task = None
        self.pool = QtCore.QThreadPool.globalInstance()
        self.signals = FlowSignals()

        self.log_records = []
        self.log = Log(str(self), record_type='flow')
        self.log.prepare_record.connect(self.prepare_record)
        self.log.emit_record.connect(self.emit_record)

        self.runner = runner or current('runner')
        if self.runner:
            self.runner.add_flow(self)

        self.log.debug('Flow initialized...')

    def __repr__(self):
        return '<{}:{}:{}>'.format(self.__class__.__name__, self.name, self.id)

    def __enter__(self):
        push('flow', self)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pop('flow', self)

    def default_context(self):
        return {
            'flow': self,
            'task': None,
            'results': {},
            'results_by_step': {},
        }

    def set_context(self, context):
        self.context = self.default_context()
        self.context.update(context)

    def update_context(self, context):
        self.context.update(context)

    def emit_record(self, record):
        self.log_records.append(record)

    def prepare_record(self, record):
        record.flow = self
        record.flow_id = self.id
        record.flow_name = self.name
        record.flow_step = self.step
        record.flow_progress = self.progress

    def add_task(self, task):
        task.signals.status_changed.connect(self.task_status_changed)
        task.log.prepare_record.connect(self.log.prepare_record)
        task.log.emit_record.connect(self.log.emit_record)
        self.tasks.append(task)
        self.tasks_by_id[task.id] = task

    def task_status_changed(self, event):
        # convert task percent to flow percent
        task = self.tasks_by_id[event['task']]
        task_index = self.tasks.index(task)
        progress_per_step = 100.0 / len(self.tasks)
        self.progress = fit100(
            event['progress'],
            task_index * progress_per_step,
            (task_index * progress_per_step) + progress_per_step,
        )
        self.set_step(event['step'])

    def depends_on(self, dependencies):
        if not isinstance(dependencies, (list, tuple)):
            dependencies = [dependencies]

        for dep in dependencies:
            if not isinstance(dep, (Task, Flow)):
                raise ValueError('Expected Task or Flow got %s' % type(dep))

        for dep in dependencies:
            if dep not in self.dependencies:
                self.dependencies.append(dep)

    def set_status(self, status):
        if status != self.status:
            self.log.debug(
                'Status changed from %s to %s.'
                % (self.status.upper(), status.upper())
            )
        self.status = status
        self.signals.status_changed.emit(status)

    def set_step(self, step):
        self.step = step
        self.signals.step_changed.emit({
            'flow': self.name,
            'step': self.step,
            'progress': self.progress,
        })

    def get_result(self, step):
        return self.context['results_by_step'].get(step)

    def request(self, status):
        self.log.debug('%s requested...' % status.upper())
        self.status_request = const.Cancelled

    def accept(self, status):
        self.log.debug('%s accepted...' % status.upper())
        self.set_status(status)

    def wait(self):
        while True:
            if self.status in const.DoneList:
                return self.status
            time.sleep(1)

    def await_task(self, task):
        while True:
            if self.status_request == const.Cancelled:
                task.request(const.Cancelled)
                task.wait()
            if task.status in const.DoneList:
                return task.status
            time.sleep(1)

    def await_dependencies(self):
        self.log.debug('Waiting for requirements...')
        while True:

            if self.status_request == const.Cancelled:
                return self.accept(const.Cancelled)

            done = []
            for dep in self.dependencies:
                status = dep.status
                done.append(dep.status in const.DoneList)
                if status == const.Failed:
                    self.log.debug('Upstream dependency has Failed: %s', dep)
                    return False
                if status == const.Cancelled:
                    self.log.debug('Upstream dependency has been Cancelled: %s', dep)
                    return False

            if all(done):
                self.log.debug('Upstream Dependencies satisfied...')
                return True

            time.sleep(1)

    def run(self):
        # Wait for all dependencies to finish
        dependencies_satisfied = self.await_dependencies()
        if not dependencies_satisfied:
            # When an upstream dependency has Failed or been Cancelled
            # this flow should be revoked.
            self.set_status(const.Revoked)
            self.set_step(const.Revoked)
            return

        self.set_status(const.Running)

        for task in self.tasks:

            # Cancelled
            if self.status_request == const.Cancelled:
                return self.accept(const.Cancelled)

            # Start next task
            self.step = task.step
            self.log.debug('Setting context...')
            self.context['task'] = task
            task.set_context(self.context)
            self.log.debug('Starting...')
            self.pool.start(task)

            # Wait for task to finish
            upstream_status = self.await_task(task)
            if upstream_status == const.Failed:
                self.set_status(const.Failed)
                self.set_step(const.Failed)
                return

            self.context['results'][task.id] = task.result
            self.context['results_by_step'][task.step] = task.result

        self.context['task'] = None
        self.set_status(const.Success)
        self.set_step(const.Done)


class Runner(QtCore.QThread):
    '''Flow executor.'''

    status_changed = QtCore.Signal(str)
    step_changed = QtCore.Signal(dict)

    def __init__(self, name, flows=None, parent=None):
        super(Runner, self).__init__(parent)
        self.id = uuid.uuid4().hex
        self.name = name
        self.flows = []
        self.status = const.Waiting
        self.status_request = None
        self.pool = QtCore.QThreadPool.globalInstance()

        self.log_records = []
        self.log = Log(str(self), record_type='runner')
        self.log.prepare_record.connect(self.prepare_record)
        self.log.emit_record.connect(self.emit_record)

        if flows:
            for flow in flows:
                self.add_flow(flow)

        self.log.debug('Runner initialized...')

    def __enter__(self):
        push('runner', self)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pop('runner', self)

    def emit_record(self, record):
        self.log_records.append(record)

    def prepare_record(self, record):
        record.runner = self
        record.runner_id = self.id
        record.runner_name = self.name

    def get_flow(self, name):
        for flow in self.flows:
            if flow.name == name:
                return flow

    def add_flow(self, flow, requirements=None):
        self.log.debug('Adding flow %s', flow)
        if requirements:
            flow.requires(requirements)
        flow.log.prepare_record.connect(self.log.prepare_record.emit)
        flow.log.emit_record.connect(self.log.emit_record.emit)
        flow.signals.step_changed.connect(self.step_changed.emit)
        self.flows.append(flow)

    def request(self, status):
        self.log.debug('%s requested...' % status.upper())
        self.status_request = const.Cancelled

    def accept(self, status):
        self.log.debug('%s accepted...' % status.upper())
        self.set_status(status)

    def set_status(self, status):
        if status != self.status:
            self.log.debug(
                'Status changed from %s to %s.'
                % (self.status.upper(), status.upper())
            )
        self.status = status
        self.status_changed.emit(status)

    def run(self):
        self.set_status(const.Running)

        # Start all flows
        for flow in self.flows:
            self.pool.start(flow)

        # Wait for flows to finish
        while True:
            if self.status_request == const.Cancelled:
                for flow in self.flows:
                    flow.request(const.Cancelled)
                    flow.wait()
                return self.accept(const.Cancelled)

            if all([flow.status in const.DoneList for flow in self.flows]):
                break

            time.sleep(1)

        if any([flow.status == const.Failed for flow in self.flows]):
            self.set_status(const.Failed)
        else:
            self.set_status(const.Success)


def generate_report(runner):
    '''Generate a well formatted report for a Runner.'''

    formatters = {
        'flow': LogFormatter(
            '  %(flow_step)s [%(flow_progress)3d%%] %(message)s'
        ),
        'task': LogFormatter(
            '    %(task_status)s [%(task_progress)3d%%] %(message)s'
        ),
    }

    report = []
    for flow in runner.flows:
        report.append(f'{flow.name}')
        for record in flow.log_records:
            if record.exc_info:
                # Temporarily modify record so we can nicely format the exception...
                einfo, etext, stk = record.exc_info, record.exc_text, record.stack_info
                record.exc_info = record.exc_text = record.stack_info = None
                record.message = str(einfo[1])

                formatted_exc = ''.join(traceback.format_exception(*einfo))
                report.append(formatters[record.type].format(record))
                report.append(f'\n{formatted_exc}\n')

                # Restore record
                record.exc_info, record.exc_text, record.stack_info = einfo, etext, stk
            else:
                report.append(formatters[record.type].format(record))
    return '\n'.join(report)


def generate_html_report(runner):
    '''Generate a well formatted html report for a Runner.'''

    formatters = {
        'flow': LogFormatter(
            '<pre style="margin: 0px;">  %(flow_step)s [%(flow_progress)3d%%] %(message)s</pre>'
        ),
        'task': LogFormatter(
            '<pre style="margin: 0px;">   %(branch)s %(task_status)s [%(task_progress)3d%%] %(message)s</pre>'
        ),
    }

    def format_record(record):
        formatter = formatters[record.type]
        record.branch = '├'
        if record.type == 'task' and record.task_status in const.DoneList:
            record.branch = '└'
        lines = []
        # Apply base formatting
        if record.exc_info:
            # Temporarily modify record so we can nicely format the exception...
            einfo, etext, stk = record.exc_info, record.exc_text, record.stack_info
            record.exc_info = record.exc_text = record.stack_info = None
            record.message = str(einfo[1])

            formatted_exc = ''.join(traceback.format_exception(*einfo))
            lines.append(formatter.format(record))
            lines.append(f'<pre style="color: #EB5757;">{formatted_exc}</pre>')

            # Restore record
            record.exc_info, record.exc_text, record.stack_info = einfo, etext, stk
        else:
            lines.append(formatters[record.type].format(record))

        # Apply color and emphasis to status labels
        if record.type == 'flow':
            pattern = record.flow_step
            status = pattern.split()[0].lower()
            color = '#CFCFCF'
        else:
            pattern = record.task_status
            status = pattern.split()[0].lower()
            color = '#AFAFAF'
        repl = f'<em style="color: {color};">{pattern}</em>'
        for i, line in enumerate(lines):
            lines[i] = re.sub(pattern, repl, line)

        return lines

    report = ['<pre style="line-height:0%;">  </pre>']
    for flow in runner.flows:
        report.append(f'<pre style="font-family: Roboto; font-size: 14px;color: #DDDDDD;">  {flow.name}</pre>')
        for record in flow.log_records:
            report.extend(format_record(record))

    return '\n'.join(report)


def clamp(value, mn, mx):
    '''Clamp <value> between <mn> and <mx>.'''

    return min(max(value, mn), mx)


def fit(value, omin, omax, nmin, nmax):
    '''Remap <value> between <omin> and <omax> to <nmin> and <nmax>'''

    nvalue = (((value - omin) * (nmax - nmin)) / (omax - omin)) + nmin
    return clamp(nvalue, nmin, nmax)


def fit100(value, mn, mx):
    '''Fit <value> between 0 and 100 to <mn> and <mx>.'''

    return fit(value, 0, 100, mn, mx)


class FunctionEvent(QtCore.QEvent):
    '''QEvent wrapping a function and arguments.

    Has a result queue that can be used to await a result of the Events acceptance and
    execution.
    '''

    _type = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self, fn, args, kwargs):
        super(FunctionEvent, self).__init__(self._type)

        self.result = Queue()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


class FunctionCaller(QtCore.QObject):
    '''QObject whose sole purpose is handling FunctionEvents.

    Calls a FunctionEvent's function and puts the result and exc_info on the
    FunctionEvent's result queue.
    '''

    def event(self, event):
        event.accept()
        result = None
        exc_info = None
        try:
            result = event.fn(*event.args, **event.kwargs)
        except Exception:
            exc_info = sys.exc_info()
        finally:
            event.result.put((result, exc_info))


function_caller = FunctionCaller()


def call_in_main(fn, *args, **kwargs):
    '''Calls a function in the MainThread and returns the result.'''

    if threading.current_thread().name == 'MainThread':
        return fn(*args, **kwargs)

    # Post event for function_caller to execute in main thread
    event = FunctionEvent(fn, args, kwargs)
    event_loop = QtWidgets.QApplication.instance()
    event_loop.postEvent(function_caller, event)

    # Wait for result to turn up in result queue
    result, exc_info = event.result.get()
    if exc_info:
        exc_type, exc_value, exc_traceback = exc_info
        raise exc_value.with_traceback(exc_traceback)
    return result
