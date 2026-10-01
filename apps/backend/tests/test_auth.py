"""鉴权：Bearer 校验、豁免清单、空 token 放行、环境变量映射。

用例刻意选「在触库之前就会返回」的请求，避免测试创建真实库文件
（沿用 test_api_envelope / test_library_types 的既有做法）。
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from app.main import app
from app.shared.config import Settings, settings
from app.shared.constants import is_auth_exempt

TOKEN = "s3cret-token"
PROTECTED = "/library/resources"
VALIDATION_ONLY = "/library/resources/batch"
OVER_LIMIT_IDS = list(range(1, 202))


class AuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = settings.token
        settings.token = TOKEN

    def tearDown(self) -> None:
        settings.token = self._previous

    def _client(self) -> TestClient:
        return TestClient(app)

    def test_missing_header_is_unauthorized(self) -> None:
        res = self._client().get(PROTECTED)
        self.assertEqual(res.status_code, 401)
        body = res.json()
        self.assertEqual(body["code"], 401)
        self.assertEqual(body["status"], "error")
        self.assertEqual(body["message"], "未授权")
        self.assertIsNone(body["data"])

    def test_wrong_token_is_unauthorized(self) -> None:
        res = self._client().get(PROTECTED, headers={"Authorization": "Bearer wrong"})
        self.assertEqual(res.status_code, 401)

    def test_non_bearer_scheme_is_unauthorized(self) -> None:
        res = self._client().get(PROTECTED, headers={"Authorization": f"Token {TOKEN}"})
        self.assertEqual(res.status_code, 401)

    def test_valid_token_passes_through(self) -> None:
        # 201 个 id 在鉴权之后才被校验 → 422 说明请求已到达路由，未被 401 拦下
        res = self._client().post(
            VALIDATION_ONLY,
            json={"action": "trash", "ids": OVER_LIMIT_IDS},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        self.assertEqual(res.status_code, 422)

    def test_cors_preflight_is_not_blocked(self) -> None:
        # 浏览器预检不带 Authorization；被 401 拦下会导致真实请求根本发不出去
        res = self._client().options(
            PROTECTED,
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("access-control-allow-origin"), "*")

    def test_unauthorized_response_keeps_cors_headers(self) -> None:
        # CORS 必须是最外层，否则 401 没有 CORS 头，前端只能看到 Network Error
        res = self._client().get(PROTECTED, headers={"Origin": "http://localhost:5173"})
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.headers.get("access-control-allow-origin"), "*")

    def test_health_paths_are_exempt(self) -> None:
        client = self._client()
        for path in ("/health", "/library/health"):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 200)

    def test_openapi_is_exempt_and_unwrapped(self) -> None:
        res = self._client().get("/openapi.json")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("status", res.json())

    def test_media_proxy_is_exempt(self) -> None:
        # 缺 url 参数 → 422（校验阶段），说明鉴权没拦它
        res = self._client().get("/scrape/proxy-image")
        self.assertNotEqual(res.status_code, 401)
        self.assertEqual(res.status_code, 422)

    def test_media_content_paths_are_exempt_by_rule(self) -> None:
        self.assertTrue(is_auth_exempt("/library/resources/1/content"))
        self.assertTrue(is_auth_exempt("/library/resources/1/files/2/content"))
        self.assertFalse(is_auth_exempt(PROTECTED))
        self.assertFalse(is_auth_exempt("/library/resources/batch"))

    def test_token_value_is_not_logged(self) -> None:
        with self.assertLogs("backend", level="WARNING") as captured:
            res = self._client().get(PROTECTED, headers={"Authorization": f"Bearer {TOKEN}-leak"})
        self.assertEqual(res.status_code, 401)
        joined = "\n".join(captured.output)
        self.assertNotIn(TOKEN, joined)
        self.assertIn(PROTECTED, joined)

    def test_empty_token_disables_auth(self) -> None:
        settings.token = ""
        res = self._client().post(
            VALIDATION_ONLY,
            json={"action": "trash", "ids": OVER_LIMIT_IDS},
        )
        self.assertNotEqual(res.status_code, 401)
        self.assertEqual(res.status_code, 422)

    def test_backend_token_env_is_mapped(self) -> None:
        with mock.patch.dict(os.environ, {"BACKEND_TOKEN": "from-env"}, clear=False):
            self.assertEqual(Settings().token, "from-env")


if __name__ == "__main__":
    unittest.main()
