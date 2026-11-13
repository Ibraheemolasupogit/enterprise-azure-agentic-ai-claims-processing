"""Stage A refuses serving: no cloud host, credentials or adapters are implemented."""

import argparse
import json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", choices=("api-ui", "mcp"), default="api-ui")
    parser.add_argument("--healthcheck", action="store_true")
    parser.parse_args()
    print(
        json.dumps(
            {
                "stage": "M23_A",
                "ready": False,
                "cloud_execution": "DISABLED",
                "reason": "cloud_host_and_adapters_not_implemented",
            },
            sort_keys=True,
        )
    )
    # No import/start of demo servers, no env-variable escape, no credential fallback.
    raise SystemExit(78)


if __name__ == "__main__":
    main()
