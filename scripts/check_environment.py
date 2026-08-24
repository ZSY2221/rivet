from __future__ import annotations

import platform

import cryptography
import matplotlib
import numpy
import pandas
import py_ecc
import torch
import torchvision

EXPECTED = {
    "torch": "2.5.1+cpu",
    "torchvision": "0.20.1+cpu",
    "numpy": "2.1.3",
    "pandas": "2.2.3",
    "matplotlib": "3.9.2",
    "py_ecc": "8.0.0",
    "cryptography": "43.0.3",
}


def main() -> None:
    python_version = platform.python_version()
    if not ((3, 10) <= tuple(map(int, python_version.split(".")[:2])) <= (3, 12)):
        raise RuntimeError(f"python={python_version}; required=3.10-3.12")
    versions = {
        "python": python_version,
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "numpy": numpy.__version__,
        "pandas": pandas.__version__,
        "matplotlib": matplotlib.__version__,
        "py_ecc": py_ecc.__version__,
        "cryptography": cryptography.__version__,
    }
    for name, expected in EXPECTED.items():
        if versions[name] != expected:
            raise RuntimeError(f"{name}={versions[name]}; required={expected}")
    for name, version in versions.items():
        print(f"{name}={version}")
    print(f"device={'cuda' if torch.cuda.is_available() else 'cpu'}")


if __name__ == "__main__":
    main()
