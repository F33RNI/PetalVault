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
import threading

import cv2
import numpy as np
from PyQt6 import QtCore, QtGui

from get_resource_path import get_resource_path

COLOR_OK = (190, 203, 106)
COLOR_ERROR = (136, 125, 219)

WORDLIST_FILE = get_resource_path("wordlist.txt")


class QRScannerThread(threading.Thread, QtCore.QObject):
    # See ScanDialog for more info
    set_image_signal = QtCore.pyqtSignal(QtGui.QImage)
    received_part_flag_signal = QtCore.pyqtSignal(tuple)
    finished_signal = QtCore.pyqtSignal()

    def __init__(self, camera_index: int, expected_data: str):
        """Initializes QRScannerThread instance

        Args:
            camera_index (int): ID of camera (use 0 for default camera)
            expected_data (str): "mnemonic" or "actions"
        """
        threading.Thread.__init__(self)
        QtCore.QObject.__init__(self)

        self._camera_index = camera_index
        self._expected_data = expected_data

        # Dialog result
        self.actions = []
        self.mnemonic = None
        self.exception = None

        # Load wordlist and Mnemonic instance for checking
        self._wordlist = []
        logging.debug(f"Loading words from {WORDLIST_FILE} file")
        with open(WORDLIST_FILE, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    self._wordlist.append(line)
        logging.debug(f"Loaded {len(self._wordlist)} words")

        self._exit_flag = False

    def run(self):
        """OpenCV scanning loop"""
        # Open camera and try to read the first frame
        logging.debug(f"Opening camera: {self._camera_index}")
        self.exception = None
        try:
            capture = cv2.VideoCapture(self._camera_index)
            ret, _ = capture.read()
            if not ret:
                raise Exception(f"Unable to open camera {self._camera_index}. Try to change camera index")

            # Initialize QR decoder
            logging.debug("Initializing QRCodeDetector instance")
            detector = cv2.QRCodeDetector()
            self._exit_flag = False
            while not self._exit_flag:
                # Read one frame
                ret, frame = capture.read()
                if not ret or frame is None:
                    raise Exception(f"Error reading frame from camera {self._camera_index}")

                data = None
                try:
                    # Read QR codes
                    data, points, _ = detector.detectAndDecode(frame)
                    if data:
                        color = COLOR_ERROR

                        # Decode actions (JSON)
                        if self._expected_data == "actions":
                            # "i": part index, "n": total parts, "acts": [{"act": sync, "id": 123, "iv": ., "enc": .}]
                            data_dict = json.loads("{" + data + "}")

                            # Check part (just in case)
                            part_idx = data_dict.get("i", 0)
                            parts_total = data_dict.get("n", 1)
                            if part_idx >= parts_total:
                                raise Exception("Wrong index or number of parts")

                            logging.debug(f"Received part {part_idx + 1} / {parts_total}")

                            # Add to the final list
                            for action in data_dict.get("acts", []):
                                if action not in self.actions:
                                    self.actions.append(action)

                            # Final part
                            if part_idx == parts_total - 1:
                                logging.debug("Received final part")
                                self._exit_flag = True

                            # Show progress
                            if parts_total != 1:
                                self.received_part_flag_signal.emit((part_idx, parts_total))

                        # Decode and check mnemonic phrase
                        elif self._expected_data == "mnemonic":
                            words = data.strip().lower().split(" ")

                            # For now, accept only 12-word mnemonic
                            if len(words) != 12:
                                raise Exception("Mnemonic phrase must be 12 words long")

                            # Check each word
                            for word in words:
                                if word not in self._wordlist:
                                    raise Exception(f"{word} is not a mnemonic phrase word")

                            # Seems OK
                            self.mnemonic = words
                            self._exit_flag = True

                        else:
                            raise Exception(
                                f'expected_data must be "actions" or "mnemonic", not {self._expected_data}'
                            )

                        # Use OK color because we was able to decode it
                        color = COLOR_OK
                except Exception as e:
                    logging.warning(f"Unable to read or parse QR-code data {data}: {e}. Wrong QR code?")

                # Draw bounding lines
                if data:
                    points = points.astype(np.int32)
                    _, _, width, height = cv2.boundingRect(points)
                    line_thickness = max(1, (width + height) // 2 // 30)
                    frame = cv2.polylines(frame, points.astype(np.int32), True, color, line_thickness, cv2.LINE_AA)

                # Convert to QImage and push to GUI
                image = QtGui.QImage(
                    frame,
                    frame.shape[1],
                    frame.shape[0],
                    frame.strides[0],
                    QtGui.QImage.Format.Format_BGR888,
                )
                self.set_image_signal.emit(image)

            # Cleanup
            logging.debug("Closing camera")
            capture.release()
            cv2.destroyAllWindows()
        except Exception as e:
            logging.error("Error capturing frame", exc_info=e)
            self.exception = e

        self.finished_signal.emit()

    def cancel(self):
        """Cancels running scanner
        (clears self._exit_flag) Call this to stop QR scanning thread
        """
        if self._exit_flag:
            return
        logging.debug("qr_scanner_thread cancel requested")
        self._exit_flag = True
