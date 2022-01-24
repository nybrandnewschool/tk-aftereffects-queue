import os
import sys
sys.path.insert(1, os.path.abspath('python'))

import aequeue.tests


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        prog='AEQueue UI Tests...',
        description=(
            'Commands:\n'
            '         test_ui: Basic UI for viewing styling.\n'
            '      simple_app: Simple render test using Mock tasks.\n'
            '       tasks_app: Advanced render test using Flow and Task objects.\n'
            '       toast_app: Test Toast popups when buttons are pressed.\n'
            '  item_menus_app: Test Kebab Menus for each render item.\n'
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'command',
        help='Test command to run...',
        choices=['test_ui', 'simple_app', 'item_menus_app', 'tasks_app', 'toast_app'],
    )
    args = parser.parse_args()
    command = getattr(aequeue.tests, 'show_' + args.command)
    command()
