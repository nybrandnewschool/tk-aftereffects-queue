import xml.etree.ElementTree as xmlElementTree

from ..vendor.qtpy import QtCore

from ..widgets import Window


class TestApplication(QtCore.QObject):

    ae_mime_format = 'application/x-qt-windows-mime;value="dynamiclinksourcelist"'

    def __init__(self, parent=None):
        super(TestApplication, self).__init__(parent)

        # Create UI
        self.ui = Window()
        self.ui.queue.drag.connect(self.drag_queue)
        self.ui.queue.drop.connect(self.drop_queue)

    def show(self):
        self.ui.show()

    def drag_queue(self, event):
        data = {
            'action': event.proposedAction(),
            'formats': event.mimeData().formats(),
            'hasColor': event.mimeData().hasColor(),
            'hasHtml': event.mimeData().hasHtml(),
            'hasImage': event.mimeData().hasImage(),
            'hasText': event.mimeData().hasText(),
            'hasUrls': event.mimeData().hasUrls(),
            'html': event.mimeData().html(),
            'text': event.mimeData().text(),
            'color': event.mimeData().colorData(),
            'imageData': event.mimeData().imageData(),
            'urls': event.mimeData().urls(),
        }
        format_data = {
            format: event.mimeData().data(format).data().decode('utf-8', 'ignore')
            for format in event.mimeData().formats()
        }
        print('Received drag event...\n')
        print('\n'.join([f'{k}: {v}' for k, v in data.items()]))
        print('\n'.join([f'{k}: {v}' for k, v in format_data.items()]))
        print('HAS AE DYNAMIC LINKS: %s' % self.has_dynamic_links(event.mimeData()))
        print('LINKS: %s' % self.get_dynamic_links(event.mimeData()))
        event.acceptProposedAction()

    def drop_queue(self, event):
        dynamic_links = self.get_dynamic_links(event.mimeData())
        for link in dynamic_links:
            self.ui.queue.add_item(link['ID'])
        event.acceptProposedAction()

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
