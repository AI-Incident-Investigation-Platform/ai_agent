import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def main(full: bool) -> int:
    if any(shutil.which(command) is None for command in ("initdb", "pg_ctl")):
        print("Нужен локальный PostgreSQL с initdb и pg_ctl в PATH.", file=sys.stderr)
        return 1
    with TemporaryDirectory(prefix="ai11pg-", dir="/tmp") as directory:
        data = str(Path(directory) / "data")
        subprocess.run(
            [
                "initdb",
                "-D",
                data,
                "-A",
                "trust",
                "-U",
                "ai_demo",
                "--no-locale",
                "--encoding=UTF8",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "pg_ctl",
                "-D",
                data,
                "-l",
                str(Path(directory) / "postgres.log"),
                "-o",
                f"-h '' -k {directory}",
                "-w",
                "start",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        try:
            env = {
                **os.environ,
                "AI_AGENT_TEST_POSTGRES_DSN": (
                    f"host={directory} dbname=postgres user=ai_demo"
                ),
                "AI_AGENT_RUN_LIVE_LLM": "0",
            }
            args = (
                []
                if full
                else [
                    "-s",
                    "tests/integration/application/test_run_worker.py",
                ]
            )
            return subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-rs", *args],
                cwd=ROOT,
                env=env,
                check=False,
            ).returncode
        finally:
            subprocess.run(
                ["pg_ctl", "-D", data, "-m", "fast", "-w", "stop"],
                check=True,
                stdout=subprocess.DEVNULL,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    raise SystemExit(main(parser.parse_args().full))
