# APIM MCP reference only

No Azure commands or deployment are provided. [Governance design](../../docs/deployment/apim-governance-reference.md) records identity separation, prerequisites and cost risks. Both resource gates default false. The existing APIM/logger, identity, network and backend must be supplied through separately approved future work; identifiers are placeholders, not secrets.

```sh
make apim-static-check
# Use an independently verified, locally available Bicep compiler:
make apim-compile BICEP=/path/to/bicep
```

The first command checks selected XML/Bicep security invariants without executing policy expressions. The second compiles [reference.bicep](reference.bicep) and [reference.dev.bicepparam](reference.dev.bicepparam) to ignored `outputs/apim/`; it does not contact Azure or validate live APIM behavior. [mcp-policy.xml](mcp-policy.xml) is a proposed gateway policy, not evidence of Entra authentication or enforcement.
