# Standard library imports
import os

# Third party imports
from sgtk.platform import Application


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


class AEQueueApplication(Application):

    def init_app(self):
        # Perform additional validation before registering
        self.ensure_ffmpeg_installed()
        self.ensure_templates_exist()

        self.aequeue_module = self.import_module('aequeue')
        self.aequeue = self.aequeue_module.Application(
            self,
            parent=self.engine._get_dialog_parent()
        )
        self.engine.register_command(
            self.get_setting('command_name'),
            self.show_app,
        )

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
        self.aequeue.show()

    def hide_app(self):
        self.aequeue.hide()

    def destroy_app(self):
        self.aequeue.hide()
        self.aequeue.ui.deleteLater()
        del self.aequeue
        self.aequeue = None

    def get_resource(self, path):
        """Get a path to a file in this application directory."""
        return normalize(self.disk_location, path)

    def get_default_output_module(self, existing_output_modules):
        defaults = self.get_setting('default_output_module')
        for default in defaults:
            if default in existing_output_modules:
                return default

    def get_work_template(self):
        template_name = self.get_setting('template_work_file')
        template = self.sgtk.templates.get(template_name)
        return template

    def get_render_template(self):
        template_name = self.get_setting('template_render_area')
        template = self.sgtk.templates.get(template_name)
        return template

    def get_review_template(self):
        template_name = self.get_setting('template_review_area')
        template = self.sgtk.templates.get(template_name)
        return template

    def get_copy_to_review(self):
        return self.get_setting('copy_to_review_area')

    @property
    def context_change_allowed(self):
        return True

    def post_context_change(self, old_context, new_context):
        self.aequeue.reset()
