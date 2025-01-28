import ctypes
import ctypes.wintypes
import fnmatch
import uuid
from collections import namedtuple

from .vendor.qtpy import QtWidgets

GWL_EXSTYLE = -20
WS_EX_NOPARENTNOTIFY = 0x00000004
WS_EX_NOINHERITLAYOUT = 0x00100000

# Messages
BM_CLICK = 245

# Functions
EnumWindows = ctypes.windll.user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(
    ctypes.c_bool,
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
)
EnumChildWindows = ctypes.windll.user32.EnumChildWindows
EnumChildProc = ctypes.WINFUNCTYPE(
    ctypes.c_bool,
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
)
GetParent = ctypes.windll.user32.GetParent
SetParent = ctypes.windll.user32.SetParent
SetWindowLong = ctypes.windll.user32.SetWindowLongW
GetWindowLong = ctypes.windll.user32.GetWindowLongW
GetWindowText = ctypes.windll.user32.GetWindowTextW
GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
GetWindowClass = ctypes.windll.user32.RealGetWindowClassW
GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
FindWindowEx = ctypes.windll.user32.FindWindowExW
SendMessage = ctypes.windll.user32.SendMessageW


Window = namedtuple("Window", "title cls hwnd pid")
Child = namedtuple("Child", "title cls hwnd parent pid")


def enumerate_windows(callback):
    """Execute a function against all Window's hwnd."""

    return EnumWindows(EnumWindowsProc(callback), 0)


def get_windows():
    """Returns a list of Windows for all Windows.

    A Window has two attributes, title, and hwnd.
    """

    results = []

    def record_hwnds(hwnd, lParam):
        window = Window(
            title=get_window_title(hwnd),
            cls=get_window_class(hwnd),
            hwnd=hwnd,
            pid=get_pid(hwnd),
        )
        results.append(window)
        return True

    enumerate_windows(record_hwnds)
    return results


def get_pid(hwnd):
    """Get a window's pid."""

    pid = ctypes.wintypes.DWORD()
    return GetWindowThreadProcessId(hwnd, ctypes.byref(pid))


def get_window_title(hwnd):
    """Get a window's title."""

    length = GetWindowTextLength(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    GetWindowText(hwnd, buff, length + 1)
    return buff.value


def get_window_class(hwnd):
    """Get a window's class name."""

    length = 1024
    buff = ctypes.create_unicode_buffer(length)
    GetWindowClass(hwnd, buff, length)
    return buff.value


def find_window_by_title(pattern):
    """Get the first Window whose title matches pattern."""

    for window in get_windows():
        if fnmatch.fnmatch(window.title, pattern):
            return window


def find_window_by_hwnd(hwnd):
    """Return a Window including it's title from an hwnd."""

    length = GetWindowTextLength(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    GetWindowText(hwnd, buff, length + 1)
    return Window(buff.value, hwnd)


def enumerate_children(hwnd, callback):
    """Execute a function against all Window children."""

    return EnumChildWindows(hwnd, EnumChildProc(callback), 0)


def get_children(phwnd):
    """Return a list of children of the specified Window."""

    ppid = get_pid(phwnd)
    results = []

    def record_hwnds(hwnd, lParam):
        child = Child(
            title=get_window_title(hwnd),
            cls=get_window_class(hwnd),
            hwnd=hwnd,
            parent=phwnd,
            pid=ppid,
        )
        results.append(child)
        return True

    enumerate_children(phwnd, record_hwnds)
    return results


def find_child(hwnd, title=None, cls=None):
    """Find a child by title and cls."""

    for child in get_children(hwnd):
        if title and child.title != title:
            continue
        if cls and child.cls != cls:
            continue
        return child


def click(hwnd):
    """Send a click message to the specified hwnd."""

    SendMessage(hwnd, BM_CLICK, 0, 0)


def close_popup(window_title, button_title=None, button_cls="Button", pid=None):
    """Attempts to local a popup window and close it!

    Arguments:
        window_title (str): Name of the window to close.
        button_title (str): Name of the child button.
        button_cls (str): Name of the child button class.
    """

    for window in get_windows():
        if pid and window.pid != pid:
            continue

        if window.title == window_title:
            button = find_child(window.hwnd, button_title, button_cls)
            click(button.hwnd)
            return True

    return False


def close_popups(window_title, button_title=None, button_cls="Button", pid=None):
    """Attempts to local a popup window and close it!

    Arguments:
        window_title (str): Name of the window to close.
        button_title (str): Name of the child button.
        button_cls (str): Name of the child button class.
    """

    for window in get_windows():
        if pid and window.pid != pid:
            continue

        if window.title == window_title:
            button = find_child(window.hwnd, button_title, button_cls)
            click(button.hwnd)


def set_qt_parent(qt_hwnd, parent_hwnd):
    """Parent a QWidget to another Window using hwnd's."""

    exstyle = GetWindowLong(qt_hwnd, GWL_EXSTYLE)
    SetWindowLong(
        qt_hwnd,
        GWL_EXSTYLE,
        exstyle | WS_EX_NOPARENTNOTIFY | WS_EX_NOINHERITLAYOUT,
    )
    SetParent(qt_hwnd, parent_hwnd)
    return qt_hwnd


class ProxyParent(QtWidgets.QWidget):
    """A convenience class for creating a QWidget proxy parented to another processes
    Window.

    Once created, a ProxyParent can be used as the primary parent for the rest of your
    application windows.

    Example:
        afx = ProxyParent('Adobe After Effects*')
        dialog = QtWidgets.QDialog(parent=afx)
        dialog.setWindowTitle('AFX Child Dialog!')
        dialog.exec()
    """

    def __init__(self, parent_title_or_hwind=None):
        super().__init__()
        self.attached = False
        self.uuid = str(uuid.uuid4())
        self.setGeometry(0, 0, 0, 0)
        self.setWindowTitle(self.uuid)
        self.show()
        self.this_window = find_window_by_title(self.uuid)
        self.parent_window = None
        if parent_title_or_hwind:
            self.attach(parent_title_or_hwind)

    def find_parent_window(self, parent_title_or_hwind=None):
        if not parent_title_or_hwind:
            return
        if isinstance(parent_title_or_hwind, str):
            return find_window_by_title(parent_title_or_hwind)
        else:
            return find_window_by_hwnd(parent_title_or_hwind)

    def attach(self, parent_title_or_hwind):
        if self.attached:
            self.detach()
        self.parent_window = self.find_parent_window(parent_title_or_hwind)
        set_qt_parent(self.this_window.hwnd, self.parent_window.hwnd)
        self.attached = True
        self.hide()

    def detach(self):
        if not self.attached:
            return
        SetParent(self.this_window.hwnd, 0)
        self.parent_window = None
        self.attached = False
