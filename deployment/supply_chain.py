"""M23 B1 offline evidence admission. No subprocess, network, signing or execution API."""

import hashlib
import itertools
import json
import re
import stat
import time
import zipfile
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from deployment.foundation import FoundationError, load, require

HEX = re.compile(r"[a-f0-9]{64}")
DOMAIN = b"m23-offline-build-review-v2\0"
EVIDENCE = {
    "provenance",
    "licence",
    "sbom",
    "vulnerability",
    "reproducibility",
    "builder_isolation",
}
PLANS = {"reproducibility", "builder_isolation"}
CONTEXT = (
    "pyproject.toml",
    "MANIFEST.in",
    "README.md",
    "deployment/containers/Dockerfile",
    "deployment/containers/.dockerignore",
    "deployment/containers/entrypoint.py",
    "deployment/containers/smoke.py",
    "data/rules/motor/v1/manifest.json",
    "data/rules/motor/v1/specification.json",
    "data/rules/motor/v1/scenarios.json",
)


def fields(value: object, keys: set[str], code: str) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == keys, code)
    assert isinstance(value, dict)
    return value


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 4096


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def file_hash(path: Path, limit: int = 67108864) -> str:
    require(not path.is_symlink() and path.is_file(), "artifact_unavailable")
    require(path.stat().st_size <= limit, "artifact_capacity")
    hashed = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(65536):
            size += len(block)
            require(size <= limit, "artifact_capacity")
            hashed.update(block)
    return hashed.hexdigest()


def local_record(directory: Path, record: object, *, limit: int = 67108864) -> Path:
    value = fields(record, {"file", "sha256"}, "artifact_record")
    name, sha = value["file"], value["sha256"]
    require(
        isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.+-]*", name) is not None,
        "artifact_basename",
    )
    require(isinstance(sha, str) and HEX.fullmatch(sha) is not None, "artifact_hash_format")
    assert isinstance(name, str)
    path = directory / name
    require(path.resolve().is_relative_to(directory.resolve()), "artifact_root")
    require(file_hash(path, limit) == sha, "artifact_hash_mismatch")
    return path


def source_inventory(root: Path) -> dict[str, str]:
    paths = {root / n for n in CONTEXT}
    paths.update((root / "src/claims_ai").rglob("*.py"))
    paths.add(root / "src/claims_ai/py.typed")
    paths.update((root / "deployment").rglob("*.py"))
    paths.update((root / "requirements").glob("*.txt"))
    return {str(p.relative_to(root)): file_hash(p) for p in sorted(paths)}


def glibc_version(value: object) -> tuple[int, int]:
    require(
        isinstance(value, str) and re.fullmatch(r"2\.(0|[1-9][0-9]*)", value) is not None,
        "base_glibc_version",
    )
    assert isinstance(value, str)
    return 2, int(value.split(".")[1])


def python_version(value: object) -> tuple[int, int, int]:
    require(
        isinstance(value, str) and re.fullmatch(r"3\.12\.(0|[1-9][0-9]*)", value) is not None,
        "base_cpython312_version",
    )
    assert isinstance(value, str)
    return 3, 12, int(value.split(".")[2])


def expanded_tags(value: str) -> set[tuple[str, str, str]]:
    parts = value.split("-")
    require(
        len(parts) == 3
        and all(re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", p) for p in parts),
        "wheel_tag_shape",
    )
    require(all(len(p.split(".")) <= 16 for p in parts), "wheel_tag_capacity")
    return {(a, b, c) for a, b, c in itertools.product(*(p.split(".") for p in parts))}


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def compatible_tag(tag: tuple[str, str, str], glibc: tuple[int, int] | None) -> bool:
    python, abi, platform = tag
    if tag == ("py3", "none", "any"):
        return True
    legacy = {
        "manylinux1_x86_64": (2, 5),
        "manylinux2010_x86_64": (2, 12),
        "manylinux2014_x86_64": (2, 17),
    }
    floor = legacy.get(platform)
    match = re.fullmatch(r"manylinux_2_(0|[1-9][0-9]*)_x86_64", platform)
    if match:
        floor = (2, int(match[1]))
    return (
        glibc is not None
        and floor is not None
        and floor <= glibc
        and (
            (python == "cp312" and abi == "cp312")
            or (re.fullmatch(r"cp3(?:[2-9]|1[0-2])", python) is not None and abi == "abi3")
        )
    )


def requires_python(value: object, target: tuple[int, int, int]) -> None:
    # Restricted, fail-closed subset. Unknown PEP 440 syntax requires explicit checker review.
    require(isinstance(value, str) and bool(value), "wheel_requires_python")
    assert isinstance(value, str)
    for clause in value.split(","):
        match = re.fullmatch(r"\s*(>=|<=|==|!=|>|<)\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?\s*", clause)
        require(match is not None, "wheel_requires_python_syntax")
        assert match is not None
        version = tuple(int(v or 0) for v in match.groups()[1:])
        allowed = {
            ">=": target >= version,
            "<=": target <= version,
            "==": target == version,
            "!=": target != version,
            ">": target > version,
            "<": target < version,
        }
        require(allowed[match[1]], "wheel_python_version_mismatch")


def wheel_metadata(
    path: Path, glibc: tuple[int, int] | None = None, python: str = "3.12.0"
) -> tuple[str, str]:
    target = python_version(python)
    parts = path.name.removesuffix(".whl").split("-")
    require(path.suffix == ".whl" and len(parts) in (5, 6), "wheel_filename")
    require(
        len(parts) == 5 or re.fullmatch(r"[0-9][A-Za-z0-9_]*", parts[2]) is not None,
        "wheel_build_tag",
    )
    filename_tags = expanded_tags("-".join(parts[-3:]))
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        require(
            len(entries) <= 8192 and sum(e.file_size for e in entries) <= 268435456,
            "wheel_entry_capacity",
        )
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
        require(
            all(
                stat.S_IFMT(e.external_attr >> 16) in (0, stat.S_IFREG, stat.S_IFDIR)
                and not e.flag_bits & 1
                for e in entries
            ),
            "unsafe_wheel_entry_type",
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
        name, version = metadata.get("Name"), metadata.get("Version")
        require(
            all(
                len(metadata.get_all(key, [])) == 1
                for key in ("Name", "Version", "Requires-Python")
            ),
            "wheel_metadata_headers",
        )
        require(isinstance(name, str) and isinstance(version, str), "wheel_identity")
        assert isinstance(name, str) and isinstance(version, str)
        require(
            normalize(parts[0]) == normalize(name) and parts[1] == version,
            "wheel_filename_identity",
        )
        prefix = f"{parts[0]}-{parts[1]}.dist-info/"
        require(
            metadata_names[0] == prefix + "METADATA" and wheel_names[0] == prefix + "WHEEL",
            "wheel_dist_info_identity",
        )
        require(wheel.get_all("Wheel-Version", []) == ["1.0"], "wheel_format_version")
        tags = wheel.get_all("Tag", [])
        require(0 < len(tags) <= 64, "wheel_tag_inventory")
        declared = set().union(*(expanded_tags(str(t)) for t in tags))
        require(declared == filename_tags, "wheel_filename_tags")
        require(
            any(compatible_tag(tag, glibc) for tag in declared), "wheel_not_linux_amd64_python312"
        )
        for entry in entries:
            if re.search(r"\.so(?:\.|$)", entry.filename):
                require(
                    any(tag[2] != "any" and compatible_tag(tag, glibc) for tag in declared),
                    "wheel_native_platform_tag_required",
                )
                with archive.open(entry) as stream:
                    header = stream.read(64)
                require(
                    len(header) >= 20
                    and header[:6] == b"\x7fELF\x02\x01"
                    and int.from_bytes(header[18:20], "little") == 62,
                    "wheel_native_amd64_required",
                )
                require(
                    (match := re.search(r"\.cpython-([0-9]+)", entry.filename)) is None
                    or match[1] == "312",
                    "wheel_native_cpython_mismatch",
                )
        requires_python(metadata.get("Requires-Python"), target)
        return normalize(name), version


def review_bytes(manifest: dict[str, Any]) -> bytes:
    review = dict(manifest["review"])
    review.pop("signature_hex", None)
    return DOMAIN + canonical(
        {"manifest": {k: v for k, v in manifest.items() if k != "review"}, "attestation": review}
    )


def authenticate(
    manifest: dict[str, Any], trust: Path | None, trust_pin: str | None, now: int
) -> None:
    require(
        trust is not None and isinstance(trust_pin, str) and HEX.fullmatch(trust_pin) is not None,
        "independent_reviewer_trust_required",
    )
    assert trust is not None
    require(file_hash(trust) == trust_pin, "reviewer_trust_hash_mismatch")
    store = fields(load(trust), {"format", "keys"}, "reviewer_trust_shape")
    require(store["format"] == "m23-reviewer-trust-v1", "reviewer_trust_version")
    require(
        isinstance(store["keys"], list) and 1 <= len(store["keys"]) <= 16, "reviewer_key_inventory"
    )
    keys: dict[str, dict[str, Any]] = {}
    for raw in store["keys"]:
        key = fields(
            raw,
            {"key_id", "reviewer", "public_key_hex", "not_before", "expires", "revoked"},
            "reviewer_key_shape",
        )
        require(
            nonempty(key["key_id"]) and key["key_id"] not in keys and nonempty(key["reviewer"]),
            "reviewer_identity",
        )
        require(
            isinstance(key["public_key_hex"], str)
            and HEX.fullmatch(key["public_key_hex"]) is not None,
            "reviewer_public_key",
        )
        require(
            type(key["not_before"]) is int
            and type(key["expires"]) is int
            and 0 < key["not_before"] < key["expires"]
            and type(key["revoked"]) is bool,
            "reviewer_key_validity",
        )
        keys[key["key_id"]] = key
    review = fields(
        manifest.get("review"),
        {"key_id", "reviewer", "signed_at", "expires_at", "signature_hex"},
        "review_signature_required",
    )
    require(isinstance(review["key_id"], str) and review["key_id"] in keys, "untrusted_reviewer")
    key = keys[review["key_id"]]
    require(
        review["reviewer"] == key["reviewer"] and key["revoked"] is False,
        "reviewer_revoked_or_mismatched",
    )
    require(
        type(review["signed_at"]) is int
        and type(review["expires_at"]) is int
        and key["not_before"] <= review["signed_at"] <= now < review["expires_at"] <= key["expires"]
        and 0 < review["expires_at"] - review["signed_at"] <= 604800,
        "review_expired_or_invalid",
    )
    signature = review["signature_hex"]
    require(
        isinstance(signature, str) and re.fullmatch(r"[a-f0-9]{128}", signature) is not None,
        "review_signature_format",
    )
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(key["public_key_hex"])).verify(
            bytes.fromhex(signature), review_bytes(manifest)
        )
    except (InvalidSignature, ValueError) as exc:
        raise FoundationError("review_signature_invalid") from exc


def base_evidence(value: object, image: object, directory: Path, now: int) -> dict[str, Any]:
    require(
        isinstance(image, str)
        and re.fullmatch(r"docker.io/library/python@sha256:[a-f0-9]{64}", image) is not None
        and not image.endswith("0" * 64),
        "base_image_digest_required",
    )
    assert isinstance(image, str)
    base = fields(value, {"manifest", "config", "layers", "runtime"}, "base_evidence_shape")
    manifest = load(local_record(directory, base["manifest"], limit=1048576))
    require(base["manifest"]["sha256"] == image.split(":")[-1], "base_manifest_digest_mismatch")
    require(
        type(manifest.get("schemaVersion")) is int
        and manifest["schemaVersion"] == 2
        and manifest.get("mediaType")
        in (
            "application/vnd.oci.image.manifest.v1+json",
            "application/vnd.docker.distribution.manifest.v2+json",
        ),
        "base_platform_manifest_required",
    )
    config = load(local_record(directory, base["config"], limit=1048576))
    require(
        manifest["config"]["digest"] == "sha256:" + base["config"]["sha256"], "base_config_digest"
    )
    require(
        manifest["config"]["size"] == (directory / base["config"]["file"]).stat().st_size,
        "base_config_size",
    )
    require(config.get("os") == "linux" and config.get("architecture") == "amd64", "base_platform")
    require(
        isinstance(base["layers"], list)
        and isinstance(manifest.get("layers"), list)
        and 0 < len(base["layers"]) == len(manifest["layers"]) <= 128,
        "base_layer_inventory",
    )
    for record, descriptor in zip(base["layers"], manifest["layers"], strict=True):
        path = local_record(directory, record, limit=1073741824)
        require(
            descriptor["digest"] == "sha256:" + record["sha256"]
            and descriptor["size"] == path.stat().st_size,
            "base_layer_digest_or_size",
        )
    runtime = fields(
        load(local_record(directory, base["runtime"], limit=1048576)),
        {
            "format",
            "status",
            "manifest_sha256",
            "config_sha256",
            "os",
            "architecture",
            "implementation",
            "python_version",
            "glibc_version",
            "observed_at",
        },
        "base_runtime_shape",
    )
    require(
        runtime["format"] == "m23-base-runtime-v1"
        and runtime["status"] == "VERIFIED"
        and runtime["manifest_sha256"] == base["manifest"]["sha256"]
        and runtime["config_sha256"] == base["config"]["sha256"],
        "base_runtime_binding",
    )
    require(
        runtime["os"] == "linux"
        and runtime["architecture"] == "amd64"
        and runtime["implementation"] == "CPython",
        "base_runtime_platform",
    )
    python_version(runtime["python_version"])
    glibc_version(runtime["glibc_version"])
    require(
        type(runtime["observed_at"]) is int and 0 < runtime["observed_at"] <= now,
        "base_runtime_time",
    )
    return runtime


def subject(value: dict[str, Any]) -> str:
    return digest({k: v for k, v in value.items() if k not in ("evidence", "review")})


def validate_evidence(value: dict[str, Any], directory: Path, now: int) -> None:
    records = fields(value["evidence"], EVIDENCE, "evidence_inventory")
    artifacts = {
        value["base_image"].split(":")[-1],
        value["project_wheel"]["sha256"],
        *(r["sha256"] for r in value["dependency_wheels"]),
    }
    for kind, record in records.items():
        report = fields(
            load(local_record(directory, record, limit=1048576)),
            {"format", "status", "subject_sha256", "artifact_sha256s", "observed_at", "details"},
            "evidence_shape",
        )
        require(
            report["format"] == f"m23-{kind}-evidence-v1"
            and report["subject_sha256"] == subject(value),
            "evidence_subject_binding",
        )
        expected_status = "PLAN_REVIEWED" if kind in PLANS else "VERIFIED_FOR_LOCAL_BUILD"
        require(report["status"] == expected_status, "evidence_status")
        require(
            isinstance(report["artifact_sha256s"], list)
            and all(isinstance(h, str) for h in report["artifact_sha256s"])
            and len(report["artifact_sha256s"]) == len(artifacts)
            and set(report["artifact_sha256s"]) == artifacts,
            "evidence_artifact_coverage",
        )
        require(
            type(report["observed_at"]) is int
            and 0 < report["observed_at"] <= value["review"]["signed_at"],
            "evidence_time",
        )
        details = report["details"]
        if kind in {"provenance", "licence"}:
            data = fields(details, {"inventory", "review_notes"}, "artifact_review_details")
            require(nonempty(data["review_notes"]), "review_notes_required")
            inventory = fields(data["inventory"], artifacts, "artifact_review_coverage")
            for raw in inventory.values():
                keys = (
                    {"origin", "verification_method", "receipt"}
                    if kind == "provenance"
                    else {"spdx_expression", "notices"}
                )
                item = fields(raw, keys, "artifact_review_item")
                if kind == "provenance":
                    require(
                        nonempty(item["origin"])
                        and item["verification_method"]
                        in (
                            "REVIEWED_UPSTREAM_DIGEST",
                            "REVIEWED_UPSTREAM_ATTESTATION",
                            "SOURCE_MATCHED_PROJECT",
                        ),
                        "artifact_provenance",
                    )
                    local_record(directory, item["receipt"])
                else:
                    require(
                        nonempty(item["spdx_expression"])
                        and isinstance(item["notices"], list)
                        and bool(item["notices"]),
                        "artifact_licence",
                    )
                    for notice in item["notices"]:
                        local_record(directory, notice)
        elif kind in {"sbom", "vulnerability"}:
            keys = {"tool", "tool_version", "report", "coverage"}
            if kind == "sbom":
                keys |= {"document_format"}
            else:
                keys |= {
                    "database",
                    "database_updated_at",
                    "unresolved_critical",
                    "unresolved_high",
                }
            data = fields(details, keys, "scanner_evidence_details")
            require(
                nonempty(data["tool"])
                and nonempty(data["tool_version"])
                and data["coverage"] == ["os", "python", "native"],
                "scanner_evidence_coverage",
            )
            local_record(directory, data["report"])
            if kind == "sbom":
                require(data["document_format"] in ("SPDX-2.3", "CycloneDX-1.6"), "sbom_format")
            else:
                local_record(directory, data["database"], limit=1073741824)
                require(
                    type(data["database_updated_at"]) is int
                    and 0 < now - data["database_updated_at"] <= 604800,
                    "vulnerability_database_stale",
                )
                require(
                    type(data["unresolved_critical"]) is int
                    and data["unresolved_critical"] == 0
                    and type(data["unresolved_high"]) is int
                    and data["unresolved_high"] == 0,
                    "vulnerability_gate",
                )
        elif kind == "reproducibility":
            data = fields(
                details,
                {"result", "independent_clean_builds", "comparisons", "plan"},
                "reproducibility_plan",
            )
            require(
                data["result"] == "NOT_TESTED"
                and type(data["independent_clean_builds"]) is int
                and data["independent_clean_builds"] == 2
                and data["comparisons"]
                == ["source", "wheels", "sbom", "image_config", "oci_manifest"],
                "reproducibility_not_a_result",
            )
            local_record(directory, data["plan"])
        else:
            data = fields(
                details,
                {
                    "execution_allowed",
                    "mechanism",
                    "interfaces",
                    "daemon_egress",
                    "frontend_egress",
                    "run_egress",
                    "remote_builders",
                    "registry_access",
                    "preloaded_inputs_only",
                    "builder_identity",
                    "builder_version",
                    "policy",
                },
                "offline_builder_contract",
            )
            require(
                data["execution_allowed"] is False
                and data["mechanism"] == "DISCONNECTED_LINUX_VM"
                and data["interfaces"] == []
                and data["remote_builders"] is False
                and data["registry_access"] is False
                and data["preloaded_inputs_only"] is True
                and all(
                    data[k] == "DENY_ALL"
                    for k in ("daemon_egress", "frontend_egress", "run_egress")
                )
                and nonempty(data["builder_identity"])
                and nonempty(data["builder_version"]),
                "offline_builder_isolation_required",
            )
            local_record(directory, data["policy"])


def clock() -> int:
    return int(time.time())
