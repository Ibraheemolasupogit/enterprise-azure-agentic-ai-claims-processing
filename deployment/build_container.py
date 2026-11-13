"""Locked local build contract. No downloads, registry login, image push or Azure calls."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from deployment.foundation import load, pins, require

HEX = re.compile(r"[a-f0-9]{64}")


def file_hash(path: Path) -> str:
    require(not path.is_symlink() and path.is_file(), "artifact_unavailable")
    require(path.stat().st_size <= 67108864, "artifact_capacity")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(65536):
            digest.update(block)
    return digest.hexdigest()


def application_hash(root: Path) -> str:
    package = root / "src/claims_ai"
    return hashlib.sha256(
        b"".join(
            str(p.relative_to(package)).encode() + b"\0" + p.read_bytes()
            for p in sorted(package.rglob("*.py"))
        )
    ).hexdigest()


def wheel_metadata(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        require(len(entries) <= 8192, "wheel_entry_capacity")
        names = [e.filename for e in entries]
        require(len(set(names)) == len(names), "duplicate_wheel_entry")
        require(
            all(
                not n.startswith("/")
                and ".." not in Path(n).parts
                and "\\" not in n
                and not n.endswith(".pth")
                for n in names
            ),
            "unsafe_wheel_entry",
        )
        metadata_names = [n for n in names if n.endswith(".dist-info/METADATA")]
        wheel_names = [n for n in names if n.endswith(".dist-info/WHEEL")]
        require(len(metadata_names) == len(wheel_names) == 1, "wheel_metadata_inventory")
        require(
            all(archive.getinfo(n).file_size <= 1048576 for n in metadata_names + wheel_names),
            "wheel_metadata_capacity",
        )
        metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
        wheel = BytesParser().parsebytes(archive.read(wheel_names[0]))
        tags = wheel.get_all("Tag", [])
        compatible = False
        for tag in tags:
            python, abi, platform = str(tag).split("-")
            if python == "py3" and abi == "none" and platform == "any":
                compatible = True
            if platform.endswith("_x86_64") and platform.startswith("manylinux"):
                if python == "cp312" and abi == "cp312":
                    compatible = True
                if re.fullmatch(r"cp3(?:[6-9]|1[0-2])", python) and abi == "abi3":
                    compatible = True
        require(compatible, "wheel_not_linux_amd64_python312")
        name, version = metadata.get("Name"), metadata.get("Version")
        require(isinstance(name, str) and isinstance(version, str), "wheel_identity")
        assert isinstance(name, str) and isinstance(version, str)
        return name.lower().replace("_", "-"), version


def artifact_path(directory: Path, record: dict[str, Any]) -> Path:
    filename = record["file"]
    require(
        isinstance(filename, str) and Path(filename).name == filename and filename.endswith(".whl"),
        "artifact_basename",
    )
    assert isinstance(filename, str)
    path = directory / filename
    require(path.resolve().is_relative_to(directory.resolve()), "artifact_root")
    require(
        isinstance(record["sha256"], str) and HEX.fullmatch(record["sha256"]) is not None,
        "artifact_hash_format",
    )
    require(file_hash(path) == record["sha256"], "artifact_hash_mismatch")
    return path


def validate_inputs(
    root: Path, manifest: Path, directory: Path, trusted_pin: str
) -> dict[str, Any]:
    require(
        HEX.fullmatch(trusted_pin) is not None and file_hash(manifest) == trusted_pin,
        "independent_input_manifest_pin",
    )
    value = load(manifest)
    require(value["format"] == "m23-linux-build-inputs-v1", "build_input_version")
    require(value["status"] == "REVIEWED_LOCAL_BUILD_INPUTS", "linux_inputs_pending")
    require(
        value["platform"] == "linux/amd64" and value["python_minor"] == "3.12", "build_platform"
    )
    require(
        value["network_access"] == "FORBIDDEN_DURING_BUILD_AND_SMOKE"
        and value["registry_push_allowed"] is False,
        "offline_build_only",
    )
    image = value["base_image"]
    require(
        isinstance(image, str)
        and re.fullmatch(r"docker.io/library/python@sha256:[a-f0-9]{64}", image) is not None,
        "base_image_digest_required",
    )
    require(image.split(":")[-1] != "0" * 64, "placeholder_base_digest")
    require(
        isinstance(value["base_image_review"], dict)
        and isinstance(value["licence_and_vulnerability_review"], dict),
        "artifact_review_missing",
    )
    require(
        type(value["source_date_epoch"]) is int and value["source_date_epoch"] > 0,
        "reproducible_build_epoch",
    )
    expected = pins(root / "requirements/m23-constraints.txt")
    require(value["runtime_pins"] == expected, "runtime_pins_mismatch")
    require(
        value["expected_application_source_sha256"] == application_hash(root),
        "application_source_mismatch",
    )
    require(
        isinstance(value["dependency_wheels"], list)
        and len(value["dependency_wheels"]) == len(expected),
        "linux_wheel_roster",
    )
    actual: dict[str, str] = {}
    for record in value["dependency_wheels"]:
        path = artifact_path(directory, record)
        name, version = wheel_metadata(path)
        require(name not in actual, "duplicate_distribution")
        actual[name] = version
    require(actual == expected, "linux_closure_mismatch")
    project = artifact_path(directory, value["project_wheel"])
    require(wheel_metadata(project) == ("northstar-claims-ai", "0.1.0"), "project_wheel_identity")
    with zipfile.ZipFile(project) as archive:
        names = archive.namelist()
        actual_files = {n for n in names if n.startswith("claims_ai/") and n.endswith(".py")}
        expected_files = {
            str(p.relative_to(root / "src")) for p in (root / "src/claims_ai").rglob("*.py")
        }
        require(actual_files == expected_files, "project_wheel_inventory")
        for name in expected_files:
            require(
                archive.read(name) == (root / "src" / name).read_bytes(), "project_wheel_source"
            )
        require(archive.read("claims_ai/py.typed") == b"", "typed_marker")
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


def build(root: Path, manifest: Path, artifacts: Path, trusted_pin: str) -> str:
    value = validate_inputs(root, manifest, artifacts, trusted_pin)
    # Artifact checks precede every Docker invocation; a pending manifest cannot reach Docker.
    context = subprocess.run(
        ["docker", "context", "inspect"], capture_output=True, check=True, text=True, timeout=10
    )
    endpoint = json.loads(context.stdout)[0]["Endpoints"]["docker"]["Host"]
    require(isinstance(endpoint, str) and endpoint.startswith("unix://"), "local_daemon_only")
    subprocess.run(
        ["docker", "image", "inspect", value["base_image"]],
        check=True,
        capture_output=True,
        timeout=10,
    )  # Never pulls a missing base.
    tag = "northstar-m23-local:" + trusted_pin[:16]
    with tempfile.TemporaryDirectory(prefix="m23-build-") as name:
        directory = Path(name) / "context"
        make_context(root, value, artifacts, directory)
        subprocess.run(
            [
                "docker",
                "build",
                "--pull=false",
                "--network=none",
                "--platform=linux/amd64",
                "--build-arg",
                "PYTHON_BASE=" + value["base_image"],
                "--build-arg",
                "SOURCE_DATE_EPOCH=" + str(value["source_date_epoch"]),
                "--tag",
                tag,
                str(directory),
            ],
            check=True,
            timeout=600,
        )
    inspected = subprocess.run(
        ["docker", "image", "inspect", tag, "--format", "{{.Id}}"],
        capture_output=True,
        check=True,
        text=True,
        timeout=10,
    )
    image_id = inspected.stdout.strip()
    require(re.fullmatch(r"sha256:[a-f0-9]{64}", image_id) is not None, "image_digest")
    common = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=128",
        "--memory=1g",
        "--cpus=1",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
    ]
    subprocess.run(
        [*common, "--entrypoint", "/opt/venv/bin/python", image_id, "-I", "-B", "/app/smoke.py"],
        check=True,
        timeout=60,
    )
    blocked = subprocess.run([*common, image_id], capture_output=True, timeout=15)
    require(blocked.returncode == 78, "cloud_host_must_remain_blocked")
    return image_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Local artifacts only, no downloads or image push")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--trusted-manifest-sha256", required=True)
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                {
                    "local_image_id": build(
                        args.root, args.manifest, args.artifacts, args.trusted_manifest_sha256
                    ),
                    "cloud_execution": False,
                },
                sort_keys=True,
            )
        )
    except (KeyError, ValueError, OSError, subprocess.SubprocessError):
        parser.exit(
            78, "M23 local build blocked; locked Linux inputs or local engine unavailable.\n"
        )


if __name__ == "__main__":
    main()
