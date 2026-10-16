import argparse
import json
import sys
from pathlib import Path

from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.wiring_config import verify_wiring


def main():
    parser = argparse.ArgumentParser(
        description="Check Bob/Sophia/dashboard configuration alignment without exposing configured values or changing services."
    )
    for name in ("bob", "rei", "dashboard"):
        parser.add_argument("--" + name + "-env", type=Path, required=True)
    parser.add_argument("--allow-loopback", action="store_true")
    args = parser.parse_args()
    try:
        configs = []
        for path in (args.bob_env, args.rei_env, args.dashboard_env):
            with path.open() as source:
                content = source.read(65537)
            if len(content) > 65536:
                raise ValueError("Configuration budget exceeded")
            from io import StringIO

            configs.append(
                {
                    key: value or ""
                    for key, value in dotenv_values(
                        stream=StringIO(content), interpolate=False
                    ).items()
                }
            )
        report = verify_wiring(*configs, allow_loopback=args.allow_loopback)
    except (OSError, ValueError, TypeError):
        report = {
            "schema_version": 1,
            "status": "blocked",
            "issues": ["configuration_files_unavailable_or_invalid"],
        }
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report["status"] == "configuration_consistent" else 2


if __name__ == "__main__":
    raise SystemExit(main())
