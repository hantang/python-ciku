import sys
import logging

from .cli import main

if __name__ == "__main__":
    fmt = "%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s"
    logging.basicConfig(level=logging.WARNING, format=fmt)

    sys.exit(main())
