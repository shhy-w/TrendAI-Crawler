from __future__ import annotations

from dataclasses import dataclass


class CrawlFailureType:
    AUTH_REQUIRED = "auth_required"
    RATE_LIMITED = "rate_limited"
    GUEST_TOKEN_DENIED = "guest_token_denied"
    NO_CONTENT = "no_content"
    NETWORK = "network"
    PARSER = "parser"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ClassifiedError:
    failure_type: str
    message: str
    debug_path: str | None = None


def classify_exception(exc: Exception) -> ClassifiedError:
    message = str(exc)
    lowered = message.lower()
    if "guest token" in lowered and ("401" in lowered or "403" in lowered):
        return ClassifiedError(CrawlFailureType.GUEST_TOKEN_DENIED, message, _extract_debug_path(message))
    if "429" in lowered or "rate" in lowered:
        return ClassifiedError(CrawlFailureType.RATE_LIMITED, message, _extract_debug_path(message))
    if "登录" in message or "login" in lowered or "auth" in lowered:
        return ClassifiedError(CrawlFailureType.AUTH_REQUIRED, message, _extract_debug_path(message))
    if "未采集到内容" in message or "no content" in lowered:
        return ClassifiedError(CrawlFailureType.NO_CONTENT, message, _extract_debug_path(message))
    if "timeout" in lowered or "connect" in lowered or "network" in lowered:
        return ClassifiedError(CrawlFailureType.NETWORK, message, _extract_debug_path(message))
    if "parse" in lowered or "json" in lowered or "queryid" in lowered:
        return ClassifiedError(CrawlFailureType.PARSER, message, _extract_debug_path(message))
    return ClassifiedError(CrawlFailureType.UNKNOWN, message, _extract_debug_path(message))


def _extract_debug_path(message: str) -> str | None:
    marker = "调试文件："
    if marker not in message:
        return None
    return message.split(marker, 1)[1].strip()
