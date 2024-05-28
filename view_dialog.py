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

import datetime
import json
import os
from typing import Dict, List

import pyqrcode
from PyQt6 import QtCore, QtGui, uic
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QSizePolicy, QWidget

from _version import __version__
from config_manager import ConfigManager
from get_resource_path import get_resource_path
from translator import Translator

GUI_VIEW_FILE = get_resource_path(os.path.join("forms", "view.ui"))

# Approximately. Actual data may exceed this value slightly
QR_LIMIT_BYTES = 500


class ViewDialog(QDialog):
    def __init__(self, parent: QWidget or None, translator_: Translator, config_manager_: ConfigManager):
        super().__init__(parent)

        self.translator = translator_
        self.config_manager = config_manager_

        self._datas = []
        self._index = 0
        self._image = None
        self._data_type = None

        # Load GUI from file
        uic.loadUi(GUI_VIEW_FILE, self)

        # Connect buttons
        self.btn_prev.clicked.connect(lambda: self._show_qr(self._index - 1))
        self.btn_next.clicked.connect(lambda: self._show_qr(self._index + 1))
        self.button_box.button(QDialogButtonBox.StandardButton.Save).clicked.disconnect()
        self.button_box.button(QDialogButtonBox.StandardButton.Save).clicked.connect(self._save_qr)

        # For resize event
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.installEventFilter(self)

    def show(
        self, title: str, description: str, actions: List[Dict] or None = None, mnemonic: List[str] or None = None
    ) -> None:
        """Non-blocking wrapper for _pre_show_or_exec()
        Opens dialog and shows 1st QR code
        """
        self._pre_show_or_exec(title, description, actions, mnemonic)

        super().show()

        self._index = 0
        self._show_qr()

    def exec(
        self, title: str, description: str, actions: List[Dict] or None = None, mnemonic: List[str] or None = None
    ) -> None:
        """Blocking wrapper for _pre_show_or_exec()
        Opens dialog and shows 1st QR code
        """
        self._pre_show_or_exec(title, description, actions, mnemonic)

        self._index = 0
        self._show_qr()

        super().exec()

    def _pre_show_or_exec(
        self, title: str, description: str, actions: List[Dict] or None = None, mnemonic: List[str] or None = None
    ):
        """Prepares dialog

        Args:
            title (str): dialog title text
            description (str): dialog description text
            actions (List[Dict] or None, optional): list of json objects to sync. Defaults to None
            mnemonic (List[str] or None, optional): list of mnemonic words. Defaults to None
        """

        # Translate buttons
        self.button_box.button(QDialogButtonBox.StandardButton.Close).setText(self.translator.get("btn_close"))
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText(self.translator.get("btn_save_image"))
        self.btn_prev.setText(self.translator.get("btn_prev"))
        self.btn_next.setText(self.translator.get("btn_next"))

        # Set title and description
        self.setWindowTitle(title)
        self.title.setText(title)
        self.description.setText(description)

        self._datas.clear()

        # Mnemonic phrase -> just separate each word with space
        if mnemonic is not None:
            self._data_type = "mnemonic"
            self._datas.append(" ".join(mnemonic))

        # List of actions -> parse and split (if needed)
        elif actions is not None:
            self._data_type = "actions"

            # Pre-build as JSON
            index_data = 0
            data_dicts = []
            for action in actions:
                # New QR code
                if index_data >= len(data_dicts):
                    data_dicts.append({"i": index_data, "acts": []})

                # Append our action
                data_dicts[index_data]["acts"].append(action)

                # Check size and request new QR code if exceeded
                data_str = json.dumps(data_dicts[index_data], separators=(",", ":"), ensure_ascii=False)[1:][:-1]
                if len(data_str.encode("utf-8")) >= QR_LIMIT_BYTES:
                    index_data += 1

            # Convert to string
            for data_dict in data_dicts:
                data_dict["n"] = len(data_dicts)
                data_str = json.dumps(data_dict, separators=(",", ":"), ensure_ascii=False)[1:][:-1]
                self._datas.append(data_str)

        # Hide navigation buttons if there is only one QR code
        if len(self._datas) > 1:
            self.btn_prev.show()
            self.btn_next.show()
        else:
            self.btn_prev.hide()
            self.btn_next.hide()

    @QtCore.pyqtSlot()
    def _show_qr(self, index: int or None = None) -> None:
        """Draws QR code with data from self._datas

        Args:
            index (int or None, optional): QR code index or None to use self._index. Defaults to None
        """
        if index is None:
            index = self._index

        if self._datas is None or index >= len(self._datas) or index < 0:
            return

        self._index = index

        # Print stats or nothing if there is only one QR code
        if len(self._datas) != 1:
            self.lb_index.setText(f"{index + 1} / {len(self._datas)}")
        else:
            self.lb_index.setText("")

        # Encode and convert to QImage
        qr = pyqrcode.create(self._datas[index], error="L", encoding="utf-8")
        self._image = QtGui.QImage.fromData(
            QtCore.QByteArray.fromBase64(qr.png_as_base64_str().encode("utf-8")), "PNG"
        )

        # Scale and show
        image_scaled = self._image.scaled(
            self.lb_image.width() - 2,
            self.lb_image.height() - 2,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.FastTransformation,
        )
        self.lb_image.setPixmap(QPixmap.fromImage(image_scaled))

        # Disable buttons if needed
        self.btn_prev.setEnabled(index > 0)
        self.btn_next.setEnabled(index < len(self._datas) - 1)

    @QtCore.pyqtSlot()
    def _save_qr(self) -> None:
        """Exports current QR code as file"""
        if self._image is None:
            return

        # Ask user
        name_suggestion = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S.png")
        if self._data_type:
            name_suggestion = f"{self._data_type}_{name_suggestion}"
        file_name = QFileDialog.getSaveFileName(
            self,
            self.translator.get("btn_save_image"),
            os.path.join(self.config_manager.get("qr_save_path", os.path.expanduser("~")), name_suggestion),
            "All Files(*);;PNG Files (*.png);;JPEG Files (*.jpg *.jpeg)",
        )
        if not file_name or not file_name[0]:
            return

        file_name = file_name[0]

        # Save dir to config for next selection
        self.config_manager.set("qr_save_path", os.path.dirname(file_name))

        # Save image with the same size
        image_scaled = self._image.scaled(
            self.lb_image.width() - 2,
            self.lb_image.height() - 2,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.FastTransformation,
        )
        image_scaled.save(file_name)

    def eventFilter(self, obj, event):
        """Dirty way to resize image"""
        if event.type() == QtCore.QEvent.Type.Resize:
            if self._image is not None:
                image_scaled = self._image.scaled(
                    self.lb_image.width() - 2,
                    self.lb_image.height() - 2,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.FastTransformation,
                )
                self.lb_image.setPixmap(QPixmap.fromImage(image_scaled))

        return super().eventFilter(obj, event)
