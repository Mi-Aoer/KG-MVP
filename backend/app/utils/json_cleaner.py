import json
import re


REQUIRED_TRIPLE_KEYS = [
    "subject",
    "subject_type",
    "predicate",
    "object",
    "object_type",
]


class ParseError(Exception):
    pass


def _extract_first_json_array(text: str) -> str | None:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\[", text):
        start = match.start()
        try:
            data, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(data, list) and all(isinstance(item, dict) for item in data):
            return text[start : start + end].strip()
    return None


def clean_output_text(output_text: str) -> str:
    text = output_text.strip()
    text = re.sub(r"<think\b[^>]*>.*?</think>\s*", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    return _extract_first_json_array(text) or text


def extract_output_string(raw_response: str) -> str:
    try:
        obj = json.loads(raw_response)
    except Exception as exc:
        raise ParseError("RAW_RESPONSE_NOT_JSON") from exc

    if "output" not in obj:
        raise ParseError("OUTPUT_FIELD_MISSING")

    if not isinstance(obj["output"], str):
        raise ParseError("OUTPUT_TYPE_INVALID")

    return clean_output_text(obj["output"])


def parse_cleaned_output_text(output_text: str) -> list[dict]:
    try:
        data = json.loads(output_text)
    except Exception as exc:
        raise ParseError("INVALID_JSON_OUTPUT") from exc

    if not isinstance(data, list):
        raise ParseError("OUTPUT_NOT_ARRAY")

    triples: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            raise ParseError("TRIPLE_ITEM_NOT_OBJECT")
        for key in REQUIRED_TRIPLE_KEYS:
            if key not in item:
                raise ParseError(f"TRIPLE_FIELD_MISSING:{key}")

        triple = {
            "subject": str(item["subject"]).strip(),
            "subject_type": str(item["subject_type"]).strip(),
            "predicate": str(item["predicate"]).strip(),
            "object": str(item["object"]).strip(),
            "object_type": str(item["object_type"]).strip(),
        }
        if not all(triple.values()):
            raise ParseError("TRIPLE_FIELD_EMPTY")
        triples.append(triple)

    return triples


def parse_output_to_triples(raw_response: str) -> tuple[list[dict], str]:
    output_text = extract_output_string(raw_response)
    return parse_cleaned_output_text(output_text), output_text
