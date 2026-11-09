"""Static APIM reference checks, explicitly not an APIM/C# policy runtime emulator."""

import json
import re
import xml.etree.ElementTree as ET
from hashlib import sha256
from pathlib import Path

from claims_ai.agent_tools.contracts import ALLOWLIST
from claims_ai.mcp_http.contracts import METHODS


def require(condition: bool, name: str) -> None:
    if not condition:
        raise ValueError("APIM reference invariant failed: " + name)


def validate_reference(root: Path) -> dict[str, object]:
    policy = (root / "mcp-policy.xml").read_bytes()
    bicep = (root / "reference.bicep").read_text()
    require(
        len(policy) <= 65536 and b"<!DOCTYPE" not in policy and b"<!ENTITY" not in policy,
        "bounded XML",
    )
    tree = ET.fromstring(policy)
    inbound = tree.find("inbound")
    require(inbound is not None, "inbound section")
    assert inbound is not None
    token = inbound.find("validate-azure-ad-token")
    require(token is not None, "Entra token validation")
    assert token is not None
    require(
        token.get("tenant-id") == "{{client-tenant-id}}"
        and token.get("header-name") == "Authorization",
        "pinned tenant/header",
    )
    require(token.findtext("audiences/audience") == "{{client-audience}}", "pinned client audience")
    require(
        token.findtext("client-application-ids/application-id") == "{{client-application-id}}",
        "client application allow-list",
    )
    role = token.find("required-claims/claim")
    require(
        role is not None
        and role.get("name") == "roles"
        and role.findtext("value") == "Claims.Read",
        "required client role",
    )
    rate = inbound.find("rate-limit-by-key")
    require(rate is not None, "rate policy")
    assert rate is not None
    require(rate.get("calls") == "12" and rate.get("renewal-period") == "60", "reviewed throttle")
    require(
        'context.Variables["validatedClient"]' in rate.get("counter-key", "")
        and "Headers" not in rate.get("counter-key", ""),
        "verified identity counter",
    )
    content = inbound.find("validate-content")
    require(content is not None, "request size policy")
    assert content is not None
    require(
        content.get("max-size") == "16384" and content.get("size-exceeded-action") == "prevent",
        "request limit",
    )
    guard = inbound.find("set-variable")
    require(guard is not None, "RPC guard")
    assert guard is not None
    expression = guard.get("value", "")
    require(
        set(re.findall(r'tool == "([^"]+)"', expression)) == set(ALLOWLIST), "exact tool allow-list"
    )
    require(
        set(re.findall(r'method [!=]= "([^"]+)"', expression)) == set(METHODS),
        "exact method allow-list",
    )
    require(
        'context.Request.Method != "POST"' in expression
        and 'body["jsonrpc"] != "2.0"' in expression
        and "catch { return false; }" in expression,
        "fail-closed RPC parsing",
    )
    denial = inbound.find("choose/when/return-response/set-status")
    require(denial is not None and denial.get("code") == "403", "denied RPC response")
    identity = inbound.find("authentication-managed-identity")
    require(identity is not None, "backend managed identity")
    assert identity is not None
    require(
        identity.get("resource") == "{{backend-audience}}"
        and identity.get("ignore-error") == "false",
        "separate fail-closed backend audience",
    )
    deleted = {
        n.get("name"): n
        for n in inbound.findall("set-header")
        if n.get("exists-action") == "delete"
    }
    require(
        {"Authorization", "X-Claims-Grant", "X-Gateway-Principal", "X-Claim-Id", "X-Policy-Version"}
        <= set(deleted),
        "remove client authorization/context headers",
    )
    tags = [node.tag for node in inbound]
    require(
        tags.index("validate-azure-ad-token")
        < tags.index("rate-limit-by-key")
        < tags.index("choose")
        < tags.index("authentication-managed-identity"),
        "policy order",
    )
    forward = tree.find("backend/forward-request")
    require(
        forward is not None and forward.get("buffer-response") == "false", "streaming unbuffered"
    )
    require(
        b"context.Response.Body" not in policy
        and tree.find(".//trace") is None
        and tree.find(".//log-to-eventhub") is None,
        "no payload diagnostics",
    )
    require(
        json.loads(tree.findtext("on-error/return-response/set-body") or "null")
        == {"status": "error", "code": "gateway_rejected"},
        "safe errors",
    )
    require(
        "param deploymentEnabled bool = false" in bicep
        and "param prerequisitesVerified bool = false" in bicep,
        "disabled deployment defaults",
    )
    require(
        "var enabled = deploymentEnabled && prerequisitesVerified" in bicep, "prerequisite gate"
    )
    require(
        "Microsoft.ApiManagement/service@2025-09-01-preview' existing" in bicep
        and "type: 'mcp'" in bicep
        and "transportType: 'streamable'" in bicep,
        "existing service and MCP schema",
    )
    require(
        "protocols: ['https']" in bicep
        and "serviceUrl: 'https://${backendHost}'" in bicep
        and "subscriptionRequired: true" in bicep,
        "TLS/subscription defaults",
    )
    require(
        "bytes: 0" in bicep
        and bicep.count("body: { bytes: 0 }") == 4
        and "logClientIp: false" in bicep
        and "headers: []" in bicep,
        "empty diagnostics payload/header capture",
    )
    return {
        "validation_mode": "STATIC_ONLY_NOT_APIM_ENFORCEMENT",
        "policy_sha256": sha256(policy).hexdigest(),
        "bicep_sha256": sha256(bicep.encode()).hexdigest(),
        "tools": list(ALLOWLIST),
        "methods": list(METHODS),
        "checks": "XML structure, required security invariants and Bicep reference defaults",
    }
