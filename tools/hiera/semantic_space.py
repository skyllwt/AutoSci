"""Frozen semantic space and deterministic candidate proposals."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import HieraError, atomic_write_json, canonical_digest, read_json

SPACE_SCHEMA_VERSION = 1
_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _maps(space: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    dimensions = {dimension["id"]: dimension for dimension in space["dimensions"]}
    hypotheses = {
        hypothesis["id"]: dimension["id"]
        for dimension in space["dimensions"]
        for hypothesis in dimension["hypotheses"]
    }
    return dimensions, hypotheses


def validate_space(space: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(space, dict) or space.get("schema_version") != SPACE_SCHEMA_VERSION:
        errors.append(f"schema_version must be {SPACE_SCHEMA_VERSION}")
    dimensions = space.get("dimensions") if isinstance(space, dict) else None
    if not isinstance(dimensions, list) or not dimensions:
        return errors + ["dimensions must be a non-empty list"]

    dimension_ids: set[str] = set()
    hypothesis_ids: set[str] = set()
    hypothesis_to_dimension: dict[str, str] = {}
    for dimension in dimensions:
        if not isinstance(dimension, dict):
            errors.append("each dimension must be an object")
            continue
        dimension_id = dimension.get("id")
        if (
            not isinstance(dimension_id, str)
            or not _ID_RE.fullmatch(dimension_id)
            or not dimension_id.startswith("dim-")
        ):
            errors.append(f"invalid dimension id: {dimension_id!r}")
            continue
        if dimension_id in dimension_ids:
            errors.append(f"duplicate dimension id: {dimension_id}")
        dimension_ids.add(dimension_id)
        hypotheses = dimension.get("hypotheses")
        if not isinstance(hypotheses, list) or not hypotheses:
            errors.append(f"{dimension_id}: hypotheses must be non-empty")
            continue
        hypothesis_names: list[Any] = []
        for hypothesis in hypotheses:
            if not isinstance(hypothesis, dict):
                errors.append(f"{dimension_id}: hypothesis must be an object")
                continue
            hypothesis_id = hypothesis.get("id")
            hypothesis_names.append(hypothesis_id)
            if (
                not isinstance(hypothesis_id, str)
                or not _ID_RE.fullmatch(hypothesis_id)
                or not hypothesis_id.startswith("hyp-")
            ):
                errors.append(f"{dimension_id}: invalid hypothesis id: {hypothesis_id!r}")
                continue
            if hypothesis_id in hypothesis_ids:
                errors.append(f"duplicate hypothesis id: {hypothesis_id}")
            hypothesis_ids.add(hypothesis_id)
            hypothesis_to_dimension[hypothesis_id] = dimension_id
        if dimension.get("baseline_hypothesis_id") not in hypothesis_names:
            errors.append(f"{dimension_id}: baseline_hypothesis_id must name a hypothesis")

    relations = space.get("relations", [])
    if not isinstance(relations, list):
        errors.append("relations must be a list")
        relations = []
    for relation in relations:
        if not isinstance(relation, dict) or relation.get("type") not in {
            "activates",
            "requires",
            "excludes",
        }:
            errors.append("relation type must be activates, requires, or excludes")
            continue
        selectors = (
            relation.get("members", [])
            if relation["type"] == "excludes"
            else [relation.get("when"), relation.get("then")]
        )
        if not isinstance(selectors, list) or not selectors:
            errors.append("relation selectors missing")
            continue
        for selector in selectors:
            if not isinstance(selector, dict):
                errors.append("relation selector must be an object")
                continue
            dimension_id = selector.get("dimension_id")
            selected = selector.get("hypothesis_ids")
            if dimension_id not in dimension_ids or not isinstance(selected, list):
                errors.append("relation selector references an unknown dimension")
                continue
            if any(
                hypothesis_to_dimension.get(hypothesis_id) != dimension_id
                for hypothesis_id in selected
            ):
                errors.append("relation selector hypothesis belongs to another dimension")
    return errors


def load_space(path: Path) -> dict[str, Any]:
    space = read_json(path)
    if not isinstance(space, dict):
        raise HieraError(f"semantic space must be an object: {path}")
    errors = validate_space(space)
    if errors:
        raise HieraError("invalid semantic space: " + "; ".join(errors))
    base = {key: value for key, value in space.items() if key != "space_revision"}
    space["space_revision"] = canonical_digest(base)
    return space


def write_space(path: Path, space: dict[str, Any]) -> None:
    errors = validate_space(space)
    if errors:
        raise HieraError("invalid semantic space: " + "; ".join(errors))
    output = {key: value for key, value in space.items() if key != "space_revision"}
    output["space_revision"] = canonical_digest(output)
    atomic_write_json(path, output)


def baseline_point(space: dict[str, Any]) -> dict[str, str]:
    return {
        dimension["id"]: dimension["baseline_hypothesis_id"]
        for dimension in space["dimensions"]
    }


def point_id(point: dict[str, str], space_revision: str = "") -> str:
    payload = {"space_revision": space_revision, "point": dict(sorted(point.items()))}
    return "point-" + canonical_digest(payload)[7:23]


def _matches(point: dict[str, str], selector: Any) -> bool:
    return (
        isinstance(selector, dict)
        and point.get(selector.get("dimension_id")) in selector.get("hypothesis_ids", [])
    )


def validate_point(space: dict[str, Any], point: dict[str, str]) -> None:
    errors = validate_space(space)
    if errors:
        raise HieraError("cannot validate point against invalid space: " + "; ".join(errors))
    dimensions, hypothesis_to_dimension = _maps(space)
    if set(point) != set(dimensions):
        raise HieraError(
            f"point dimensions mismatch (expected {sorted(dimensions)}, got {sorted(point)})"
        )
    for dimension_id, hypothesis_id in point.items():
        if hypothesis_to_dimension.get(hypothesis_id) != dimension_id:
            raise HieraError(f"hypothesis {hypothesis_id!r} does not belong to {dimension_id}")
    for relation in space.get("relations", []):
        relation_type = relation["type"]
        if relation_type in {"requires", "activates"}:
            if _matches(point, relation.get("when")) and not _matches(
                point, relation.get("then")
            ):
                raise HieraError(
                    f"point violates {relation_type} relation "
                    f"{relation.get('id', '<unnamed>')}"
                )
        elif sum(_matches(point, member) for member in relation.get("members", [])) > 1:
            raise HieraError(
                f"point violates excludes relation {relation.get('id', '<unnamed>')}"
            )


def diff(parent: dict[str, str], child: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"dimension_id": dimension_id, "from": parent.get(dimension_id, ""), "to": child.get(dimension_id, "")}
        for dimension_id in sorted(set(parent) | set(child))
        if parent.get(dimension_id) != child.get(dimension_id)
    ]


def _complete_point(space: dict[str, Any], point: dict[str, str]) -> dict[str, str]:
    """Apply deterministic single-choice requires/activates closures."""
    for _ in range(len(space["dimensions"]) + 1):
        changed = False
        for relation in space.get("relations", []):
            if relation.get("type") not in {"requires", "activates"}:
                continue
            if not _matches(point, relation.get("when")):
                continue
            then = relation.get("then", {})
            choices = then.get("hypothesis_ids", [])
            dimension_id = then.get("dimension_id")
            if dimension_id and choices and point.get(dimension_id) not in choices:
                point[dimension_id] = sorted(choices)[0]
                changed = True
        if not changed:
            return point
    return point


def _active_hypotheses(dimension: dict[str, Any]) -> list[dict[str, Any]]:
    return [hypothesis for hypothesis in dimension["hypotheses"] if hypothesis.get("status") != "disabled"]


def propose(
    space: dict[str, Any],
    operation: str,
    parents: list[dict[str, str]],
    limit: int = 8,
) -> list[dict[str, Any]]:
    if operation not in {"fresh", "improve", "crossover"}:
        raise HieraError(f"unsupported operation: {operation}")
    if limit <= 0:
        return []
    revision = space.get("space_revision", canonical_digest(space))
    base = baseline_point(space)
    raw: list[dict[str, str]] = []
    if operation == "fresh":
        raw.append(dict(base))
        for dimension in space["dimensions"]:
            for hypothesis in _active_hypotheses(dimension):
                if hypothesis["id"] == dimension["baseline_hypothesis_id"]:
                    continue
                point = dict(base)
                point[dimension["id"]] = hypothesis["id"]
                raw.append(_complete_point(space, point))
    elif operation == "improve":
        for parent in parents or [base]:
            validate_point(space, parent)
            for dimension in space["dimensions"]:
                for hypothesis in _active_hypotheses(dimension):
                    if hypothesis["id"] == parent[dimension["id"]]:
                        continue
                    point = dict(parent)
                    point[dimension["id"]] = hypothesis["id"]
                    raw.append(_complete_point(space, point))
    else:
        parents = parents[:8]
        for index, first in enumerate(parents):
            validate_point(space, first)
            for second in parents[index + 1 :]:
                validate_point(space, second)
                first_child = {
                    dimension["id"]: (
                        first[dimension["id"]]
                        if dimension_index % 2 == 0
                        else second[dimension["id"]]
                    )
                    for dimension_index, dimension in enumerate(space["dimensions"])
                }
                second_child = {
                    dimension["id"]: (
                        second[dimension["id"]]
                        if dimension_index % 2 == 0
                        else first[dimension["id"]]
                    )
                    for dimension_index, dimension in enumerate(space["dimensions"])
                }
                raw.extend(
                    [_complete_point(space, first_child), _complete_point(space, second_child)]
                )

    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for point in raw:
        try:
            validate_point(space, point)
        except HieraError:
            continue
        candidate_id = point_id(point, revision)
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        result.append(
            {"point_id": candidate_id, "semantic_point": point, "change": diff(base, point)}
        )
        if len(result) >= limit:
            break
    return result


def default_space(experiment_slug: str, context: dict[str, Any]) -> dict[str, Any]:
    """Return a baseline-only draft that requires explicit user review."""
    return {
        "schema_version": SPACE_SCHEMA_VERSION,
        "space_id": f"hiera/{experiment_slug}/semantic-space",
        "source": "explicit-init-review-required",
        "dimensions": [
            {
                "id": "dim-method",
                "title": "Method mechanism",
                "definition": "User-specified method mechanism candidates.",
                "baseline_hypothesis_id": "hyp-baseline-method",
                "hypotheses": [
                    {
                        "id": "hyp-baseline-method",
                        "title": "Existing experiment method",
                        "kind": "baseline",
                        "status": "active",
                    }
                ],
            }
        ],
        "relations": [],
    }
