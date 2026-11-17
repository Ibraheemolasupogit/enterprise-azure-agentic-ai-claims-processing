"""Locked local build contract. No downloads, registry login, image push or Azure calls."""

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from deployment.foundation import FoundationError, load, pins, require
from deployment.supply_chain import (
    HEX,
    authenticate,
    base_evidence,
    clock,
    fields,
    glibc_version,
    local_record,
    source_inventory,
    validate_evidence,
)
from deployment.supply_chain import (
    file_hash as file_hash,
)
from deployment.supply_chain import (
    wheel_metadata as wheel_metadata,
)


def application_hash(root: Path) -> str:
    package = root / "src/claims_ai"
    return hashlib.sha256(
        b"".join(
            str(p.relative_to(package)).encode() + b"\0" + p.read_bytes()
            for p in sorted(package.rglob("*.py"))
        )
    ).hexdigest()


def artifact_path(directory: Path, record: dict[str, Any]) -> Path:
    path = local_record(directory, record)
    require(path.suffix == ".whl", "artifact_basename")
    return path


def validate_inputs(
    root: Path,
    manifest: Path,
    directory: Path,
    trusted_pin: str,
    *,
    trust: Path | None = None,
    trust_pin: str | None = None,
    now: int | None = None,
) -> dict[str, Any]:
    """Admit reviewed inputs only. No daemon access or build authorisation is returned."""
    try:
        return _validate_inputs(
            root,
            manifest,
            directory,
            trusted_pin,
            trust,
            trust_pin,
            clock() if now is None else now,
        )
    except FoundationError:
        raise
    except (
        KeyError,
        TypeError,
        ValueError,
        OSError,
        zipfile.BadZipFile,
        OverflowError,
        AttributeError,
        IndexError,
    ) as exc:
        raise FoundationError("malformed_supply_chain_evidence") from exc


def _validate_inputs(
    root: Path,
    manifest: Path,
    directory: Path,
    trusted_pin: str,
    trust: Path | None,
    trust_pin: str | None,
    now: int,
) -> dict[str, Any]:
    require(
        isinstance(trusted_pin, str)
        and HEX.fullmatch(trusted_pin) is not None
        and file_hash(manifest) == trusted_pin,
        "independent_input_manifest_pin",
    )
    value = load(manifest)
    require(value.get("status") == "REVIEWED_LOCAL_BUILD_INPUTS", "linux_inputs_pending")
    require(value.get("format") == "m23-linux-build-inputs-v2", "build_input_version")
    fields(
        value,
        {
            "format",
            "status",
            "platform",
            "python_minor",
            "network_access",
            "registry_push_allowed",
            "base_image",
            "base_image_review",
            "source_date_epoch",
            "runtime_pins",
            "expected_application_source_sha256",
            "source_files",
            "dependency_wheels",
            "project_wheel",
            "evidence",
            "review",
        },
        "build_manifest_fields",
    )
    require(type(now) is int and now > 0, "review_clock")
    authenticate(value, trust, trust_pin, now)
    require(directory.is_dir() and not directory.is_symlink(), "artifact_directory")
    require(
        value["platform"] == "linux/amd64" and value["python_minor"] == "3.12", "build_platform"
    )
    require(
        value["network_access"] == "FORBIDDEN_DURING_BUILD_AND_SMOKE"
        and value["registry_push_allowed"] is False,
        "offline_build_only",
    )
    require(
        type(value["source_date_epoch"]) is int
        and 0 < value["source_date_epoch"] <= value["review"]["signed_at"],
        "reproducible_build_epoch",
    )
    require(value["source_files"] == source_inventory(root), "build_source_inventory_mismatch")
    require(
        value["expected_application_source_sha256"] == application_hash(root),
        "application_source_mismatch",
    )
    expected = pins(root / "requirements/m23-constraints.txt")
    require(len(expected) == 39 and value["runtime_pins"] == expected, "runtime_pins_mismatch")
    runtime = base_evidence(
        value["base_image_review"], value["base_image"], directory, value["review"]["signed_at"]
    )
    glibc = glibc_version(runtime["glibc_version"])
    require(
        isinstance(value["dependency_wheels"], list)
        and len(value["dependency_wheels"]) == len(expected),
        "linux_wheel_roster",
    )
    actual: dict[str, str] = {}
    for record in value["dependency_wheels"]:
        path = artifact_path(directory, record)
        name, version = wheel_metadata(path, glibc, runtime["python_version"])
        require(name not in actual, "duplicate_distribution")
        actual[name] = version
    require(actual == expected, "linux_closure_mismatch")
    project = artifact_path(directory, value["project_wheel"])
    require(
        wheel_metadata(project, glibc, runtime["python_version"])
        == ("northstar-claims-ai", "0.1.0"),
        "project_wheel_identity",
    )
    with zipfile.ZipFile(project) as archive:
        actual_files = {
            n for n in archive.namelist() if n.startswith("claims_ai/") and not n.endswith("/")
        }
        expected_files = {
            str(p.relative_to(root / "src")) for p in (root / "src/claims_ai").rglob("*.py")
        }
        expected_files.add("claims_ai/py.typed")
        require(actual_files == expected_files, "project_wheel_inventory")
        for name in expected_files:
            require(
                archive.read(name) == (root / "src" / name).read_bytes(), "project_wheel_source"
            )
    validate_evidence(value, directory, now)
    return value


def make_context(root: Path, value: dict[str, Any], artifacts: Path, target: Path) -> None:
    target.mkdir(exist_ok=False)
    for name in ("Dockerfile", ".dockerignore", "entrypoint.py", "smoke.py"):
        shutil.copy2(root / "deployment/containers" / name, target / name)
    fixtures = target / "fixtures"
    fixtures.mkdir()
    for name in ("manifest.json", "specification.json", "scenarios.json"):
        shutil.copy2(root / "data/rules/motor/v1" / name, fixtures / name)
    wheels = target / "artifacts/wheels"
    wheels.mkdir(parents=True)
    requirements = []
    for record in [*value["dependency_wheels"], value["project_wheel"]]:
        path = artifact_path(artifacts, record)  # Recheck immediately before copying.
        shutil.copy2(path, wheels / path.name)
        requirements.append("/artifacts/wheels/" + path.name + " --hash=sha256:" + record["sha256"])
    (target / "artifacts/requirements.txt").write_text("\n".join(sorted(requirements)) + "\n")


def build(
    root: Path,
    manifest: Path,
    artifacts: Path,
    trusted_pin: str,
    *,
    trust: Path | None = None,
    trust_pin: str | None = None,
) -> str:
    validate_inputs(root, manifest, artifacts, trusted_pin, trust=trust, trust_pin=trust_pin)
    # B1 cannot safely assert kernel/daemon isolation from a signed plan alone.
    # Refuse ALL builds, including otherwise valid signed evidence, before any process.
    raise FoundationError("b1_build_execution_disabled")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local artifacts only, no downloads or image push")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--trusted-manifest-sha256", required=True)
    parser.add_argument("--trust-store", type=Path)
    parser.add_argument("--trusted-trust-sha256")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        options = {"trust": args.trust_store, "trust_pin": args.trusted_trust_sha256}
        if args.validate_only:
            validate_inputs(
                args.root, args.manifest, args.artifacts, args.trusted_manifest_sha256, **options
            )
            print(
                json.dumps(
                    {
                        "input_validation": "PASS",
                        "build_execution": "DISABLED_B1",
                        "cloud_execution": False,
                        "reproducibility": "NOT_TESTED",
                    },
                    sort_keys=True,
                )
            )
        else:
            build(args.root, args.manifest, args.artifacts, args.trusted_manifest_sha256, **options)
    except (ValueError, OSError):
        parser.exit(78, "M23 B1 refused: evidence incomplete, untrusted or execution prohibited.\n")


if __name__ == "__main__":
    main()
