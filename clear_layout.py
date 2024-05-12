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

from PyQt6.QtWidgets import QLayout


def clear_layout(layout: QLayout) -> None:
    """Recursively removes all widgets and layouts from parent

    Args:
        layout (QLayout): parent layout
    """
    logging.debug(f"Clearing layout: {layout}")
    for i in reversed(range(layout.count())):
        layout_item = layout.itemAt(i)
        if layout_item.widget() is not None:
            widget_to_remove = layout_item.widget()
            logging.debug(f"Found child widget: {widget_to_remove}")
            widget_to_remove.setParent(None)
            layout.removeWidget(widget_to_remove)

        elif layout_item.spacerItem() is None:
            layout_to_remove = layout.itemAt(i)
            logging.debug(f"Found child layout: {layout_to_remove}")
            clear_layout(layout_to_remove)
