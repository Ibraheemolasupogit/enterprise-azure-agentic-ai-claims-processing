"""Synthetic ephemeral evidence only: no artifact acquisition, Docker or real approvals."""

import json
import shutil
import socket
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deployment.build_container import (  # noqa: E402
    application_hash,
    build,
    validate_inputs,
)
from deployment.foundation import FoundationError, pins  # noqa: E402
from deployment.supply_chain import (  # noqa: E402
    EVIDENCE,
    PLANS,
    file_hash,
    review_bytes,
    source_inventory,
    subject,
    wheel_metadata,
)

NOW = 1794571238


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True))


def wheel(
    path: Path,
    name: str,
    version: str,
    tag: str = "py3-none-any",
    requires: str = ">=3.12,<3.13",
    members: dict[str, bytes] | None = None,
) -> None:
    prefix = name.replace("-", "_") + "-" + version + ".dist-info/"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            prefix + "METADATA", f"Name: {name}\nVersion: {version}\nRequires-Python: {requires}\n"
        )
        archive.writestr(prefix + "WHEEL", "Wheel-Version: 1.0\nTag: " + tag + "\n")
        for n, content in (members or {}).items():
            archive.writestr(n, content)


class SyntheticPacket:
    """Only unit-test bytes, one ephemeral test key; never a real review packet."""

    def __init__(self, folder: Path) -> None:
        self.root, self.artifacts = folder / "root", folder / "artifacts"
        self.artifacts.mkdir()
        for n in ("deployment", "requirements"):
            shutil.copytree(ROOT / n, self.root / n, ignore=shutil.ignore_patterns("__pycache__"))
        for n in ("pyproject.toml", "MANIFEST.in", "README.md"):
            shutil.copyfile(ROOT / n, self.root / n)
        (self.root / "src/claims_ai").mkdir(parents=True)
        (self.root / "src/claims_ai/example.py").write_text("# synthetic fixture only\n")
        (self.root / "src/claims_ai/py.typed").touch()
        fixture = self.root / "data/rules/motor/v1"
        fixture.mkdir(parents=True)
        for n in ("manifest", "specification", "scenarios"):
            write_json(fixture / (n + ".json"), {"synthetic_test_only": True})
        self.key = Ed25519PrivateKey.generate()
        self.trust = folder / "test-only-trust.json"
        write_json(
            self.trust,
            {
                "format": "m23-reviewer-trust-v1",
                "keys": [
                    {
                        "key_id": "test-only",
                        "reviewer": "synthetic-unit-test-not-an-approval",
                        "public_key_hex": self.key.public_key().public_bytes_raw().hex(),
                        "not_before": NOW - 100,
                        "expires": NOW + 1000,
                        "revoked": False,
                    }
                ],
            },
        )
        self.manifest = folder / "test-only-manifest.json"
        layer = self.record("layer.bin", b"synthetic, not an OCI layer")
        config = self.record_json("config.json", {"os": "linux", "architecture": "amd64"})
        manifest = self.record_json(
            "base.json",
            {
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "config": {
                    "digest": "sha256:" + config["sha256"],
                    "size": (self.artifacts / config["file"]).stat().st_size,
                },
                "layers": [
                    {
                        "digest": "sha256:" + layer["sha256"],
                        "size": (self.artifacts / layer["file"]).stat().st_size,
                    }
                ],
            },
        )
        runtime = self.record_json(
            "runtime.json",
            {
                "format": "m23-base-runtime-v1",
                "status": "VERIFIED",
                "manifest_sha256": manifest["sha256"],
                "config_sha256": config["sha256"],
                "os": "linux",
                "architecture": "amd64",
                "implementation": "CPython",
                "python_version": "3.12.8",
                "glibc_version": "2.36",
                "observed_at": NOW - 10,
            },
        )
        closure = pins(self.root / "requirements/m23-constraints.txt")
        deps = []
        for name, version in closure.items():
            p = self.artifacts / f"{name.replace('-', '_')}-{version}-py3-none-any.whl"
            wheel(p, name, version)
            deps.append({"file": p.name, "sha256": file_hash(p)})
        project = self.artifacts / "northstar_claims_ai-0.1.0-py3-none-any.whl"
        wheel(
            project,
            "northstar-claims-ai",
            "0.1.0",
            members={
                "claims_ai/example.py": (self.root / "src/claims_ai/example.py").read_bytes(),
                "claims_ai/py.typed": b"",
            },
        )
        self.value: dict[str, Any] = {
            "format": "m23-linux-build-inputs-v2",
            "status": "REVIEWED_LOCAL_BUILD_INPUTS",
            "platform": "linux/amd64",
            "python_minor": "3.12",
            "registry_push_allowed": False,
            "network_access": "FORBIDDEN_DURING_BUILD_AND_SMOKE",
            "base_image": "docker.io/library/python@sha256:" + manifest["sha256"],
            "base_image_review": {
                "manifest": manifest,
                "config": config,
                "layers": [layer],
                "runtime": runtime,
            },
            "source_date_epoch": NOW - 50,
            "runtime_pins": closure,
            "expected_application_source_sha256": application_hash(self.root),
            "source_files": source_inventory(self.root),
            "dependency_wheels": deps,
            "project_wheel": {"file": project.name, "sha256": file_hash(project)},
            "evidence": {},
            "review": {},
        }
        self.reports: dict[str, dict[str, Any]] = {}
        subjects = {manifest["sha256"], file_hash(project), *(r["sha256"] for r in deps)}
        receipt = self.record(
            "test-only-receipt.txt", b"synthetic receipt, not security results or a licence"
        )
        for kind in EVIDENCE:
            details: dict[str, Any]
            if kind == "provenance":
                details = {
                    "inventory": {
                        h: {
                            "origin": "synthetic-unit-test-only",
                            "verification_method": "REVIEWED_UPSTREAM_DIGEST",
                            "receipt": receipt,
                        }
                        for h in subjects
                    },
                    "review_notes": "synthetic test only",
                }
            elif kind == "licence":
                details = {
                    "inventory": {
                        h: {"spdx_expression": "TEST-ONLY", "notices": [receipt]} for h in subjects
                    },
                    "review_notes": "synthetic test only",
                }
            elif kind in {"sbom", "vulnerability"}:
                details = {
                    "tool": "synthetic-test",
                    "tool_version": "0",
                    "report": receipt,
                    "coverage": ["os", "python", "native"],
                }
                if kind == "sbom":
                    details["document_format"] = "SPDX-2.3"
                else:
                    details.update(
                        {
                            "database": receipt,
                            "database_updated_at": NOW - 10,
                            "unresolved_critical": 0,
                            "unresolved_high": 0,
                        }
                    )
            elif kind == "reproducibility":
                details = {
                    "result": "NOT_TESTED",
                    "independent_clean_builds": 2,
                    "comparisons": ["source", "wheels", "sbom", "image_config", "oci_manifest"],
                    "plan": receipt,
                }
            else:
                details = {
                    "execution_allowed": False,
                    "mechanism": "DISCONNECTED_LINUX_VM",
                    "interfaces": [],
                    "daemon_egress": "DENY_ALL",
                    "frontend_egress": "DENY_ALL",
                    "run_egress": "DENY_ALL",
                    "remote_builders": False,
                    "registry_access": False,
                    "preloaded_inputs_only": True,
                    "builder_identity": "test-only",
                    "builder_version": "0",
                    "policy": receipt,
                }
            self.reports[kind] = {
                "format": f"m23-{kind}-evidence-v1",
                "status": "PLAN_REVIEWED" if kind in PLANS else "VERIFIED_FOR_LOCAL_BUILD",
                "subject_sha256": subject(self.value),
                "artifact_sha256s": sorted(subjects),
                "observed_at": NOW - 5,
                "details": details,
            }
        self.save()

    def record(self, name: str, data: bytes) -> dict[str, str]:
        p = self.artifacts / name
        p.write_bytes(data)
        return {"file": name, "sha256": file_hash(p)}

    def record_json(self, name: str, value: object) -> dict[str, str]:
        return self.record(name, json.dumps(value, sort_keys=True).encode())

    def save(self) -> None:
        for kind, report in self.reports.items():
            report["subject_sha256"] = subject(self.value)
            self.value["evidence"][kind] = self.record_json(kind + ".json", report)
        self.value["review"] = {
            "key_id": "test-only",
            "reviewer": "synthetic-unit-test-not-an-approval",
            "signed_at": NOW,
            "expires_at": NOW + 100,
            "signature_hex": "",
        }
        self.value["review"]["signature_hex"] = self.key.sign(review_bytes(self.value)).hex()
        write_json(self.manifest, self.value)

    def check(self, **kwargs: Any) -> dict[str, Any]:
        return validate_inputs(
            self.root,
            self.manifest,
            self.artifacts,
            file_hash(self.manifest),
            trust=self.trust,
            trust_pin=file_hash(self.trust),
            now=NOW,
            **kwargs,
        )


@pytest.fixture
def packet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SyntheticPacket:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("B1 must never invoke Docker, subprocess or external network")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    return SyntheticPacket(tmp_path)


def test_authenticated_synthetic_packet_admitted_without_execution(
    packet: SyntheticPacket, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert packet.check()["platform"] == "linux/amd64"
    import deployment.build_container as module

    monkeypatch.setattr(module, "clock", lambda: NOW)
    with pytest.raises(FoundationError, match="b1_build_execution_disabled"):
        build(
            packet.root,
            packet.manifest,
            packet.artifacts,
            file_hash(packet.manifest),
            trust=packet.trust,
            trust_pin=file_hash(packet.trust),
        )


@pytest.mark.parametrize(
    "attack",
    [
        "unsigned",
        "signature",
        "self_signed",
        "expired",
        "future",
        "revoked",
        "key_expired",
        "reviewer",
        "trust_pin",
        "manifest_pin",
    ],
)
def test_unauthenticated_evidence_rejected(packet: SyntheticPacket, attack: str) -> None:
    if attack == "unsigned":
        packet.value["review"] = {}
    elif attack == "signature":
        packet.value["review"]["signature_hex"] = "00" * 64
    elif attack == "self_signed":
        packet.value["review"]["signature_hex"] = (
            Ed25519PrivateKey.generate().sign(review_bytes(packet.value)).hex()
        )
    elif attack == "expired":
        packet.value["review"]["expires_at"] = NOW
    elif attack == "future":
        packet.value["review"]["signed_at"] = NOW + 1
    elif attack == "reviewer":
        packet.value["review"]["reviewer"] = "forged"
    elif attack in {"revoked", "key_expired"}:
        store = json.loads(packet.trust.read_text())
        if attack == "revoked":
            store["keys"][0]["revoked"] = True
        else:
            store["keys"][0]["expires"] = NOW - 1
        write_json(packet.trust, store)
    write_json(packet.manifest, packet.value)
    with pytest.raises(FoundationError):
        validate_inputs(
            packet.root,
            packet.manifest,
            packet.artifacts,
            "0" * 64 if attack == "manifest_pin" else file_hash(packet.manifest),
            trust=packet.trust,
            trust_pin="0" * 64 if attack == "trust_pin" else file_hash(packet.trust),
            now=NOW,
        )


def test_manifest_pin_alone_is_not_review_authentication(packet: SyntheticPacket) -> None:
    with pytest.raises(FoundationError, match="independent_reviewer_trust_required"):
        validate_inputs(
            packet.root, packet.manifest, packet.artifacts, file_hash(packet.manifest), now=NOW
        )


@pytest.mark.parametrize(
    "attack",
    [
        "missing",
        "extra",
        "source",
        "epoch",
        "pins",
        "project",
        "platform",
        "bool_epoch",
        "symlink",
        "missing_wheel",
        "wheel_hash",
        "filename",
        "duplicate",
        "closure",
        "project_extra",
        "project_source",
    ],
)
def test_source_manifest_and_local_artifacts_fail_closed(
    packet: SyntheticPacket, attack: str
) -> None:
    v = packet.value
    if attack == "missing":
        del v["base_image_review"]
    elif attack == "extra":
        v["enable_execution"] = True
    elif attack == "source":
        (packet.root / "deployment/containers/smoke.py").write_text("# changed\n")
    elif attack == "epoch":
        v["source_date_epoch"] = NOW + 1
    elif attack == "bool_epoch":
        v["source_date_epoch"] = True
    elif attack == "pins":
        v["runtime_pins"]["uvicorn"] = "0"
    elif attack == "project":
        v["expected_application_source_sha256"] = "0" * 64
    elif attack == "platform":
        v["platform"] = "linux/arm64"
    elif attack == "duplicate":
        v["dependency_wheels"][1] = v["dependency_wheels"][0]
    elif attack == "closure":
        v["dependency_wheels"].pop()
    elif attack.startswith("project_"):
        p = packet.artifacts / v["project_wheel"]["file"]
        members = {
            "claims_ai/example.py": (packet.root / "src/claims_ai/example.py").read_bytes(),
            "claims_ai/py.typed": b"",
        }
        members["claims_ai/extra.py" if attack == "project_extra" else "claims_ai/example.py"] = (
            b"# unexpected"
        )
        wheel(p, "northstar-claims-ai", "0.1.0", members=members)
        v["project_wheel"]["sha256"] = file_hash(p)
    else:
        record = v["dependency_wheels"][0]
        p = packet.artifacts / record["file"]
        if attack == "missing_wheel":
            p.unlink()
        elif attack == "wheel_hash":
            p.write_bytes(b"tampered")
        elif attack == "filename":
            record["file"] = "bad\n--index-url.whl"
        elif attack == "symlink":
            target = p.with_suffix(".saved")
            p.rename(target)
            p.symlink_to(target)
    packet.save()
    with pytest.raises(FoundationError):
        packet.check()


@pytest.mark.parametrize(
    "target,field,value,error",
    [
        ("runtime", "python_version", "3.13.0", "base_cpython312_version"),
        ("runtime", "implementation", "PyPy", "base_runtime_platform"),
        ("runtime", "architecture", "arm64", "base_runtime_platform"),
        ("runtime", "glibc_version", "musl-1.2", "base_glibc_version"),
        ("runtime", "manifest_sha256", "0" * 64, "base_runtime_binding"),
        ("runtime", "observed_at", NOW + 1, "base_runtime_time"),
        ("config", "architecture", "arm64", "base_platform"),
        ("config", "os", "windows", "base_platform"),
        (
            "manifest",
            "mediaType",
            "application/vnd.oci.image.index.v1+json",
            "base_platform_manifest_required",
        ),
    ],
)
def test_base_evidence_rejected(
    packet: SyntheticPacket, target: str, field: str, value: object, error: str
) -> None:
    record = packet.value["base_image_review"][target]
    data = json.loads((packet.artifacts / record["file"]).read_text())
    data[field] = value
    packet.value["base_image_review"][target] = packet.record_json(record["file"], data)
    base = packet.value["base_image_review"]
    if target == "config":
        manifest = json.loads((packet.artifacts / base["manifest"]["file"]).read_text())
        manifest["config"]["digest"] = "sha256:" + base["config"]["sha256"]
        manifest["config"]["size"] = (packet.artifacts / base["config"]["file"]).stat().st_size
        base["manifest"] = packet.record_json(base["manifest"]["file"], manifest)
    if target in {"manifest", "config"}:
        packet.value["base_image"] = "docker.io/library/python@sha256:" + base["manifest"]["sha256"]
        runtime = json.loads((packet.artifacts / base["runtime"]["file"]).read_text())
        runtime["manifest_sha256"] = base["manifest"]["sha256"]
        runtime["config_sha256"] = base["config"]["sha256"]
        base["runtime"] = packet.record_json(base["runtime"]["file"], runtime)
    packet.save()
    with pytest.raises(FoundationError, match=error):
        packet.check()


@pytest.mark.parametrize("kind", sorted(EVIDENCE))
@pytest.mark.parametrize(
    "attack", ["absent", "pending", "wrong_subject", "missing_artifact", "tampered"]
)
def test_evidence_coverage_and_binding(packet: SyntheticPacket, kind: str, attack: str) -> None:
    if attack == "pending":
        packet.reports[kind]["status"] = "PENDING_REVIEW"
    elif attack == "missing_artifact":
        packet.reports[kind]["artifact_sha256s"].pop()
    packet.save()
    if attack == "absent":
        del packet.value["evidence"][kind]
        packet.value["review"]["signature_hex"] = packet.key.sign(review_bytes(packet.value)).hex()
        write_json(packet.manifest, packet.value)
    if attack in {"wrong_subject", "tampered"}:
        p = packet.artifacts / packet.value["evidence"][kind]["file"]
        data = json.loads(p.read_text())
        data["subject_sha256"] = "0" * 64
        write_json(p, data)
        if attack == "wrong_subject":
            packet.value["evidence"][kind]["sha256"] = file_hash(p)
            packet.value["review"]["signature_hex"] = packet.key.sign(
                review_bytes(packet.value)
            ).hex()
            write_json(packet.manifest, packet.value)
    with pytest.raises(FoundationError):
        packet.check()


@pytest.mark.parametrize(
    "kind,field,value",
    [
        ("builder_isolation", "daemon_egress", "ALLOW"),
        ("builder_isolation", "frontend_egress", "ALLOW"),
        ("builder_isolation", "run_egress", "ALLOW"),
        ("builder_isolation", "interfaces", ["eth0"]),
        ("builder_isolation", "remote_builders", True),
        ("builder_isolation", "registry_access", True),
        ("builder_isolation", "execution_allowed", True),
        ("builder_isolation", "mechanism", "PULL_FALSE"),
        ("vulnerability", "unresolved_high", 1),
        ("vulnerability", "unresolved_critical", True),
        ("vulnerability", "database_updated_at", NOW - 604801),
        ("reproducibility", "result", "PASS"),
        ("reproducibility", "independent_clean_builds", True),
        ("sbom", "coverage", ["python"]),
    ],
)
def test_scanner_and_offline_builder_policy(
    packet: SyntheticPacket, kind: str, field: str, value: object
) -> None:
    packet.reports[kind]["details"][field] = value
    packet.save()
    with pytest.raises(FoundationError):
        packet.check()


@pytest.mark.parametrize(
    "tag,glibc,accepted",
    [
        ("cp312-cp312-manylinux_2_28_x86_64", (2, 28), True),
        ("cp312-cp312-manylinux_2_36_x86_64", (2, 28), False),
        ("cp311-abi3-manylinux2014_x86_64", (2, 17), True),
        ("cp313-abi3-manylinux_2_17_x86_64", (2, 36), False),
        ("cp312-cp312-manylinux_2_28_aarch64", (2, 36), False),
        ("cp312-cp312-musllinux_1_2_x86_64", (2, 36), False),
        ("cp312-cp312-linux_x86_64", (2, 36), False),
        ("cp312-cp312-manylinux_999_x86_64", (2, 36), False),
        ("cp312-cp312-manylinux_2_28_x86_64", None, False),
        ("cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64", (2, 17), True),
    ],
)
def test_real_target_tag_interpretation(
    tmp_path: Path, tag: str, glibc: tuple[int, int] | None, accepted: bool
) -> None:
    p = tmp_path / f"synthetic-0-{tag}.whl"
    wheel(p, "synthetic", "0", tag)
    if accepted:
        assert wheel_metadata(p, glibc, "3.12.8") == ("synthetic", "0")
    else:
        with pytest.raises(FoundationError):
            wheel_metadata(p, glibc, "3.12.8")


@pytest.mark.parametrize("attack", ["name", "tags", "requires", "zip", "symlink", "duplicate"])
def test_wheel_metadata_is_bound_to_filename(tmp_path: Path, attack: str) -> None:
    p = tmp_path / "synthetic-0-py3-none-any.whl"
    wheel(
        p,
        "wrong" if attack == "name" else "synthetic",
        "0",
        "cp312-cp312-manylinux_2_17_x86_64" if attack == "tags" else "py3-none-any",
        ">=3.13" if attack == "requires" else ">=3.12,<3.13",
    )
    if attack == "zip":
        p.write_bytes(b"not a ZIP")
    elif attack in {"symlink", "duplicate"}:
        with zipfile.ZipFile(p, "a") as z:
            if attack == "symlink":
                info = zipfile.ZipInfo("link")
                info.external_attr = 0o120777 << 16
                z.writestr(info, "/etc/passwd")
            else:
                with pytest.warns(UserWarning, match="Duplicate name"):
                    z.writestr("synthetic-0.dist-info/METADATA", "duplicate")
    with pytest.raises((FoundationError, zipfile.BadZipFile)):
        wheel_metadata(p, (2, 36), "3.12.8")


@pytest.mark.parametrize(
    "machine,filename,accepted",
    [
        (62, "native.cpython-312-x86_64-linux-gnu.so", True),
        (183, "native.cpython-312-x86_64-linux-gnu.so", False),
        (62, "native.cpython-311-x86_64-linux-gnu.so", False),
    ],
)
def test_native_elf_header_and_cpython_abi(
    tmp_path: Path, machine: int, filename: str, accepted: bool
) -> None:
    p = tmp_path / "synthetic-0-cp312-cp312-manylinux_2_17_x86_64.whl"
    header = bytearray(64)
    header[:6] = b"\x7fELF\x02\x01"
    header[18:20] = machine.to_bytes(2, "little")
    wheel(
        p, "synthetic", "0", "cp312-cp312-manylinux_2_17_x86_64", members={filename: bytes(header)}
    )
    if accepted:
        assert wheel_metadata(p, (2, 36), "3.12.8") == ("synthetic", "0")
    else:
        with pytest.raises(FoundationError, match="wheel_native"):
            wheel_metadata(p, (2, 36), "3.12.8")


@pytest.mark.parametrize(
    "attack",
    [
        "config_digest",
        "manifest_digest",
        "layer_digest",
        "missing_layer",
        "runtime_missing",
        "empty_layers",
    ],
)
def test_base_missing_or_mismatched_local_bytes(packet: SyntheticPacket, attack: str) -> None:
    base = packet.value["base_image_review"]
    if attack == "config_digest":
        base["config"] = packet.record_json(
            "other-config.json", {"os": "linux", "architecture": "amd64"}
        )
        # Different serialized bytes, still a well-formed same-platform config.
        base["config"] = packet.record_json(
            "other-config.json", {"os": "linux", "architecture": "amd64", "extra": True}
        )
    elif attack == "manifest_digest":
        packet.value["base_image"] = "docker.io/library/python@sha256:" + "1" * 64
    elif attack == "layer_digest":
        base["layers"][0] = packet.record("other-layer.bin", b"other layer bytes")
    elif attack == "empty_layers":
        base["layers"] = []
    else:
        record = base["layers"][0] if attack == "missing_layer" else base["runtime"]
        (packet.artifacts / record["file"]).unlink()
    packet.save()
    with pytest.raises(FoundationError):
        packet.check()


@pytest.mark.parametrize(
    "attack",
    [
        "null",
        "array",
        "duplicate_json",
        "missing_signature",
        "untrusted_key",
        "review_ttl",
        "boolean_time",
        "stale_source_inventory",
    ],
)
def test_malformed_evidence_cannot_escape_validation(packet: SyntheticPacket, attack: str) -> None:
    if attack == "null":
        packet.value["dependency_wheels"] = None
    elif attack == "array":
        packet.value["base_image_review"] = []
    elif attack == "untrusted_key":
        packet.value["review"]["key_id"] = "unenrolled-key"
    elif attack == "review_ttl":
        packet.value["review"]["expires_at"] = NOW + 604801
    elif attack == "boolean_time":
        packet.value["review"]["signed_at"] = True
    elif attack == "stale_source_inventory":
        packet.value["source_files"].pop(next(iter(packet.value["source_files"])))
    if attack in {"null", "array", "stale_source_inventory"}:
        packet.save()
    else:
        if attack == "missing_signature":
            del packet.value["review"]["signature_hex"]
        write_json(packet.manifest, packet.value)
        if attack == "duplicate_json":
            packet.manifest.write_text(
                '{"status":"REVIEWED_LOCAL_BUILD_INPUTS","status":"PENDING"}'
            )
    with pytest.raises(FoundationError):
        packet.check()


def test_supplied_report_cannot_be_edited_after_signing(packet: SyntheticPacket) -> None:
    packet.value["source_date_epoch"] -= 1
    write_json(packet.manifest, packet.value)
    with pytest.raises(FoundationError, match="review_signature_invalid"):
        packet.check()


def test_empty_review_dicts_are_rejected(packet: SyntheticPacket) -> None:
    packet.value["evidence"] = {}
    packet.value["review"]["signature_hex"] = packet.key.sign(review_bytes(packet.value)).hex()
    write_json(packet.manifest, packet.value)
    with pytest.raises(FoundationError, match="evidence_inventory"):
        packet.check()


def test_review_templates_are_pending_and_cannot_authorise_builds(tmp_path: Path) -> None:
    templates = ROOT / "deployment/containers/evidence-templates"
    files = sorted(templates.glob("*.json"))
    assert len(files) == 9
    for path in files:
        value = json.loads(path.read_text())
        if "status" in value:
            assert value["status"].startswith("PENDING_")
    trust = json.loads((templates / "reviewer-trust.template.json").read_text())
    assert trust["keys"] == []
    manifest = templates / "build-inputs.v2.template.json"
    assert json.loads(manifest.read_text())["review"]["signature_hex"] is None
    with pytest.raises(FoundationError, match="linux_inputs_pending"):
        validate_inputs(ROOT, manifest, tmp_path, file_hash(manifest))


@pytest.mark.parametrize(
    "field", ["not_before", "expires", "revoked", "public_key_hex", "reviewer"]
)
def test_malformed_trust_store_cannot_authenticate(packet: SyntheticPacket, field: str) -> None:
    data = json.loads(packet.trust.read_text())
    data["keys"][0][field] = None
    write_json(packet.trust, data)
    with pytest.raises(FoundationError):
        packet.check()


def test_database_freshness_is_checked_at_admission_not_only_signature_time(
    packet: SyntheticPacket,
) -> None:
    packet.reports["vulnerability"]["details"]["database_updated_at"] = NOW - 604750
    packet.save()
    with pytest.raises(FoundationError, match="vulnerability_database_stale"):
        validate_inputs(
            packet.root,
            packet.manifest,
            packet.artifacts,
            file_hash(packet.manifest),
            trust=packet.trust,
            trust_pin=file_hash(packet.trust),
            now=NOW + 90,
        )
