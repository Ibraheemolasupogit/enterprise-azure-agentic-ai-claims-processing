"""Static policy safeguards; no APIM policy execution or Azure deployment is simulated as real."""

from pathlib import Path

import pytest

from claims_ai.mcp_http.policy_validation import validate_reference

ROOT = Path(__file__).resolve().parents[1] / "infra/apim"


def test_reference_policy_is_explicitly_static_and_fail_closed() -> None:
    result = validate_reference(ROOT)
    assert result["validation_mode"] == "STATIC_ONLY_NOT_APIM_ENFORCEMENT"
    tools = result["tools"]
    assert isinstance(tools, list) and len(tools) == 3


@pytest.mark.parametrize("claim_name", ["unrelated", "role", "Roles", ""])
def test_required_role_value_under_another_claim_name_is_rejected(
    tmp_path: Path, claim_name: str
) -> None:
    text = (ROOT / "mcp-policy.xml").read_text()
    assert '<claim name="roles"' in text
    (tmp_path / "mcp-policy.xml").write_text(
        text.replace('<claim name="roles"', f'<claim name="{claim_name}"')
    )
    (tmp_path / "reference.bicep").write_bytes((ROOT / "reference.bicep").read_bytes())
    with pytest.raises(ValueError, match="required client role"):
        validate_reference(tmp_path)


@pytest.mark.parametrize(
    "fault",
    [
        "jwt",
        "audience",
        "role",
        "rate",
        "request_limit",
        "tools",
        "backend_identity",
        "streaming",
        "diagnostics",
        "unsafe_error",
    ],
)
def test_policy_security_regressions_are_rejected(tmp_path: Path, fault: str) -> None:
    text = (ROOT / "mcp-policy.xml").read_text()
    replacements = {
        "jwt": ("validate-azure-ad-token", "validate-jwt"),
        "audience": ("{{client-audience}}", "untrusted"),
        "role": ("Claims.Read", "Any.Role"),
        "rate": ('calls="12"', 'calls="999"'),
        "request_limit": ('max-size="16384"', 'max-size="999999"'),
        "tools": ("read_rule_findings", "settle_claim"),
        "backend_identity": ('ignore-error="false"', 'ignore-error="true"'),
        "streaming": ('buffer-response="false"', 'buffer-response="true"'),
        "diagnostics": ("<outbound>", "<outbound><!-- context.Response.Body -->"),
        "unsafe_error": ("gateway_rejected", "raw-exception-details"),
    }
    old, new = replacements[fault]
    (tmp_path / "mcp-policy.xml").write_text(text.replace(old, new))
    (tmp_path / "reference.bicep").write_bytes((ROOT / "reference.bicep").read_bytes())
    with pytest.raises(ValueError):
        validate_reference(tmp_path)


@pytest.mark.parametrize("fault", ["deploy", "prerequisites", "tls", "protocol", "payload_logging"])
def test_bicep_reference_security_defaults_cannot_silently_relax(
    tmp_path: Path, fault: str
) -> None:
    text = (ROOT / "reference.bicep").read_text()
    replacements = {
        "deploy": ("param deploymentEnabled bool = false", "param deploymentEnabled bool = true"),
        "prerequisites": (
            "param prerequisitesVerified bool = false",
            "param prerequisitesVerified bool = true",
        ),
        "tls": ("serviceUrl: 'https://${backendHost}'", "serviceUrl: 'http://${backendHost}'"),
        "protocol": ("transportType: 'streamable'", "transportType: 'sse'"),
        "payload_logging": ("body: { bytes: 0 }", "body: { bytes: 1024 }"),
    }
    old, new = replacements[fault]
    (tmp_path / "reference.bicep").write_text(text.replace(old, new))
    (tmp_path / "mcp-policy.xml").write_bytes((ROOT / "mcp-policy.xml").read_bytes())
    with pytest.raises(ValueError):
        validate_reference(tmp_path)
