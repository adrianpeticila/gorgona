"""Entry point for executing gorgona as a module: python -m gorgona."""

import sys
from gorgona.cli import main

if __name__ == "__main__":
    sys.exit(main())
