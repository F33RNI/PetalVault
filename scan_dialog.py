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

import logging
import os
from typing import Any, Dict, List, Tuple

from PyQt6 import QtCore, QtGui, uic
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QWidget

from _version import __version__
from clear_layout import clear_layout
from config_manager import ConfigManager
from get_resource_path import get_resource_path
from qr_scanner_thread import QRScannerThread
from translator import Translator

GUI_SCAN_FILE = get_resource_path(os.path.join("forms", "scan.ui"))

STYLESHEET_LABEL_INACTIVE = "background-color: #406e66;"
STYLESHEET_LABEL_RECEIVED = "background-color: #6ad0be;"


class ScanDialog(QDialog):
    # Connect this to catch result
    # List[str] or Tuple[List[Dict], bytes] or None: mnemonic, (list of actions, sync salt) or None if canceled
    result_signal = QtCore.pyqtSignal(object)

    def __init__(self, parent: QWidget or None, translator_: Translator, config_manager_: ConfigManager):
        super().__init__(parent)

        self.translator = translator_
        self.config_manager = config_manager_

        self._expected_data = None
        self._qr_scanner_thread = None
        self._parts_widgets = []

        # Load GUI from file
        uic.loadUi(GUI_SCAN_FILE, self)

        # Connect camera ID controls
        self.sb_camera_id.valueChanged.connect(self._camera_id_changed)
        self.btn_apply.clicked.connect(self._camera_id_apply)

        self.finished.connect(self._finished)

    @QtCore.pyqtSlot()
    def _qr_scanner_thread_finished(self):
        """Scanned callback"""
        # Error
        if self._qr_scanner_thread.exception is not None:
            self.lb_preview.setText(
                self.translator.get("qr_scanner_error_camera").format(error=str(self._qr_scanner_thread.exception))
            )
            return

        try:
            logging.debug("Emitting result_signal")
            if self._expected_data == "mnemonic":
                self.result_signal.emit(self._qr_scanner_thread.mnemonic)
            elif self._expected_data == "actions":
                self.result_signal.emit((self._qr_scanner_thread.actions, self._qr_scanner_thread.sync_salt))
            else:
                self.result_signal.emit(None)
        except Exception as e:
            logging.error(f"Unable to emit result_signal: {e}")

        self.close()

    @QtCore.pyqtSlot(QtGui.QImage)
    def _set_image(self, image: QtGui.QImage):
        """Resizes and sets image of lb_preview
        call QRScannerThread.set_image_signal.connect(self.set_image)

        Args:
            image (QtGui.QImage): preview image
        """
        image_scaled = image.scaled(self.lb_preview.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        pixmap = QPixmap.fromImage(image_scaled)
        self.lb_preview.setPixmap(pixmap)

    @QtCore.pyqtSlot(tuple)
    def _set_received_part_flag(self, part_idx_total: Tuple[int, int]):
        """Multiple QR parts callback

        Args:
            part_idx_total (Tuple[int, int]): (current part starting from 0, total N of parts)
        """
        part_idx, parts_total = part_idx_total

        # Add labels if needed
        if len(self._parts_widgets) < parts_total:
            for i in range(parts_total):
                part_label = QLabel()
                part_label.setText(str(i + 1))
                part_label.setStyleSheet(STYLESHEET_LABEL_INACTIVE)
                part_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                self.layout_parts.addWidget(part_label)
                self._parts_widgets.append(part_label)

        # Set label
        self._parts_widgets[part_idx].setStyleSheet(STYLESHEET_LABEL_RECEIVED)

    def show(self, title: str, description: str, expected_data: str):
        """Non-blocking wrapper for _pre_show_or_exec()

        Connect result_signal to catch result
        List[str] or Tuple[List[Dict], bytes] or None: mnemonic, (list of actions, sync salt) or None if canceled
        """
        self._pre_show_or_exec(title, description, expected_data)
        super().show()

    def exec(self, title: str, description: str, expected_data: str) -> List[str] or Tuple[List[Dict], bytes] or None:
        """Blocking wrapper for _pre_show_or_exec()

        Returns:
            List[str] or Tuple[List[Dict], bytes] or None: mnemonic, (list of actions, sync salt) or None if canceled
        """
        mnemonic_or_actions = []
        sync_salt = {"salt": None}

        @QtCore.pyqtSlot(object)
        def _catch_finished(result_: List[str] or Tuple[List[Dict], bytes] or None):
            if result_ is None:
                return

            if isinstance(result_, Tuple):
                for action in result_[0]:
                    mnemonic_or_actions.append(action)
                sync_salt["salt"] = result_[1]

            elif isinstance(result_, List):
                for word in result_:
                    mnemonic_or_actions.append(word)

        try:
            self.result_signal.disconnect()
        except:
            pass
        self.result_signal.connect(_catch_finished)

        self._pre_show_or_exec(title, description, expected_data)
        super().exec()

        if len(mnemonic_or_actions) != 0:
            if expected_data == "mnemonic":
                return mnemonic_or_actions
            elif expected_data == "actions":
                return mnemonic_or_actions, sync_salt["salt"]

        return None

    def _pre_show_or_exec(self, title: str, description: str, expected_data: str):
        """Starts scanner

        Args:
            title (str): dialog title text
            description (str): dialog description text
            expected_data (str): "mnemonic" or "actions"

        Connect ScanDialog.result_signal to catch result
        """
        self._expected_data = expected_data

        # Clear layout from previous run
        clear_layout(self.layout_parts)

        # Translate widgets
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(self.translator.get("btn_cancel"))
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setFocus()
        self.lb_camera_id.setText(self.translator.get("qr_scanner_camera_id"))
        self.btn_apply.setText(self.translator.get("btn_apply"))

        # Set title and description
        self.setWindowTitle(title)
        self.title.setText(title)
        self.description.setText(description)

        # Set camera ID
        self.sb_camera_id.setValue(self.config_manager.get("camera_index", 0))

        # Start thread
        logging.debug("Initializing and starting QR scanner thread")
        self.lb_preview.setText(self.translator.get("qr_scanner_opening_camera"))
        self._qr_scanner_thread = QRScannerThread(self.config_manager.get("camera_index", 0), expected_data)
        self._qr_scanner_thread.set_image_signal.connect(self._set_image)
        self._qr_scanner_thread.received_part_flag_signal.connect(self._set_received_part_flag)
        self._qr_scanner_thread.finished_signal.connect(self._qr_scanner_thread_finished)
        self._qr_scanner_thread.start()

    @QtCore.pyqtSlot(int)
    def _camera_id_changed(self, value: int) -> None:
        """Camera ID spinbox callback"""
        self.btn_apply.setEnabled(value != self.config_manager.get("camera_index", 0))

    @QtCore.pyqtSlot()
    def _camera_id_apply(self) -> None:
        """Apply button callback"""
        # Change camera ID
        camera_index = self.sb_camera_id.value()
        self.config_manager.set("camera_index", camera_index)

        # Restart thread
        if self._qr_scanner_thread is not None and self._qr_scanner_thread.is_alive():
            self._qr_scanner_thread.finished_signal.disconnect()
            self._qr_scanner_thread.cancel()
            self._qr_scanner_thread.join()
        logging.debug("Initializing and starting QR scanner thread")
        self.lb_preview.setText(self.translator.get("qr_scanner_opening_camera"))
        self._qr_scanner_thread = QRScannerThread(self.config_manager.get("camera_index", 0), self._expected_data)
        self._qr_scanner_thread.set_image_signal.connect(self._set_image)
        self._qr_scanner_thread.received_part_flag_signal.connect(self._set_received_part_flag)
        self._qr_scanner_thread.finished_signal.connect(self._qr_scanner_thread_finished)
        self._qr_scanner_thread.start()

    def _finished(self, result: Any) -> None:
        """Cancels QR scanning (must be connected to self.finished signal)

        Args:
            result (Any): dialog result object
        """
        logging.debug(f"Received finished signal. Result: {result}")

        if self._qr_scanner_thread is not None and self._qr_scanner_thread.is_alive():
            self._qr_scanner_thread.cancel()
            self._qr_scanner_thread.join()
