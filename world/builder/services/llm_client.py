from __future__ import annotations

import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from time import perf_counter
import uuid

from dataclasses import dataclass

import httpx

try:
    from django.conf import settings as django_settings
except Exception:  # pragma: no cover - Django may not be configured in plain unit tests
    django_settings = None


DEFAULT_LLM_BASE_URL = "http://192.168.200.246:1234"
DEFAULT_LLM_MODEL = "mistral-nemo-12b-instruct"
DEFAULT_LLM_TIMEOUT = 60.0
DEFAULT_LLM_TEMPERATURE = 0.5
_LLM_CHAT_COMPLETIONS_PATH = "/v1/chat/completions"
_LOG_NAME = "world.builder.llm_client"


@dataclass(frozen=True, slots=True)
class BuilderLLMConfig:
    llm_enabled: bool = False
    llm_base_url: str = DEFAULT_LLM_BASE_URL
    llm_model: str = DEFAULT_LLM_MODEL
    llm_temperature: float = DEFAULT_LLM_TEMPERATURE
    log_llm_calls: bool = True


class LLMError(RuntimeError):
    """Raised when the local LLM service cannot satisfy a generation request."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _log_path() -> Path:
    return _repo_root() / "logs" / "llm_calls.log"


def _build_logger() -> logging.Logger:
    logger = logging.getLogger(_LOG_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    log_path = _log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _coerce_bool(value: object, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _coerce_float(value: object, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        numeric = float(value if value not in (None, "") else default)
    except (TypeError, ValueError):
        numeric = default
    if minimum is not None:
        numeric = max(minimum, numeric)
    if maximum is not None:
        numeric = min(maximum, numeric)
    return numeric


def _config_value(name: str, settings_obj, default):
    env_value = os.getenv(name)
    if env_value not in (None, ""):
        return env_value
    if settings_obj is not None and hasattr(settings_obj, name):
        setting_value = getattr(settings_obj, name)
        if setting_value not in (None, ""):
            return setting_value
    return default


def load_llm_config(settings_obj=None) -> BuilderLLMConfig:
    config_source = settings_obj
    if config_source is None and django_settings is not None and getattr(django_settings, "configured", False):
        config_source = django_settings

    llm_enabled = _coerce_bool(
        _config_value("LLM_ENABLED", config_source, False),
        False,
    )
    llm_base_url = str(_config_value("LLM_BASE_URL", config_source, DEFAULT_LLM_BASE_URL)).strip() or DEFAULT_LLM_BASE_URL
    llm_model = str(_config_value("LLM_MODEL", config_source, DEFAULT_LLM_MODEL)).strip() or DEFAULT_LLM_MODEL
    llm_temperature = _coerce_float(
        _config_value("LLM_TEMPERATURE", config_source, DEFAULT_LLM_TEMPERATURE),
        DEFAULT_LLM_TEMPERATURE,
        minimum=0.0,
        maximum=1.5,
    )
    log_llm_calls = _coerce_bool(
        _config_value("LOG_LLM_CALLS", config_source, True),
        True,
    )
    return BuilderLLMConfig(
        llm_enabled=llm_enabled,
        llm_base_url=llm_base_url.rstrip("/"),
        llm_model=llm_model,
        llm_temperature=llm_temperature,
        log_llm_calls=log_llm_calls,
    )


def _extract_response_text(payload: dict) -> str:
    choices = list(payload.get("choices") or [])
    if not choices:
        raise LLMError("LLM response missing choices.")
    first_choice = dict(choices[0] or {})
    message = first_choice.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text") or ""))
            content = "".join(parts)
    else:
        content = first_choice.get("text")
    text = str(content or "").strip()
    if not text:
        raise LLMError("LLM response did not contain text.")
    return text


class LocalLLMClient:
    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: float | None = None):
        self.base_url = str(base_url or os.getenv("LLM_BASE_URL") or DEFAULT_LLM_BASE_URL).strip().rstrip("/")
        self.model = str(model or os.getenv("LLM_MODEL") or DEFAULT_LLM_MODEL).strip() or DEFAULT_LLM_MODEL
        raw_timeout = timeout if timeout is not None else os.getenv("LLM_TIMEOUT")
        try:
            self.timeout = float(raw_timeout if raw_timeout not in (None, "") else DEFAULT_LLM_TIMEOUT)
        except (TypeError, ValueError):
            self.timeout = DEFAULT_LLM_TIMEOUT
        self._logger = _build_logger()

    @property
    def completions_url(self) -> str:
        return f"{self.base_url}{_LLM_CHAT_COMPLETIONS_PATH}"

    def _log_call(self, *, correlation_id: str, prompt_hash: str, temperature: float, input_chars: int, output_chars: int, latency_ms: float, success: bool, error_type: str | None = None) -> None:
        self._logger.info(
            json.dumps(
                {
                    "timestamp": __import__("datetime").datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
                    "correlation_id": correlation_id,
                    "prompt_hash": prompt_hash,
                    "model": self.model,
                    "temperature": temperature,
                    "input_chars": input_chars,
                    "output_chars": output_chars,
                    "latency_ms": round(latency_ms, 2),
                    "success": success,
                    "error_type": error_type,
                },
                sort_keys=True,
            )
        )

    async def generate(self, prompt: str, max_tokens: int = 250, temperature: float = 0.75) -> str:
        correlation_id = uuid.uuid4().hex[:12]
        normalized_prompt = str(prompt or "")
        prompt_hash = _hash_prompt(normalized_prompt)
        started = perf_counter()
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": normalized_prompt}],
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
        }
        headers = {"X-Correlation-ID": correlation_id}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.completions_url, json=payload, headers=headers)
            try:
                response_payload = response.json()
            except ValueError:
                response_payload = {}
            if response.status_code >= 400:
                detail = response_payload.get("error") if isinstance(response_payload, dict) else None
                if isinstance(detail, dict):
                    detail = detail.get("message") or detail.get("type") or detail
                detail_text = str(detail or response.text or f"HTTP {response.status_code}").strip()
                raise LLMError(f"LLM API error [{correlation_id}]: {detail_text}")
            text = _extract_response_text(response_payload if isinstance(response_payload, dict) else {})
        except httpx.TimeoutException as error:
            latency_ms = (perf_counter() - started) * 1000.0
            self._log_call(
                correlation_id=correlation_id,
                prompt_hash=prompt_hash,
                temperature=float(temperature),
                input_chars=len(normalized_prompt),
                output_chars=0,
                latency_ms=latency_ms,
                success=False,
                error_type="timeout",
            )
            raise LLMError(f"LLM request timed out [{correlation_id}]: {error}") from error
        except httpx.ConnectError as error:
            latency_ms = (perf_counter() - started) * 1000.0
            self._log_call(
                correlation_id=correlation_id,
                prompt_hash=prompt_hash,
                temperature=float(temperature),
                input_chars=len(normalized_prompt),
                output_chars=0,
                latency_ms=latency_ms,
                success=False,
                error_type="connection_error",
            )
            raise LLMError(f"LLM connection failed [{correlation_id}]: {error}") from error
        except LLMError as error:
            latency_ms = (perf_counter() - started) * 1000.0
            self._log_call(
                correlation_id=correlation_id,
                prompt_hash=prompt_hash,
                temperature=float(temperature),
                input_chars=len(normalized_prompt),
                output_chars=0,
                latency_ms=latency_ms,
                success=False,
                error_type="api_error",
            )
            raise
        except httpx.HTTPError as error:
            latency_ms = (perf_counter() - started) * 1000.0
            self._log_call(
                correlation_id=correlation_id,
                prompt_hash=prompt_hash,
                temperature=float(temperature),
                input_chars=len(normalized_prompt),
                output_chars=0,
                latency_ms=latency_ms,
                success=False,
                error_type="http_error",
            )
            raise LLMError(f"LLM HTTP error [{correlation_id}]: {error}") from error

        latency_ms = (perf_counter() - started) * 1000.0
        self._log_call(
            correlation_id=correlation_id,
            prompt_hash=prompt_hash,
            temperature=float(temperature),
            input_chars=len(normalized_prompt),
            output_chars=len(text),
            latency_ms=latency_ms,
            success=True,
        )
        return text

    async def health(self) -> dict[str, object]:
        correlation_id = uuid.uuid4().hex[:12]
        started = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/v1/models", headers={"X-Correlation-ID": correlation_id})
            payload = response.json() if response.content else {}
            if response.status_code >= 400:
                detail = payload.get("error") if isinstance(payload, dict) else None
                if isinstance(detail, dict):
                    detail = detail.get("message") or detail.get("type") or detail
                detail_text = str(detail or response.text or f"HTTP {response.status_code}").strip()
                raise LLMError(f"LLM health check failed [{correlation_id}]: {detail_text}")
        except httpx.TimeoutException as error:
            raise LLMError(f"LLM health check timed out [{correlation_id}]: {error}") from error
        except httpx.ConnectError as error:
            raise LLMError(f"LLM health check connection failed [{correlation_id}]: {error}") from error
        except httpx.HTTPError as error:
            raise LLMError(f"LLM health check HTTP error [{correlation_id}]: {error}") from error

        latency_ms = (perf_counter() - started) * 1000.0
        return {
            "model": self.model,
            "base_url": self.base_url,
            "reachable": True,
            "latency_ms": round(latency_ms, 2),
        }