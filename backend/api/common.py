"""Shared API response helpers."""
from __future__ import annotations

from flask import jsonify


def ok(data=None):
    return jsonify({"code": 0, "message": "ok", "data": data if data is not None else {}})


def fail(code: int, message: str, status: int = 400, data=None):
    return jsonify({"code": code, "message": message, "data": data}), status
