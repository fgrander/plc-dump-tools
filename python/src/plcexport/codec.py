"""``ExportModel`` <-> JSON.

The child process returns its model this way, and the core validates it before anything is
written. Decoding is driven by the dataclass type hints, so new model fields need no
codec changes.
"""

from __future__ import annotations

import base64
import dataclasses
import json
import types
import typing
from collections.abc import Mapping
from functools import cache
from typing import Any, Literal, Union, get_args, get_origin

from plcexport.model import ExportBundle, ExportModel


def _encode(obj: Any) -> Any:
    if isinstance(obj, bytes):  # native part files: base64, decoded by type hint
        return base64.b64encode(obj).decode("ascii")
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _encode(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Mapping):
        return {str(k): _encode(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [_encode(v) for v in obj]
    return obj


def model_to_dict(model: ExportModel) -> dict[str, Any]:
    out = _encode(model)
    assert isinstance(out, dict)
    return out


def model_to_json(model: ExportModel) -> str:
    return json.dumps(model_to_dict(model), ensure_ascii=False, sort_keys=True)


@cache
def _hints(cls: type) -> dict[str, Any]:
    return typing.get_type_hints(cls)


def _decode(tp: Any, value: Any) -> Any:
    if tp is Any:
        return value
    origin = get_origin(tp)
    if origin in (Union, types.UnionType):
        if value is None:
            return None
        options = [a for a in get_args(tp) if a is not type(None)]
        return _decode(options[0], value) if len(options) == 1 else value
    if origin is Literal:
        if value not in get_args(tp):
            raise ValueError(f"{value!r} is not one of {get_args(tp)}")
        return value
    if origin is tuple:
        args = get_args(tp)
        item = args[0] if len(args) == 2 and args[1] is Ellipsis else Any
        return tuple(_decode(item, v) for v in value)
    if origin is list:
        return [_decode(get_args(tp)[0], v) for v in value]
    if origin in (dict, Mapping, typing.Mapping) or tp in (dict, Mapping):
        args = get_args(tp)
        vt = args[1] if len(args) == 2 else Any
        return {str(k): _decode(vt, v) for k, v in value.items()}
    if origin is frozenset:
        return frozenset(_decode(get_args(tp)[0], v) for v in value)
    if isinstance(tp, type) and dataclasses.is_dataclass(tp):
        if not isinstance(value, dict):
            raise ValueError(f"expected an object for {tp.__name__}")
        hints = _hints(tp)
        known = {f.name for f in dataclasses.fields(tp)}
        unknown = set(value) - known
        if unknown:
            raise ValueError(f"unknown fields for {tp.__name__}: {sorted(unknown)}")
        return tp(**{k: _decode(hints[k], v) for k, v in value.items()})
    if tp is float and isinstance(value, int):
        return float(value)
    if tp is bytes:
        if not isinstance(value, str):
            raise ValueError(f"expected base64 text for bytes, got {type(value).__name__}")
        return base64.b64decode(value.encode("ascii"), validate=True)
    if isinstance(tp, type) and value is not None and not isinstance(value, tp):
        raise ValueError(f"expected {tp.__name__}, got {type(value).__name__}")
    return value


def model_from_dict(data: dict[str, Any]) -> ExportModel:
    model = _decode(ExportModel, data)
    assert isinstance(model, ExportModel)
    return model


def model_from_json(text: str) -> ExportModel:
    return model_from_dict(json.loads(text))


def bundle_to_dicts(bundle: ExportBundle) -> list[dict[str, Any]]:
    return [model_to_dict(m) for m in bundle.models]


def bundle_from_dicts(data: list[dict[str, Any]]) -> ExportBundle:
    return ExportBundle([model_from_dict(d) for d in data])
