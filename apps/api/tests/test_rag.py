"""
RAG pipeline tests.

Embeddings are mocked with DETERMINISTIC fake vectors (not random) so
that similarity ordering is verifiable: two mocked vectors that are
identical should retrieve as the top match for each other, over a third,
unrelated vector. This proves the actual pgvector cosine-distance query
in document_repository.py works correctly, independent of real model
quality (which needs a gemini API key, unavailable in this sandbox).
"""
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.models.document import EMBEDDING_DIM
from app.services.ai.router import AIRouter
from app.services.rag_service import _chunk_text


def _fake_vector(seed: float) -> list[float]:
    """A simple deterministic vector: mostly zeros with one distinctive
    value, so cosine similarity between two `seed`-close vectors is
    predictably higher than between far-apart ones."""
    v = [0.0] * EMBEDDING_DIM
    v[0] = seed
    v[1] = 1.0  # keeps magnitude non-zero so cosine distance is well-defined
    return v


class TestChunking:
    def test_short_text_single_chunk(self):
        chunks = _chunk_text("hello world")
        assert chunks == ["hello world"]

    def test_empty_text_no_chunks(self):
        assert _chunk_text("") == []
        assert _chunk_text("   ") == []

    def test_long_text_produces_overlapping_chunks(self):
        text = "x" * 2000
        chunks = _chunk_text(text, chunk_size=800, overlap=100)
        assert len(chunks) == 3
        # verify actual overlap: end of chunk 1 should reappear at start of chunk 2
        assert chunks[0][-100:] == chunks[1][:100]


class TestIngestion:
    async def test_ingest_creates_indexed_document_with_chunks(
        self, client: AsyncClient, registered_business, monkeypatch
    ):
        headers = registered_business["headers"]

        async def fake_embed(self, text, *, input_type="passage"):
            return _fake_vector(1.0)

        monkeypatch.setattr(AIRouter, "create_embedding", fake_embed)

        r = await client.post(
            "/api/v1/documents",
            json={
                "title": "Supplier Agreement",
                "document_type": "invoice",
                "text": "Payment terms: net 30 days from invoice date. " * 30,
            },
            headers=headers,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "INDEXED"
        assert body["chunk_count"] > 0

    async def test_ingest_empty_text_rejected(self, client: AsyncClient, registered_business):
        r = await client.post(
            "/api/v1/documents",
            json={"title": "Empty", "text": " "},
            headers=registered_business["headers"],
        )
        assert r.status_code == 422

    async def test_embedding_failure_marks_document_failed(
        self, client: AsyncClient, registered_business, monkeypatch
    ):
        from app.services.ai.base import AIProviderTimeoutError

        async def failing_embed(self, text, *, input_type="passage"):
            raise AIProviderTimeoutError("simulated outage")

        monkeypatch.setattr(AIRouter, "create_embedding", failing_embed)

        r = await client.post(
            "/api/v1/documents",
            json={"title": "Doomed Doc", "text": "some content here"},
            headers=registered_business["headers"],
        )
        assert r.status_code == 503

        # Confirm the document was actually recorded as FAILED, not left
        # dangling in PROCESSING or silently absent.
        listing = await client.get("/api/v1/documents", headers=registered_business["headers"])
        assert any(d["title"] == "Doomed Doc" and d["status"] == "FAILED" for d in listing.json())


class TestRetrievalOrdering:
    async def test_similarity_search_ranks_closest_vector_first(
        self, client: AsyncClient, registered_business, monkeypatch
    ):
        """The real proof the pgvector query works: ingest two documents
        with distinctly different fake embeddings, then query with a
        vector close to one of them, and verify THAT one comes back
        ranked first — not just that retrieval returns something."""
        headers = registered_business["headers"]

        embed_calls = {"count": 0}

        async def fake_embed(self, text, *, input_type="passage"):
            embed_calls["count"] += 1
            # First ingested doc gets seed=1.0, second gets seed=100.0 (far apart)
            return _fake_vector(1.0) if embed_calls["count"] == 1 else _fake_vector(100.0)

        monkeypatch.setattr(AIRouter, "create_embedding", fake_embed)

        await client.post(
            "/api/v1/documents",
            json={"title": "Close Doc", "text": "This document is about pickle bottle pricing."},
            headers=headers,
        )
        await client.post(
            "/api/v1/documents",
            json={"title": "Far Doc", "text": "This document is about something unrelated."},
            headers=headers,
        )

        async def query_embed(self, text, *, input_type="query"):
            return _fake_vector(1.0)  # close to "Close Doc"'s vector

        monkeypatch.setattr(AIRouter, "create_embedding", query_embed)

        async def fake_answer(self, query, retrieved_context):
            return "mocked answer", "mocked_provider"

        monkeypatch.setattr(AIRouter, "generate_rag_answer", fake_answer)

        r = await client.post(
            "/api/v1/documents/query", json={"query": "what about pickle bottles?"}, headers=headers
        )
        assert r.status_code == 200
        body = r.json()
        assert body["sources"][0]["document_title"] == "Close Doc"

    async def test_query_respects_tenant_isolation(
        self, client: AsyncClient, registered_business, monkeypatch
    ):
        headers = registered_business["headers"]

        async def fake_embed(self, text, *, input_type="passage"):
            return _fake_vector(5.0)

        monkeypatch.setattr(AIRouter, "create_embedding", fake_embed)
        await client.post(
            "/api/v1/documents",
            json={"title": "Business A Doc", "text": "Confidential business A information."},
            headers=headers,
        )

        await client.post(
            "/api/v1/auth/register",
            json={"name": "Other", "email": "other-rag@example.com", "password": "password123"},
        )
        login = await client.post(
            "/api/v1/auth/login", json={"email": "other-rag@example.com", "password": "password123"}
        )
        await client.post(
            "/api/v1/businesses",
            json={"name": "Other RAG Biz", "currency": "INR"},
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )
        login2 = await client.post(
            "/api/v1/auth/login", json={"email": "other-rag@example.com", "password": "password123"}
        )
        other_headers = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        async def query_embed(self, text, *, input_type="query"):
            return _fake_vector(5.0)

        monkeypatch.setattr(AIRouter, "create_embedding", query_embed)

        async def fake_answer(self, query, retrieved_context):
            return ("no context" if not retrieved_context else "has context"), "mock"

        monkeypatch.setattr(AIRouter, "generate_rag_answer", fake_answer)

        r = await client.post(
            "/api/v1/documents/query", json={"query": "anything"}, headers=other_headers
        )
        assert r.status_code == 200
        assert r.json()["sources"] == []
        assert r.json()["has_sufficient_context"] is False


class TestQueryIntentThroughAgentGraph:
    async def test_query_command_routes_through_rag_agent(
        self, client: AsyncClient, registered_business, monkeypatch
    ):
        """Proves QUERY intent flows through the actual LangGraph
        (supervisor -> rag_agent), not a special-cased shortcut."""
        headers = registered_business["headers"]

        async def fake_embed(self, text, *, input_type="passage"):
            return [0.1] * EMBEDDING_DIM

        monkeypatch.setattr(AIRouter, "create_embedding", fake_embed)
        await client.post(
            "/api/v1/documents",
            json={"title": "Return Policy", "text": "Items can be returned within 7 days with a receipt."},
            headers=headers,
        )

        from app.services.ai.base import ParsedCommand
        from app.services.ai.providers.gemini_provider import GeminiProvider

        async def fake_parse(self, text, business_context):
            return ParsedCommand(
                intent="QUERY", confidence=0.95, entities={}, provider_used="gemini"
            )

        async def fake_rag_answer(self, query, retrieved_context):
            return "You can return items within 7 days with a receipt."

        monkeypatch.setattr(GeminiProvider, "parse_command", fake_parse)
        monkeypatch.setattr(GeminiProvider, "generate_rag_answer", fake_rag_answer)
        monkeypatch.setattr(GeminiProvider, "create_embedding", fake_embed)

        import app.api.v1.endpoints.voice_commands as vc_module
        from app.services.voice_command_service import VoiceCommandService as OrigService

        def patched_service(session):
            svc = OrigService(session)
            svc.ai_router = AIRouter(
                primary=GeminiProvider(
                    api_key="fake",
                    base_url="https://fake/v1",
                    model="fake",
                    timeout_seconds=5,
                    embedding_model="gemini-embedding-001",
                    embedding_dimension=EMBEDDING_DIM,
                )
            )
            return svc

        monkeypatch.setattr(GeminiProvider, "parse_command", fake_parse)
        monkeypatch.setattr(GeminiProvider, "generate_rag_answer", fake_rag_answer)
        monkeypatch.setattr(GeminiProvider, "create_embedding", fake_embed)
        r = await client.post(
            "/api/v1/voice-commands",
            json={"text": "what is your return policy?", "idempotency_key": "rag-query-1"},
            headers=headers,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "COMPLETED"
        assert body["intent"] == "QUERY"
        assert "7 days" in body["final_response"]
