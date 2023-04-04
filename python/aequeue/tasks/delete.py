import os

from .. import const
from .core import Task


class Delete(Task):
    step = const.Cleaning

    def __init__(self, file, *args, **kwargs):
        self.file = file
        super(Delete, self).__init__(*args, **kwargs)

    def execute(self):
        # Check for cancelled before performing copy.
        if self.status_request == const.Cancelled:
            return self.accept(const.Cancelled)

        self.log.debug("Removing file %s...", self.file)

        if not os.path.exists(self.file):
            self.log.debug("Skipped: File does not exist...%s", self.file)
            self.set_status(const.Running, 100)
            return

        os.remove(self.file)
        self.set_status(const.Running, 100)
