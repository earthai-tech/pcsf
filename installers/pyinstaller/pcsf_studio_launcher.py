"""Entry script that PyInstaller freezes into PCSF Studio."""

import sys

from pcsf.studio import main

if __name__ == "__main__":
    sys.exit(main())
