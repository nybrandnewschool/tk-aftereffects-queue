import os
import tempfile

from .. import const
from ..vendor import ffmpeg_lib
from .core import Task


def get_shotgun():
    from sgtk.util.shotgun import create_sg_connection
    return create_sg_connection()


class SGUploadVersion(Task):

    step = const.Uploading

    def __init__(self, src_file, sg_ctx, comment, *args, **kwargs):
        self.sg = get_shotgun()
        self.sg_ctx = sg_ctx
        self.comment = comment
        self.src_file = src_file
        super(SGUploadVersion, self).__init__(*args, **kwargs)

    def execute(self):
        # Get necessary data from task context
        app = self.context['app']
        options = self.context['options']
        src_file = self.src_file
        src_file_info = app.engine.get_ae_path_info(src_file)
        if src_file_info['is_sequence']:
            src_file = src_file.replace(
                src_file_info['padding_str'],
                '%{:0>2}d'.format(src_file_info['padding'])
            )

        self.log.debug('Preparing version data for ShotGrid...')
        dirname, basename = os.path.split(src_file)
        filename, ext = os.path.splitext(basename)
        code = filename.split('.')[0]
        version_data = {
            'code': code,
            'description': self.comment,
            'entity': self.sg_ctx.entity,
            'project': self.sg_ctx.project,
            'sg_path_to_frames': src_file,
            'sg_status_list': 'rev',
            'sg_task': self.sg_ctx.task,
            'user': self.sg_ctx.user,
        }
        self.set_status(const.Running, 25)

        upload_file = src_file
        if src_file_info['is_sequence']:
            if options.mp4:
                upload_file = self.context['flow'].get_result(const.Encoding + ' MP4')
            else:
                self.log.debug('Encoding sequence as mp4 for ShotGrid...')
                upload_file = self.encode_sequence(
                    src_file,
                    os.path.join(tempfile.gettempdir(), filename + '.mp4'),
                )
        self.set_status(const.Running, 50)

        self.log.debug('Creating or updating Version in ShotGrid...')
        version = self.create_version(version_data)
        self.set_status(const.Running, 75)

        self.log.debug('Uploading media to ShotGrid...')
        self.upload_media(version, upload_file)
        self.set_status(const.Running, 100)
        return version

    def create_version(self, version_data):
        '''Get existing version or create a new one.'''

        version = self.sg.find_one(
            'Version',
            [
                ['project', 'is', version_data['project']],
                ['code', 'is', version_data['code']],
                ['sg_task', 'is', version_data['sg_task']],
                ['entity', 'is', version_data['entity']],
            ],
            ['id', 'code', 'sg_path_to_frames'],
        )

        if not version:
            version = self.sg.create('Version', version_data)
        else:
            self.sg.update('Version', version['id'], version_data)

        return version

    def upload_media(self, version, file):
        '''Upload file to sg_uploaded_media field of a Version entity.'''

        media = self.sg.upload(
            'Version',
            version['id'],
            path=file,
            field_name='sg_uploaded_movie',
        )
        return media

    def encode_sequence(self, in_file, out_file):
        '''Encode an image sequence as an mp4.'''

        proc = ffmpeg_lib.encode_sequence(in_file, out_file, framerate=24)
        success = ffmpeg_lib.watch(proc)
        if not success:
            raise RuntimeError('ffmpeg encoding stopped.')

        return out_file
