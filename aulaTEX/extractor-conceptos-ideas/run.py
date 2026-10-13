from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fichador.cli import main as cli_main
from fichador.gui import main as gui_main

if __name__ == "__main__":
    if "--gui" in sys.argv:
        sys.argv.remove("--gui")
        gui_main()
    else:
        cli_main()
