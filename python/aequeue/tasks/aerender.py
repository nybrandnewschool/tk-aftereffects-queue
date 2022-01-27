import os
import sys

from .. import const, paths
from ..render import AERenderProcess
from ..vendor.Qt import QtCore
from .core import Task, SyncTask, call_in_main


class AERenderFailed(Exception):
    pass


class AERenderComp(SyncTask):

    step = const.Rendering

    def __init__(self, project, comp, output_module, output_path, *args, **kwargs):
        self.project = project
        self.comp = comp
        self.output_module = output_module
        self.output_path = output_path
        self.output_folder = os.path.dirname(output_path)
        super(AERenderComp, self).__init__(*args, **kwargs)

    def execute(self):
        # Get required context data
        app = self.context['app']

        self.log.debug('Preparing output path...')
        # Create output module for comp
        comp_item = app.engine.get_comp(self.comp)
        rq_item = app.engine.enqueue_comp(comp_item)
        om = rq_item.outputModule(1)
        self.set_status(const.Running, 20)

        # Apply output module template
        om.applyTemplate(self.output_module)
        self.set_status(const.Running, 40)

        # Apply file info
        self.log.debug('Setting Full Flat Path: %s' % self.output_path)
        app.engine.set_file_info(om, {'Full Flat Path': self.output_path})

        self.log.debug('Rendering AEComp...')
        self.set_status(const.Running, 60)
        try:
            os.makedirs(self.output_folder, exist_ok=True)
        except Exception:
            raise RuntimeError('Failed to create output folder %s' % self.output_folder)

        success = app.engine.render_queue_item(rq_item)
        if not success:
            raise AERenderFailed('Failed to render queue item: %s' % self.comp)

        self.set_status(const.Running, 100)
        return self.output_path


class BackgroundAERenderComp(Task):

    step = const.Rendering

    def __init__(self, project, comp, output_module, output_path, *args, **kwargs):
        self.project = project
        self.comp = comp
        self.output_module = output_module
        self.output_path = output_path
        self.output_folder = os.path.dirname(output_path)
        super(BackgroundAERenderComp, self).__init__(*args, **kwargs)

    def on_render_status_changed(self, event):
        self.set_status(event['status'])

    def on_render_progress_changed(self, event):
        self.set_status(const.Running, event['progress'])

    def execute(self):
        # Get required context data
        app = self.context['app']

        self.log.debug('Rendering AEComp...')
        try:
            os.makedirs(self.output_folder, exist_ok=True)
        except Exception:
            raise RuntimeError('Failed to create output folder %s' % self.output_folder)
        self.set_status(const.Running, 10)

        self.render = AERenderProcess(
            project=self.project,
            comp=self.comp,
            omtemplate=self.output_module,
            output=self.output_path,
            version=self.context['host_version'],
        )
        self.render.status_changed.connect(self.on_render_status_changed)
        self.render.progress_changed.connect(self.on_render_progress_changed)
        self.render.start()
        self.set_status(const.Running, 20)

        # Raise Error if render process failed.
        state = self.render.wait()
        if state['status'] == const.Failed:
            raise RuntimeError(state['message'])

        return self.output_path
