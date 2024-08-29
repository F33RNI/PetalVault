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

import gc
import logging
import os
from typing import override

from mnemonic import Mnemonic
from PyQt6 import QtCore, uic
from PyQt6.QtWidgets import (
    QApplication,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QWidget,
)

from _version import __version__
from clear_layout import clear_layout
from config_manager import ConfigManager
from get_resource_path import get_resource_path
from scan_dialog import ScanDialog
from translator import Translator
from view_dialog import ViewDialog

GUI_MNEMONIC_FILE = get_resource_path(os.path.join("forms", "mnemonic.ui"))
WORDLIST_FILE = get_resource_path("wordlist.txt")


class MnemonicDialog(QDialog):
    result_signal = QtCore.pyqtSignal(object)

    def __init__(self, parent: QWidget | None, translator_: Translator, config_manager_: ConfigManager):
        super().__init__(parent)

        self.translator = translator_
        self.config_manager = config_manager_

        # QR scanner
        self.scan_dialog = ScanDialog(self, self.translator, self.config_manager)
        self.scan_dialog.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.scan_dialog.result_signal.connect(self._scan_qr_result)

        # QR viewer
        self.view_dialog = ViewDialog(self, self.translator, self.config_manager)
        self.view_dialog.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)

        # Clipboard
        self.clipboard = QApplication.clipboard()

        # Load wordlist and Mnemonic instance
        self.wordlist = []
        logging.debug(f"Loading words from {WORDLIST_FILE} file")
        with open(WORDLIST_FILE, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    self.wordlist.append(line)
        logging.debug(f"Loaded {len(self.wordlist)} words")
        self.mnemo = Mnemonic("english", self.wordlist)

        # Load GUI from file
        uic.loadUi(GUI_MNEMONIC_FILE, self)

        self._line_edits = []
        self._completing_flags = []
        self._words = []
        self._read_only = False
        self._closed = False

        # Don't close on OK
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).clicked.disconnect()
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(self._finished)

        # Extra buttons
        self.btn_scan_qr.clicked.connect(self._scan_qr)
        self.btn_show_qr.clicked.connect(self._show_qr)
        self.btn_random.clicked.connect(self._random)
        self.btn_copy.clicked.connect(self._copy)
        self.btn_paste.clicked.connect(self._paste)

        # On exit
        self.finished.connect(lambda: self._finished(canceled=True))

    @override
    def show(
        self,
        title: str,
        description: str,
        initial_phrase: list[str] | None = None,
        random: bool = True,
        read_only: bool = False,
    ) -> None:
        """Non-blocking wrapper for _pre_show_or_exec()

        Connect result_signal to catch result
        """
        self._pre_show_or_exec(title, description, initial_phrase, random, read_only)
        super().show()

    @override
    def exec(
        self,
        title: str,
        description: str,
        initial_phrase: list[str] | None = None,
        random: bool = True,
        read_only: bool = False,
    ) -> list[str] | None:
        """Blocking wrapper for _pre_show_or_exec()

        Returns:
            list[str] or None: mnemonic phrase as list of words or None in case of dialog canceled
        """
        cancel_flag = {}
        mnemonic = []

        @QtCore.pyqtSlot(object)
        def _catch_finished(mnemonic_: list[str] | None):
            if mnemonic_ is None:
                cancel_flag["cancel"] = True
                return
            for word in mnemonic_:
                mnemonic.append(word)

        try:
            self.result_signal.disconnect()
        except:
            pass

        if not read_only:
            self.result_signal.connect(_catch_finished)

        self._pre_show_or_exec(title, description, initial_phrase, random, read_only)
        super().exec()

        # Recursively block until user cancel dialog or provide correct data
        if len(mnemonic) == 0 and not cancel_flag.get("cancel") and not read_only:
            return self.exec(title, description, initial_phrase, random, read_only)

        return mnemonic if not read_only and len(mnemonic) != 0 else None

    def _pre_show_or_exec(
        self,
        title: str,
        description: str,
        initial_phrase: list[str] | None = None,
        random: bool = True,
        read_only: bool = False,
    ) -> None:
        """Removes previous data and fills it new

        Args:
            title (str): dialog title text
            description (str): dialog description text
            initial_phrase (list[str] | None, optional): list of words to fill in. Defaults to None
            random (bool, optional): True to fill with random data instead of empty one in case of no initial_phrase
            read_only (bool, optional): True to only allow copying and showing QR (no modify). Defaults to False
        """
        self._read_only = read_only
        self._closed = False

        clear_layout(self.layout_words)
        self._line_edits.clear()
        self._completing_flags.clear()
        self._words.clear()

        # Run full garbage collection (just in case)
        gc.collect()

        # Translate buttons
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText(self.translator.get("btn_ok"))
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setDefault(True)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setFocus()
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(self.translator.get("btn_cancel"))
        self.btn_scan_qr.setText(self.translator.get("btn_scan_qr"))
        self.btn_show_qr.setText(self.translator.get("btn_show_qr"))
        self.btn_random.setText(self.translator.get("btn_random"))
        self.btn_copy.setText(self.translator.get("btn_copy"))
        self.btn_paste.setText(self.translator.get("btn_paste"))

        # Set title and description
        self.setWindowTitle(title)
        self.title.setText(title)
        self.description.setText(description)

        # Random or empty phrase
        if initial_phrase is None or len(initial_phrase) == 0:
            if random:
                initial_phrase = self.mnemo.generate(strength=128).split(" ")
            else:
                initial_phrase = ["" for _ in range(12)]

        # Pre-fill
        for i, word in enumerate(initial_phrase):
            self._add_word_input(i, i // 6, i % 6, word)

        # Disable elements in read-only mode
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(not read_only)
        self.btn_scan_qr.setEnabled(not read_only)
        self.btn_random.setEnabled(not read_only)
        self.btn_paste.setEnabled(not read_only)
        for line_edit in self._line_edits:
            line_edit.setReadOnly(read_only)

    @QtCore.pyqtSlot(bool)
    def _finished(self, canceled: bool = False):
        """User pressed OK or Cancel"""
        if self._closed:
            return

        # User closed read-only dialog
        if self._read_only:
            self._closed = True
            self.close()
            return

        # User canceled dialog
        if canceled:
            try:
                logging.debug("Emitting None to result_signal")
                self.result_signal.emit(None)
            except Exception as e:
                logging.error(f"Unable to emit result_signal: {e}")
            self._closed = True
            return

        # User pressed OK
        words = self._check_get()
        if words is None:
            self._closed = False
            return
        try:
            logging.debug("Emitting mnemonic phrase to result_signal")
            self.result_signal.emit(words)
        except Exception as e:
            logging.error(f"Unable to emit result_signal: {e}")
        self._closed = True
        self.close()

    @QtCore.pyqtSlot()
    def _scan_qr(self) -> None:
        self.scan_dialog.show(
            self.translator.get("qr_scanner_mnemo_title"),
            self.translator.get("qr_scanner_mnemo_description"),
            "mnemonic",
        )

    @QtCore.pyqtSlot(object)
    def _scan_qr_result(self, data: str | list[str] | None = None) -> None:
        if not isinstance(data, list):
            return
        for i, line_edit in enumerate(self._line_edits):
            if i >= len(data):
                logging.warning("Number of scanned words doesn't match number of available fields")
                break
            self._completing_flags[i] = True
            line_edit.setText(data[i])
            self._completing_flags[i] = False

    @QtCore.pyqtSlot()
    def _show_qr(self) -> None:
        words = self._check_get()
        if words is None:
            return
        self.view_dialog.show(
            self.translator.get("qr_viewer_mnemo_title"),
            self.translator.get("qr_viewer_mnemo_description"),
            mnemonic=words,
        )

    @QtCore.pyqtSlot()
    def _random(self) -> None:
        phrase = self.mnemo.generate(strength=128).split(" ")
        for i, line_edit in enumerate(self._line_edits):
            self._completing_flags[i] = True
            line_edit.setText(phrase[i])
            self._completing_flags[i] = False

    @QtCore.pyqtSlot()
    def _copy(self) -> None:
        self.clipboard.clear(mode=self.clipboard.Mode.Clipboard)
        self.clipboard.setText(" ".join(self._words), mode=self.clipboard.Mode.Clipboard)

    @QtCore.pyqtSlot()
    def _paste(self) -> None:
        text = str(self.clipboard.text(mode=self.clipboard.Mode.Clipboard)).strip().lower().split(" ")
        for i, line_edit in enumerate(self._line_edits):
            self._completing_flags[i] = True
            if i < len(text) and text[i] in self.wordlist:
                line_edit.setText(text[i])
                self._words[i] = text[i]
            else:
                line_edit.setText("")
                self._words[i] = ""
            self._completing_flags[i] = False

    def _check_get(self) -> list[str] | None:
        """Checks if all words are in the wordlist and can be converted into entropy and returns mnemonic phrase

        Returns:
            list[str] or None: mnemonic phrase as list or None in case of error
        """
        # Check words
        words = []
        for line_edit in self._line_edits:
            word = line_edit.text().strip().lower()
            if not word or word not in self.wordlist:
                if not word:
                    error_text = self.translator.get("error_empty_word")
                else:
                    error_text = self.translator.get("error_wrong_word").format(word=word)
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setText(error_text)
                msg.setWindowTitle(error_text)
                msg.exec()
                return None
            words.append(word)

        # Check entropy
        try:
            entropy = self.mnemo.to_entropy(words)
            if not entropy:
                raise Exception("Empty entropy")
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText(self.translator.get("error_wrong_mnemo"))
            msg.setDetailedText(str(e))
            msg.setWindowTitle(self.translator.get("error_wrong_mnemo"))
            msg.exec()
            return None

        return words

    def _add_word_input(self, id_: int, row: int, col: int, word: str | None = None):
        """Adds input field

        Args:
            id_ (int): absolute index (0 - N)
            row (int): self.layout_words row index
            col (int): self.layout_words column index
            word (str | None, optional): initial value. Defaults to None
        """
        logging.debug(f"Adding word with ID {id_}")

        # Word number
        label = QLabel()
        label.setText(str(id_ + 1))

        # Input itself
        line_edit = QLineEdit()
        if word:
            line_edit.setText(word)
        self._line_edits.append(line_edit)

        # Attach completer
        completer = QCompleter(self.wordlist)
        completer.setMaxVisibleItems(10)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(QtCore.Qt.MatchFlag.MatchStartsWith)
        completer.setWidget(line_edit)
        completer.activated.connect(lambda text: self._word_completion(id_, line_edit, completer, text))
        line_edit.textChanged.connect(lambda text: self._word_text_changed(id_, completer, text))
        if len(self._completing_flags) <= id_:
            self._completing_flags.append(False)
        else:
            self._completing_flags[id_] = False

        # Final phrase will be in self._words
        if len(self._words) <= id_:
            self._words.append(word)
        else:
            self._words[id_] = word

        # ID + input container
        layout = QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(line_edit)

        # Add to the main container
        self.layout_words.addLayout(layout, row, col)

    def _word_text_changed(self, id_: int, completer: QCompleter, text: str) -> None:
        self._words[id_] = text

        if self._completing_flags[id_] or not text:
            return

        completer.setCompletionPrefix(text)

        if completer.currentRow() >= 0:
            completer.complete()
        else:
            completer.popup().hide()

    def _word_completion(self, id_: int, line_edit: QLineEdit, completer: QCompleter, text: str) -> None:
        if self._completing_flags[id_]:
            return

        self._completing_flags[id_] = True
        prefix = completer.completionPrefix()
        line_edit.setText(line_edit.text()[: -len(prefix)] + text)
        self._completing_flags[id_] = False
