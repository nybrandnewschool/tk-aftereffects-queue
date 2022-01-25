# Standard library imports
import os
import subprocess
import sys
import webbrowser
from queue import Queue

# Local imports
from . import const, resources, ae, paths
from .options import RenderOptions
from .widgets import Window, Menu
from .tasks.core import LogFormatter, Runner, Flow, call_in_main
from .tasks.aerender import AERenderComp, BackgroundAERenderComp
from .tasks.encode import EncodeMP4, EncodeGIF
from .tasks.copy import Copy
from .tasks.sgupload import SGUploadVersion
from .vendor.Qt import QtCore, QtGui, QtWidgets


class Application(QtCore.QObject):

    def __init__(self, tk_app, parent=None):
        super(Application, self).__init__(parent)

        self.tk_app = tk_app
        self.log = tk_app.logger
        self.engine = ae.AfterEffectsEngineWrapper(tk_app.engine)
        self.host_version = '20' + self.tk_app.engine.host_info['version'].split('.')[0]
        self.delay = DelayedQueue(self.log, self)

        self.items = []
        self.runner = None

        # Create UI
        self.ui = Window(parent)
        self.ui.queue_button.clicked.connect(self.load_queue)
        self.ui.queue.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.queue.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.queue.drag.connect(self.drag_queue)
        self.ui.queue.drop.connect(self.drop_queue)
        self.ui.render.clicked.connect(self.render)
        self.ui.closeEvent = self.closeEvent
        self.load_options()

    def closeEvent(self, event):
        if self.runner and self.runner.status == const.Running:
            self.ui.show_error("Can't close while rendering.")
            event.ignore()
        else:
            return QtWidgets.QWidget.closeEvent(self.ui, event)

    def show(self):
        self.log.debug('Showing UI.')
        should_reset = (
            not self.ui.isVisible()
            and (self.runner and self.runner.status in [const.Failed, const.Success])
        )
        if should_reset:
            self.reset()

        self.ui.show()
        if self.ui.windowState() == QtCore.Qt.WindowMinimized:
            self.ui.setWindowState(QtCore.Qt.WindowNoState)
        self.ui.raise_()
        self.ui.activateWindow()

    def hide(self):
        self.log.debug('Hiding UI.')
        self.ui.hide()

    def reset(self):
        self.log.debug('Resetting Render Queue.')
        self.ui.queue.clear()
        self.items[:] = []
        self.runner = None
        self.set_render_status(const.Waiting)

    def load_options(self):
        # Set output module options
        existing_output_modules = self.engine.find_output_module_templates()
        self.ui.options.module.clear()
        self.ui.options.module.addItems(existing_output_modules)

        # Set default output module
        default_module = self.tk_app.get_default_output_module(existing_output_modules)
        if default_module:
            self.ui.options.module.setCurrentText(default_module)

    def drag_queue(self, event):
        self.log.debug('DRAG EVENT')
        if self.engine.has_dynamic_links(event.mimeData()):
            self.log.debug('ACCEPTING DRAG EVENT')
            event.acceptProposedAction()

    def drop_queue(self, event):
        self.log.debug('DROP EVENT')
        dynamic_links = self.engine.get_dynamic_links(event.mimeData())
        if dynamic_links:
            self.delay(self.add_queue_dynamic_links, dynamic_links)
        event.acceptProposedAction()

    def load_queue(self):
        self.reset()
        self.items[:] = []

        # Find selected CompItems
        for item in self.engine.adobe.app.project.selection:
            if item['instanceof'] == 'CompItem':
                self.items.append(item)

        # TODO Could load unrendered RQItems here if there are no selected comps...

        if not self.items:
            self.ui.show_error('Select Comps to add to the queue.')
            return

        for item in self.items:
            self.ui.queue.add_item(item['name'])

    def pop_queue(self, item):
        for comp_item in list(self.items):
            if comp_item['name'] == item:
                self.items.remove(comp_item)
        self.ui.queue.remove_item(item)

    def add_queue_dynamic_links(self, dynamic_links):
        queued = [i['name'] for i in self.items]
        for item in self.engine.get_items_from_dynamic_links(dynamic_links):
            if item.data['instanceof'] == 'CompItem' and item['name'] not in queued:
                self.items.append(item)
                self.ui.queue.add_item(item['name'])

    def show_context_menu(self, point):
        # Get selected item
        item = self.ui.queue.get_selected_label()

        # Generate context menu
        menu = Menu(parent=self.ui.queue)
        if not self.runner:
            menu.addAction(
                QtGui.QIcon(resources.get_path('remove.png')),
                'Remove',
                lambda: self.pop_queue(item),
            )
        else:
            flow = self.runner.get_flow(item)
            if flow.status in [const.Done, const.Success]:
                file_path = flow.get_result(const.Rendering)
                render_folder = flow.context['render_folder']
                review_folder = flow.context['review_folder']
                sg_version = flow.get_result(const.Uploading)
                menu.addAction(
                    QtGui.QIcon(resources.get_path('play_filled.png')),
                    'Play with Default Player',
                    lambda: self.open_with_default_player(file_path),
                )
                menu.addAction(
                    QtGui.QIcon(resources.get_path('import.png')),
                    'Import Footage',
                    lambda: self.import_footage(file_path),
                )
                menu.addAction(
                    QtGui.QIcon(resources.get_path('clipboard.png')),
                    'Copy File Path',
                    lambda: self.copy_text_to_clipboard(os.path.abspath(file_path)),
                )
                browser = {
                    'win32': 'Explorer',
                    'darwin': 'Finder',
                }.get(sys.platform, 'File Manager')
                menu.addAction(
                    QtGui.QIcon(resources.get_path('folder.png')),
                    'Show Renders in ' + browser,
                    lambda: self.open_folder_in_browser(render_folder),
                )
                menu.addAction(
                    QtGui.QIcon(resources.get_path('folder.png')),
                    'Show Review in ' + browser,
                    lambda: self.open_folder_in_browser(review_folder),
                )
                if sg_version:
                    menu.addAction(
                        QtGui.QIcon(resources.get_path('shotgrid.png')),
                        'Show in ShotGrid',
                        lambda: self.open_in_shotgrid(sg_version)
                    )
            elif flow.status == const.Running:
                menu.addAction(
                    QtGui.QIcon(resources.get_path('cancel.png')),
                    'Cancel',
                    lambda: flow.request(const.Cancelled),
                )

        self.log.debug('Showing Context Menu at %s for %s' % (point, item))
        menu.exec_(self.ui.queue.mapToGlobal(point))

    def open_in_shotgrid(self, version):
        url_template = (
            'https://brandnewschool.shotgunstudio.com/page/media_center'
            '?type=Shot&id={shot_id}&project_id={project_id}'
            '&tree_path=%2Fbrowse_tree%2FProject%2F{project_id}%2F'
            'Shot%2F{seq_id}%2F{shot_id}'
        )
        more_version = self.engine.shotgun.find_one(
            'Shot',
            filters=[
                ['project', 'is', version['project']],
                ['id', 'is', version['entity']['id']]
            ],
            fields=['sg_sequence']
        )
        url = url_template.format(
            project_id=version['project']['id'],
            shot_id=version['entity']['id'],
            seq_id=more_version['sg_sequence']['id'],
        )
        webbrowser.open(url)
        self.ui.show_info('Opening in Web Browser...')

    def open_with_default_player(self, file_path):
        self.ui.show_info('Opening with default player...')
        if sys.platform == 'win32':
            os.startfile(file_path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', file_path])
        else:
            subprocess.Popen(['xdg-open', file_path])

    def copy_text_to_clipboard(self, text):
        self.ui.show_info('Copied to clipboard!')
        clipboard = QtWidgets.QApplication.instance().clipboard()
        clipboard.setText(text)

    def open_folder_in_browser(self, folder_path):
        if sys.platform == 'win32':
            self.ui.show_info('Opening Explorer...')
            subprocess.Popen(['explorer', os.path.abspath(folder_path)])
        elif sys.platform == 'darwin':
            self.ui.show_info('Opening Finder...')
            subprocess.Popen(['open', '-R', folder_path])
        else:
            self.ui.show_info('Opening File Browser...')
            subprocess.Popen(['xdg-open', folder_path])

    def import_footage(self, file_path):
        self.ui.show_info('Importing footage...')
        file_info = self.engine.get_ae_path_info(file_path)
        if file_info['is_sequence']:
            framerange = self.engine.find_sequence_range(file_path)
            if not framerange:
                return
            file_path = file_path.replace(
                file_info['padding_str'],
                str(framerange[0]).zfill(file_info['padding']),
            )

        self.engine.import_filepath(file_path)

    def render(self):
        options = RenderOptions(**self.ui.options.get())

        self.log.debug('Constructing Render Flows...')
        with Runner('Render and Review', parent=self) as runner:
            prev_flow = None
            for item in self.items:
                flow = self.new_render_flow(item['name'], options)
                if prev_flow:
                    flow.depends_on(prev_flow.tasks[0])
                prev_flow = flow

        self.log.debug('Starting Render Flows...')
        self.runner = runner
        self.runner.step_changed.connect(self.on_flow_step_changed)
        self.runner.status_changed.connect(self.set_render_status)
        self.runner.log.emit_record.connect(self.on_runner_emit_record)
        self.runner.start()

    def new_render_flow(self, item, options):
        # Get required flow data...
        sg_ctx = self.engine.context

        # Extract template fields from work file template...
        work_template = self.tk_app.get_work_template()
        sg_fields = sg_ctx.as_template_fields(work_template)

        # Get the rest of the required flow data...
        copy_to_review = self.tk_app.get_copy_to_review()
        render_folder = self.tk_app.get_render_template().apply_fields(sg_fields)
        review_folder = self.tk_app.get_review_template().apply_fields(sg_fields)
        output_data = self.generate_output_data(item, options.module, render_folder)
        output_path, output_resolution = output_data
        framerate = 1.0 / self.engine.get_comp(item).frameDuration
        project = self.engine.project_path

        # Build the flow context...
        flow_ctx = {
            'app': self,
            'comp': item,
            'options': options,
            'sg_ctx': sg_ctx,
            'sg_fields': sg_fields,
            'render_folder': render_folder,
            'review_folder': review_folder,
            'output_path': output_path,
            'output_resolution': output_resolution,
            'framerate': framerate,
            'project': self.engine.project_path,
            'host': 'AfterFX',
            'host_version': self.host_version,
        }

        with Flow(item) as flow:

            # Add main render task
            AERenderComp(
                project=project,
                comp=item,
                output_module=options.module,
                output_path=output_path,
            )

            mp4_path = paths.normalize(render_folder, item + '.mp4')
            if options.mp4:
                # Add Encode MP4 Task
                EncodeMP4(
                    src_file=output_path,
                    dst_file=mp4_path,
                    quality=options.mp4_quality,
                    framerate=framerate,
                )

                # Add Copy MP4 to review folder Task
                if copy_to_review:
                    review_path = paths.normalize(review_folder, item + '.mp4')
                    Copy(
                        src_file=mp4_path,
                        dst_file=review_path,
                        step='Copying ' + 'MP4',
                    )

            gif_path = paths.normalize(render_folder, item + '.gif')
            if options.gif:
                # Add Encode GIF Task
                EncodeGIF(
                    src_file=output_path,
                    dst_file=gif_path,
                    quality=options.gif_quality,
                    framerate=framerate,
                )

                # Add Copy GIF to review folder Task
                if copy_to_review:
                    review_path = paths.normalize(review_folder, item + '.gif')
                    Copy(
                        src_file=gif_path,
                        dst_file=review_path,
                        step='Copying ' + 'GIF',
                    )

            if options.sg:
                # Add SG Upload Version Task
                SGUploadVersion(
                    src_file=(output_path, mp4_path)[options.mp4],
                    sg_ctx=sg_ctx,
                    comment=options.sg_comment,
                )

            flow.set_context(flow_ctx)

        return flow

    def generate_output_data(self, comp, output_module, render_folder):
        comp_item = self.engine.get_comp(comp)
        with self.engine.TempEnqueue(comp_item) as rq_item:
            # Create output module for comp
            om = rq_item.outputModule(1)

            # Apply output module template
            om.applyTemplate(output_module)
            file_info = self.engine.get_file_info(om)
            path_info = self.engine.get_ae_path_info(file_info['Full Flat Path'])

            # Generate new file info
            padding = '#' * path_info['padding']
            extension = path_info['extension']
            if path_info['is_sequence']:
                output_path = paths.normalize(
                    render_folder,
                    comp,
                    f'{comp}.[{padding}].{extension}',
                )
            else:
                output_path = paths.normalize(
                    render_folder,
                    f'{comp}.{extension}'
                )
        return output_path, (comp_item.width, comp_item.height)

    def on_runner_emit_record(self, record):
        formatter = LogFormatter()
        self.log.debug(formatter.format(record))

    def on_flow_step_changed(self, event):
        self.ui.queue.update_item(
            label=event['flow'],
            status=event['step'],
            percent=event['progress'],
        )

    def set_render_status(self, status):
        self.log.debug('Render status changed to %s...', status)
        if status == const.Waiting:
            self.ui.options_header.label.setText('OPTIONS')
            self.ui.options.setEnabled(True)
            self.ui.render.setEnabled(True)
            self.ui.queue_button.setVisible(True)

            self.ui.render.enable_movie(False)
            self.ui.render.set_height(36)
        if status == const.Running:
            self.ui.options_header.label.setText('STATUS')
            self.ui.options.setEnabled(False)
            self.ui.render.setEnabled(False)
            self.ui.queue_button.setVisible(False)

            movie = resources.get_path(const.Running.title() + '.gif')
            self.ui.render.set_movie(movie)
            self.ui.render.enable_movie(True)
            self.ui.render.set_height(
                self.ui.options_header.height()
                + self.ui.options.height()
            )
        if status in [const.Failed, const.Success]:
            self.ui.options_header.label.setText('STATUS')
            self.ui.options.setEnabled(False)
            self.ui.render.setEnabled(False)
            self.ui.queue_button.setVisible(True)

            movie = resources.get_path(status.title() + '.gif')
            self.ui.render.add_movie_to_queue(movie)
            if status == const.Failed:
                self.ui.show_error("Failed to render...", 3000)
            else:
                self.ui.show_info("Success!", 3000)


class DelayedQueue(QtCore.QObject):

    def __init__(self, log, parent=None):
        super(DelayedQueue, self).__init__(parent=parent)

        self.log = log
        self.queue = Queue()
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self.process_queue)

    def __call__(self, func, *args, **kwargs):
        self.log.debug('Delaying execution of: %s(*%s, **%s)' % (func, args, kwargs))
        self.queue.put((func, args, kwargs))
        if not self._timer.isActive():
            self._timer.start()

    def process_queue(self):
        while not self.queue.empty():
            func, args, kwargs = self.queue.get()
            self.log.debug('Executing: %s(*%s, **%s)' % (func, args, kwargs))
            try:
                func(*args, **kwargs)
            except Exception:
                self.log.exception('Failed to execute...')
