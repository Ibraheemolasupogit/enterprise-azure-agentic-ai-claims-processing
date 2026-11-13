"""Fixed trusted native-text DEVELOPMENT parser; stdin contains inputs only, never labels."""

import json
import sys

from claims_ai.quality_ops.operational_contracts import (
    FIELDS,
    DevelopmentInput,
    DevelopmentPrediction,
    FieldName,
)


def predict(value: DevelopmentInput) -> DevelopmentPrediction:
    fields: dict[FieldName, str | None] = {}
    for key in FIELDS:
        matches = [
            line.split("=", 1)[1].strip()
            for line in value.text.splitlines()
            if line.startswith(key.upper() + "=")
        ]
        result = matches[0] if len(matches) == 1 else None
        if result is not None and key == "estimate_pence":
            normalized = result.replace(",", "")
            result = str(int(normalized)) if normalized.isdecimal() else None
        if result is not None and key == "currency":
            result = result.upper()
        fields[key] = result
    return DevelopmentPrediction(case_id=value.case_id, fields=fields)


def main() -> None:
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise ValueError("input capacity")
        data = json.loads(raw)
        if set(data) != {"inputs"} or not 1 <= len(data["inputs"]) <= 16:
            raise ValueError("input protocol")
        inputs = tuple(DevelopmentInput.model_validate(v) for v in data["inputs"])
        results = [predict(v).model_dump(mode="json") for v in inputs]
        if any(
            name.endswith((".references", ".development_labels", ".candidate"))
            for name in sys.modules
        ):
            raise ValueError("reference import in prediction process")
        content = json.dumps(results, sort_keys=True)
        if len(content) > 65536:
            raise ValueError("output capacity")
        print(content)
    except Exception:
        raise SystemExit(3) from None


if __name__ == "__main__":
    main()
