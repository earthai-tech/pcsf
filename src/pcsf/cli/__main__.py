"""Entry point for ``python -m pcsf.cli``."""

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main())
