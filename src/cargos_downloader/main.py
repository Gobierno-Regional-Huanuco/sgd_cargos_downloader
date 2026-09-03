import faulthandler
import sys
from pathlib import Path

from cargos_downloader.ui import run_app

CRASH_LOG = Path.home() / ".sgd_cargos_downloader" / "crash.log"


def main() -> int:
    CRASH_LOG.parent.mkdir(parents=True, exist_ok=True)
    crash_file = CRASH_LOG.open("w", encoding="utf-8")
    faulthandler.enable(file=crash_file, all_threads=True)
    return run_app()


if __name__ == "__main__":
    sys.exit(main())
