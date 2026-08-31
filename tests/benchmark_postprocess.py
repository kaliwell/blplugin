# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

"""Small reproducible benchmark for mask Alpha edge processing."""

import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collection_mask_exporter.core.postprocess import _morph_alpha_array


for width, height in ((1920, 1080), (3840, 2160)):
    alpha = np.zeros(width * height, dtype=np.float32)
    alpha.reshape(height, width)[
        height // 4:3 * height // 4, width // 4:3 * width // 4
    ] = 1.0
    started = time.perf_counter()
    _morph_alpha_array(alpha, width, height, 1)
    elapsed = time.perf_counter() - started
    print(f"CMASK MORPH {width}x{height} +1: {elapsed:.4f}s")
