from app.llm_parse import parse_llm_json


def test_parse_plain_json():
    content = '{"verdict":"True","confidence":0.9,"reasoning":"ok","citations":["Reuters"]}'
    parsed = parse_llm_json(content)
    assert parsed["verdict"] == "True"
    assert parsed["confidence"] == 0.9
    assert parsed["citations"] == ["Reuters"]


def test_parse_fenced_json():
    content = """
```json
{
  "verdict": "False",
  "confidence": 0.42,
  "reasoning": "mismatch",
  "citations": ["SEC"]
}
```
"""
    parsed = parse_llm_json(content)
    assert parsed["verdict"] == "False"
    assert parsed["confidence"] == 0.42
    assert parsed["citations"] == ["SEC"]


def test_parse_noisy_text_with_json():
    content = "Result below -> {\n  \"verdict\": \"Misleading\", \n  \"confidence\": 0.6, \n  \"reasoning\": \"partially supported\", \n  \"citations\": [\"AP\"]\n}\nThanks!"
    parsed = parse_llm_json(content)
    assert parsed["verdict"] == "Misleading"
    assert parsed["confidence"] == 0.6
    assert parsed["citations"] == ["AP"]
