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

import ctypes
import logging
import os
import sys

from PyQt6.QtWidgets import QApplication

from _version import __version__
from config_manager import ConfigManager
from gui_main_window import GUIMainWindow


class GUIWrapper:
    def __init__(self, config_manager_: ConfigManager, working_dir: str) -> None:
        """Initializes _Window instance

        Args:
            config_manager_ (ConfigManager): ConfigManager class instance
            working_dir (str): app directory
        """

        # Replace icon in taskbar
        if os.name == "nt":
            logging.debug("Replacing icon in taskbar")
            app_ip = "f3rni.petalvault.petalvault." + __version__
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_ip)

        # Start app
        logging.debug("Initializing GUIMainWindow instance")
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.window = GUIMainWindow(config_manager_, working_dir)

    def open(self) -> int:
        """Starts application (blocking)

        Returns:
            int: exit code
        """
        return self.app.exec()

    # pylint: disable=unused-argument
    def close(self, *args) -> None:
        """Closes application
        This can be connected with signal package
        """
        logging.debug("Closing GUI")
        self.window.close()

    # pylint: enable=unused-argument
