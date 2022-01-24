import sys
import textwrap
from weakref import WeakValueDictionary
from string import Template

from . import const, resources
from .vendor.Qt import QtCore, QtGui, QtWidgets


def lerp(a, b, t):
    '''Linearly interpolate between two values.'''

    return (1 - t) * a + t * b


class ValueAnimation(QtCore.QVariantAnimation):

    value_changed = QtCore.Signal(object)

    def updateCurrentTime(self, time):
        progress = self.easingCurve().valueForProgress(time / self.duration())
        value = lerp(self.startValue(), self.endValue(), progress)
        self.value_changed.emit(value)
        return super(ValueAnimation, self).updateCurrentTime(time)


class Theme:
    color_codes = {
        'light_highlight': '#DDDDDD',
        'light': '#AFAFAF',
        'dark': '#1A1A1A',
        'on_surface_highlight': '#393939',
        'on_surface': '#303030',
        'surface_highlight': '#292929',
        'surface': '#202020',
        'on_color': '#F2F2F2',
        'yellow': '#F2C94C',
        'red': '#EB5757',
        'purple': '#9B51E0',
        'blue': '#2D9CDB',
        'green': '#219653',
    }
    colors = {
        key: QtGui.QColor(value)
        for key, value in color_codes.items()
    }
    status_color_codes = {
        const.Queued: color_codes['on_surface'],
        const.Rendering: color_codes['yellow'],
        const.Encoding: color_codes['red'],
        const.Failed: color_codes['red'],
        const.Copying: color_codes['purple'],
        const.Uploading: color_codes['blue'],
        const.Done: color_codes['green'],
        const.Success: color_codes['green'],
    }
    status_colors = {
        key: QtGui.QColor(value)
        for key, value in status_color_codes.items()
    }
    icons = resources.get_icon_variables()
    variables = {
        'h1': (
            'font-family: "Roboto";\n'
            'font-size: 14px;\n'
        ),
        'p': (
            'font-family: "Roboto";\n'
            'font-size: 12px;\n'
        ),
        'border': 'border: 1px solid $on_surface',
        'border_highlight': 'border: 1px solid $on_surface_highlight',
        'rounded': 'border-radius: 3px',
        'border_thick': 'border: 2px solid $on_surface',
        'outline': 'outline: 1px solid $on_surface_highlight'
    }

    @classmethod
    def StyleSheet(cls, css, **extra_variables):
        variables = dict(cls.variables)
        variables.update(cls.color_codes)
        variables.update(cls.status_color_codes)
        variables.update(cls.icons)
        variables.update(extra_variables)
        css = textwrap.dedent(css)
        css = Template(css).safe_substitute(variables)
        css = Template(css).safe_substitute(variables)
        return css


class SectionHeader(QtWidgets.QWidget):

    css = Theme.StyleSheet('''
        QWidget {
            background: $surface;
        }
        QLabel {
            $h1;
            color: $light;
        }
    ''')

    def __init__(self, label, button=None, parent=None):
        super(SectionHeader, self).__init__(parent)

        self.label = QtWidgets.QLabel(label)

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignVCenter)
        self.layout.setContentsMargins(20, 0, 20, 0)
        self.layout.setSpacing(0)

        self.layout.addWidget(self.label)
        self.layout.addStretch()

        if button:
            self.layout.addWidget(button)

        self.setFixedHeight(46)
        self.setLayout(self.layout)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setStyleSheet(self.css)


class Tool(QtWidgets.QToolButton):

    css = Theme.StyleSheet('''
        QToolButton {
            $rounded;
            border: None;
            background: None;
        }
        QToolButton:focus {
            $border;
        }
        QToolButton:hover {
            $border_highlight;
            background: $surface_highlight;
        }
        QToolButton:pressed {
            $border;
            background: $dark;
        }
    ''')

    def __init__(self, icon, parent=None):
        super(Tool, self).__init__(parent)

        self.setIcon(QtGui.QIcon(icon))
        self.setIconSize(QtCore.QSize(20, 20))
        self.setStyleSheet(self.css)


class CheckBox(QtWidgets.QCheckBox):

    css = Theme.StyleSheet('''
        QCheckBox {
            border: 0;
            padding: 2px;
            background: transparent;
        }
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
        }
        QCheckBox::indicator:unchecked {
            image: url("$cb_unchecked");
        }
        QCheckBox::indicator:unchecked:hover {
            image: url("$cb_unchecked_hover");
        }
        QCheckBox::indicator:unchecked:pressed {
            image: url("$cb_unchecked");
        }
        QCheckBox::indicator:checked {
            image: url("$cb_checked");
        }
        QCheckBox::indicator:checked:disabled {
            image: url("$cb_checked_disabled");
        }
        QCheckBox::indicator:checked:hover {
            image: url("$cb_checked_hover");
        }
        QCheckBox::indicator:checked:pressed {
            image: url("$cb_checked");
        }
        QCheckBox::indeterminate:checked {
            image: url("$cb_indeterminate");
        }
        QCheckBox::indeterminate:checked:hover {
            image: url("$cb_indeterminate_hover");
        }
        QCheckBox::indeterminate:checked:pressed {
            image: url("$cb_indeterminate");
        }
    ''')

    def __init__(self, parent=None):
        super(CheckBox, self).__init__(parent)

        self.setMinimumSize(24, 24)
        self.setFixedSize(24, 24)
        self.setStyleSheet(self.css)


class ComboBox(QtWidgets.QComboBox):

    css = Theme.StyleSheet('''
        QComboBox {
            $p;
            $border;
            $rounded;
            padding-left: 10px;
            background: $dark;
            color: $light;
        }
        QComboBox:focus {
            $border_highlight;
        }
        QComboBox:disabled {
            border: 0;
            color: $on_surface_highlight;
        }
        QComboBox:hover {
            $border_highlight;
            padding-left: 10px;
            background: $surface_highlight;
            color: $light;
        }
        QComboBox::down-arrow {
            image: url("$chevron_down");
            width: 20px;
            height: 24px;
        }
        QComboBox::down-arrow:disabled {
            image: none;
        }
        QComboBox::drop-down {
            width: 20px;
            border: 0px;
        }
        QListView {
            $p;
            $border;
            background: $dark;
            color: $light;
        }
        QListView::item {
            border: 0px;
            padding-left: 7px;
            height: 24px;
        }
        QListView::item:selected {
            background: $on_surface;
        }
    ''')

    def __init__(self, parent=None):
        super(ComboBox, self).__init__(parent)

        self.setView(QtWidgets.QListView())
        self.setFixedHeight(24)
        self.setStyleSheet(self.css)


class LineEdit(QtWidgets.QLineEdit):

    css = Theme.StyleSheet('''
        QLineEdit {
            $p;
            $border;
            $rounded;
            padding-left: 10px;
            background: $dark;
            color: $light;
        }
        QLineEdit:focus {
            $border_highlight;
        }
        QLineEdit:disabled {
            border: 0;
            color: $on_surface_highlight;
        }
        QLineEdit:hover {
            $border_highlight;
            background: $surface_highlight;
        }
        QLineEdit[text=""]{
            color: $on_surface_highlight;
        }
        QLineEdit[text=""]::hover{
            color: $light;
        }
    ''')

    def __init__(self, placeholder=None, parent=None):
        super(LineEdit, self).__init__(parent)

        if placeholder:
            self.setPlaceholderText(placeholder)

        self.textChanged.connect(lambda: self.style().polish(self))
        self.setFixedHeight(24)
        self.setStyleSheet(self.css)


class Status(QtWidgets.QWidget):

    css = Theme.StyleSheet('''
        QWidget {
            $rounded;
        }
        QWidget[status="default"]{
            background: $queued;
        }
        QWidget[status="queued"]{
            background: $queued;
        }
        QWidget[status="rendering"]{
            background: $rendering;
        }
        QWidget[status="encoding"]{
            background: $encoding;
        }
        QWidget[status="copying"]{
            background: $copying;
        }
        QWidget[status="uploading"]{
            background: $uploading;
        }
        QWidget[status="done"]{
            background: $done;
        }
        QWidget[status="failed"]{
            background: $failed;
        }
        QWidget[status="success"]{
            background: $success;
        }
        QLabel {
            $p;
            color: $on_color;
            background: transparent;
        }
    ''')

    def __init__(self, status, percent, parent=None):
        super(Status, self).__init__(parent)

        self.bar = QtWidgets.QWidget()
        self.bar.setFixedHeight(24)
        self.bar_anim = None

        self.label = QtWidgets.QLabel(status.title())
        self.label.setAlignment(QtCore.Qt.AlignCenter)

        self.layout = QtWidgets.QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.bar, 0, 0, alignment=QtCore.Qt.AlignLeft)
        self.layout.addWidget(self.label, 0, 0)

        self.setProperty('status', 'default')
        self.setFixedHeight(24)
        self.setFixedWidth(100)
        self.setLayout(self.layout)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.set(status, percent)

    def set(self, status, percent):
        self.bar.setProperty('status', status.lower().split()[0])
        self.bar.setFixedWidth(percent)
        self.label.setText(status.title())
        self.setStyleSheet(self.css)


class Menu(QtWidgets.QMenu):

    css = Theme.StyleSheet('''
        QMenu {
            $p;
            $border;
            background: $dark;
            color: $light;
        }
        QMenu::item {
            border: 0px;
            padding-left: 10px;
            padding-right: 10px;
            height: 24px;
        }
        QMenu::item:selected {
            background: $surface_highlight;
            color: $light_highlight;
        }
        QMenu::icon {
            padding-left: 10px;
            padding-right: 0px;
        }
    ''')

    def __init__(self, parent=None):
        super(Menu, self).__init__(parent)
        self.setStyleSheet(self.css)


class KebabMenu(QtWidgets.QPushButton):

    css = Theme.StyleSheet('''
        QPushButton[menu_visible="false"] {
            $rounded;
            border: 0;
            padding: 0;
            margin: 0;
            background-image: url("$more_checked");
            background-repeat: no-repeat;
            background-position: center;
        }
        QPushButton[menu_visible="true"] {
            $border;
            background-color: $surface_highlight;
            background-image: url("$more_hover");
            background-repeat: no-repeat;
            background-position: center;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }
        QPushButton::menu-indicator {
            image: none;
        }
        QPushButton[menu_visible="false"]:disabled {
            background-image: url("$more_disabled");
            background-repeat: no-repeat;
        }
        QPushButton[menu_visible="false"]:focus {
            background-image: url("$more_checked");
            background-repeat: no-repeat;
        }
        QPushButton[menu_visible="false"]:hover {
            background-image: url("$more_hover");
            background-repeat: no-repeat;
        }
        QPushButton[menu_visible="false"]:pressed {
            background-color: $dark;
            background-image: url("$more_checked");
            background-repeat: no-repeat;
        }
        QPushButton[menu_visible="false"]:hover {
            background-image: url("$more_hover");
            background-repeat: no-repeat;
        }
        QMenu {
            $p;
            $border;
            background: $dark;
            color: $light;
        }
        QMenu::item {
            border: 0px;
            padding-left: 10px;
            padding-right: 10px;
            height: 24px;
        }
        QMenu::item:selected {
            background: $surface_highlight;
            color: $light_highlight;
        }
        QMenu::icon {
            padding-left: 10px;
            padding-right: 0px;
        }
    ''')

    def __init__(self, parent=None):
        super(KebabMenu, self).__init__(parent)
        self._menu = QtWidgets.QMenu(parent=self)
        self._menu.aboutToHide.connect(self.before_hide_menu)
        self._anim = None

        self.clicked.connect(self.show_menu)

        self.setStyleSheet(self.css)
        self.setFixedSize(QtCore.QSize(20, 24))
        self.setEnabled(False)
        self.setProperty('menu_visible', False)

    def clear(self):
        self._menu.clear()
        self.setEnabled(False)

    def addAction(self, label, callback, icon=None):
        action = self._menu.addAction(label, callback)
        if icon:
            action.setIcon(QtGui.QIcon(icon))
        self.setEnabled(True)

    def show_menu(self):
        self.setProperty('menu_visible', True)
        self.setStyleSheet(self.css)
        self.before_show_menu()

    def before_show_menu(self):
        menu_size = self._menu.sizeHint()
        self._anim = QtCore.QPropertyAnimation(self._menu, b'size', self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.setStartValue(QtCore.QSize(menu_size.width(), 0))
        self._anim.setEndValue(menu_size)
        self._anim.start(self._anim.DeleteWhenStopped)
        self._menu.move(self.mapToGlobal(QtCore.QPoint(0, self.height() - 1)))
        QtCore.QTimer.singleShot(20, self._menu.show)

    def before_hide_menu(self):
        self.setProperty('menu_visible', False)
        self.setStyleSheet(self.css)


class RenderQueueItemWidget(QtWidgets.QWidget):

    css = Theme.StyleSheet('''
        QWidget {
            background: transparent;
        }
        QLabel {
            $h1;
            color: $light_highlight;
        }
    ''')

    def __init__(self, label, status, percent, parent=None):
        super(RenderQueueItemWidget, self).__init__(parent)

        self.label = QtWidgets.QLabel(label)
        self.status = Status(status, percent)
        self.menu = KebabMenu()
        self.menu.hide()

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignVCenter)
        self.layout.setContentsMargins(14, 0, 14, 0)
        self.layout.setSpacing(0)

        self.layout.addWidget(self.label)
        self.layout.addStretch()
        self.layout.addWidget(self.status)
        self.layout.addWidget(self.menu)

        self.setFixedHeight(36)
        self.setLayout(self.layout)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setStyleSheet(self.css)

    def set_margin_for_scrollbar_state(self, state):
        if state == 'visible':
            self.layout.setContentsMargins(14, 0, 4, 0)
        else:
            self.layout.setContentsMargins(14, 0, 14, 0)

    def sizeHint(self):
        return QtCore.QSize(0, 48)


class RenderQueue(QtWidgets.QListWidget):

    css = Theme.StyleSheet('''
        QListView {
            $p;
            $border;
            background: $dark;
            color: $light;
        }
        QListView::item {
            margin: 6px;
            $rounded;
        }
        QListView::item:selected {
            $border;
        }
        QListView::item:selected:!active {
            background: $surface;
        }
        QListView::item:selected:active {
            $border;
            background: $surface;
        }
        QListView::item:hover {
            $border;
        }
        QAbstractScrollArea[scroll="hidden"] {
            background: $dark;
            border: 0;
            padding-right: 0px;
        }
        QAbstractScrollArea[scroll="visible"] {
            background: $dark;
            border: 0;
            padding-right: 0px;
        }
        QScrollBar:vertical {
            background: $dark;
            width: 10px;
            margin: 0;
            padding-top: 10px;
            padding-bottom: 10px;
            padding-left: 1px;
            padding-right: 4px;
        }

        QScrollBar::handle:vertical {
            background: $surface_highlight;
        }

        QScrollBar::handle:vertical:hover {
            background: $on_surface;
        }

        QScrollBar::add-line:vertical {
            background: transparent;
            width: 1px;
            left: 4px;
            top: 20px;
            bottom: 20px;
            subcontrol-origin: paddding;
            subcontrol-position: top;
        }

        QScrollBar::sub-line:vertical {
            background: transparent;
            width: 1px;
            left: 4px;
            top: 20px;
            bottom: 20px;
            subcontrol-origin: padding;
            subcontrol-position: bottom;
        }

        QScrollBar::top-arrow:vertical, QScrollBar::bottom-arrow:vertical {
            background: transparent;
        }

        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: transparent;
        }
    ''')

    def __init__(self, parent=None):
        super(RenderQueue, self).__init__(parent)
        self.items = WeakValueDictionary()

        self.setSizeAdjustPolicy(self.AdjustToContents)
        self.setStyleSheet(self.css)
        self.verticalScrollBar().setStyle(QtWidgets.QCommonStyle())
        self.installEventFilter(self)

    def eventFilter(self, source, event):
        if source == self.verticalScrollBar():
            cur_value = self.property('scroll')
            if self.verticalScrollBar().isVisible():
                self.setProperty('scroll', 'visible')
            else:
                self.setProperty('scroll', 'hidden')
            if cur_value != self.property('scroll'):
                for item in self.items.values():
                    item.widget.set_margin_for_scrollbar_state(self.property('scroll'))
                self.setStyleSheet(self.css)
        return super(RenderQueue, self).eventFilter(source, event)

    def get_selected_item(self):
        items = self.selectedItems()
        if items:
            return items[0]

    def get_selected_label(self):
        items = self.selectedItems()
        if items:
            return items[0].label

    def get_item(self, label):
        item = self.items.get(label)
        if not item:
            raise AttributeError('Could not find item for label "%s"' % label)
        return item

    def add_item(self, label, status=const.Queued, percent=0):
        item = QtWidgets.QListWidgetItem()
        item.label = label
        item.widget = RenderQueueItemWidget(label, status, percent)
        item.setSizeHint(item.widget.sizeHint())
        self.items[label] = item
        self.addItem(item)
        self.setItemWidget(item, item.widget)
        return item

    def update_item(self, label, status, percent):
        item = self.get_item(label)
        item.widget.status.set(status, percent)

    def remove_item(self, label):
        item = self.items.get(label)
        if item:
            self.takeItem(self.row(item))

    def add_item_action(self, label, action_label, action_callback, action_icon=None):
        item = self.get_item(label)
        item.widget.menu.addAction(action_label, action_callback, action_icon)
        item.widget.menu.show()

    def clear_item_actions(self, label):
        item = self.get_item(label)
        item.widget.menu.clear()
        item.widget.menu.hide()


class Label(QtWidgets.QLabel):

    css = Theme.StyleSheet('''
        QLabel {
            $p;
            color: $light_highlight;
        }
        QLabel:disabled {
            color: $on_surface_highlight;
        }
    ''')

    def __init__(self, text, parent=None):
        super(Label, self).__init__(text, parent)

        self.setStyleSheet(self.css)


class Options(QtWidgets.QWidget):

    css = Theme.StyleSheet('''
        QWidget {
            background: $surface;
        }
    ''')

    def __init__(self, parent=None):
        super(Options, self).__init__(parent)

        self.module = ComboBox()
        self.module.addItems(['PNG', 'Prores 422', 'Prores 444'])

        self.mp4 = CheckBox()
        self.mp4_quality = ComboBox()
        self.mp4_quality.addItems(
            ['High Quality', 'Medium Quality', 'Low Quality']
        )
        self.mp4_quality.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum,
        )
        self.mp4.stateChanged.connect(self.mp4_quality.setEnabled)
        self.mp4_layout = QtWidgets.QHBoxLayout()
        self.mp4_layout.setSpacing(12)
        self.mp4_layout.setStretch(1, 1)
        self.mp4_layout.addWidget(self.mp4)
        self.mp4_layout.addWidget(self.mp4_quality)

        self.gif = CheckBox()
        self.gif_quality = ComboBox()
        self.gif_quality.addItems(
            ['High Quality', 'Medium Quality', 'Low Quality']
        )
        self.gif_quality.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum,
        )
        self.gif.stateChanged.connect(self.gif_quality.setEnabled)
        self.gif_layout = QtWidgets.QHBoxLayout()
        self.gif_layout.setSpacing(12)
        self.gif_layout.setStretch(1, 1)
        self.gif_layout.addWidget(self.gif)
        self.gif_layout.addWidget(self.gif_quality)

        self.sg = CheckBox()
        self.sg_comment = LineEdit('Comment...')
        self.sg.stateChanged.connect(self.sg_comment.setEnabled)
        self.sg_layout = QtWidgets.QHBoxLayout()
        self.sg_layout.setSpacing(12)
        self.sg_layout.setStretch(1, 1)
        self.sg_layout.addWidget(self.sg)
        self.sg_layout.addWidget(self.sg_comment)

        self.layout = QtWidgets.QFormLayout()
        self.layout.setContentsMargins(20, 4, 20, 4)
        self.layout.setVerticalSpacing(12)
        self.layout.setHorizontalSpacing(20)
        self.layout.addRow(Label('Output Module'), self.module)
        self.layout.addRow(Label('Output MP4'), self.mp4_layout)
        self.layout.addRow(Label('Output GIF'), self.gif_layout)
        self.layout.addRow(Label('Upload to ShotGrid'), self.sg_layout)
        self.setLayout(self.layout)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setStyleSheet(self.css)

    def get(self):
        return {
            'module': self.module.currentText(),
            'mp4': self.mp4.isChecked(),
            'mp4_quality': self.mp4_quality.currentText(),
            'gif': self.gif.isChecked(),
            'gif_quality': self.gif_quality.currentText(),
            'sg': self.sg.isChecked(),
            'sg_comment': self.sg_comment.text(),
        }

    def set(self, **options):
        for k, v in options.items():
            control = getattr(self, k, None)
            if not control:
                raise AttributeError('Control "%s" not found.' % k)
            if isinstance(control, ComboBox):
                control.setCurrentText(v)
            elif isinstance(control, LineEdit):
                control.setText(v)
            elif isinstance(control, CheckBox):
                control.setChecked(v)
            else:
                raise AttributeError(
                    'Could not set "%s" to %r. Control type %s not recognized.'
                    % (k, v, type(control))
                )


class BigButton(QtWidgets.QWidget):

    css = Theme.StyleSheet('''
        QPushButton {
            $h1;
            $rounded;
            background: $on_surface;
            border: 0;
            color: $light;
        }
        QPushButton:focus {
            $border_highlight;
        }
        QPushButton:hover {
            background: $on_surface_highlight;
        }
        QPushButton:pressed {
            $border;
            background: $dark;
        }
        QLabel {
            background: transparent;
        }
    ''')

    clicked = QtCore.Signal()

    def __init__(self, text, parent=None):
        super(BigButton, self).__init__(parent)

        expanding = (
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )

        self.text = text
        self.button = QtWidgets.QPushButton(text)
        self.button.setSizePolicy(*expanding)
        self.button.clicked.connect(self.clicked)
        self.label = QtWidgets.QLabel()
        self.label.setSizePolicy(*expanding)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.hide()

        self.movie_queue = []
        self.movie = QtGui.QMovie()
        self.movie.frameChanged.connect(self.frame_changed)
        self.label.setMovie(self.movie)

        self.anim = None

        self.layout = QtWidgets.QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.button, 0, 0)
        self.layout.addWidget(self.label, 0, 0)
        self.setLayout(self.layout)

        self.setFixedHeight(36)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum,
        )
        self.setStyleSheet(self.css)

    def set_text(self, text):
        self.text = text
        self.button.set_text(text)

    def set_movie(self, movie):
        if self.movie.state() is self.movie.Running:
            self.movie.stop()

        self.movie_queue.clear()
        self.movie.setFileName(movie)

    def add_movie_to_queue(self, movie):
        self.movie_queue.insert(0, movie)

    def frame_changed(self, frame):
        if not self.movie_queue or frame < self.movie.frameCount() - 1:
            return

        # Load next movie in queue
        self.movie.stop()
        self.movie.setFileName(self.movie_queue.pop())
        self.movie.start()

    def enable_movie(self, enabled):
        if enabled:
            self.label.show()
            self.movie.start()
            self.button.setEnabled(False)
            self.button.setText('')
        else:
            self.label.hide()
            self.movie.stop()
            self.button.setEnabled(True)
            self.button.setText(self.text)

    def set_height(self, height):
        self.anim = ValueAnimation(self)
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.anim.setStartValue(self.height())
        self.anim.setEndValue(height)
        self.anim.value_changed.connect(self.setFixedHeight)
        self.anim.start()


class Footer(QtWidgets.QWidget):

    css = Theme.StyleSheet('''
        background: $surface;
    ''')

    def __init__(self, parent=None):
        super(Footer, self).__init__(parent)

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(self.layout)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setStyleSheet(self.css)


class Toast(QtWidgets.QWidget):

    css = Theme.StyleSheet('''
        QWidget[status="info"]{
            background: $uploading;
        }
        QWidget[status="error"]{
            background: $failed;
        }
        QWidget[status="warning"]{
            background: $rendering;
        }
        QLabel {
            $h1;
            color: $on_color;
            background: transparent;
        }
    ''')

    def __init__(self, status, icon, message, duration, parent=None):
        super(Toast, self).__init__(parent=parent)

        self.message = QtWidgets.QLabel(message)
        self.icon = QtWidgets.QLabel()
        self.icon.setFixedSize(20, 20)
        self.icon.setPixmap(QtGui.QPixmap(icon))
        self.duration = duration
        self.status = status
        self._anim = None
        self._open = False
        self._timer = None

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignVCenter)
        self.layout.setContentsMargins(20, 0, 20, 0)
        self.layout.addWidget(self.icon, stretch=0)
        self.layout.addWidget(self.message, stretch=1)
        self.setLayout(self.layout)

        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )
        self.setProperty('status', self.status)
        self.setStyleSheet(self.css)
        self.setGeometry(QtCore.QRect(0, 0, 9999, 1))
        self.hide()

    def show(self, status=None, icon=None, message=None, duration=None):
        if status:
            self.status = status
            self.setProperty('status', status)
            self.setStyleSheet(self.css)
        if icon:
            self.icon.setPixmap(QtGui.QPixmap(icon))
        if message:
            self.message.setText(message)
        if duration:
            self.duration = duration
        if self._timer and self._timer.isActive():
            self._timer.stop()

        super(Toast, self).show()

        if not self._open:
            self._anim = QtCore.QPropertyAnimation(self, b'geometry', self)
            self._anim.setDuration(200)
            self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
            self._anim.setStartValue(QtCore.QRect(0, 0, 9999, 1))
            self._anim.setEndValue(QtCore.QRect(0, 0, 9999, 46))
            self._anim.start()

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(self.duration)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.expire)
        self._timer.start()
        self._open = True

    def expire(self):
        self._open = False
        self._anim = QtCore.QPropertyAnimation(self, b'geometry', self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.InCubic)
        self._anim.setStartValue(QtCore.QRect(0, 0, 9999, 46))
        self._anim.setEndValue(QtCore.QRect(0, 0, 9999, 1))
        self._anim.finished.connect(self.hide)
        self._anim.start()

        self._timer = None

    def sizeHint(self):
        return QtCore.QSize(9999, 46)


class Window(QtWidgets.QWidget):

    css = Theme.StyleSheet('''
        * {
            outline: none;
        }
        QWidget {
            background: $surface;
        }
    ''')

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.queue = RenderQueue()
        self.queue_button = Tool(resources.get_path('arrow_download.png'))
        self.queue_header = SectionHeader('QUEUE', self.queue_button)
        self.toast = Toast('info', resources.get_path('info.png'), '', 3000)

        self.options = Options()
        self.options.set(mp4=True, gif=True, sg=True)
        self.options_header = SectionHeader('OPTIONS')
        self.options_placeholder = BigButton('RENDER')
        self.options_footer = Footer()
        self.options_footer.layout.addWidget(self.options_placeholder)

        self.render = BigButton('RENDER')
        self.footer = Footer()
        self.footer.layout.addWidget(self.render)

        self.top_stack = QtWidgets.QGridLayout()
        self.top_stack.setContentsMargins(0, 0, 0, 0)
        self.top_stack.addWidget(self.queue_header)
        self.top_stack.addWidget(self.toast, 0, 0, 1, 1, QtCore.Qt.AlignTop)

        self.bot_stack = QtWidgets.QGridLayout()
        self.bot_stack.setContentsMargins(0, 0, 0, 0)
        self.bot_stack.addWidget(self.options_header, 0, 0)
        self.bot_stack.addWidget(self.options, 1, 0)
        self.bot_stack.addWidget(self.options_footer, 2, 0)
        self.bot_stack.addWidget(self.footer, 0, 0, 3, 1, QtCore.Qt.AlignBottom)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addLayout(self.top_stack)
        self.layout.addWidget(self.queue)
        self.layout.addLayout(self.bot_stack)


        self.setLayout(self.layout)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setStyleSheet(self.css)
        self.setWindowTitle('Render and Review')
        self.setWindowIcon(QtGui.QIcon(resources.get_path('icon_dark.png')))
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.resize(360, 540)

    def show_error(self, message, duration=3000):
        self.toast.show(
            status='error',
            icon=resources.get_path('error.png'),
            message=message,
            duration=duration,
        )

    def show_info(self, message, duration=3000):
        self.toast.show(
            status='info',
            icon=resources.get_path('info.png'),
            message=message,
            duration=duration,
        )

    def show_warning(self, message, duration=3000):
        self.toast.show(
            status='warning',
            icon=resources.get_path('warning.png'),
            message=message,
            duration=duration,
        )


def DEBUG(msg, *args):
    try:
        import sgtk
        sgtk.platform.current_engine().log_debug(msg, *args)
    except:
        if args:
            msg = msg % args
        print(msg)
