import os
import sqlite3
import tempfile
import unittest
import gc


class _FakeUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeResponse:
    def __init__(self, prompt_tokens: int, completion_tokens: int):
        self.usage = _FakeUsage(prompt_tokens, completion_tokens)


class _FakeChatCompletions:
    def create(self, *args, **kwargs):
        return _FakeResponse(prompt_tokens=1000, completion_tokens=500)


class _FakeChat:
    def __init__(self):
        self.completions = _FakeChatCompletions()


class _FakeOpenAIClient:
    def __init__(self, *args, **kwargs):
        self.chat = _FakeChat()


class BasicTest(unittest.TestCase):
    def test_logs_cost_to_sqlite(self):
        with tempfile.TemporaryDirectory() as td:
            cwd = os.getcwd()
            try:
                os.chdir(td)

                import runcost

                # Patch the underlying OpenAI client constructor
                runcost._openai.OpenAI = _FakeOpenAIClient

                client = runcost.OpenAI()
                client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": "hello"}],
                )

                self.assertTrue(os.path.exists("runcost.db"))
                conn = sqlite3.connect("runcost.db")
                try:
                    row = conn.execute(
                        "SELECT model, prompt_tokens, completion_tokens, cost_usd FROM calls"
                    ).fetchone()
                finally:
                    conn.close()

                self.assertIsNotNone(row)
                model, pt, ct, cost = row
                self.assertEqual(model, "gpt-4o")
                self.assertEqual(int(pt), 1000)
                self.assertEqual(int(ct), 500)

                # gpt-4o: $0.005/1k input, $0.015/1k output
                expected = 1000 * (0.005 / 1000.0) + 500 * (0.015 / 1000.0)
                self.assertAlmostEqual(float(cost), expected, places=9)

                # Ensure all objects are released before temp dir cleanup on Windows
                del client
                gc.collect()
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()

