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

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt
from Crypto.Util import Padding

from _version import __version__

# CPU/Memory cost parameter for master key / password derivation
MASTER_KEY_COST = 2**16


def decrypt_entry(encrypted: dict[str, str], master_key: bytes) -> dict[str, str] | None:
    """Decrypts and decompresses dictionary data

    Args:
        encrypted (dict[str, str]): dictionary that contains "enc" and "iv" keys
        master_key (bytes): mnemonic entropy as AES key (16 bytes) for v<2.0.0 or derived key (32 bytes) for v>=2.0.0

    Returns:
        dict | None: decrypted dictionary or None in case of error
    """
    try:
        # Decrypt
        iv_bytes = base64.b64decode(encrypted["iv"].encode("utf-8"))
        entry_encrypted = base64.b64decode(encrypted["enc"].encode("utf-8"))
        cipher = AES.new(master_key, AES.MODE_CBC, iv=iv_bytes)
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

        # Check for ID key
        if "id" not in entry_dict:
            raise Exception('No "id" key')

        return entry_dict

    except Exception as e:
        logging.error(f"Error decrypting {encrypted.get('id', '')} entry", exc_info=e)

    return None


def encrypt_entry(decrypted: dict[str, str], master_key: bytes) -> dict[str, str] | None:
    """Compresses and encrypts dictionary data

    Args:
        decrypted (dict[str, str]): decrypted dictionary. Must contains "id" key
        master_key (bytes): mnemonic entropy as AES key (16 bytes) for v<2.0.0 or derived key (32 bytes) for v>=2.0.0

    Returns:
        dict[str, str] | None: encrypted dictionary (with "enc" and "iv" keys) or None in case of error
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
        cipher = AES.new(master_key, AES.MODE_CBC, iv=iv_bytes)
        entry_encrypted = cipher.encrypt(entry_padded)

        # Convert to base64
        enc = base64.b64encode(entry_encrypted).decode("utf-8")
        iv = base64.b64encode(iv_bytes).decode("utf-8")

        return {"enc": enc, "iv": iv}

    except Exception as e:
        logging.error(f"Error encrypting {decrypted.get('id', '')} entry", exc_info=e)

    return None


def encrypt_mnemonic(mnemonic: list[str], master_password: str) -> tuple[bytes, bytes, bytes]:
    """Encrypts mnemonic with master password

    Args:
        mnemonic (list[str]): mnemonic phrase to encrypt as list of words
        master_password (str): strong master password

    Returns:
        tuple[bytes, bytes, bytes]: (padded and encrypted mnemonic with checksum, 32B salt of scrypt, 16B IV of AES)
    """
    # Derive key from master password
    master_salt_1 = secrets.token_bytes(32)
    derived_key = scrypt(master_password.encode("utf-8"), master_salt_1, 32, N=MASTER_KEY_COST, r=8, p=1)

    # Convert mnemonic to str->bytes, add checksum and pad
    mnemonic_bytes = " ".join(mnemonic).encode("utf-8")
    checksum = hashlib.md5(mnemonic_bytes).digest()
    mnemonic_with_checksum = mnemonic_bytes + checksum
    mnemonic_padded = Padding.pad(mnemonic_with_checksum, AES.block_size)

    # Encrypt
    master_salt_2 = secrets.token_bytes(16)
    cipher = AES.new(derived_key, AES.MODE_CBC, iv=master_salt_2)
    mnemonic_encrypted = cipher.encrypt(mnemonic_padded)

    return mnemonic_encrypted, master_salt_1, master_salt_2


def decrypt_mnemonic(
    mnemonic_encrypted: bytes, master_password: str, master_salt_1: bytes, master_salt_2: bytes
) -> list[str]:
    """Decrypts mnemonic with master password

    Args:
        mnemonic_encrypted (bytes): padded and encrypted mnemonic with checksum
        master_password (str): strong master password
        master_salt_1 (bytes): 32 bytes salt of derived key
        master_salt_2 (bytes): 16 bytes IV of AES

    Raises:
        Exception: decrypt / check error

    Returns:
        list[str]: mnemonic phrase as list of words
    """
    # Derive key from master password
    derived_key = scrypt(master_password.encode("utf-8"), master_salt_1, 32, N=MASTER_KEY_COST, r=8, p=1)

    # Decrypt
    cipher = AES.new(derived_key, AES.MODE_CBC, iv=master_salt_2)
    mnemonic_decrypted = cipher.decrypt(mnemonic_encrypted)

    # Unpad and extract checksum
    mnemonic_unpadded = Padding.unpad(mnemonic_decrypted, AES.block_size)
    mnemonic_bytes = mnemonic_unpadded[:-16]
    mnemonic_checksum = mnemonic_unpadded[-16:]

    # Check
    checksum_new = hashlib.md5(mnemonic_bytes).digest()
    if checksum_new != mnemonic_checksum:
        raise Exception("Checksums are not equal! Wrong password?")

    # Convert to list of strings
    return mnemonic_bytes.decode("utf-8").split(" ")


def decrypt_mnemonic_old(mnemonic_encrypted: bytes, master_password: str, iv: bytes) -> list[str]:
    """Decrypts mnemonic in old way (below v2.0.0)

    Args:
        mnemonic_encrypted (bytes): padded and encrypted mnemonic
        master_password (str): strong master password
        iv (bytes): 16 bytes IV of AES

    Returns:
        list[str]: mnemonic phrase as list of words
    """
    # Convert password to 128 bit key
    master_password_hash = hashlib.sha256(hashlib.sha256(master_password.encode("utf-8")).digest()).digest()
    mnemo_key = master_password_hash[-16:]

    # Decrypt mnemonic
    cipher = AES.new(mnemo_key, AES.MODE_CBC, iv=iv)
    mnemonic_decrypted = cipher.decrypt(mnemonic_encrypted)
    mnemonic_unpadded = Padding.unpad(mnemonic_decrypted, AES.block_size)

    # Convert to list of strings
    return mnemonic_unpadded.decode("utf-8").split(" ")


def entropy_to_master_key(entropy: bytes, master_salt: bytes | None = None) -> tuple[bytes, bytes]:
    """Derives master key from entropy

    Args:
        entropy (bytes): 128-bit entropy from mnemonic
        salt (bytes | None, optional): existing salt (32-bytes) | None to generate a new one. Defaults to None

    Returns:
        tuple[bytes, bytes]: (32-bytes master key, 32 - bytes salt)
    """
    if master_salt is None:
        master_salt = secrets.token_bytes(32)
    master_key = scrypt(entropy, master_salt, 32, N=MASTER_KEY_COST, r=8, p=1)
    return master_key, master_salt
