import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import create_app
from service import ExcerptSearch


class FinanceRAGTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = ExcerptSearch()
        cls.client = TestClient(create_app(cls.engine))

    def test_quarterly_sources(self):
        for quarter, profit in [(2, "10.44"), (3, "9.18")]:
            res = self.client.post("/api/chat", json={"q": f"삼성전자 2024년 {quarter}분기 실적"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn(profit, data["sources"][0]["text"])
            self.assertIn(data["sources"][0]["text"], data["answer"])
            self.assertIn(f"{quarter}분기", data["sources"][0]["url"])
            self.assertIsNone(data["adapter"])
            self.assertGreaterEqual(data["elapsed_ms"], 0)

    def test_empty_search(self):
        data = self.client.post("/api/chat", json={"q": "zzzzzz"}).json()
        self.assertEqual(data["sources"], [])

    def test_invalid_question(self):
        for q in ["", "   ", "가" * 601]:
            self.assertEqual(self.client.post("/api/chat", json={"q": q}).status_code, 422)

    def test_missing_adapter(self):
        res = self.client.post("/api/chat", json={"q": "반도체", "use_lora": True})
        self.assertEqual(res.status_code, 409)

    def test_engine_error(self):
        with patch.object(self.engine, "ask", side_effect=RuntimeError("model unavailable")):
            with self.assertLogs("app", level="ERROR"):
                res = self.client.post("/api/chat", json={"q": "반도체"})
        self.assertEqual(res.status_code, 503)
        self.assertNotIn("RuntimeError", res.text)


if __name__ == "__main__":
    unittest.main()
