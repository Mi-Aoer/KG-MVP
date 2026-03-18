from typing import Any


def ok(data=None, message: str = "ok"):
    return {"code": 0, "message": message, "data": data}


def fail(code: int, message: str, data: Any | None = None):
    return {"code": code, "message": message, "data": data}
