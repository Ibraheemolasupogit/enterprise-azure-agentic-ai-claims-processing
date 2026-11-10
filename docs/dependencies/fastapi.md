# FastAPI dependency and API record — M16

FastAPI **0.162.2** and annotated-doc **0.0.5** are the only two new distributions. The minimal optional `api` extra reuses existing Agent Framework 1.23.0, msgspec 0.22.0, Starlette 1.10.0 and httpx2 2.16.0. No standard/CLI, live provider, cloud or telemetry-exporter extra is installed.

Official [FastAPI release metadata](https://pypi.org/pypi/fastapi/0.162.2/json) requires Python >=3.10, Starlette >=0.46.0, Pydantic >=2.9.0, typing-extensions >=4.8.0, typing-inspection >=0.4.2, annotated-doc >=0.0.2 and opentelemetry-api >=1.44.0. The existing M13/M10 pins satisfy all requirements except the two additions. [annotated-doc metadata](https://pypi.org/pypi/annotated-doc/0.0.5/json) declares no runtime dependencies. Existing SDK/runtime pins are not upgraded.

The two official universal wheels were downloaded to a temporary wheelhouse, SHA-256 checked against official PyPI metadata before installation, then installed offline with `--no-index --no-deps`. [m16-wheel-manifest.json](../../requirements/m16-wheel-manifest.json) records URLs, versions and hashes; [m16-constraints.txt](../../requirements/m16-constraints.txt) nests the original M13/M10 closure. No wheel or vendor implementation is committed.

Genuine APIs exercised: `FastAPI`, `APIRouter`, Pydantic request/response validation, `HTTPBearer` OpenAPI security, typed Header/Path/Query dependencies, custom exception handlers, lifespan context, the actual FastAPI/Starlette `TestClient`, OpenAPI 3.1 generation and `fastapi.openapi.models.OpenAPI` validation. Existing jsonschema checks component schemas and an actual response without adding a validator dependency. References: [official testing guide](https://fastapi.tiangolo.com/tutorial/testing/), [lifespan guide](https://fastapi.tiangolo.com/advanced/events/).

Installed Starlette TestClient prefers the already pinned httpx2 distribution; no additional legacy httpx installation is necessary. Its ASGI server field is a two-item list, while other transports may use a tuple. M16 normalizes that representation and retains exact loopback/port checks. Tests do not replace FastAPI/router/client classes with HTTP-shaped mocks.

Recommended complete local environment:

```sh
.venv/bin/python -m pip install -c requirements/m16-constraints.txt '.[dev,mcp,api]'
```

Application and protocol execution are offline. PyPI package acquisition is dependency setup, not an Azure operation or authorization to deploy. The existing M14 non-editable installation convention remains appropriate on the managed macOS filesystem that hides editable `.pth` files.
