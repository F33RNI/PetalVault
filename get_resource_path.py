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

import os


def get_resource_path(filename_: str) -> str:
    """Converts local file path to absolute path
    (For proper resources loading using pyinstaller)

    Args:
        filename_ (str): local file path

    Returns:
        str: absolute file path
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), filename_))
