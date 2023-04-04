import os
import shutil

from .. import const
from .core import Task


class Delete(Task):
    step = const.Cleaning

    def __init__(self, file, *args, **kwargs):
        self.file = file
        super(Dlete, self).__init__(*args, **kwargs)

    def execute(self):
        # Check for cancelled before performing copy.
        if self.status_request == const.Cancelled:
            return self.accept(const.Cancelled)

        if not os.path.exists(self.file):
            self.log.debug("File does not exist...%s", file)
            self.set_status(const.Running, 100)
            return

        self.log.debug("Removing %s...", file)
        os.path.unlink(self.file)
        self.set_status(const.Running, 100)
