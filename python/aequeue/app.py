# Standard library imports
import os
import subprocess
import sys
import webbrowser
from queue import Queue

# Local imports
from . import const, resources, ae, paths
from .options import RenderOptions
from .render import AERenderPopupMonitor
from .widgets import Window, Menu
from .tasks.core import LogFormatter, Runner, Flow, generate_html_report, generate_report, call_in_main
from .tasks.aerender import AERenderComp, BackgroundAERenderComp
from .tasks.encode import EncodeMP4, EncodeGIF
from .tasks.copy import Copy
from .tasks.move import Move
from .tasks.sgupload import SGUploadVersion
from .tasks.sgpublish import SGPublish
from .tasks.generic import ErrorTask
from .vendor.Qt import QtCore, QtGui, QtWidgets


class Application(QtCore.QObject):

    def __init__(self, tk_app, parent=None):
        super(Application, self).__init__(parent)

        self.items = []
        self.runner = None
        self._aerender_popup_monitor = None

        # Create UI
        self.ui = Window(parent)
        self.ui.reset_button.clicked.connect(self.reset_queue)
        self.ui.queue_button.clicked.connect(self.load_queue)
        self.ui.queue.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.queue.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.queue.drag.connect(self.drag_queue)
        self.ui.queue.drop.connect(self.drop_queue)
        self.ui.render_button.clicked.connect(self.render)
        self.ui.send_button.clicked.connect(self.send_report)
        self.ui.cancel_button.clicked.connect(self.cancel)
        self.ui.closeEvent = self.closeEvent

        # Initialize tk_app dependent parts
        self.update_tk_app(tk_app)

        # Track whether default options have been loaded
        self._defaults_loaded = False

    def closeEvent(self, event):
        if self.runner and self.runner.status == const.Running:
            self.ui.show_error("Can't close while rendering.")
            event.ignore()
        else:
            return QtWidgets.QWidget.closeEvent(self.ui, event)

    def show(self):
        self.log.debug('Showing UI...')
        self.load_options(not self._defaults_loaded)
        should_reset = (
            not self.ui.isVisible()
            and (self.runner and self.runner.status in [const.Failed, const.Success])
        )
        if should_reset:
            self.reset_queue()

        self.ui.show()
        if self.ui.windowState() == QtCore.Qt.WindowMinimized:
            self.ui.setWindowState(QtCore.Qt.WindowNoState)
        self.ui.raise_()
        self.ui.activateWindow()

    def hide(self):
        self.log.debug('Hiding UI.')
        self.ui.hide()

    def update_tk_app(self, tk_app):
        self.tk_app = tk_app
        self.log = tk_app.logger
        self.engine = ae.AfterEffectsEngineWrapper(tk_app.engine)
        self.host_version = self.tk_app.engine.host_info['version']
        self.delay = DelayedQueue(self.log, self)
        if self.ui:
            self.ui.setWindowTitle(tk_app.get_window_title())

    def load_options(self, apply_defaults):
        self.log.debug('Loading UI options...')
        # Stash previous option values
        stash = self.ui.options.get()

        # Populate options with data from AE
        existing_modules = self.engine.find_output_module_templates()
        self.ui.options.module.clear()
        self.ui.options.module.addItems(existing_modules)

        # Apply defaults OR stash!
        if apply_defaults:
            self.log.debug('Applying UI option defaults...')
            default_module = self.tk_app.get_default_output_module(existing_modules)
            if default_module:
                self.ui.options.module.setCurrentText(default_module)

            default_mp4_quality = self.tk_app.get_default_mp4_quality()
            self.ui.options.mp4_quality.setCurrentText(default_mp4_quality)

            default_gif_quality = self.tk_app.get_default_gif_quality()
            self.ui.options.gif_quality.setCurrentText(default_gif_quality)

            # Update flag so we don't update them next time we load options.
            self._defaults_loaded = True
        else:
            if stash['module']:
                self.ui.options.module.setCurrentText(stash['module'])

    def reset_queue(self):
        self.log.debug('Resetting Render Queue...')
        self.ui.queue.clear()
        self.items[:] = []
        self.runner = None
        self.set_render_status(const.Waiting)

    def drag_queue(self, event):
        if self.engine.has_dynamic_links(event.mimeData()):
            event.acceptProposedAction()

    def drop_queue(self, event):
        if not hasattr(event, 'mimeData'):
            self.log.debug('Got invalid event: %s' % event)
            return
        dynamic_links = self.engine.get_dynamic_links(event.mimeData())
        if dynamic_links:
            self.delay(self.add_queue_dynamic_links, dynamic_links)
        event.acceptProposedAction()

    def load_queue(self):
        self.reset_queue()
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
        if status in const.DoneList:
            self.ui.report.setText(generate_html_report(self.runner))

            # Stop the AERenderPopupMonitor
            if self._aerender_popup_monitor:
                self.log.debug('Stopping AERenderPopupMonitor...')
                self._aerender_popup_monitor.stop()

        self.ui.set_status(status)

        # Update Send button state and send report if needed.
        if status == const.Failed:
            self.ui.send_button.setVisible(self.is_send_button_visible())
            if self.tk_app.send_on_error():
                self.send_report()

    def is_send_button_visible(self):
        return (
            self.tk_app.send_is_available()
            and not self.tk_app.send_on_error()
        )

    def send_report(self):
        try:
            self.tk_app.send_report(
                self.engine.context,
                self.runner,
                generate_report(self.runner),
                generate_html_report(self.runner),
            )
            if not self.tk_app.send_on_error():
                self.ui.show_info('Error report sent!')
        except Exception:
            self.log.exception('Failed to send error report.')
            self.ui.show_error('Failed to send error report.')

    def cancel(self):
        self.runner.request(const.Cancelled)

    def render(self):
        if not self.items:
            self.ui.show_error('Add items to the queue first!')
            return

        ready_to_run, message = self.tk_app.ensure_context_optimal()
        if not ready_to_run:
            self.ui.show_error(message)
            return

        # Set status to Running manually - makes the UI feel more responsive
        # as the first status change from Waiting -> Running make take a moment.
        self.set_render_status(const.Running)

        self.log.debug('Constructing Render Flows...')
        with Runner('Render and Review', parent=self) as runner:

            # Get the user options
            options = RenderOptions(**self.ui.options.get())

            # Setup bg pool
            render_pool = None
            if options.bg:
                render_pool = QtCore.QThreadPool()
                render_pool.setMaxThreadCount(options.bg_threads)

            # Generate a path template by creating a temporary render queue item
            # with the output module specified in options.
            path_template = self.generate_path_template(options.module)

            # Create flow for each item
            prev_flow = None
            for item in self.items:
                flow = self.new_render_flow(
                    item['name'],
                    options,
                    path_template,
                    render_pool,
                )
                if prev_flow and not options.bg:
                    flow.depends_on(prev_flow.tasks[0])
                prev_flow = flow


        self.log.debug('Starting Render Flows...')
        self.runner = runner
        self.runner.step_changed.connect(self.on_flow_step_changed)
        self.runner.status_changed.connect(self.set_render_status)
        self.runner.log.emit_record.connect(self.on_runner_emit_record)
        self.runner.start()

        if options.bg:
            self.log.debug('Starting AERenderPopupMonitor...')
            self._aerender_popup_monitor = AERenderPopupMonitor()
            self._aerender_popup_monitor.start()

    def new_render_flow(self, item, options, path_template, render_pool):
        # Get required flow data...
        sg_ctx = self.engine.context
        comp_item = self.engine.get_comp(item)

        # Extract template fields from work file template...
        work_template = self.tk_app.get_work_template()
        sg_fields = sg_ctx.as_template_fields(work_template)

        # Get the rest of the required flow data...
        publish_on_upload = self.tk_app.get_publish_on_upload()
        copy_to_review = self.tk_app.get_copy_to_review()
        move_to_review = self.tk_app.get_move_to_review()
        render_folder = self.tk_app.get_render_template().apply_fields(sg_fields)
        review_folder = self.tk_app.get_review_template().apply_fields(sg_fields)
        output_path = path_template.format(folder=render_folder, name=item)
        output_resolution = comp_item.width, comp_item.height
        framerate = 1.0 / comp_item.frameDuration
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

        # Use a separate threadpool for AERender processes. When background rendering
        # the aerender process is the least reliable.
        # aerender_pool = QtCore.QThreadPool()
        # aerender_pool.setMaxThreadCount(options.bg_threads)

        with Flow(item) as flow:

            # Add main render task
            RenderComp = (AERenderComp, BackgroundAERenderComp)[options.bg]
            render_comp = RenderComp(
                project=project,
                comp=item,
                output_module=options.module,
                output_path=output_path,
            )
            render_comp.pool = render_pool

            # Poison pill for debugging and testing purposes
            # ErrorTask(step=const.Rendering)

            # Add Encode MP4 Task
            mp4_path = paths.normalize(render_folder, item + '.mp4')
            mp4_upload_path = mp4_path
            if options.mp4:
                EncodeMP4(
                    src_file=output_path,
                    dst_file=mp4_path,
                    quality=options.mp4_quality,
                    framerate=framerate,
                )

            # Add Encode GIF Task
            gif_path = paths.normalize(render_folder, item + '.gif')
            if options.gif:
                EncodeGIF(
                    src_file=output_path,
                    dst_file=gif_path,
                    quality=options.gif_quality,
                    framerate=framerate,
                )

            # Add Move MP4 to review folder Task
            if move_to_review and options.mp4:
                review_path = paths.normalize(review_folder, item + '.mp4')
                mp4_upload_path = review_path
                Move(
                    src_file=mp4_path,
                    dst_file=review_path,
                    step=const.Moving + ' MP4',
                )
            elif copy_to_review and options.mp4:
                review_path = paths.normalize(review_folder, item + '.mp4')
                mp4_upload_path = review_path
                Copy(
                    src_file=mp4_path,
                    dst_file=review_path,
                    step=const.Copying + ' MP4',
                )

            # Add Copy GIF to review folder Task
            if move_to_review and options.gif:
                review_path = paths.normalize(review_folder, item + '.gif')
                Move(
                    src_file=gif_path,
                    dst_file=review_path,
                    step=const.Moving + ' GIF',
                )
            elif copy_to_review and options.gif:
                review_path = paths.normalize(review_folder, item + '.gif')
                Copy(
                    src_file=gif_path,
                    dst_file=review_path,
                    step=const.Copying + ' GIF',
                )

            # Add SG Upload Version Task
            if options.sg:
                version_task = SGUploadVersion(
                    src_file=(output_path, mp4_upload_path)[options.mp4],
                    sg_ctx=sg_ctx,
                    comment=options.sg_comment,
                )

                # Register a publish
                if publish_on_upload:
                    SGPublish(
                        file=output_path,
                        thumbnail_src_file=(None, mp4_upload_path)[options.mp4],
                        sg_ctx=sg_ctx,
                        version_task=version_task,
                    )

            flow.set_context(flow_ctx)

        return flow

    def generate_path_template(self, output_module):
        token = "__NAME__"
        with self.engine.TempComp(token) as comp:
            with self.engine.TempEnqueue(comp) as rq_item:
                # Create output module for comp
                om = rq_item.outputModule(1)

                # Apply output module template
                om.setSettings({"Output File Info": {"Full Flat Path": "~/[compName]"}})
                om.applyTemplate(output_module)

                file_info = self.engine.get_file_info(om)
                path_info = self.engine.get_ae_path_info(file_info['Full Flat Path'])
                self.log.debug('FILE INFO: %s' % file_info)
                self.log.debug('PATH INFO: %s' % path_info)

                # Generate new file info
                padding = '#' * path_info['padding']
                extension = path_info['extension']
                if path_info['is_sequence']:
                    output_path = paths.normalize(
                        '{folder}',
                        token,
                        f'{token}.[{padding}].{extension}',
                    )
                else:
                    output_path = paths.normalize(
                        '{folder}',
                        f'{token}.{extension}'
                    )
        return output_path.replace(token, '{name}')

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
            file_path = flow.context['output_path']
            render_folder = flow.context['render_folder']
            review_folder = flow.context['review_folder']
            if flow.status in [const.Done, const.Success]:
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
                        QtGui.QIcon(resources.get_path('shotgrid_outlines.png')),
                        'Show in ShotGrid',
                        lambda: self.open_in_shotgrid(sg_version)
                    )
            if flow.status in [const.Running, const.Queued]:
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


class DelayedQueue(QtCore.QObject):
    '''Function that facilitates executing a function a little later.

    Useful in cases where you need to return control to another thread or process
    temporarily and you don't care about the return value of what you're executing.

    For example, when accepting dropped items from AfterEffects, we need to return
    control to AfterEffects signalling that we accepted the drop, before asking
    AfterEffects what items were dropped. Otherwise, the drop is never accepted and we
    deadlock AfterEffects.
    '''

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
