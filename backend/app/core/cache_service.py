"""Redis caching service for job matching scores and extracted keywords."""
import json
import uuid

import redis

from app.core.config import settings


class CacheService:
    """Wraps Redis with typed get/set helpers for Phase 10A caching."""

    SCORE_TTL_SECONDS = 24 * 3600   # 24 hours
    KEYWORD_TTL_SECONDS = 7 * 86400  # 7 days
    JOB_FEED_TTL_SECONDS = 3600      # 1 hour

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        if redis_client is not None:
            self._redis = redis_client
        else:
            self._redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    # ------------------------------------------------------------------
    # Match scores
    # ------------------------------------------------------------------

    def get_cached_score(self, user_id: uuid.UUID, job_id: uuid.UUID) -> dict | None:
        key = self._score_key(user_id, job_id)
        raw = self._redis.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_cached_score(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        score_data: dict,
        ttl_hours: int = 24,
    ) -> None:
        key = self._score_key(user_id, job_id)
        self._redis.setex(key, ttl_hours * 3600, json.dumps(score_data))

    def invalidate_score(self, user_id: uuid.UUID, job_id: uuid.UUID) -> None:
        self._redis.delete(self._score_key(user_id, job_id))

    def invalidate_all_scores_for_user(self, user_id: uuid.UUID) -> None:
        """Remove all cached scores for a user (e.g., after CV update)."""
        pattern = f"score:{user_id}:*"
        keys = list(self._redis.scan_iter(pattern))
        if keys:
            self._redis.delete(*keys)

    # ------------------------------------------------------------------
    # Extracted keywords
    # ------------------------------------------------------------------

    def get_cached_keywords(self, job_id: uuid.UUID) -> dict | None:
        raw = self._redis.get(self._keyword_key(job_id))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_cached_keywords(
        self,
        job_id: uuid.UUID,
        keywords: dict,
        ttl_days: int = 7,
    ) -> None:
        self._redis.setex(self._keyword_key(job_id), ttl_days * 86400, json.dumps(keywords))

    # ------------------------------------------------------------------
    # Job feed (list responses)
    # ------------------------------------------------------------------

    def get_cached_job_feed(self, cache_key: str) -> list | None:
        raw = self._redis.get(f"feed:{cache_key}")
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_cached_job_feed(self, cache_key: str, jobs: list, ttl_hours: int = 1) -> None:
        self._redis.setex(f"feed:{cache_key}", ttl_hours * 3600, json.dumps(jobs))

    def invalidate_job_feed(self) -> None:
        """Invalidate all cached job feeds (e.g., after new scrape)."""
        keys = list(self._redis.scan_iter("feed:*"))
        if keys:
            self._redis.delete(*keys)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _score_key(self, user_id: uuid.UUID, job_id: uuid.UUID) -> str:
        return f"score:{user_id}:{job_id}"

    def _keyword_key(self, job_id: uuid.UUID) -> str:
        return f"keywords:{job_id}"
