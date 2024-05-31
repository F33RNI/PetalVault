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

import json
import locale
import logging
import os
from typing import Any

from _version import __version__

# Crude way to get default language
_LOCALE = "eng"
try:
    _LOCALE = locale.getlocale()[0]
except:
    pass

try:
    LANG_ID_DEFAULT = "rus" if _LOCALE.startswith("ru") else "eng"
except:
    LANG_ID_DEFAULT = "eng"

CONFIG_DEFAULT = {"version": __version__, "lang_id": LANG_ID_DEFAULT, "camera_index": 0}


class ConfigManager:
    def __init__(self, config_file: str) -> None:
        """Initializes ConfigManager and reads config file

        Args:
            config_file (str): config file (.json)
        """
        self._config_file = config_file

        self._config = {}

        # Try to load config file
        if os.path.exists(config_file):
            logging.debug(f"Loading {config_file}")
            with open(config_file, encoding="utf-8", errors="replace") as config_file_io:
                json_content = json.load(config_file_io)
                if json_content is not None and isinstance(json_content, dict):
                    self._config = json_content
                else:
                    logging.warning(f"Unable to load config from {config_file}")

    def get(self, key: str, default_value: Any or None = None) -> Any:
        """Retrieves value from config by key

        Args:
            key (str): config key to get value of
            default_value (Any or None): value to return if key doesn't exists in config file and in CONFIG_DEFAULT

        Returns:
            Any: key's value or default_value
        """
        # Retrieve from config
        if key in self._config:
            return self._config[key]

        # Use default value
        elif key in CONFIG_DEFAULT:
            return CONFIG_DEFAULT[key]

        # No key -> return default value
        else:
            logging.debug(f"Key {key} doesn't exist in config")
            return default_value

    def set(self, key: str, value: Any) -> None:
        """Updates config values and saves it to the file

        Args:
            key (str): config key
            value (Any): key's value
        """
        # Set value
        self._config[key] = value

        # Save to file
        logging.debug(f"Saving config to {self._config_file}")
        with open(self._config_file, "w+", encoding="utf-8") as config_file_io:
            json.dump(self._config, config_file_io, indent=4, ensure_ascii=False)
