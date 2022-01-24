import os
import shutil

from .. import const
from .core import Task


class Copy(Task):

    step = const.Copying

    def __init__(self, src_file, dst_file, *args, **kwargs):
        self.src_file = src_file
        self.dst_file = dst_file
        super(Copy, self).__init__(*args, **kwargs)

    def execute(self):
        self.log.debug('Ensuring folder "%s" exists...', self.dst_file)
        dst_dir = os.path.dirname(self.dst_file)
        if not os.path.exists(dst_dir):
            self.log.debug('Creating dst folder...')
            os.makedirs(dst_dir)
        self.set_status(const.Running, 50)

        self.log.debug('Copying "%s" to "%s"...', self.src_file, self.dst_file)
        shutil.copy2(self.src_file, self.dst_file)
        self.set_status(const.Running, 100)
