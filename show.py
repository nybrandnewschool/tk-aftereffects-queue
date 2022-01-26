import argparse
import os
import sys
sys.path.insert(1, os.path.abspath('python'))

import aequeue.tests


def apps_description():
    lines = []
    width = len(max(aequeue.tests.apps.keys(), key=len)) + 2
    for app_name, app in aequeue.tests.apps.items():
        lines.append(f'{app_name:>{width}}: {app.__doc__}')
    return '\n'.join(lines)


def main():
    # Create parser
    parser = argparse.ArgumentParser(
        prog='AEQueue Test Applications...',
        description=(
            'A series of applications for feature development and testing.\n\n'
            'Apps:\n'
        ) + apps_description(),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('app', choices=aequeue.tests.apps.keys())

    # Parse cli arguments
    args = parser.parse_args()

    # Show application
    app = aequeue.tests.apps[args.app]
    app()


if __name__ == '__main__':
    main()
