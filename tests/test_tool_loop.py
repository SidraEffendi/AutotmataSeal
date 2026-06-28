import unittest

from agents.tool_loop import _extract_failed_generation, _parse_json_generation


class ToolLoopParsingTests(unittest.TestCase):
    def test_parse_json_generation_accepts_single_object(self):
        parsed = _parse_json_generation('{"action":"answer","text":"done"}')
        self.assertEqual(parsed["action"], "answer")

    def test_parse_json_generation_accepts_concatenated_objects(self):
        parsed = _parse_json_generation('{"action":"call_tool","tool":"x","args":{}}\n{"action":"answer","text":"done"}')
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["action"], "call_tool")
        self.assertEqual(parsed[1]["text"], "done")

    def test_extract_failed_generation_from_exception_body(self):
        class FakeGroqError(Exception):
            body = {
                "error": {
                    "failed_generation": '{"action":"answer","text":"done"}'
                }
            }

        self.assertEqual(
            _extract_failed_generation(FakeGroqError("bad request")),
            '{"action":"answer","text":"done"}',
        )


if __name__ == "__main__":
    unittest.main()
