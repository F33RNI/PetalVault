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

import base64
import functools
import gc
import hashlib
import json
import logging
import os
import secrets
import string
import webbrowser
from typing import Dict, Tuple

import qdarktheme
from Crypto.Cipher import AES
from Crypto.Util import Padding
from PyQt6 import QtCore, QtGui, uic
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
)

from _version import __version__
from clear_layout import clear_layout
from combo_box_dialog import combo_box_dialog
from config_manager import ConfigManager
from encrypt_decrypt import decrypt_entry, encrypt_entry
from get_resource_path import get_resource_path
from mnemonic_dialog import MnemonicDialog
from scan_dialog import ScanDialog
from translator import Translator
from view_dialog import ViewDialog

# Maximum length of each data field (in characters)
LINE_EDIT_MAX_LENGTH = 70

# Automatically save vault if no new edits during this time
SAVE_AFTER_EDIT_MS = 500

# How long to keep saving text visible
SAVING_TEXT_LABEL_DURATION = 100

GUI_MAIN_FILE = get_resource_path(os.path.join("forms", "main.ui"))
LANGUAGES_DIR = get_resource_path("langs")
ICON_FILE = get_resource_path(os.path.join("icons", "icon.svg"))

ICON_SHOW = get_resource_path(os.path.join("icons", "show.png"))
ICON_HIDE = get_resource_path(os.path.join("icons", "hide.png"))
ICON_COPY = get_resource_path(os.path.join("icons", "copy.png"))
ICON_DELETE = get_resource_path(os.path.join("icons", "delete.png"))

# Generated password parameters
PASSWORD_DATASET = string.ascii_letters + string.digits + string.punctuation
PASSWORD_LENGTH = 12


class GUIMainWindow(QMainWindow):
    def __init__(self, config_manager_: ConfigManager, working_dir: str) -> None:
        """Initializes and starts GUI (blocking)

        Args:
            config_manager_ (ConfigManager): ConfigManager class instance
            working_dir (str): app directory
        """
        super(GUIMainWindow, self).__init__()

        self.config_manager = config_manager_
        self.working_dir = working_dir

        self._vaults = []
        self._vault = {}
        self._save_timer = QtCore.QTimer(self)
        self._save_timer.timeout.connect(lambda: self._vault_save(self._vault["path"]))
        self._saving_timer = QtCore.QTimer(self)
        self._saving_timer.timeout.connect(self._saving_text_hide)

        # Initialize translator and load messages
        self.translator = Translator()
        self.translator.langs_load(self.config_manager.get("langs_dir", LANGUAGES_DIR))

        # Initialize dialogs
        self.mnemonic_dialog = MnemonicDialog(self, self.translator, self.config_manager)
        self.mnemonic_dialog.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.scan_dialog = ScanDialog(self, self.translator, self.config_manager)
        self.scan_dialog.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.view_dialog = ViewDialog(self, self.translator, self.config_manager)
        self.view_dialog.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)

        # Load GUI from file
        uic.loadUi(GUI_MAIN_FILE, self)

        # Set window title
        self.setWindowTitle(f"PetalVault {__version__}")

        # Set icon
        self.setWindowIcon(QtGui.QIcon(ICON_FILE))

        # Start GUI (non-blocking)
        logging.debug("Opening GUI")
        self.show()

        # Connect menu buttons
        self.act_new.triggered.connect(lambda: self._create_vault(from_device=False))
        self.act_open.triggered.connect(lambda: self._open_vault(path=None))
        self.act_import.triggered.connect(lambda: self._create_vault(from_device=True))
        self.act_export.triggered.connect(lambda: self._sync_to(clean_device=True))
        self.act_exit.triggered.connect(self.close)
        self.act_close.triggered.connect(self._close_vault)
        self.act_rename.triggered.connect(self._rename_vault)
        self.act_delete.triggered.connect(self._delete_vault)
        self.act_light.triggered.connect(lambda: self._set_theme("light"))
        self.act_dark.triggered.connect(lambda: self._set_theme("dark"))
        self.act_auto.triggered.connect(lambda: self._set_theme("auto"))
        self.act_issue.triggered.connect(self._report_issue)
        self.act_about.triggered.connect(self._about)

        # Connect other buttons
        self.btn_entry_add.clicked.connect(self._add_entry)
        self.btn_show_mnemonic.clicked.connect(self._show_mnemonic)
        self.btn_search.clicked.connect(lambda: self._render_vault_entries(filter_=self.le_search.text()))
        self.btn_sync_from.clicked.connect(self._sync_from)
        self.btn_sync_to.clicked.connect(lambda: self._sync_to(clean_device=False))

        # Set translations and theme
        self._set_translations()
        self._set_theme()

        # Load vaults and list of recent vaults
        self._update_vaults()

        # Hide and disable widgets
        self._close_vault()

        # Done
        logging.debug("GUI loading finished")

    def _set_translations(self, lang_id: str or None = None) -> None:
        """Loads list of available languages and translates some widgets on a main GUI

        Args:
            lang_id (str or None, optional): None to load languages, ID (ex. "eng") to load it. Defaults to None
        """
        # Load available languages
        if lang_id is None:
            for lang_id_, lang in self.translator.langs.items():
                action = QAction(lang["lang_name"], self)
                action.triggered.connect(functools.partial(self._set_translations, lang_id_))
                self.menu_lang.addAction(action)

            lang_id = self.config_manager.get("lang_id")

        # Language selected
        else:
            self.config_manager.set("lang_id", lang_id)

        logging.debug(f"App language: {lang_id}")
        self.translator.lang_id = lang_id

        # Translate menu bar
        menu_bar = self.translator.get("menu_bar")
        for key, value in menu_bar.items():
            try:
                getattr(self, key).setText(value)
            except:
                try:
                    getattr(self, key).setTitle(value)
                except:
                    logging.warning(f"Unable to set translation of {key}")

        # Translate other elements
        self.lb_search.setText(self.translator.get("search"))
        self.btn_search.setText(self.translator.get("btn_search"))
        self.lb_start.setText(self.translator.get("start"))
        self.lb_site.setText(self.translator.get("site"))
        self.lb_username.setText(self.translator.get("username"))
        self.lb_password.setText(self.translator.get("password"))
        self.lb_notes.setText(self.translator.get("notes"))
        self.btn_show_mnemonic.setText(self.translator.get("btn_show_mnemonic"))
        self.btn_sync_to.setText(self.translator.get("btn_sync_to"))
        self.btn_sync_from.setText(self.translator.get("btn_sync_from"))
        self.btn_entry_add.setText(self.translator.get("btn_entry_add"))

    def _set_theme(self, theme: str or None = None) -> None:
        """Sets GUI theme

        Args:
            theme (str or None, optional): "light", "auto", "dark" or None to load from config. Defaults to None
        """
        if theme is None:
            theme = self.config_manager.get("theme", "auto")
        else:
            self.config_manager.set("theme", theme)

        qdarktheme.setup_theme(theme, custom_colors={"primary": "#BF526B"})

    def _saving_text_hide(self) -> None:
        """self._saving_timer callback that hides self.lb_saving"""
        if self._saving_timer.isActive():
            self._saving_timer.stop()
        self.status_bar.showMessage("")

    @QtCore.pyqtSlot()
    def _show_mnemonic(self) -> None:
        """Shows current mnemonic phrase"""
        if not self._vault or "mnemonic" not in self._vault:
            return
        self.mnemonic_dialog.exec(
            self._vault["name"],
            self.translator.get("mnemonic"),
            initial_phrase=self._vault["mnemonic"],
            read_only=True,
        )

    @QtCore.pyqtSlot()
    def _add_entry(self) -> None:
        """Adds new entry and generates password"""
        password = "".join([secrets.choice(PASSWORD_DATASET) for _ in range(PASSWORD_LENGTH)])
        action = {"act": "add", "pass": password}
        self._vault_action(action=action)

    def _update_vaults(self) -> None:
        """Reads vaults from config and adds up to 10 recent vaults"""
        # Remove all recent vaults
        while len(self.menu_recent.actions()) != 0:
            self.menu_recent.removeAction(self.menu_recent.actions()[0])
        self.menu_recent.update()

        # Parse from config
        self._vaults.clear()
        for vault_path in self.config_manager.get("vaults", []):
            try:
                with open(vault_path, "r", encoding="utf-8") as file:
                    vault = json.loads(file.read())

                # Add ad tuple (path, name)
                vault_name = vault["name"]
                self._vaults.append((vault_path, vault_name))

                # Add to the recent actions up to 10 vaults
                if len(self._vaults) < 10:
                    logging.debug(f"Adding recent vault: {vault_path}")
                    action = QAction(vault_name, self)
                    action.triggered.connect(functools.partial(self._open_vault, vault_path, True))
                    self.menu_recent.addAction(action)
                self.menu_recent.update()

            except Exception as e:
                logging.warning(f"Unable to parse vault from {vault_path}: {e}")

        # Enable Open and recent action only if there is at least one vault
        self.act_open.setEnabled(len(self._vaults) > 0)
        self.menu_recent.setEnabled(len(self._vaults) > 0)

    @QtCore.pyqtSlot()
    def _sync_from(self, save: bool = True, rerender: bool = True) -> bool:
        """Reads QR codes and executes all actions

        Args:
            save (bool, optional): save vault after. Defaults to True
            rerender (bool, optional): rerender vault after. Defaults to True

        Returns:
            bool: True in case of success, False if failed
        """
        if not self._vault:
            return

        actions = self.scan_dialog.exec(
            self.translator.get("qr_scanner_actions_title"),
            self.translator.get("qr_scanner_actions_description_import_sync"),
            "actions",
        )
        if actions is None:
            logging.debug("No actions provided")
            return

        # pylint: disable=not-an-iterable
        for action in actions:
            if not self._vault_action(action, save=False, rerender=False):
                return False
        # pylint: enable=not-an-iterable

        # Save vault
        if save:
            if not self._vault_save(filepath=self._vault.get("path")):
                return False

        # Update GUI
        if rerender:
            self._render_vault_entries()

        return True

    def _delete_device(self, device_name: str) -> None:
        """Deletes device from current vault by name

        Args:
            device_name (str): _description_
        """
        if not self._vault or not self._vault.get("devices") or device_name not in self._vault["devices"]:
            return

        # Ask for confirmation
        confirm = QMessageBox().question(
            self,
            device_name,
            self.translator.get("device_delete_confirmation"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            defaultButton=QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        # Delete
        del self._vault["devices"][device_name]

        # Save
        self._vault_save()

        # Show confirmation
        text = self.translator.get("device_deleted").format(device_name=device_name)
        QMessageBox().information(self, text, text)

        # Refresh
        self._update_devices()

    def _update_devices(self) -> None:
        """Loads list of sync devices into menu"""
        # Remove all devices to delete
        while len(self.menu_delete_device.actions()) != 0:
            self.menu_delete_device.removeAction(self.menu_delete_device.actions()[0])
        self.menu_delete_device.update()

        if not self._vault or not self._vault.get("devices"):
            self.menu_delete_device.setEnabled(False)
            return

        # Load list of devices
        for device_name in self._vault.get("devices", {}).keys():
            logging.debug(f"Adding device delete: {device_name}")
            action = QAction(device_name, self)
            action.triggered.connect(functools.partial(self._delete_device, device_name))
            self.menu_delete_device.addAction(action)
        self.menu_delete_device.update()
        self.menu_delete_device.setEnabled(True)

    def _open_vault(self, path: str or None = None, close_before: bool = True) -> None:
        """Opens vault from path

        Args:
            path (str or None, optional): None to ask user. Defaults to None
            close_before (bool, optional): close current vault before loading a new one. Defaults to True

        """
        # Ask user for vault
        if not path:
            items = [path_name[1] for path_name in self._vaults]
            index = combo_box_dialog(self, self.translator.get("select_vault"), items)
            path = self._vaults[index][0] if index is not None else None

        # User canceled selection
        if not path:
            return

        # Close current vault
        if close_before:
            self._close_vault()

        # Load
        if not self._vault:
            logging.debug(f"Loading vault from {path}")
            try:
                with open(path, "r", encoding="utf-8") as file:
                    self._vault = json.loads(file.read())

                # Ask for master password instead of mnemonic
                master_password = None
                if self._vault.get("mnemonic_encrypted"):
                    dialog = QInputDialog(self)
                    dialog.setWindowTitle(self.translator.get("encrypt_plain_password_use_title"))
                    dialog.setLabelText(self.translator.get("encrypt_plain_password_use_label"))
                    dialog.setCancelButtonText(self.translator.get("use_mnemo_instead"))
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        master_password = dialog.textValue()
                        if not master_password:
                            logging.debug("No master password provided")
                            return

                # Ask for mnemonic
                if not master_password:
                    mnemonic = self.mnemonic_dialog.exec(
                        self._vault["name"], self.translator.get("open_vault_mnemonic"), random=False
                    )
                    if mnemonic is None:
                        logging.debug("No mnemonic phrase provided")
                        return

                # Try to build entropy
                try:
                    # Use master password to decrypt mnemonic (POSSIBLY NOT SAFE)
                    if master_password:
                        master_password_hash = hashlib.sha256(
                            hashlib.sha256(master_password.encode("utf-8")).digest()
                        ).digest()
                        mnemo_key = master_password_hash[-16:]

                        # Decrypt mnemonic
                        iv = base64.b64decode(self._vault["mnemonic_encrypted_iv"].encode("utf-8"))
                        cipher = AES.new(mnemo_key, AES.MODE_CBC, iv=iv)
                        mnemonic_encrypted = base64.b64decode(self._vault["mnemonic_encrypted"].encode("utf-8"))
                        mnemonic_decrypted = cipher.decrypt(mnemonic_encrypted)
                        mnemonic_unpadded = Padding.unpad(mnemonic_decrypted, AES.block_size).decode("utf-8")
                        mnemonic = mnemonic_unpadded.split(" ")

                    # Convert to entropy
                    entropy = self.mnemonic_dialog.mnemo.to_entropy(mnemonic)

                except Exception as e:
                    logging.error("Unable to decrypt mnemonic", exc_info=e)
                    self._error_wrapper(self.translator.get("error_wrong_master_password"), exception_text=str(e))
                    self._close_vault()
                    return

                # Save mnemonic and
                self._vault["mnemonic"] = mnemonic
                self._vault["entropy"] = entropy

                # Decrypt entries
                entries_decrypted = []
                entries = self._vault.get("entries", [])
                for entry in entries:
                    # Extract data
                    unique_id = entry.get("id")
                    encrypted = entry.get("enc")
                    iv = entry.get("iv")
                    if not unique_id or not encrypted or not iv:
                        continue

                    entry_decrypted = decrypt_entry(entry, self._vault["entropy"])
                    if not entry_decrypted:
                        raise Exception(f"Unable to decrypt {unique_id} entry")

                    # Add
                    entries_decrypted.append(entry_decrypted)

                self._vault["entries_decrypted"] = entries_decrypted

            except Exception as e:
                logging.error("Error opening vault", exc_info=e)
                self._error_wrapper(
                    self.translator.get("error_open_vault_title"),
                    self.translator.get("error_open_vault_description"),
                    exception_text=str(e),
                )
                self._close_vault()
                return

        self._vault["path"] = path

        # Move to the top and reload recent vaults
        index = self._vaults.index((path, self._vault["name"]))
        if index != 0:
            path, name = self._vaults.pop(index)
            self._vaults.insert(0, (path, name))
            self.config_manager.set("vaults", [path_name[0] for path_name in self._vaults])
            self._update_vaults()
        else:
            path, name = self._vaults[0]

        # Load sync devices
        self._update_devices()

        # Add rows
        self._render_vault_entries()

        # Show and enable vault controls
        self._show_hide(show=True)

    def _create_vault(self, from_device: bool = False) -> None:
        """Asks user for name, mnemonic and creates vault
        if from_device is True will ask user for import

        Args:
            from_device (bool, optional): True to import instead of just creating new. Defaults to False
        """
        # Close vault
        self._close_vault()

        # Ask user for vault name
        name = QInputDialog().getText(
            self,
            self.translator.get(f"{'import' if from_device else 'new'}_vault_title"),
            self.translator.get("new_vault_label"),
        )
        if not name or not name[0] or not name[0].strip():
            logging.debug("No name provided")
            return

        name = name[0].strip()

        # Check if exists
        for _, name_ in self._vaults:
            if name == name_:
                self._error_wrapper(self.translator.get("error_vault_exists").format(name=name))
                return

        self._vault["name"] = name

        # Ask for mnemonic
        text = self.translator.get("open_vault_mnemonic") if from_device else self.translator.get("new_vault_mnemonic")
        mnemonic = self.mnemonic_dialog.exec(name, text)
        if mnemonic is None:
            logging.debug("No mnemonic phrase provided")
            return

        self._vault["mnemonic"] = mnemonic

        # Ask if user wants to use master password to encrypt mnemonic phrase
        confirm = QMessageBox().question(
            self,
            self.translator.get("encrypt_plain_password_ask_title"),
            self.translator.get("encrypt_plain_password_ask_text"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            defaultButton=QMessageBox.StandardButton.No,
        )

        # Ask user for a master password
        master_password = None
        if confirm == QMessageBox.StandardButton.Yes:
            master_password = QInputDialog().getText(
                self,
                self.translator.get("encrypt_plain_password_create_title"),
                self.translator.get("encrypt_plain_password_create_label"),
                text="".join([secrets.choice(PASSWORD_DATASET) for _ in range(16)]),
            )
            if not master_password or not master_password[0]:
                logging.debug("No master password provided")
                self._error_wrapper(
                    self.translator.get("encrypt_plain_no_password_title"),
                    self.translator.get("encrypt_plain_no_password_text"),
                )
                self._close_vault()
                return

            master_password = master_password[0]

        # Temporally save entropy (actual master key)
        self._vault["entropy"] = self.mnemonic_dialog.mnemo.to_entropy(mnemonic)

        # Use master password to encrypt mnemonic (POSSIBLY NOT SAFE)
        if master_password:
            master_password_hash = hashlib.sha256(hashlib.sha256(master_password.encode("utf-8")).digest()).digest()
            mnemo_key = master_password_hash[-16:]

            # Encrypt and save mnemonic (POSSIBLY NOT SAFE)
            iv = secrets.token_bytes(16)
            cipher = AES.new(mnemo_key, AES.MODE_CBC, iv=iv)
            mnemonic_padded = Padding.pad(" ".join(mnemonic).encode("utf-8"), AES.block_size)
            mnemonic_encrypted = cipher.encrypt(mnemonic_padded)
            self._vault["mnemonic_encrypted"] = base64.b64encode(mnemonic_encrypted).decode("utf-8")
            self._vault["mnemonic_encrypted_iv"] = base64.b64encode(iv).decode("utf-8")

        # Ask for data (import)
        if from_device:
            if not self._sync_from(save=False, rerender=False):
                logging.error("Import error")
                self._close_vault()
                return

        # Save without secrets
        filepath = self._vault_save()

        # Save to config
        self._vaults.append((filepath, name))
        self.config_manager.set("vaults", [path_name[0] for path_name in self._vaults])

        # Show confirmation
        text = self.translator.get("vault_created").format(name=name)
        QMessageBox().information(self, text, text)

        # Reload recent vaults
        self._update_vaults()

        # Open this vault
        self._open_vault(filepath, close_before=False)

    def _vault_save(self, filepath: str or None = None) -> str or None:
        """Saves current vault as filepath without secret keys

        Args:
            filepath (str or None, optional): None to generate safe filepath. Defaults to None

        Returns:
            str or None: path to saved file or None in case of error
        """
        if not self._vault:
            return

        # Stop timer
        if self._save_timer.isActive():
            self._save_timer.stop()

        # Show saving text
        self.status_bar.showMessage(self.translator.get("saving"))

        try:
            # Create vaults dir if needed
            vaults_dir = os.path.join(self.working_dir, "vaults")
            if not os.path.exists(vaults_dir):
                logging.debug(f"Creating {vaults_dir} directory")
                os.makedirs(vaults_dir)

            # Build safe filepath
            if not filepath:
                filename = "".join(c for c in self._vault["name"] if c.isalpha() or c.isdigit() or c == " ").rstrip()
                filename += ".json"
                filepath = os.path.join(vaults_dir, filename)

            # Make copy
            vault_ = self._vault.copy()

            # Delete secret fields
            if "mnemonic" in vault_:
                del vault_["mnemonic"]
            if "entropy" in vault_:
                del vault_["entropy"]
            if "path" in vault_:
                del vault_["path"]
            if "entries_decrypted" in vault_:
                del vault_["entries_decrypted"]

            # Add version info
            vault_["version"] = __version__

            # Save
            logging.debug(f"Saving vault as {filepath}")
            with open(filepath, "w+", encoding="utf-8") as file:
                file.write(json.dumps(vault_, ensure_ascii=False, indent=4))

            return filepath

        except Exception as e:
            logging.error("Error saving vault", exc_info=e)
            self._error_wrapper(self.translator.get("error_save"), description=str(e))

        # Hide saving text after a bit
        finally:
            self._saving_timer.start(SAVING_TEXT_LABEL_DURATION)

        return None

    def _vault_action(self, action: Dict, save: bool = True, rerender: bool = True) -> bool:
        """Applies action to the current vault

        Args:
            action (Dict): action as dictionary (encrypted or not)
            save (bool, optional): save vault after. Defaults to True
            rerender (bool, optional): rerender vault after. Defaults to True

        Returns:
            bool: True in case of success or nothing to do, False if failed
        """
        if not self._vault:
            return True

        act = action.get("act")
        if not act:
            return True

        try:
            # Add or sync action
            if act == "new" or act == "add" or act == "sync":
                # Generate unique ID
                if "id" not in action:
                    action["id"] = secrets.token_urlsafe(8)

                # Decrypt action data if needed
                if "enc" in action and "iv" in action:
                    entry_decrypted = decrypt_entry(action, self._vault["entropy"])
                else:
                    entry_decrypted = action.copy()
                    del entry_decrypted["act"]

                # Try to find decrypted entry (to update it and grab other keys for encryption)
                index_decrypted, _ = self._id_to_entry(action["id"], "entries_decrypted")

                # Create new element
                if index_decrypted == -1:
                    if "entries_decrypted" not in self._vault:
                        self._vault["entries_decrypted"] = []
                    self._vault["entries_decrypted"].insert(0, entry_decrypted)
                    index_decrypted = 0

                # Update entry
                else:
                    for key in ["site", "user", "pass", "notes"]:
                        if key in entry_decrypted:
                            self._vault["entries_decrypted"][index_decrypted][key] = entry_decrypted[key]

                # Keep existing keys
                entry_to_encrypt = entry_decrypted.copy()
                for key in ["site", "user", "pass", "notes"]:
                    if key in self._vault["entries_decrypted"][index_decrypted]:
                        entry_to_encrypt[key] = self._vault["entries_decrypted"][index_decrypted][key]

                # Encrypt again (to rotate IV)
                entry_encrypted = encrypt_entry(entry_to_encrypt, self._vault["entropy"])
                if not entry_encrypted:
                    return False

                # Try to find encrypted entry (to update it)
                index_encrypted, _ = self._id_to_entry(action["id"])

                # Create new element
                if index_encrypted == -1:
                    if "entries" not in self._vault:
                        self._vault["entries"] = []
                    self._vault["entries"].insert(0, entry_encrypted)

                # Update entry
                else:
                    self._vault["entries"][index_encrypted]["enc"] = entry_encrypted["enc"]
                    self._vault["entries"][index_encrypted]["iv"] = entry_encrypted["iv"]

            # Delete entry action
            elif act == "delete":
                unique_id = action.get("id")
                self._delete_entry(unique_id, ask_confirmation=False, save=False, rerender=False)

            # Wrong action
            else:
                logging.warning(f"Unknown action: {act}")

        except Exception as e:
            logging.error("Error execution action", exc_info=e)
            self._error_wrapper(self.translator.get("error_action"), exception_text=str(e))
            return False

        # Save vault
        if save:
            self._vault_save(filepath=self._vault.get("path"))

        # Update GUI
        if rerender:
            self._render_vault_entries()

        return True

    def _render_vault_entries(self, filter_: str or None = None) -> None:
        """Removes all entries and renders them again

        Args:
            filter_ (str or None, optional): search box text. Defaults to None
        """
        if not self._vault:
            return

        # Remove all entries
        clear_layout(self.passwords_container)

        # Run full garbage collection (just in case)
        gc.collect()

        # Render each entry
        for i, entry in enumerate(self._vault.get("entries_decrypted", [])):
            unique_id = entry["id"]
            site = entry.get("site", "")
            username = entry.get("user", "")
            password = entry.get("pass", "")
            notes = entry.get("notes", "")

            # Skip if needed
            if filter_ and filter_ not in site and filter_ not in username and filter_ not in notes:
                continue

            # Row layout
            layout = QHBoxLayout()

            # ID
            number = QLabel()
            number.setText(str(i + 1))
            number.setMinimumWidth(40)
            number.setMaximumWidth(40)
            layout.addWidget(number)

            # Site
            site_ = QLineEdit()
            site_.setText(site)
            site_.setMaxLength(LINE_EDIT_MAX_LENGTH)
            site_.textEdited.connect(functools.partial(self._entry_text_changed, unique_id, "site", site_))
            layout.addWidget(site_)

            # Username
            username_ = QLineEdit()
            username_.setText(username)
            username_.setMaxLength(LINE_EDIT_MAX_LENGTH)
            username_.textEdited.connect(functools.partial(self._entry_text_changed, unique_id, "user", username_))
            layout.addWidget(username_)

            # Password
            password_ = QLineEdit()
            password_.setEchoMode(QLineEdit.EchoMode.Password)
            password_.setText(password)
            password_.setMaxLength(LINE_EDIT_MAX_LENGTH)
            password_.textEdited.connect(functools.partial(self._entry_text_changed, unique_id, "pass", password_))
            layout.addWidget(password_)

            # Show / hide password button
            btn_show_hide = QPushButton()
            btn_show_hide.setIcon(QtGui.QIcon(ICON_SHOW))
            btn_show_hide.setMinimumWidth(40)
            btn_show_hide.setMaximumWidth(40)
            btn_show_hide.clicked.connect(functools.partial(self._show_hide_password, password_, btn_show_hide))
            layout.addWidget(btn_show_hide)

            # Copy password button
            btn_copy = QPushButton()
            btn_copy.setIcon(QtGui.QIcon(ICON_COPY))
            btn_copy.setMinimumWidth(40)
            btn_copy.setMaximumWidth(40)
            btn_copy.clicked.connect(functools.partial(self._copy_password, password_))
            layout.addWidget(btn_copy)

            # Notes
            notes_ = QLineEdit()
            notes_.setText(notes)
            notes_.setMaxLength(LINE_EDIT_MAX_LENGTH)
            notes_.textEdited.connect(functools.partial(self._entry_text_changed, unique_id, "notes", notes_))
            layout.addWidget(notes_)

            # Delete button
            btn_delete = QPushButton()
            btn_delete.setIcon(QtGui.QIcon(ICON_DELETE))
            btn_delete.setMinimumWidth(40)
            btn_delete.setMaximumWidth(40)
            btn_delete.clicked.connect(functools.partial(self._delete_entry, unique_id, True, True, True))
            layout.addWidget(btn_delete)

            # Add row to the main password container
            self.passwords_container.addLayout(layout)

    def _copy_password(self, password_line_edit: QLineEdit) -> None:
        """Copies password to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.clear(mode=clipboard.Mode.Clipboard)
        clipboard.setText(password_line_edit.text(), mode=clipboard.Mode.Clipboard)

    def _show_hide_password(self, password_line_edit: QLineEdit, btn_show_hide: QPushButton) -> None:
        """Toggles password echo mode and show/hide button icon"""
        if password_line_edit.echoMode() == QLineEdit.EchoMode.Password:
            password_line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            btn_show_hide.setIcon(QtGui.QIcon(ICON_HIDE))
        else:
            password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            btn_show_hide.setIcon(QtGui.QIcon(ICON_SHOW))

    def _entry_text_changed(self, unique_id: str, field: str, line_edit: QLineEdit) -> None:
        """Updates data in self._vault and starts timer for saving text

        Args:
            unique_id (str): entry ID
            field (str): "site", "user", "pass" or "notes"
            line_edit (QLineEdit): element of which text to save
        """
        # Update but not save
        self._vault_action({"id": unique_id, "act": "sync", field: line_edit.text()}, save=False, rerender=False)

        # Start save timer
        if self._save_timer.isActive():
            self._save_timer.stop()
        self._save_timer.start(SAVE_AFTER_EDIT_MS)
        self.status_bar.showMessage(self.translator.get("saving"))

    def _sync_to(self, clean_device: bool = True) -> None:
        """Asks user to select device or create a new one, calculates difference and sends actions as QR codes

        Args:
            clean_device (bool, optional): True to just export without selecting a new device. Defaults to True
        """
        if not self._vault or not self._vault.get("entries"):
            return

        device_entries = []
        device_name = None

        # Ask user for existing devices or create a new one
        if not clean_device:
            devices = list(self._vault.get("devices", {}).keys())
            if len(devices) != 0:
                devices.append(self.translator.get("new_device"))
                device_index = combo_box_dialog(self, self.translator.get("select_device"), devices)
                if device_index is None:
                    logging.debug("No device provided")
                    return
                if device_index < len(devices) - 1:
                    device_name = devices[device_index]
                    logging.debug(f"Selected device: {device_name}")
                    device_entries = self._vault.get("devices", {})[device_name]

            # Create a new device
            if not device_name:
                device_name_ = QInputDialog().getText(
                    self,
                    self.translator.get("new_device_title"),
                    self.translator.get("new_device_label"),
                )
                if not device_name_ or not device_name_[0].strip():
                    logging.debug("No device name provided")
                    return

                device_name = device_name_[0].strip()

                # Show mnemonic
                self._show_mnemonic()

            logging.debug(f"Current number of entries on {device_name}: {len(device_entries)}")

        # Pure export -> show mnemonic
        else:
            self._show_mnemonic()

        # Build lists of unique IDs
        device_entry_ids = []
        for device_entry in device_entries:
            device_entry_ids.append(device_entry["id"])
        entry_ids = []
        for entry in self._vault.get("entries", {}):
            entry_ids.append(entry["id"])

        # Build list of sync actions starting from delete entries
        actions = []
        for device_entry_id in device_entry_ids:
            if device_entry_id not in entry_ids:
                actions.append({"act": "delete", "id": device_entry_id})

        # Add non-existing entries actions and sync actions from bottom to top
        entry_ids.reverse()
        for entry_id in entry_ids:
            _, entry = self._id_to_entry(entry_id)
            _, device_entry = self._id_to_entry(entry_id, entries=device_entries)
            if device_entry and device_entry == entry:
                continue

            action = {"act": "add" if entry_id not in device_entry_ids else "sync", "id": entry_id}

            for key, value in entry.items():
                action[key] = value
            actions.append(action)

        logging.debug(f"Actions to execute: {actions}")

        # Check if we have anything to sync
        if len(actions) == 0:
            if device_name:
                text = self.translator.get("nothing_to_sync").format(device_name=device_name)
            else:
                text = self.translator.get("nothing_to_export")
            QMessageBox().information(self, text, text)
            return

        # Show QR codes (blocking)
        self.view_dialog.exec(
            self.translator.get("qr_viewer_actions_title"),
            self.translator.get("qr_viewer_actions_description").format(
                device_name=device_name if device_name else ""
            ),
            actions=actions,
        )

        # Save
        if device_name:
            if "devices" not in self._vault:
                self._vault["devices"] = {}
            if device_name not in self._vault["devices"]:
                self._vault["devices"][device_name] = []

            self._vault["devices"][device_name].clear()
            for entry in self._vault.get("entries", {}):
                self._vault["devices"][device_name].append(entry.copy())
            self._vault_save(filepath=self._vault.get("path"))

        # Done
        if device_name:
            text = self.translator.get("synced_with").format(device_name=device_name)
        else:
            text = self.translator.get("exported")
        QMessageBox().information(self, text, text)

        # Refresh
        self._update_devices()

    def _delete_entry(
        self, unique_id: str, ask_confirmation: bool = True, save: bool = True, rerender: bool = True
    ) -> None:
        """Removes one row

        Args:
            unique_id (str): ID if entry to remove
            ask_confirmation (bool, optional): ask user before removing. Defaults to True
            save (bool, optional): save vault after. Defaults to True
            rerender (bool, optional): re-render vault after. Defaults to True
        """
        if not self._vault or not unique_id:
            return

        try:
            # Try to find decrypted entry
            index_decrypted, entry_decrypted = self._id_to_entry(unique_id, "entries_decrypted")
            if index_decrypted == -1 or not entry_decrypted:
                return

            # Ask user if needed
            if ask_confirmation:
                title = entry_decrypted.get("site")
                if not title:
                    title = entry_decrypted.get("user")
                if not title:
                    title = str(index_decrypted + 1)
                confirm = QMessageBox().question(
                    self,
                    title,
                    self.translator.get("entry_delete"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    defaultButton=QMessageBox.StandardButton.No,
                )
                if confirm != QMessageBox.StandardButton.Yes:
                    return

            # Delete from decrypted
            del self._vault["entries_decrypted"][index_decrypted]

            # Delete from encrypted
            index_encrypted, _ = self._id_to_entry(unique_id)
            if index_encrypted != -1:
                del self._vault["entries"][index_encrypted]

            # Save vault
            if save:
                self._vault_save(filepath=self._vault.get("path"))

            # Update GUI
            if rerender:
                self._render_vault_entries()

        except Exception as e:
            logging.error("Error deleting entry", exc_info=e)
            self._error_wrapper(self.translator.get("error_delete_entry"), description=str(e))

    @QtCore.pyqtSlot()
    def _close_vault(self) -> None:
        """Closes current vault"""
        logging.debug("Closing current vault")

        # Clear vault dictionary
        self._vault.clear()

        # Remove all entries
        clear_layout(self.passwords_container)

        # Run full garbage collection (just in case)
        gc.collect()

        # Hide and disable vault controls
        self._show_hide(show=False)

    def _rename_vault(self) -> None:
        """Asks user for a new vault name and renames vault by deleting old file and saving a new one"""
        try:
            name_ = QInputDialog().getText(
                self, self._vault["name"], self.translator.get("rename_vault"), text=self._vault["name"]
            )
            if name_ and name_[0].strip() and name_[0].strip() != self._vault["name"]:
                name_new = name_[0].strip()
                name_old = self._vault["name"]
                path_old = self._vault["path"]
                logging.debug("Deleting old vault file")
                os.remove(path_old)

                logging.debug(f"New vault name: {name_new}")
                self._vault["name"] = name_new

                path_new = self._vault_save()
                self._vault["path"] = path_new
                logging.debug(f"New vault path: {path_new}")

                index = self._vaults.index((path_old, name_old))
                self._vaults[index] = (path_new, name_new)

                self.config_manager.set("vaults", [path_name[0] for path_name in self._vaults])
                self._update_vaults()

                text = self.translator.get("vault_renamed").format(name_old=name_old, name_new=name_new)
                QMessageBox().information(self, text, text)

        except Exception as e:
            logging.error("Error renaming vault", exc_info=e)
            self._error_wrapper(self.translator.get("error_rename"), description=str(e))

    def _delete_vault(self) -> None:
        """Asks user for confirmation and deletes current vault"""
        try:
            name_ = QInputDialog().getText(self, self._vault["name"], self.translator.get("delete_vault_confirmation"))
            if name_ and name_[0] == self._vault["name"]:
                logging.debug("Deleting vault")
                os.remove(self._vault["path"])
                self.config_manager.set(
                    "vaults", [path_name[0] for path_name in self._vaults if path_name[0] != self._vault["path"]]
                )
                self._close_vault()
                self._update_vaults()
                text = self.translator.get("vault_deleted").format(name=name_[0])
                QMessageBox().information(self, text, text)

        except Exception as e:
            logging.error("Error deleting vault", exc_info=e)
            self._error_wrapper(self.translator.get("error_delete"), description=str(e))

    def _id_to_entry(
        self, unique_id: str, entries_key: str = "entries", entries: Dict or None = None
    ) -> Tuple[int, Dict or None]:
        """Finds entry and it's current index by unique_id

        Args:
            unique_id (str): entry ID
            entries_key (str, optional): "entries" or "entries_decrypted". Defaults to "entries"
            entries (Dict or None, optional): entries to use instead of entries_key. Defaults to None

        Returns:
            Tuple[int, Dict or None]: (index, entry as dictionary) or (-1, None) if not found
        """
        if entries is None:
            entries = self._vault.get(entries_key, [])
        return next(((i, item) for (i, item) in enumerate(entries) if item["id"] == unique_id), (-1, None))

    def _show_hide(self, show: bool) -> None:
        """Shows (and enable) or hides (and disable) some elements

        Args:
            show (bool): True in case of opened vault, False if closed
        """
        # Hide start message
        if show:
            self.lb_start.hide()
        else:
            self.lb_start.show()

        # Enable close, rename and delete action
        self.act_close.setEnabled(show)
        self.act_rename.setEnabled(show)
        self.act_delete.setEnabled(show)
        self.act_export.setEnabled(show)

        # Disable delete device (but not enable it)
        if not show:
            self.menu_delete_device.setEnabled(False)

        # Show or hide column titles
        if show:
            self.lb_site.show()
            self.lb_username.show()
            self.lb_password.show()
            self.lb_notes.show()
        else:
            self.lb_site.hide()
            self.lb_username.hide()
            self.lb_password.hide()
            self.lb_notes.hide()

        # Show and enable or hide and disable other elements
        if show:
            self.btn_entry_add.show()
            self.lb_search.show()
            self.le_search.show()
            self.btn_search.show()
            self.btn_show_mnemonic.setEnabled(True)
            self.btn_sync_to.setEnabled(True)
            self.btn_sync_from.setEnabled(True)
        else:
            self.btn_entry_add.hide()
            self.lb_search.hide()
            self.le_search.hide()
            self.btn_search.hide()
            self.btn_show_mnemonic.setEnabled(False)
            self.btn_sync_to.setEnabled(False)
            self.btn_sync_from.setEnabled(False)

    def _error_wrapper(self, title: str, description: str or None = None, exception_text: str or None = None) -> None:
        """Shows error message

        Args:
            title (str): dialog title and main text
            description (str or None, optional): dialog description. Defaults to None
            exception_text (str or None, optional): detailed text. Defaults to None
        """
        error_msg = QMessageBox(self)
        error_msg.setIcon(QMessageBox.Icon.Critical)
        error_msg.setText(title)
        error_msg.setWindowTitle(title)
        if description:
            error_msg.setInformativeText(description)
        if exception_text:
            error_msg.setDetailedText(exception_text)
        error_msg.exec()

    @QtCore.pyqtSlot()
    def _report_issue(self) -> None:
        """Tries to open issues URL in default browser. Also shows information dialog"""
        try:
            webbrowser.open("https://github.com/F33RNI/PetalVault/issues", new=2, autoraise=True)
        except Exception as e:
            logging.warning(f"Unable to open URL: {e}")
        finally:
            QMessageBox().information(
                self, self.translator.get("report_issue"), "https://github.com/F33RNI/PetalVault/issues"
            )

    @QtCore.pyqtSlot()
    def _about(self) -> None:
        """Shows about message (see any language file for more info)"""
        about_msg = QMessageBox(self)
        about_msg.setIconPixmap(QtGui.QPixmap(ICON_FILE).scaled(64, 64))
        about_msg.setText(f"PetalVault v{__version__}")
        about_msg.setInformativeText(self.translator.get("about"))
        about_msg.setWindowTitle(f"PetalVault v{__version__}")
        about_msg.exec()
