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
import logging
import os
from typing import Any


class Translator:
    def __init__(self) -> None:
        # self.langs will contain all messages in format
        # {
        #   "lang_id": {
        #       "message_id": "Message text",
        #       ...
        #   },
        #   ...
        # }
        self.langs = {}

        # Set this externally to use get() without lang_id parameter
        self.lang_id = "eng"

    def langs_load(self, langs_dir: str) -> None:
        """Loads and parses languages from json files into multiprocessing dictionary

        Args:
            langs_dir (str): path to directory with language files

        Raises:
            Exception: file read error / parse error / no keys
        """
        logging.debug(f"Parsing {langs_dir} directory")
        for file in os.listdir(langs_dir):
            # Parse only .json files
            if file.lower().endswith(".json"):
                # Read file
                lang_id = os.path.splitext(os.path.basename(file))[0]
                logging.debug(f"Loading file {file} as language with ID {lang_id}")
                file_path = os.path.join(langs_dir, file)
                with open(file_path, "r", encoding="utf-8") as file_:
                    lang_dict = json.loads(file_.read())

                # Append to loaded languages
                self.langs[lang_id] = lang_dict

        # Check other languages by comparing with english
        for key, value in self.langs["eng"].items():
            for lang_id, lang in self.langs.items():
                if lang_id == "eng":
                    continue
                if key not in lang:
                    raise Exception(f"No {key} key in {lang_id} language")
                if isinstance(value, dict):
                    for key_, _ in value.items():
                        if key_ not in lang[key]:
                            raise Exception(f"No {key}/{key_} key in {lang_id} language")

        # Sort alphabetically
        self.langs = {key: value for key, value in sorted(self.langs.items())}

        # Print final number of languages
        logging.debug(f"Loaded {len(self.langs)} languages")

    def get(self, message_key: str, lang_id: str or None = None) -> Any:
        """Retrieves message from language

        Args:
            message_key (str): key from lang file
            lang_id (str or None, optional): ID of language or None to use self.lang_id

        Returns:
            Any: values of message_key or default_value
        """
        # Fallback to English
        if lang_id is None:
            lang_id = self.lang_id

        # Get messages
        messages = self.langs.get(lang_id)

        # Check if lang_id exists or fallback to English
        if messages is None:
            logging.warning(f"No language with ID {lang_id}")
            messages = self.langs.get("eng")

        return messages.get(message_key, "?")
