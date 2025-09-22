import textwrap
from multiprocessing import cpu_count
from string import Template
from weakref import WeakValueDictionary

from . import const, resources
from .vendor.qtpy import QtCore, QtGui, QtWidgets


def lerp(a, b, t):
    """Linearly interpolate between two values."""

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
        "light_highlight": "#DDDDDD",
        "light": "#AFAFAF",
        "dark": "#1A1A1A",
        "on_surface_highlight": "#393939",
        "on_surface": "#303030",
        "surface_highlight": "#292929",
        "surface": "#202020",
        "on_color": "#F2F2F2",
        "yellow": "#F2C94C",
        "red": "#EB5757",
        "purple": "#9B51E0",
        "blue": "#2D9CDB",
        "green": "#219653",
    }
    colors = {key: QtGui.QColor(value) for key, value in color_codes.items()}
    status_color_codes = {
        # Steps
        const.Queued: color_codes["on_surface"],
        const.Rendering: color_codes["yellow"],
        const.Encoding: color_codes["red"],
        const.Moving: color_codes["purple"],
        const.Copying: color_codes["purple"],
        const.Uploading: color_codes["blue"],
        const.Publishing: color_codes["blue"],
        const.Cleaning: color_codes["blue"],
        const.Done: color_codes["green"],
        # Statuses
        const.Waiting: color_codes["on_surface"],
        const.Running: color_codes["yellow"],
        const.Cancelled: color_codes["yellow"],
        const.Revoked: color_codes["purple"],
        const.Failed: color_codes["red"],
        const.Success: color_codes["green"],
    }
    status_colors = {
        key: QtGui.QColor(value) for key, value in status_color_codes.items()
    }
    icons = resources.get_icon_variables()
    variables = {
        "h1": ('font-family: "Roboto";\nfont-size: 14px;\n'),
        "p": ('font-family: "Roboto";\nfont-size: 12px;\n'),
        "border": "border: 1px solid $on_surface",
        "border_highlight": "border: 1px solid $on_surface_highlight",
        "border_up_button": "border-width: 1px 1px 0px 0px",
        "border_dn_button": "border-width: 0px 0px 1px 1px",
        "rounded": "border-radius: 3px",
        "border_thick": "border: 2px solid $on_surface",
        "outline": "outline: 1px solid $on_surface_highlight",
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
    css = Theme.StyleSheet(
        """
        QWidget {
            background: $surface;
        }
        QLabel {
            $h1;
            color: $light;
        }
        QLabel[status="default"]{
            $h1;
            color: $queued;
        }
        QLabel[status="queued"]{
            $h1;
            color: $queued;
        }
        QLabel[status="rendering"]{
            $h1;
            color: $rendering;
        }
        QLabel[status="encoding"]{
            $h1;
            color: $encoding;
        }
        QLabel[status="copying"]{
            $h1;
            color: $copying;
        }
        QLabel[status="moving"]{
            $h1;
            color: $moving;
        }
        QLabel[status="uploading"]{
            $h1;
            color: $uploading;
        }
        QLabel[status="cleaning"]{
            $h1;
            color: $cleaning;
        }
        QLabel[status="copying"]{
            $h1;
            color: $copying;
        }
        QLabel[status="done"]{
            $h1;
            font-weight: bold;
            color: $done;
        }
        QLabel[status="failed"]{
            $h1;
            font-weight: bold;
            color: $failed;
        }
        QLabel[status="success"]{
            $h1;
            font-weight: bold;
            color: $success;
        }
        QLabel[status="cancelled"]{
            $h1;
            font-weight: bold;
            color: $cancelled;
        }
    """
    )

    def __init__(self, label, parent=None):
        super(SectionHeader, self).__init__(parent)

        self.left = QtWidgets.QHBoxLayout()
        self.left.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.left.setContentsMargins(0, 0, 0, 0)
        self.left.setSpacing(4)
        self.center = QtWidgets.QHBoxLayout()
        self.center.setAlignment(QtCore.Qt.AlignCenter)
        self.center.setContentsMargins(0, 0, 0, 0)
        self.center.setSpacing(4)
        self.right = QtWidgets.QHBoxLayout()
        self.right.setDirection(QtWidgets.QBoxLayout.RightToLeft)
        self.right.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.right.setContentsMargins(0, 0, 0, 0)
        self.right.setSpacing(4)

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignVCenter)
        self.layout.setContentsMargins(20, 0, 20, 0)
        self.layout.setSpacing(20)
        self.layout.addLayout(self.left)
        self.layout.addLayout(self.center)
        self.layout.addLayout(self.right)
        self.layout.setStretch(1, 1)

        self.label = QtWidgets.QLabel(label)
        self.left.addWidget(self.label)

        self.setFixedHeight(46)
        self.setLayout(self.layout)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setStyleSheet(self.css)

    def set_status(self, status):
        self.setProperty("status", status)
        self.label.setProperty("status", status)
        self.setStyleSheet(self.css)

    def set_label(self, text):
        self.label.setText(text)

    def transition_label(self, text):
        if text == self.label.text():
            return
        self.start_fade()
        anim = self.label_fade_out()
        anim.finished.connect(lambda: self.label.setText(text))
        anim.finished.connect(self.label_fade_in)

    def start_fade(self):
        self._anim_effect = QtWidgets.QGraphicsOpacityEffect(self.label)
        self._anim_effect.setOpacity(1.0)
        self.label.setGraphicsEffect(self._anim_effect)

    def finish_fade(self):
        self.label.setGraphicsEffect(None)

    def label_fade_out(self):
        self.start_fade()
        self._anim = QtCore.QPropertyAnimation(self._anim_effect, b"opacity")
        self._anim.setDuration(100)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()
        return self._anim

    def label_fade_in(self):
        self._anim = QtCore.QPropertyAnimation(self._anim_effect, b"opacity")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.finished.connect(self.finish_fade)
        self._anim.start()
        return self._anim


class Tool(QtWidgets.QToolButton):
    css = Theme.StyleSheet(
        """
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
    """
    )

    def __init__(self, icon, parent=None):
        super(Tool, self).__init__(parent)

        self.setIcon(QtGui.QIcon(icon))
        self.setIconSize(QtCore.QSize(20, 20))
        self.setStyleSheet(self.css)

    def set_icon(self, icon):
        self.setIcon(QtGui.QIcon(icon))
        self.setIconSize(QtCore.QSize(20, 20))


class CheckBox(QtWidgets.QCheckBox):
    css = Theme.StyleSheet(
        """
        QCheckBox {
            $p;
            border: 0;
            padding: 2px;
            background: transparent;
            color: $light;
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
    """
    )

    def __init__(self, text=None, parent=None):
        super(CheckBox, self).__init__(text, parent)

        if not text:
            self.setMinimumSize(24, 24)
            self.setFixedSize(24, 24)
        else:
            self.setFixedHeight(24)

        self.setStyleSheet(self.css)


class ComboBox(QtWidgets.QComboBox):
    css = Theme.StyleSheet(
        """
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
    """
    )

    def __init__(self, parent=None):
        super(ComboBox, self).__init__(parent)

        self.setView(QtWidgets.QListView())
        self.setFixedHeight(24)
        self.setStyleSheet(self.css)


class LineEdit(QtWidgets.QLineEdit):
    css = Theme.StyleSheet(
        """
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
    """
    )

    def __init__(self, placeholder=None, parent=None):
        super(LineEdit, self).__init__(parent)

        if placeholder:
            self.setPlaceholderText(placeholder)

        self.textChanged.connect(lambda: self.style().polish(self))
        self.setFixedHeight(24)
        self.setStyleSheet(self.css)


class SpinBox(QtWidgets.QSpinBox):
    css = Theme.StyleSheet(
        """
        QSpinBox {
            $p;
            $border;
            $rounded;
            padding-left: 10px;
            padding-right: 20px;
            background: $dark;
            color: $light;
        }
        QSpinBox:focus {
            $border_highlight;
        }
        QSpinBox:disabled {
            border: 0;
            color: $on_surface_highlight;
        }
        QSpinBox:hover {
            $border_highlight;
        }
        QSpinBox::up-button {
            subcontrol-origin: border;
            subcontrol-position: top right;
            top: 1px;
            right: 1px;
            width: 20px;
            background: transparent;
            border-top-right-radius: 3px;
            $border_up_button;
            border-color: $on_surface;
        }
        QSpinBox::up-button:hover {
            background: $surface_highlight;
            border-top-right-radius: 3px;
            $border_up_button;
            border-color: $on_surface_highlight;
        }
        QSpinBox::up-button:pressed {
            background-color: $dark;
            border-top-right-radius: 3px;
            $border_up_button;
            border-color: $on_surface;
        }
        QSpinBox::up-arrow {
            image: url("$caret_up");
            width: 9px;
            height: 9px;
        }
        QSpinBox::up-arrow:disabled, QSpinBox::up-arrow:off {
           image: url("$caret_up_disabled");
        }

        QSpinBox::down-button {
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            bottom: 1px;
            right: 1px;
            width: 20px;
            background: transparent;
            border-bottom-right-radius: 3px;
            $border_dn_button;
            border-color: $on_surface;
        }
        QSpinBox::down-button:hover {
            background: $surface_highlight;
            border-bottom-right-radius: 3px;
            $border_dn_button;
            border-color: $on_surface_highlight;
        }
        QSpinBox::down-button:pressed {
            background-color: $dark;
            border-bottom-right-radius: 3px;
            $border_dn_button;
            border-color: $on_surface;
        }
        QSpinBox::down-arrow {
            image: url("$caret_down");
            width: 9px;
            height: 9px;
        }
        QSpinBox::down-arrow:disabled, QSpinBox::down-arrow:off {
           image: url("$caret_down_disabled");
        }

    """
    )

    def __init__(self, placeholder=None, parent=None):
        super(SpinBox, self).__init__(parent)

        self.setFixedHeight(24)
        self.setStyleSheet(self.css)


class Status(QtWidgets.QWidget):
    css = Theme.StyleSheet(
        """
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
        QWidget[status="moving"]{
            background: $moving;
        }
        QWidget[status="uploading"]{
            background: $uploading;
        }
        QWidget[status="publishing"]{
            background: $publishing;
        }
        QWidget[status="done"]{
            background: $done;
        }
        QWidget[status="failed"]{
            background: $failed;
        }
        QWidget[status="cleaning"]{
            background: $cleaning;
        }
        QWidget[status="success"]{
            background: $success;
        }
        QLabel {
            $p;
            color: $on_color;
            background: transparent;
        }
    """
    )

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

        self.setProperty("status", "default")
        self.setFixedHeight(24)
        self.setFixedWidth(100)
        self.setLayout(self.layout)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.set(status, percent)

    def set(self, status, percent):
        self.bar.setProperty("status", status.lower().split()[0])
        self.bar.setFixedWidth(percent)
        self.label.setText(status.title())
        self.setStyleSheet(self.css)


class Menu(QtWidgets.QMenu):
    css = Theme.StyleSheet(
        """
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
    """
    )

    def __init__(self, parent=None):
        super(Menu, self).__init__(parent)
        self.setStyleSheet(self.css)


class KebabMenu(QtWidgets.QPushButton):
    css = Theme.StyleSheet(
        """
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
    """
    )

    def __init__(self, parent=None):
        super(KebabMenu, self).__init__(parent)
        self._menu = QtWidgets.QMenu(parent=self)
        self._menu.aboutToHide.connect(self.before_hide_menu)
        self._anim = None

        self.clicked.connect(self.show_menu)

        self.setStyleSheet(self.css)
        self.setFixedSize(QtCore.QSize(20, 24))
        self.setEnabled(False)
        self.setProperty("menu_visible", False)

    def clear(self):
        self._menu.clear()
        self.setEnabled(False)

    def addAction(self, label, callback, icon=None):
        action = self._menu.addAction(label, callback)
        if icon:
            action.setIcon(QtGui.QIcon(icon))
        self.setEnabled(True)

    def show_menu(self):
        self.setProperty("menu_visible", True)
        self.setStyleSheet(self.css)
        self.before_show_menu()

    def before_show_menu(self):
        menu_size = self._menu.sizeHint()
        self._anim = QtCore.QPropertyAnimation(self._menu, b"size", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.setStartValue(QtCore.QSize(menu_size.width(), 0))
        self._anim.setEndValue(menu_size)
        self._anim.start(self._anim.DeleteWhenStopped)
        self._menu.move(self.mapToGlobal(QtCore.QPoint(0, self.height() - 1)))
        QtCore.QTimer.singleShot(20, self._menu.show)

    def before_hide_menu(self):
        self.setProperty("menu_visible", False)
        self.setStyleSheet(self.css)


class RenderQueueItemWidget(QtWidgets.QWidget):
    css = Theme.StyleSheet(
        """
        QWidget {
            background: transparent;
        }
        QLabel {
            $h1;
            color: $light_highlight;
        }
    """
    )

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
        if state == "visible":
            self.layout.setContentsMargins(14, 0, 4, 0)
        else:
            self.layout.setContentsMargins(14, 0, 14, 0)

    def sizeHint(self):
        return QtCore.QSize(0, 48)


class RenderQueue(QtWidgets.QListWidget):
    css = Theme.StyleSheet(
        """
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
    """
    )
    drop = QtCore.Signal(object)
    drag = QtCore.Signal(object)

    def __init__(self, parent=None):
        super(RenderQueue, self).__init__(parent)
        self.items = WeakValueDictionary()

        self.setSizeAdjustPolicy(QtWidgets.QListView.AdjustToContents)
        self.setStyleSheet(self.css)
        self.verticalScrollBar().setStyle(QtWidgets.QCommonStyle())
        self.setAcceptDrops(True)
        self.installEventFilter(self)

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dragEnterEvent(self, event):
        self.drag.emit(event)

    def dropEvent(self, event):
        self.drop.emit(event)

    def eventFilter(self, source, event):
        if source == self.verticalScrollBar():
            cur_value = self.property("scroll")
            if self.verticalScrollBar().isVisible():
                self.setProperty("scroll", "visible")
            else:
                self.setProperty("scroll", "hidden")
            if cur_value != self.property("scroll"):
                for item in self.items.values():
                    item.widget.set_margin_for_scrollbar_state(self.property("scroll"))
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
        item.widget.set_margin_for_scrollbar_state(self.property("scroll"))
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


class LogReport(QtWidgets.QTextEdit):
    css = Theme.StyleSheet(
        """
        QTextEdit {
            $p;
            $border;
            background: $dark;
            color: $light;
            padding-left: 10px;
        }
        QAbstractScrollArea {
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
    """
    )

    def __init__(self, parent=None):
        super(LogReport, self).__init__(parent=parent)
        self.setStyleSheet(self.css)
        self.verticalScrollBar().setStyle(QtWidgets.QCommonStyle())
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)


class Label(QtWidgets.QLabel):
    css = Theme.StyleSheet(
        """
        QLabel {
            $p;
            color: $light_highlight;
        }
        QLabel:disabled {
            color: $on_surface_highlight;
        }
    """
    )

    def __init__(self, text, parent=None):
        super(Label, self).__init__(text, parent)

        self.setStyleSheet(self.css)


class Options(QtWidgets.QWidget):
    css = Theme.StyleSheet(
        """
        QWidget {
            background: $surface;
        }
    """
    )

    def __init__(self, parent=None):
        super(Options, self).__init__(parent)

        self.module = ComboBox()
        self.module.addItems(["PNG", "Prores 422", "Prores 444"])
        self.module.setMinimumWidth(140)
        self.settings = ComboBox()
        self.settings.addItems(["Best Settings"])
        self.settings.setMinimumWidth(100)
        self.keep_original = CheckBox("Keep?")
        self.keep_original.setToolTip(
            "Uncheck to delete the main render after compressing MP4 and GIFs.\n"
            "Useful if you're rendering only for previewing..."
        )
        self.module_layout = QtWidgets.QHBoxLayout()
        self.module_layout.setSpacing(12)
        self.module_layout.setStretch(0, 1)
        self.module_layout.addWidget(self.module)
        self.module_layout.addWidget(self.keep_original)

        self.mp4 = CheckBox()
        self.mp4_quality = ComboBox()
        self.mp4_quality.addItems(const.DefaultOptions["Quality"])
        self.mp4_quality.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum,
        )
        self.mp4_quality.setToolTip(
            "High Quality: -crf 18 -preset veryslow\n"
            "Medium Quality: -crf 22 -preset medium\n"
            "Low Quality: -crf 26 -preset veryfast\n"
            "Min Quality: -crf 30 -preset veryfast"
        )
        self.mp4_resolution = ComboBox()
        self.mp4_resolution.addItems(const.DefaultOptions["Resolution"])
        self.mp4_resolution.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum,
        )
        self.mp4.stateChanged.connect(self.mp4_quality.setEnabled)
        self.mp4.stateChanged.connect(self.mp4_resolution.setEnabled)
        self.mp4_layout = QtWidgets.QHBoxLayout()
        self.mp4_layout.setSpacing(12)
        self.mp4_layout.setStretch(1, 1)
        self.mp4_layout.addWidget(self.mp4)
        self.mp4_layout.addWidget(self.mp4_quality)
        self.mp4_layout.addWidget(self.mp4_resolution)

        self.gif = CheckBox()
        self.gif_quality = ComboBox()
        self.gif_quality.addItems(const.DefaultOptions["Quality"])
        self.gif_quality.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum,
        )
        self.gif_quality.setToolTip(
            "High Quality: 256 colors\n"
            "Medium Quality: 128 colors\n"
            "Low Quality: 64 colors\n"
            "Min Quality: 32 colors"
        )
        self.gif_resolution = ComboBox()
        self.gif_resolution.addItems(const.DefaultOptions["Resolution"])
        self.gif_resolution.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum,
        )
        self.gif.stateChanged.connect(self.gif_quality.setEnabled)
        self.gif.stateChanged.connect(self.gif_resolution.setEnabled)
        self.gif_layout = QtWidgets.QHBoxLayout()
        self.gif_layout.setSpacing(12)
        self.gif_layout.setStretch(1, 1)
        self.gif_layout.addWidget(self.gif)
        self.gif_layout.addWidget(self.gif_quality)
        self.gif_layout.addWidget(self.gif_resolution)

        self.update_keep_original = lambda _: (
            self.keep_original.setVisible(self.mp4.isChecked() or self.gif.isChecked()),
        )
        self.mp4.stateChanged.connect(self.update_keep_original)
        self.gif.stateChanged.connect(self.update_keep_original)

        self.sg = CheckBox()
        self.sg_comment = LineEdit("Comment...")
        self.sg.stateChanged.connect(self.sg_comment.setEnabled)
        self.sg_layout = QtWidgets.QHBoxLayout()
        self.sg_layout.setSpacing(12)
        self.sg_layout.setStretch(1, 1)
        self.sg_layout.addWidget(self.sg)
        self.sg_layout.addWidget(self.sg_comment)

        self.bg = CheckBox()
        self.bg_threads = SpinBox()
        self.bg.stateChanged.connect(self.bg_threads.setEnabled)
        self.bg_threads.setEnabled(self.bg.isChecked())
        self.bg_threads.setMinimum(1)
        self.bg_threads.setMaximum(cpu_count())
        self.bg_threads.setValue(4)
        self.bg_threads.setSuffix(" Threads")
        self.bg_layout = QtWidgets.QHBoxLayout()
        self.bg_layout.setSpacing(12)
        self.bg_layout.setStretch(1, 1)
        self.bg_layout.addWidget(self.bg)
        self.bg_layout.addWidget(self.bg_threads)

        async_tip = (
            "New render method that will not freeze AE while rendering.\n"
            "AE render queue progress bar will work as well.\n"
            "Please try this feature out."
        )
        self.async_render = CheckBox()
        self.async_render.setToolTip(async_tip)
        self.async_note = Label("Experimental!")
        self.async_note.setToolTip(async_tip)
        self.async_layout = QtWidgets.QHBoxLayout()
        self.async_layout.setSpacing(12)
        self.async_layout.setStretch(1, 1)
        self.async_layout.addWidget(self.async_render)
        self.async_layout.addWidget(self.async_note)

        self.layout = QtWidgets.QFormLayout()
        self.layout.setContentsMargins(20, 4, 20, 4)
        self.layout.setVerticalSpacing(12)
        self.layout.setHorizontalSpacing(20)

        self.layout.addRow(Label("Render Settings"), self.settings)
        self.layout.addRow(Label("Output Module"), self.module_layout)
        self.layout.addRow(Label("Output MP4"), self.mp4_layout)
        self.layout.addRow(Label("Output GIF"), self.gif_layout)
        self.layout.addRow(Label("Upload to ShotGrid"), self.sg_layout)
        # Comment out next line to disable Async Rendering option.
        self.layout.addRow(Label("Async Render"), self.async_layout)
        # Comment out next line to disable BG Rendering.
        # self.layout.addRow(Label("BG Render"), self.bg_layout)
        self.setLayout(self.layout)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setStyleSheet(self.css)

    def get(self):
        return {
            "settings": self.settings.currentText(),
            "module": self.module.currentText(),
            "keep_original": (
                not self.keep_original.isVisible() or self.keep_original.isChecked()
            ),
            "mp4": self.mp4.isChecked(),
            "mp4_quality": self.mp4_quality.currentText(),
            "mp4_resolution": self.mp4_resolution.currentText(),
            "gif": self.gif.isChecked(),
            "gif_quality": self.gif_quality.currentText(),
            "gif_resolution": self.gif_resolution.currentText(),
            "sg": self.sg.isChecked(),
            "sg_comment": self.sg_comment.text(),
            "bg": self.bg.isChecked(),
            "bg_threads": self.bg_threads.value(),
            "async_render": self.async_render.isChecked(),
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
            elif isinstance(control, SpinBox):
                control.setValue(v)
            else:
                raise AttributeError(
                    'Could not set "%s" to %r. Control type %s not recognized.'
                    % (k, v, type(control))
                )

    def set_height(self, height):
        self._anim = ValueAnimation(self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.setStartValue(self.height())
        self._anim.setEndValue(height)
        self._anim.value_changed.connect(self.setFixedHeight)
        self._anim.start()


class Movie(QtWidgets.QLabel):
    """Generic Movie class, supports playback of gifs and other media."""

    def __init__(self, file_path=None, parent=None):
        super(Movie, self).__init__(parent=parent)
        self.movie_queue = []
        self.movie = QtGui.QMovie()
        self.movie.frameChanged.connect(self.frame_changed)
        self.setMovie(self.movie)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )
        if file_path:
            self.movie.setFileName(file_path)

    def start(self):
        self.movie.start()

    def stop(self):
        self.movie.stop()

    def set(self, file_path):
        """Sets the current movie and clears the movie queue."""

        if self.movie.state() is QtGui.QMovie.Running:
            self.movie.stop()

        self.movie_queue.clear()
        self.movie.setFileName(file_path)
        self.movie.start()

    def queue(self, file_path):
        """Queues a movie to play once the current movie is finished."""

        self.movie_queue.insert(0, file_path)

    def frame_changed(self, frame):
        if not self.movie_queue or frame < self.movie.frameCount() - 1:
            return

        # Load next movie in queue
        self.movie.stop()
        self.movie.setFileName(self.movie_queue.pop())
        self.movie.start()


class Gif(Movie):
    """Alias for Movie to make code intentions clear."""


class StatusIndicator(Movie):
    """Movie with predefined Gifs for different statuses."""

    def __init__(self, parent=None):
        super(StatusIndicator, self).__init__(parent=parent)
        self.setFixedSize(QtCore.QSize(20, 20))

    def set_status(self, status):
        if status == const.Waiting:
            self.stop()
        elif status == const.Running:
            self.set(resources.get_path("Running_20.gif"))
            self.start()
        elif status == const.Failed:
            self.queue(resources.get_path("Failed_20.gif"))
            self.start()
        elif status == const.Success:
            self.queue(resources.get_path("Success_20.gif"))
            self.start()
        elif status == const.Cancelled:
            self.queue(resources.get_path("Cancelled_20.gif"))
            self.start()
        else:
            raise ValueError("No status animation available for: %s" % status)


class BigButton(QtWidgets.QPushButton):
    css = Theme.StyleSheet(
        """
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
    """
    )

    clicked = QtCore.Signal()

    def __init__(self, text, parent=None):
        super(BigButton, self).__init__(text, parent)

        self.setFixedHeight(36)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum,
        )
        self.setStyleSheet(self.css)


class Footer(QtWidgets.QWidget):
    css = Theme.StyleSheet(
        """
        background: $surface;
    """
    )

    def __init__(self, parent=None):
        super(Footer, self).__init__(parent)

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(self.layout)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setStyleSheet(self.css)
        self._anim = None

    def set_height(self, height):
        self._anim = ValueAnimation(self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.setStartValue(self.height())
        self._anim.setEndValue(height)
        self._anim.value_changed.connect(self.setFixedHeight)
        self._anim.start()


class Toast(QtWidgets.QWidget):
    css = Theme.StyleSheet(
        """
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
    """
    )

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
        self.setProperty("status", self.status)
        self.setStyleSheet(self.css)
        self.setGeometry(QtCore.QRect(0, 0, 9999, 1))
        self.hide()

    def show(self, status=None, icon=None, message=None, duration=None):
        if status:
            self.status = status
            self.setProperty("status", status)
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
            self._anim = QtCore.QPropertyAnimation(self, b"geometry", self)
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
        self._anim = QtCore.QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.InCubic)
        self._anim.setStartValue(QtCore.QRect(0, 0, 9999, 46))
        self._anim.setEndValue(QtCore.QRect(0, 0, 9999, 1))
        self._anim.finished.connect(self.hide)
        self._anim.start()

        self._timer = None

    def sizeHint(self):
        return QtCore.QSize(9999, 46)


class Window(QtWidgets.QDialog):
    css = Theme.StyleSheet(
        """
        * {
            outline: none;
        }
        QWidget {
            background: $surface;
        }
    """
    )

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        # Header
        self.reset_button = Tool(resources.get_path("arrow_counterclockwise.png"))
        self.reset_button.setToolTip("Reset queue.")
        self.reset_button.setVisible(False)
        self.queue_button = Tool(resources.get_path("arrow_download.png"))
        self.queue_button.setToolTip("Add selected comps to queue...")
        self.cancel_button = Tool(resources.get_path("pause.png"))
        self.cancel_button.setToolTip("Cancel!")
        self.cancel_button.setVisible(False)
        self.queue_header = SectionHeader("QUEUE")
        self.queue_header.right.addWidget(self.queue_button)
        self.queue_header.right.addWidget(self.reset_button)
        self.queue_header.right.addWidget(self.cancel_button)

        # Toast - Sliding notification that overlays on top of Header
        self.toast = Toast("info", resources.get_path("info.png"), "", 3000)

        # Body
        self.queue = RenderQueue()
        self.report = LogReport()
        self.report.hide()

        # Tools - Parented to options_header
        self.status_indicator = StatusIndicator()
        self.report_button = Tool(resources.get_path("report.png"))
        self.report_button.setToolTip("View Report")
        self.report_button.setVisible(False)
        self.report_button.clicked.connect(self.toggle_report)
        self.send_button = Tool(resources.get_path("send.png"))
        self.send_button.setToolTip("Send Error Report")
        self.send_button.setVisible(False)

        # Options
        self.options_visible = True
        self.options = Options()
        self.options.setMinimumHeight(0)
        self.options.set(
            mp4=True,
            gif=True,
            sg=True,
            bg=False,
            bg_threads=4,
            async_render=False,
        )
        self.options_header = SectionHeader("OPTIONS")
        self.options_header.right.addWidget(self.status_indicator)
        self.options_header.right.addWidget(self.send_button)
        self.options_header.right.addWidget(self.report_button)

        # Footer
        self.render_button = BigButton("RENDER")
        self.footer = Footer()
        self.footer.setMinimumHeight(0)
        self.footer.layout.addWidget(self.render_button)

        self.top_stack = QtWidgets.QGridLayout()
        self.top_stack.setContentsMargins(0, 0, 0, 0)
        self.top_stack.addWidget(self.queue_header)
        self.top_stack.addWidget(self.toast, 0, 0, 1, 1, QtCore.Qt.AlignTop)

        self.body_stack = QtWidgets.QGridLayout()
        self.body_stack.setContentsMargins(0, 0, 0, 0)
        self.body_stack.addWidget(self.queue, 0, 0)
        self.body_stack.addWidget(self.report, 0, 0)

        self.bot_stack = QtWidgets.QGridLayout()
        self.bot_stack.setContentsMargins(0, 0, 0, 0)
        self.bot_stack.addWidget(self.options_header, 0, 0)
        self.bot_stack.addWidget(self.options, 1, 0)
        self.bot_stack.addWidget(self.footer, 2, 0)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.setStretch(1, 1)
        self.layout.addLayout(self.top_stack)
        self.layout.addLayout(self.body_stack)
        self.layout.addLayout(self.bot_stack)

        self.show_options()
        self.setLayout(self.layout)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setStyleSheet(self.css)
        self.setWindowTitle("Render and Review")
        self.setWindowIcon(QtGui.QIcon(resources.get_path("icon_dark.png")))
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.resize(360, 540)

    def set_status(self, status):
        self.status_indicator.set_status(status)
        self.options_header.set_status(status)
        if status == const.Waiting:
            self.options_header.set_label("OPTIONS")
            self.options.setEnabled(True)
            self.render_button.setEnabled(True)
            self.queue_button.setVisible(True)
            self.reset_button.setVisible(False)
            self.cancel_button.setVisible(False)
            self.status_indicator.setVisible(False)
            self.report_button.setVisible(False)
            self.send_button.setVisible(False)
            self.hide_report()
            self.show_options()
        elif status == const.Running:
            self.options_header.transition_label("RUNNING")
            self.options.setEnabled(False)
            self.render_button.setEnabled(False)
            self.queue_button.setVisible(False)
            self.reset_button.setVisible(False)
            self.cancel_button.setVisible(True)
            self.status_indicator.setVisible(True)
            self.report_button.setVisible(False)
            self.send_button.setVisible(False)
            self.hide_options()
        elif status == const.Cancelled:
            self.options_header.transition_label("CANCELLED")
            self.options.setEnabled(False)
            self.render_button.setEnabled(False)
            self.reset_button.setVisible(True)
            self.cancel_button.setVisible(False)
            self.status_indicator.setVisible(True)
            self.report_button.setVisible(True)
            self.report_button.set_icon(resources.get_path("report.png"))
            self.report_button.setToolTip("View Report")
            self.send_button.setVisible(False)
        elif status == const.Success:
            self.options_header.transition_label("SUCCESS")
            self.options.setEnabled(False)
            self.render_button.setEnabled(False)
            self.reset_button.setVisible(True)
            self.cancel_button.setVisible(False)
            self.status_indicator.setVisible(True)
            self.report_button.setVisible(True)
            self.report_button.set_icon(resources.get_path("report.png"))
            self.report_button.setToolTip("View Report")
            self.send_button.setVisible(False)
        elif status == const.Failed:
            self.options_header.transition_label("FAILED")
            self.options.setEnabled(False)
            self.render_button.setEnabled(False)
            self.reset_button.setVisible(True)
            self.cancel_button.setVisible(False)
            self.status_indicator.setVisible(True)
            self.report_button.setVisible(True)
            self.report_button.set_icon(resources.get_path("error_report.png"))
            self.report_button.setToolTip("View Error Report")
            self.send_button.setVisible(True)

    def toggle_report(self):
        if self.report.isVisible():
            self.hide_report()
        else:
            self.show_report()

    def show_report(self):
        if self.report.isVisible():
            return
        pos = self.queue.pos()
        self._slide_report_anim = QtCore.QPropertyAnimation(self.report, b"pos")
        self._slide_report_anim.setDuration(300)
        self._slide_report_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._slide_report_anim.setStartValue(QtCore.QPoint(self.width(), pos.y()))
        self._slide_report_anim.setEndValue(QtCore.QPoint(0, pos.y()))
        self._slide_report_anim.start()
        self.report.setVisible(True)

    def hide_report(self):
        if self.isVisible() and not self.report.isVisible():
            return
        pos = self.report.pos()
        self._slide_report_anim = QtCore.QPropertyAnimation(self.report, b"pos")
        self._slide_report_anim.setDuration(300)
        self._slide_report_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._slide_report_anim.setStartValue(QtCore.QPoint(0, pos.y()))
        self._slide_report_anim.setEndValue(QtCore.QPoint(self.width(), pos.y()))
        self._slide_report_anim.start()
        self._slide_report_anim.finished.connect(lambda: self.report.setVisible(False))

    def hide_options(self):
        if not self.options_visible:
            return
        start_value = self.geometry()
        end_value = QtCore.QRect(self.geometry())
        end_value.setHeight(
            start_value.height()
            - self.options.sizeHint().height()
            - self.footer.sizeHint().height()
        )
        self._anim = QtCore.QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.setStartValue(start_value)
        self._anim.setEndValue(end_value)
        self._anim.start()
        self.options.set_height(0)
        self.footer.set_height(0)
        self.options_visible = False

    def show_options(self):
        if self.options_visible:
            return
        start_value = self.geometry()
        end_value = QtCore.QRect(self.geometry())
        end_value.setHeight(
            start_value.height()
            + self.options.sizeHint().height()
            + self.footer.sizeHint().height()
        )
        self._anim = QtCore.QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.setStartValue(start_value)
        self._anim.setEndValue(end_value)
        self._anim.start()
        self.options.set_height(self.options.sizeHint().height())
        self.footer.set_height(self.footer.sizeHint().height())
        self.options_visible = True

    def show_error(self, message, duration=3000):
        self.toast.show(
            status="error",
            icon=resources.get_path("error.png"),
            message=message,
            duration=duration,
        )

    def show_info(self, message, duration=3000):
        self.toast.show(
            status="info",
            icon=resources.get_path("info.png"),
            message=message,
            duration=duration,
        )

    def show_warning(self, message, duration=3000):
        self.toast.show(
            status="warning",
            icon=resources.get_path("warning.png"),
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
