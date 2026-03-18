import hashlib


def make_triple_key(project_id: str, subject: str, predicate: str, object_: str) -> str:
    raw = f"{project_id}|{subject}|{predicate}|{object_}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
