import fnmatch
import os
import sys
import re
import threading
import xml.etree.ElementTree as xmlElementTree
from contextlib import contextmanager


class AfterEffectsEngineWrapper(object):
    '''Wraps tk-aftereffects engine providing convenient api methods.'''

    file_info_properties = [
        'Full Flat Path',
        'Base Path',
        'Subfolder Path',
        'File Name',
        'File Template',
    ]
    ae_mime_format = 'application/x-qt-windows-mime;value="dynamiclinksourcelist"'

    def __init__(self, engine):
        self._engine = engine
        self.lock = threading.Lock()

    def __getattr__(self, attr):
        return getattr(self._engine, attr)

    @property
    def engine(self):
        return self._engine

    @property
    def adobe(self):
        return self._engine.adobe

    def has_dynamic_links(self, mimeData):
        return mimeData.hasFormat(self.ae_mime_format)

    def get_dynamic_links(self, mimeData):
        dynamic_links_data = mimeData.data(self.ae_mime_format).data()
        dynamic_links = dynamic_links_data.decode('utf-8', 'ignore')
        results = []
        tree = xmlElementTree.fromstring(dynamic_links)
        for source in tree.findall('.//Source'):
            link = {}
            for child in source:
                link[child.tag] = child.text
            results.append(link)
        return results

    def walk_items(self, item_collection=None):
        item_collection = item_collection or self.adobe.app.project.items
        for item in self.iter_collection(item_collection):
            if item['instanceof'] == 'FolderItem':
                yield item
                for item in self.walk_items(item):
                    yield item
            else:
                yield item

    def get_items_from_dynamic_links(self, links):
        link_ids = [link['ID'] for link in links]
        for item in self.walk_items():
            if item.dynamicLinkGUID in link_ids:
                yield item

    def get_aerender_executable(self):
        application_templates = {
            'darwin': [
                '/Applications/Adobe After Effects {version}/aerender',
                '/Applications/Adobe After Effects CC {version}/aerender',
            ],
            'win32': [
                'C:/Program Files/Adobe/Adobe After Effects {version}/Support Files/aerender.exe',
                'C:/Program Files/Adobe/Adobe After Effects CC {version}/Support Files/aerender.exe',
            ]
        }[sys.platform]
        version = self.engine.host_info['version']
        version = '20' + version.split('.')[0]
        for application_template in application_templates:
            path = application_template.format(version=version)
            if os.path.exists(path):
                return path

    @contextmanager
    def TempComp(self, name):
        '''Context yielding a comp.

        The comp will be removed from the project after exiting the context.

        Arguments:
            name (str): Name of temporary comp.

        Yields:
            Comp
        '''

        comp = None
        try:
            comp = self.adobe.app.project.items.addComp(
                name, 256, 256, 1.0, 180.0, 24.0
            )
            yield comp
        finally:
            if comp:
                comp.remove()

    @contextmanager
    def TempEnqueue(self, comp):
        '''Context yielding a RenderQueueItem for <comp>.

        The RenderQueueItem will be removed after exiting the context.
        '''

        rq_item = None
        try:
            rq_item = self.enqueue_comp(comp)
            yield rq_item
        finally:
            if rq_item:
                rq_item.remove()

    def get_comp(self, name):
        '''Get a comp by name.

        Arguments:
            name (str): AE Comp name.

        Returns:
            Comp
        '''

        for item in self.iter_collection(self.adobe.app.project.items):
            if item.name == name:
                return item

    def enqueue_comp(self, comp):
        '''Adds a comp to the Render Queue.

        Arguments:
            comp (Comp): AE Comp Object.

        Returns:
            RenderQueueItem
        '''

        return self.adobe.app.project.renderQueue.items.add(comp)

    def get_queued_render_items(self):
        '''Get a list of RQItems with status QUEUED.

        These are all of the unrendered items in the Render Queue!
        '''

        results = []
        rq_items = self.adobe.app.project.renderQueue.items
        for item in self.engine.iter_collection(rq_items):
            if item.status == self.adobe.RQItemStatus.QUEUED:
                results.append(item.comp.data)
        return results

    def find_output_module_templates(self, pattern='*', skip_hidden=True):
        '''Find Output Module templates.

        Arguments:
            pattern (str): A wildcard pattern to match. Defaults to "*". Will
                return all templates if you do not specify a different pattern.
            skip_hidden (bool): Skip "_HIDDEN" templates. Defaults to True.

        Returns:
            List[str]
        '''

        results = []
        with self.TempComp('QUERY_TEMPLATES') as comp:
            rq_item = self.enqueue_comp(comp)
            om = rq_item.outputModule(1)
            for template in om.templates:
                try:
                    if skip_hidden and template.startswith('_HIDDEN'):
                        continue

                    if fnmatch.fnmatch(template, pattern):
                        results.append(template)
                except Exception:
                    continue
        return results

    def _validate_file_info(self, data):
        errors = {}
        for key, value in data.items():
            if key not in self.file_info_properties:
                errors[key] = 'Invalid key'
            if not isinstance(value, str):
                errors[key] = 'Invalid value type: ' + str(type(value))
        if errors:
            msg = 'File Info validation error: \n'
            for key, value in errors.items():
                msg += f'    {key}: {value}\n'
            raise RuntimeError(msg)

    def _to_output_module(self, obj):
        if obj.data['instanceof'] == 'RenderQueueItem':
            return obj.outputModule(1)
        if obj.data['instanceof'] == 'OutputModule':
            return obj
        raise ValueError(
            'Argument "obj" expected RenderQueueItem or OutputModule got <%s>'
            % obj.data['instanceof']
        )

    def set_file_info(self, obj, data):
        '''Set the Output File Info for the given RenderQueueItem or OutputModule.

        Arguments:
            obj (ProxyWrapper): ProxyWrapper of type RenderQueueItem or OutputModule
            data (dict): File info data to set for the OutputModule

        Data Schema:
            {
                'Full Flat Path': str,  # ("Base Path" / "Subfolder Path" / "File Name")
                'Base Path': str,  # Base folder for output
                'Subfolder Path': str,  # Subfolder within "Base Path"
                'File Name': str,  # Name of file
                'File Template': str,  # Name template like...
                                       # [compName]/[compName].[fileextension]
                                       # [compName]/[compName].[#####].[fileextension]
            }
        '''

        self._validate_file_info(data)
        obj = self._to_output_module(obj)
        obj.setSettings({'Output File Info': data})

    def get_file_info(self, obj):
        '''Get the Output File Info for the given RenderQueueItem or OutputModule.

        Arguments:
            obj (ProxyWrapper): ProxyWrapper of type RenderQueueItem or OutputModule

        Returns:
            {
                'Full Flat Path': str,  # ("Base Path" / "Subfolder Path" / "File Name")
                'Base Path': str,  # Base folder for output
                'Subfolder Path': str,  # Subfolder within "Base Path"
                'File Name': str,  # Name of file
                'File Template': str,  # Name template like...
                                       # [compName]/[compName].[fileextension]
                                       # [compName]/[compName].[#####].[fileextension]
            }
        '''

        obj = self._to_output_module(obj)
        return {
            'Full Flat Path': obj.file.fsName,
            'File Name': os.path.basename(obj.file.fsName),
        }

    def get_ae_path_info(self, file_path):
        info = {
            'padding': 0,
            'padding_str': '',
            'is_sequence': False,
            'extension': file_path.split('.')[-1],
        }

        # Check if path represents image sequence
        sequence_match = re.search(r'\[(\#+)\]', file_path)
        if sequence_match:
            info['is_sequence'] = True
            info['padding'] = len(sequence_match.group(1))
            info['padding_str'] = sequence_match.group(0)

        return info
