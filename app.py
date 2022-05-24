# Standard library imports
import os

# Third party imports
import sgtk


def normalize(*parts):
    path = os.path.normpath(os.path.expanduser(os.path.join(*parts)))
    return path.replace('\\', '/')


def which(app):
    for path in os.getenv('PATH', '').split(os.pathsep):
        potential_app_paths = [
            normalize(path, app),
            normalize(path, app + '.exe'),
        ]
        for app_path in potential_app_paths:
            if os.path.exists(app_path):
                return app_path


def is_ffmpeg_installed():
    ffmpeg = os.getenv('FFMPEG_LOCATION', os.getenv('FFMPEG'))
    if ffmpeg and os.path.exists(ffmpeg):
        return True

    return bool(which('ffmpeg'))


class AEQueueApplication(sgtk.platform.Application):

    def init_app(self):
        # Perform additional validation before registering
        self.ensure_ffmpeg_installed()
        self.ensure_templates_exist()

        self.aequeue_module = None
        self.aequeue = None
        self.engine.register_command(
            self.get_setting('command_name'),
            self.show_app,
        )

        # Set initial values
        self._reset_on_context_change = True

    def ensure_ffmpeg_installed(self):
        if not is_ffmpeg_installed():
            msg = (
                "Couldn't load tk-aftereffects-queue. Application requires "
                "ffmpeg. Please install it and make sure it is available on "
                "your system PATH. You may also set one of the environment "
                "variables FFMPEG or FFMPEG_LOCATION."
            )
            self.log_error(msg)
            raise RuntimeError(msg)

    def ensure_templates_exist(self):
        msg = "tk-aftereffects-queue misconfigured..."
        missing_templates = []
        if not self.get_render_template():
            missing_templates.append(
                '  Template specified by "template_render_area" does not exist: %r'
                % self.get_setting('template_render_area')
            )
        if not self.get_review_template():
            missing_templates.append(
                '  Template specified by "template_review_area" does not exist: %r'
                % self.get_setting('template_review_area')
            )
        if missing_templates:
            msg += '\n' + '\n'.join(missing_templates)
            self.log_error(msg)
            raise RuntimeError(msg)

    def show_app(self):
        if self.aequeue_module is None:
            self.aequeue_module = self.import_module('aequeue')
            self.aequeue = self.aequeue_module.Application(
                self,
                parent=self.engine._get_dialog_parent()
            )
        self.aequeue.show()

    def hide_app(self):
        self.aequeue.hide()

    def destroy_app(self):
        self.aequeue.hide()
        self.aequeue.ui.deleteLater()
        del self.aequeue
        self.aequeue = None

    def get_command_name(self):
        return self.get_setting('command_name')

    def get_window_title(self):
        return self.get_setting('command_name').strip('.')

    def get_resource(self, path):
        '''Get a path to a file in this application directory.'''

        return normalize(self.disk_location, path)

    def get_default_mp4_quality(self):
        return self.get_setting('default_mp4_quality')

    def get_default_gif_quality(self):
        return self.get_setting('default_gif_quality')

    def get_default_output_module(self, existing_output_modules):
        '''Get the first configured output_module that exists.

        Used as the default output module in the UI.
        '''

        defaults = self.get_setting('default_output_module')
        for default in defaults:
            if default in existing_output_modules:
                return default

    def get_work_template(self):
        '''Get the work file template used to extract fields from the AE project path'''

        template_name = self.get_setting('template_work_file')
        template = self.sgtk.templates.get(template_name)
        return template

    def get_render_template(self):
        '''Get the path template used to generate a path to the folder for outputting
        all renders.'''

        template_name = self.get_setting('template_render_area')
        template = self.sgtk.templates.get(template_name)
        return template

    def get_review_template(self):
        '''Get the path template used to generate a path to a review folder where
        encoded media for review will be copied to.'''

        template_name = self.get_setting('template_review_area')
        template = self.sgtk.templates.get(template_name)
        return template

    def get_copy_to_review(self):
        '''Should encoded media be copied to the review area defined by
        template_review_area?'''

        return self.get_setting('copy_to_review_area')

    def get_publish_on_upload(self):
        '''Should encoded media be copied to the review area defined by
        template_review_area?'''

        return self.get_setting('publish_on_upload')

    def get_move_to_review(self):
        '''Should encoded media be copied to the review area defined by
        template_review_area?'''

        return self.get_setting('move_to_review_area')

    def send_is_available(self):
        '''Is the send_report_hook available?'''

        return self.execute_hook_method('send_report_hook', 'is_available')

    def send_on_error(self):
        '''Should errors be sent automatically when an error during rendering occurs?'''

        return self.execute_hook_method('send_report_hook', 'send_on_error')

    def send_report(self, ctx, runner, report, html_report):
        '''Send an error report using the send_report_hook's send method.'''

        if not self.send_is_available():
            raise RuntimeError("Can't send report: send_report_hook is unavailable...")

        return self.execute_hook_method(
            'send_report_hook',
            'send',
            ctx=ctx,
            runner=runner,
            report=report,
            html_report=html_report,
            settings=self.get_setting('send_report_settings') or {},
        )

    def ensure_context_optimal(self, reset=False):
        '''Make sure the current context is up to date with your project context.'''

        current_ctx = self.engine.context

        try:
            project_ctx = self.engine.sgtk.context_from_path(self.engine.project_path)
        except Exception:
            return False, "Can't determine Context. Please use ShotGrid Open/Save..."

        if project_ctx.step and not project_ctx.task:
            # Lookup tasks
            tasks = self.shotgun.find(
                'Task',
                filters=[
                    ['entity', 'is', project_ctx.entity],
                    ['step', 'is', project_ctx.step],
                ],
            )
            if len(tasks) < 2:
                task = tasks[0]
                project_ctx = self.engine.sgtk.context_from_entity('Task', task['id'])
            else:
                return False, "Can't determine Task. Please use ShotGrid Open/Save..."

        should_change_context = (
            current_ctx.project != project_ctx.project
            or current_ctx.entity != project_ctx.entity
            or current_ctx.step != project_ctx.step
            or current_ctx.task != project_ctx.task
        )
        if should_change_context:
            optimal_ctx = project_ctx
        else:
            optimal_ctx = current_ctx

        if not optimal_ctx.task:
            return False, "Can't determine Task. Please use ShotGrid Open/Save..."

        if should_change_context:
            self._reset_on_context_change = reset
            self.engine.adobe.context_about_to_change()
            sgtk.platform.change_context(optimal_ctx)

        return True, 'Ready to render!'

    @property
    def context_change_allowed(self):
        return True

    def post_context_change(self, old_context, new_context):
        if self.aequeue:
            # Update UI Application
            self.aequeue.update_tk_app(self)

            # Reset UI Queue
            if self._reset_on_context_change:
                self.aequeue.reset_queue()

        self._reset_on_context_change = True
