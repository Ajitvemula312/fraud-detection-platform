from __future__ import annotations

import shutil


def binary_available(name: str) -> bool:
    return shutil.which(name) is not None
