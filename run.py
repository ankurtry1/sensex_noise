from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sensex_noise.config import load_settings
from sensex_noise.services.engine import StrategyEngine


def main() -> None:
    settings = load_settings()
    engine = StrategyEngine(settings=settings)
    engine.run()


if __name__ == "__main__":
    main()
