"""
This file is part of the PetalVault password manager distribution. See <https://github.com/F33RNI/PetalVault>.

Copyright (C) 2024 Fern Lane

This program is free software: you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.
If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import logging
import os
import signal
import sys

from _version import __version__
from config_manager import ConfigManager
from gui_wrapper import GUIWrapper

DIR_DEFAULT = os.path.join(os.path.expanduser("~"), ".petalvault")

LOGGING_FORMATTER = "[%(asctime)s] [%(levelname)s] [%(funcName)s] %(message)s"


def parse_args() -> argparse.Namespace:
    """Parses cli arguments

    Returns:
          argparse.Namespace: parsed arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--app-dir",
        type=str,
        required=False,
        help=f"path to application directory (with config.json) (Default: {DIR_DEFAULT})",
        default=DIR_DEFAULT,
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="specify to enable DEBUG logging into console",
        default=False,
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)
    return parser.parse_args()


def main() -> None:
    """Main entry point"""
    args = parse_args()

    # Initialize logging with DEBUG level in case of --verbose or WARNING otherwise
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING, format=LOGGING_FORMATTER)

    # Create dir if not exists
    if not os.path.exists(args.app_dir):
        logging.debug(f"Creating {args.app_dir} directory")
        os.makedirs(args.app_dir)

    # Initialize class instances
    config_manager_ = ConfigManager(config_file=os.path.join(args.app_dir, "config.json"))
    gui_wrapper = GUIWrapper(config_manager_=config_manager_, working_dir=args.app_dir)

    # Connect signals to catch CTRL+C
    signal.signal(signal.SIGINT, gui_wrapper.close)
    signal.signal(signal.SIGTERM, gui_wrapper.close)

    # Open GUI (blocking) and exit with it's exit code
    sys.exit(gui_wrapper.open())


if __name__ == "__main__":
    main()
