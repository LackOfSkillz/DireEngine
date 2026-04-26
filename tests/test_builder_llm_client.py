import os
from pathlib import Path
import importlib.util
import sys
import unittest
from unittest.mock import AsyncMock, patch

import httpx


def _load_llm_client_module():
    module_path = Path(__file__).resolve().parents[1] / "world" / "builder" / "services" / "llm_client.py"
    spec = importlib.util.spec_from_file_location("tests._llm_client_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_llm_client_module = _load_llm_client_module()
DEFAULT_LLM_BASE_URL = _llm_client_module.DEFAULT_LLM_BASE_URL
DEFAULT_LLM_MODEL = _llm_client_module.DEFAULT_LLM_MODEL
DEFAULT_LLM_TIMEOUT = _llm_client_module.DEFAULT_LLM_TIMEOUT
LLMError = _llm_client_module.LLMError
LocalLLMClient = _llm_client_module.LocalLLMClient


class _MockResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


class BuilderLLMClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_posts_chat_completions_request_and_strips_text(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_MockResponse(payload={"choices": [{"message": {"content": "  Generated text.  "}}]}))
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_client
        mock_async_client.__aexit__.return_value = False

        with patch.object(_llm_client_module.httpx, "AsyncClient", return_value=mock_async_client):
            client = LocalLLMClient(base_url="http://example.test", model="demo-model", timeout=12)
            result = await client.generate("Describe this room.", max_tokens=111, temperature=0.33)

        self.assertEqual(result, "Generated text.")
        mock_client.post.assert_awaited_once()
        call_args = mock_client.post.await_args
        self.assertEqual(call_args.args[0], "http://example.test/v1/chat/completions")
        self.assertEqual(
            call_args.kwargs["json"],
            {
                "model": "demo-model",
                "messages": [{"role": "user", "content": "Describe this room."}],
                "max_tokens": 111,
                "temperature": 0.33,
            },
        )
        self.assertIn("X-Correlation-ID", call_args.kwargs["headers"])

    async def test_generate_raises_timeout_error_with_correlation_id(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ReadTimeout("slow"))
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_client
        mock_async_client.__aexit__.return_value = False

        with patch.object(_llm_client_module.httpx, "AsyncClient", return_value=mock_async_client):
            client = LocalLLMClient()
            with self.assertRaisesRegex(LLMError, r"timed out \[[0-9a-f]{12}\]"):
                await client.generate("Describe this room.")

    async def test_generate_raises_connection_error_with_correlation_id(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("offline"))
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_client
        mock_async_client.__aexit__.return_value = False

        with patch.object(_llm_client_module.httpx, "AsyncClient", return_value=mock_async_client):
            client = LocalLLMClient()
            with self.assertRaisesRegex(LLMError, r"connection failed \[[0-9a-f]{12}\]"):
                await client.generate("Describe this room.")

    async def test_generate_raises_api_error_for_non_success_response(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_MockResponse(status_code=503, payload={"error": {"message": "backend unavailable"}}))
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_client
        mock_async_client.__aexit__.return_value = False

        with patch.object(_llm_client_module.httpx, "AsyncClient", return_value=mock_async_client):
            client = LocalLLMClient()
            with self.assertRaisesRegex(LLMError, r"API error \[[0-9a-f]{12}\]: backend unavailable"):
                await client.generate("Describe this room.")

    async def test_generate_raises_api_error_for_missing_text(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_MockResponse(payload={"choices": [{"message": {"content": "   "}}]}))
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_client
        mock_async_client.__aexit__.return_value = False

        with patch.object(_llm_client_module.httpx, "AsyncClient", return_value=mock_async_client):
            client = LocalLLMClient()
            with self.assertRaisesRegex(LLMError, r"did not contain text"):
                await client.generate("Describe this room.")

    def test_client_loads_environment_defaults(self):
        with patch.dict(
            os.environ,
            {
                "LLM_BASE_URL": "http://env.example",
                "LLM_MODEL": "env-model",
                "LLM_TIMEOUT": "19",
            },
            clear=False,
        ):
            client = LocalLLMClient()

        self.assertEqual(client.base_url, "http://env.example")
        self.assertEqual(client.model, "env-model")
        self.assertEqual(client.timeout, 19.0)

    def test_client_uses_builtin_defaults_when_environment_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            client = LocalLLMClient()

        self.assertEqual(client.base_url, DEFAULT_LLM_BASE_URL)
        self.assertEqual(client.model, DEFAULT_LLM_MODEL)
        self.assertEqual(client.timeout, DEFAULT_LLM_TIMEOUT)

    def test_load_llm_config_reads_settings_values(self):
        config = _llm_client_module.load_llm_config(
            type(
                "Settings",
                (),
                {
                    "LLM_ENABLED": True,
                    "LLM_BASE_URL": "http://settings.example",
                    "LLM_MODEL": "settings-model",
                    "LLM_TEMPERATURE": 2.25,
                    "LOG_LLM_CALLS": False,
                },
            )()
        )

        self.assertTrue(config.llm_enabled)
        self.assertEqual(config.llm_base_url, "http://settings.example")
        self.assertEqual(config.llm_model, "settings-model")
        self.assertEqual(config.llm_temperature, 1.5)
        self.assertFalse(config.log_llm_calls)

    def test_load_llm_config_falls_back_to_environment(self):
        with patch.dict(
            os.environ,
            {
                "LLM_ENABLED": "true",
                "LLM_BASE_URL": "http://env-health.example",
                "LLM_MODEL": "env-health-model",
                "LLM_TEMPERATURE": "0.45",
                "LOG_LLM_CALLS": "0",
            },
            clear=True,
        ):
            config = _llm_client_module.load_llm_config(settings_obj=None)

        self.assertTrue(config.llm_enabled)
        self.assertEqual(config.llm_base_url, "http://env-health.example")
        self.assertEqual(config.llm_model, "env-health-model")
        self.assertEqual(config.llm_temperature, 0.45)
        self.assertFalse(config.log_llm_calls)


@unittest.skipUnless(os.getenv("LLM_BASE_URL"), "LLM_BASE_URL not set")
class BuilderLLMClientIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_hits_real_endpoint_when_configured(self):
        client = LocalLLMClient(timeout=10)
        result = await client.generate("Reply with exactly: test ok", max_tokens=20, temperature=0)
        self.assertIsInstance(result, str)
        self.assertTrue(result.strip())


if __name__ == "__main__":
    unittest.main()