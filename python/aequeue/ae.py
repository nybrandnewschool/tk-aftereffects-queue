import fnmatch
import os
import re
import sys
import threading
import xml.etree.ElementTree as xmlElementTree
from contextlib import contextmanager


class AfterEffectsEngineWrapper(object):
    """Wraps tk-aftereffects engine providing convenient api methods."""

    file_info_properties = [
        "Full Flat Path",
        "Base Path",
        "Subfolder Path",
        "File Name",
        "File Template",
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

    def save(self, file=None):
        if file:
            return self.adobe.app.project.save(self.adobe.File(file))

        if self.adobe.app.project.dirty:
            return self.adobe.app.project.save()

    def open(self, file):
        return self.adobe.app.open(self.adobe.File(file))

    def save_copy(self, copy_path):
        # Save original project
        original_path = self.engine.project_path
        self.save()

        # Save copy
        os.makedirs(os.path.dirname(copy_path), exist_ok=True)
        self.save(copy_path)

        # Restore original project
        self.open(original_path)

    def has_dynamic_links(self, mimeData):
        return mimeData.hasFormat(self.ae_mime_format)

    def get_dynamic_links(self, mimeData):
        dynamic_links_data = mimeData.data(self.ae_mime_format).data()
        dynamic_links = dynamic_links_data.decode("utf-8", "ignore")
        results = []
        tree = xmlElementTree.fromstring(dynamic_links)
        for source in tree.findall(".//Source"):
            link = {}
            for child in source:
                link[child.tag] = child.text
            results.append(link)
        return results

    def walk_items(self, item_collection=None):
        item_collection = item_collection or self.adobe.app.project.items
        for item in self.iter_collection(item_collection):
            if item["instanceof"] == "FolderItem":
                yield item
                for item in self.walk_items(item):
                    yield item
            else:
                yield item

    def get_items_from_dynamic_links(self, links):
        link_ids = [link["ID"] for link in links]
        for item in self.walk_items():
            if item.dynamicLinkGUID in link_ids:
                yield item

    def get_aerender_executable(self):
        application_templates = {
            "darwin": [
                "/Applications/Adobe After Effects {version}/aerender",
                "/Applications/Adobe After Effects CC {version}/aerender",
            ],
            "win32": [
                "C:/Program Files/Adobe/Adobe After Effects {version}/Support Files/aerender.exe",
                "C:/Program Files/Adobe/Adobe After Effects CC {version}/Support Files/aerender.exe",
            ],
        }[sys.platform]
        version = self.engine.host_info["version"]
        for application_template in application_templates:
            path = application_template.format(version=version)
            if os.path.exists(path):
                return path

    @contextmanager
    def TempComp(self, name):
        """Context yielding a comp.

        The comp will be removed from the project after exiting the context.

        Arguments:
            name (str): Name of temporary comp.

        Yields:
            Comp
        """

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
        """Context yielding a RenderQueueItem for <comp>.

        The RenderQueueItem will be removed after exiting the context.
        """

        rq_item = None
        try:
            rq_item = self.enqueue_comp(comp)
            yield rq_item
        finally:
            if rq_item:
                rq_item.remove()

    def get_comp(self, name):
        """Get a comp by name.

        Arguments:
            name (str): AE Comp name.

        Returns:
            Comp
        """

        for item in self.iter_collection(self.adobe.app.project.items):
            if item.name == name:
                return item

    def enqueue_comp(self, comp):
        """Adds a comp to the Render Queue.

        Arguments:
            comp (Comp): AE Comp Object.

        Returns:
            RenderQueueItem
        """

        return self.adobe.app.project.renderQueue.items.add(comp)

    def get_queued_render_items(self):
        """Get a list of RQItems with status QUEUED.

        These are all of the unrendered items in the Render Queue!
        """

        results = []
        rq_items = self.adobe.app.project.renderQueue.items
        for item in self.engine.iter_collection(rq_items):
            if item.status == self.adobe.RQItemStatus.QUEUED:
                results.append(item.comp.data)
        return results

    def render_queue_empty(self):
        """Returns True if the render queue is empty."""

        return self.adobe.app.project.renderQueue.items.length <= 0

    def find_templates(self, pattern="*", skip_hidden=True):
        templates = {}
        if self.render_queue_empty():
            with self.TempComp("QUERY_TEMPLATES") as comp:
                self.enqueue_comp(comp)
                templates["output_modules"] = self.find_output_module_templates()
                templates["render_settings"] = self.find_render_settings_templates()
        else:
            templates["output_modules"] = self.find_output_module_templates()
            templates["render_settings"] = self.find_render_settings_templates()
        return templates

    def find_output_module_templates(self, pattern="*", skip_hidden=True):
        """Find Output Module templates.

        Arguments:
            pattern (str): A wildcard pattern to match. Defaults to "*". Will
                return all templates if you do not specify a different pattern.
            skip_hidden (bool): Skip "_HIDDEN" templates. Defaults to True.

        Returns:
            List[str]
        """

        def filter_templates(om):
            for template in om.templates:
                try:
                    if skip_hidden and template.startswith("_HIDDEN"):
                        continue

                    if fnmatch.fnmatch(template, pattern):
                        yield template
                except Exception:
                    continue

        if self.render_queue_empty():
            with self.TempComp("QUERY_TEMPLATES") as comp:
                rq_item = self.enqueue_comp(comp)
                om = rq_item.outputModule(1)
                return list(filter_templates(om))
        else:
            rq_item = self.adobe.app.project.renderQueue.items[1]
            om = rq_item.outputModule(1)
            return list(filter_templates(om))

    def find_render_settings_templates(self, pattern="*", skip_hidden=True):
        """Find Output Module templates.

        Arguments:
            pattern (str): A wildcard pattern to match. Defaults to "*". Will
                return all templates if you do not specify a different pattern.
            skip_hidden (bool): Skip "_HIDDEN" templates. Defaults to True.

        Returns:
            List[str]
        """

        def filter_settings(rq_item):
            for template in rq_item.templates:
                try:
                    if skip_hidden and template.startswith("_HIDDEN"):
                        continue

                    if fnmatch.fnmatch(template, pattern):
                        yield template
                except Exception:
                    continue

        if self.render_queue_empty():
            with self.TempComp("QUERY_SETTINGS") as comp:
                rq_item = self.enqueue_comp(comp)
                return list(filter_settings(rq_item))
        else:
            rq_item = self.adobe.app.project.renderQueue.items[1]
            return list(filter_settings(rq_item))

    def _validate_file_info(self, data):
        errors = {}
        for key, value in data.items():
            if key not in self.file_info_properties:
                errors[key] = "Invalid key"
            if not isinstance(value, str):
                errors[key] = "Invalid value type: " + str(type(value))
        if errors:
            msg = "File Info validation error: \n"
            for key, value in errors.items():
                msg += f"    {key}: {value}\n"
            raise RuntimeError(msg)

    def _to_output_module(self, obj):
        if obj.data["instanceof"] == "RenderQueueItem":
            return obj.outputModule(1)
        if obj.data["instanceof"] == "OutputModule":
            return obj
        raise ValueError(
            'Argument "obj" expected RenderQueueItem or OutputModule got <%s>'
            % obj.data["instanceof"]
        )

    def set_file_info(self, obj, data):
        """Set the Output File Info for the given RenderQueueItem or OutputModule.

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
        """

        self._validate_file_info(data)
        obj = self._to_output_module(obj)

        # Generate full path from provided data.
        full_path = data.get("Full Flat Path")
        if not full_path:
            parts = [
                data.get("Base Path", ""),
                data.get("Subfolder Path", ""),
                data.get("File Name", data.get("File Template", "")),
            ]
            full_path = "/".join([part for part in parts if part])

        # Set output module's file object.
        self.set_file(obj, full_path.replace("\\", "/"))

    def set_file(self, obj, path):
        """Set the File object for the given RenderQueueItem or OutputModule.

        Arguments:
            obj (ProxyWrapper): ProxyWrapper of type RenderQueueItem or OutputModule
            path (str): Full path to output file location.
        """

        obj = self._to_output_module(obj)
        # Clear existing file info ensuring we have no conflicting data.
        obj.setSettings(
            {"Output File Info": {key: "" for key in self.file_info_properties}}
        )
        # Set output module's file object.
        obj.file = self.adobe.File(path)

    def get_file_info(self, obj):
        """Get the Output File Info for the given RenderQueueItem or OutputModule.

        Arguments:
            obj (ProxyWrapper): ProxyWrapper of type RenderQueueItem or OutputModule

        Returns:
            {
                'Full Flat Path': str,  # ("Base Path" / "Subfolder Path" / "File Name")
                'Base Path': str,  # Base folder for output
                'Subfolder Path': str,  # Subfolder within "Base Path"
                'File Name': str,  # Name of file
                'File Template': str,  # Name template like...
                                       # [compName]/[compName].[fileExtension]
                                       # [compName]/[compName].[#####].[fileExtension]
            }
        """

        obj = self._to_output_module(obj)
        return {
            "Full Flat Path": obj.file.fsName,
            "File Name": os.path.basename(obj.file.fsName),
        }

    def get_ae_path_info(self, file_path):
        info = {
            "padding": 0,
            "padding_str": "",
            "is_sequence": False,
            "extension": file_path.split(".")[-1],
            "version": None,
            "version_number": 1,
            "published_file_type": None,
        }

        # Check if path represents image sequence
        sequence_match = re.search(r"\[(\#+)\]", file_path)
        if sequence_match:
            info["is_sequence"] = True
            info["padding"] = len(sequence_match.group(1))
            info["padding_str"] = sequence_match.group(0)

        # Check if file is versioned
        version_match = re.search(r"v(\d+)", file_path)
        if version_match:
            info["version_number"] = int(version_match.group(1))
            info["version"] = version_match.group(0)

        if info["extension"] in ["avi", "mov", "mp4", "mpeg4"]:
            info["published_file_type"] = "Movie"
        else:
            info["published_file_type"] = "Rendered Image"

        return info

    @contextmanager
    def suppress_dialogs(self):
        try:
            self.adobe.app.beginSuppressDialogs()
            yield
        finally:
            self.adobe.app.endSuppressDialogs(False)

    def render_queue_item(self, rq_item):
        with self.suppress_dialogs():
            return self._engine.render_queue_item(rq_item)

    def render_queue_item_async(self, rq_item):
        with self.suppress_dialogs():
            return self._render_queue_item_async(rq_item)

    def _render_queue_item_async(self, queue_item):
        """
        renders a given queue_item, by disabling all other queued items
        and only enabling the given item. After rendering the state of the
        render-queue is reverted.

        :param queue_item: The render queue item to be rendered
        :type queue_item: `adobe.RenderQueueItemObject`_
        :returns: Indicating successful rendering or not
        :rtype: bool
        """

        # save the queue state for all unrendered items
        queue_item_state_cache = [(queue_item, queue_item.render)]
        for item in self.iter_collection(self.adobe.app.project.renderQueue.items):
            # one cannot change the status on
            if item.status != self.adobe.RQItemStatus.QUEUED:
                continue
            queue_item_state_cache.append((item, item.render))
            item.render = False

        success = False
        queue_item.render = True
        self.logger.debug("Start rendering..")
        try:
            self.adobe.app.project.renderQueue.renderAsync()

            # Wait for render queue to achieve finished state
            while True:
                rendering_states = [
                    self.adobe.RQItemStatus.RENDERING,
                    self.adobe.RQItemStatus.WILL_CONTINUE,
                ]
                if queue_item.status not in rendering_states:
                    break

                # Process UI events while we wait for render to finish.
                self.adobe.wait(single_loop=True, process_events=True)

        except Exception as e:
            # This catches errors thrown during the AfterEffects Render process.
            # Which may return various different errors. This situation never
            # occured during development.
            self.logger.error(
                ("Skipping item due to an error " "while rendering: {}").format(e)
            )
        finally:
            acceptable_states = [
                self.adobe.RQItemStatus.DONE,
                self.adobe.RQItemStatus.ERR_STOPPED,
                self.adobe.RQItemStatus.RENDERING,
            ]
            # reverting the original queued state for all
            # unprocessed items
            while queue_item_state_cache:
                item, status = queue_item_state_cache.pop(0)
                if item.status not in acceptable_states:
                    item.render = status

        # we check for success if the render queue item status
        # has changed to DONE
        success = queue_item.status == self.adobe.RQItemStatus.DONE
        return success
