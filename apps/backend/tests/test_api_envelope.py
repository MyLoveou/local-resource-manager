"""JSON 信封：成功与错误均含 code/status/message/data。"""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.shared.constants import (
    API_CODE_OK,
    API_STATUS_ERROR,
    API_STATUS_SUCCESS,
)


class ApiEnvelopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_wrapped(self) -> None:
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["code"], API_CODE_OK)
        self.assertEqual(body["status"], API_STATUS_SUCCESS)
        self.assertIn("message", body)
        self.assertEqual(body["data"]["status"], "ok")

    def test_not_found_wrapped(self) -> None:
        res = self.client.get("/this-route-does-not-exist")
        self.assertEqual(res.status_code, 404)
        body = res.json()
        self.assertEqual(body["code"], 404)
        self.assertEqual(body["status"], API_STATUS_ERROR)
        self.assertEqual(body["message"], "Not Found")
        self.assertIsNone(body["data"])

    def test_openapi_not_wrapped(self) -> None:
        res = self.client.get("/openapi.json")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("openapi", body)
        self.assertNotIn("status", body)

    def test_envelope_keeps_cors_header(self) -> None:
        res = self.client.get("/health", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("access-control-allow-origin"), "*")

    def test_validation_wrapped(self) -> None:
        res = self.client.post("/library/imports", json={})
        self.assertEqual(res.status_code, 422)
        body = res.json()
        self.assertEqual(body["code"], 422)
        self.assertEqual(body["status"], API_STATUS_ERROR)
        self.assertEqual(body["message"], "validation error")
        self.assertIsNotNone(body["data"])


if __name__ == "__main__":
    unittest.main()
