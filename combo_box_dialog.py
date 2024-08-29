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

from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QVBoxLayout, QWidget

from _version import __version__


def combo_box_dialog(parent: QWidget | None, title: str, items: list[str]) -> int | None:
    """Creates dialog contains combobox

    Args:
        parent (QWidget or None): parent widget
        title (str): dialog title
        items (list[str]): list of combobox items

    Returns:
        int or None: selected index
    """
    dialog = _ComboBoxDialog(parent, title, items)
    result = dialog.exec()
    index = dialog.selected_index()
    return index if result == QDialog.DialogCode.Accepted else None


class _ComboBoxDialog(QDialog):
    def __init__(self, parent: QWidget | None, title: str, items: list[str]):
        super().__init__(parent)

        self.setWindowTitle(title)

        layout = QVBoxLayout()

        self.comboBox = QComboBox()
        self.comboBox.addItems(items)
        layout.addWidget(self.comboBox)

        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        button_box = QDialogButtonBox(buttons)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setLayout(layout)

    def selected_index(self) -> int:
        """
        Returns:
            int: selected index
        """
        return self.comboBox.currentIndex()
