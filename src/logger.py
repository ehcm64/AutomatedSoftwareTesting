import sys
from datetime import datetime
from pathlib import Path
from loguru import logger

def setup_logging() -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = Path(f"runs/run_{timestamp}")
    run_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stdout,
        filter=lambda record: len(record["extra"]) == 0,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    logger.add(
        run_dir / "fuzzer.log",
        filter=lambda record: len(record["extra"]) == 0,
        level="DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    logger.add(
        run_dir / "queries.log",
        filter=lambda record: "query" in record["extra"],
        format="{message}\n"
    )
    return run_dir