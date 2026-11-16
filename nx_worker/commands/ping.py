"""NX availability probe."""

import os
import platform
from typing import Any


def run(inputs: dict[str, Any], options: dict[str, Any], log: list[str]) -> dict[str, Any]:
    del inputs, options
    import NXOpen

    NXOpen.Session.GetSession()
    log.append("NXOpen session acquired")
    return {
        "nx_version": os.environ.get("UGII_VERSION"),
        "python_version": platform.python_version(),
    }
