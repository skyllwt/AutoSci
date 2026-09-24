"""Deterministic bounded parameter tuning for admitted candidate snapshots."""

from __future__ import annotations

import itertools
import math
from typing import Any

from .common import HieraError, canonical_digest, finite_number


def _field_specs(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields = schema.get("fields", schema)
    if not isinstance(fields, dict):
        raise HieraError("candidate.config_schema must contain a fields object")
    if any(not isinstance(name, str) or not isinstance(spec, dict) for name, spec in fields.items()):
        raise HieraError("each config_schema field must be an object")
    return fields


def validate_config(schema: dict[str, Any], config: dict[str, Any]) -> None:
    if not isinstance(config, dict):
        raise HieraError("candidate config must be an object")
    for name, spec in _field_specs(schema).items():
        if name not in config:
            if spec.get("required", False):
                raise HieraError(f"candidate config is missing required field: {name}")
            continue
        value = config[name]
        kind = spec.get("type")
        if kind == "float" and not finite_number(value):
            raise HieraError(f"config field {name} must be a finite number")
        if kind == "int" and (not isinstance(value, int) or isinstance(value, bool)):
            raise HieraError(f"config field {name} must be an integer")
        if kind == "categorical" and value not in spec.get("values", []):
            raise HieraError(f"config field {name} is outside its categorical values")
        if kind not in {"float", "int", "categorical"}:
            raise HieraError(f"unsupported config field type for {name}: {kind!r}")
        if kind in {"float", "int"}:
            low, high = spec.get("min"), spec.get("max")
            if not finite_number(low) or not finite_number(high) or low > high or not low <= value <= high:
                raise HieraError(f"config field {name} is outside its min/max bounds")


def _values(name: str, spec: dict[str, Any], current: Any) -> list[Any]:
    kind = spec.get("type")
    if kind == "categorical":
        values = spec.get("values")
        if not isinstance(values, list) or not values:
            raise HieraError(f"config field {name} needs a non-empty values list")
        return list(values)
    low, high = spec.get("min"), spec.get("max")
    if not finite_number(low) or not finite_number(high) or low > high:
        raise HieraError(f"config field {name} needs finite min <= max")
    if kind == "int":
        values = sorted({int(low), int(round((low + high) / 2)), int(high)})
    elif spec.get("scale") == "log" and low > 0:
        values = [low, math.sqrt(low * high), high]
    else:
        values = [low, (low + high) / 2, high]
    if current in values:
        values.remove(current)
    return values


def propose_configs(
    schema: dict[str, Any],
    base_config: dict[str, Any],
    tried_configs: list[dict[str, Any]],
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Generate a deterministic bounded Cartesian neighborhood."""
    validate_config(schema, base_config)
    fields = _field_specs(schema)
    if not fields or limit <= 0:
        return []
    names = sorted(fields)
    choices = [_values(name, fields[name], base_config.get(name)) for name in names]
    tried = {canonical_digest(config) for config in tried_configs}
    output: list[dict[str, Any]] = []
    for combination in itertools.product(*choices):
        config = dict(base_config)
        config.update(dict(zip(names, combination)))
        if canonical_digest(config) in tried:
            continue
        validate_config(schema, config)
        output.append(config)
        if len(output) >= limit:
            break
    return output
