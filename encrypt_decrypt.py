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
import hashlib
import json
import logging
import secrets
import zlib
from typing import Dict

from Crypto.Cipher import AES
from Crypto.Util import Padding

from _version import __version__


def decrypt_entry(encrypted: Dict, entropy: bytes) -> Dict or None:
    """Decrypts and decompresses dictionary data

    Args:
        encrypted (Dict): dictionary that contains "id", "enc" and "iv" keys
        entropy (bytes): AES key

    Returns:
        Dict or None: decrypted dictionary or None in case of error
    """
    try:
        # Decrypt
        iv_bytes = base64.b64decode(encrypted["iv"].encode("utf-8"))
        entry_encrypted = base64.b64decode(encrypted["enc"].encode("utf-8"))
        cipher = AES.new(entropy, AES.MODE_CBC, iv=iv_bytes)
        entry_decrypted = cipher.decrypt(entry_encrypted)
        entry_unpadded = Padding.unpad(entry_decrypted, AES.block_size)

        # Decompress
        entry_uncompressed = zlib.decompress(entry_unpadded)

        # Split checksum
        entry_bytes = entry_uncompressed[:-16]
        entry_checksum_original = entry_uncompressed[-16:]

        # Verify checksum
        entry_checksum = hashlib.md5(entry_bytes).digest()
        if entry_checksum_original != entry_checksum:
            raise Exception("Checksum verification error")

        # Convert to dictionary
        entry_dict = json.loads("{" + entry_bytes.decode("utf-8") + "}")

        # Check ID
        if encrypted["id"] != entry_dict["id"]:
            raise Exception("Unique IDs don't match")

        return entry_dict

    except Exception as e:
        logging.error(f"Error decrypting {encrypted.get('id', '')} entry", exc_info=e)

    return None


def encrypt_entry(decrypted: Dict, entropy: bytes) -> Dict or None:
    """Compresses and encrypts dictionary data

    Args:
        decrypted (Dict): decrypted dictionary. Must contains "id" key
        entropy (bytes): AES key

    Returns:
        Dict or None: encrypted dictionary (with "id", "enc" and "iv" keys) or None in case of error
    """
    try:
        # Convert to bytes and calculate checksum
        entry_str = json.dumps(decrypted, separators=(",", ":"), ensure_ascii=False)[1:][:-1]
        entry_bytes = entry_str.encode("utf-8")
        entry_checksum = hashlib.md5(entry_bytes).digest()
        entry_bytes += entry_checksum

        # Compress and pad data
        entry_compressed = zlib.compress(entry_bytes, level=9)
        entry_padded = Padding.pad(entry_compressed, AES.block_size)

        # Encrypt
        iv_bytes = secrets.token_bytes(16)
        cipher = AES.new(entropy, AES.MODE_CBC, iv=iv_bytes)
        entry_encrypted = cipher.encrypt(entry_padded)

        # Convert to base64
        enc = base64.b64encode(entry_encrypted).decode("utf-8")
        iv = base64.b64encode(iv_bytes).decode("utf-8")

        return {"id": decrypted["id"], "enc": enc, "iv": iv}

    except Exception as e:
        logging.error(f"Error encrypting {decrypted.get('id', '')} entry", exc_info=e)

    return None
