import asyncio

from app.core.config import get_settings
from app.services.ai.providers.gemini_provider import GeminiProvider


async def main() -> None:
    settings = get_settings()

    if not settings.llm_api_key:
        raise RuntimeError(
            "LLM_API_KEY is not available. Set it in apps/api/.env "
            "or your environment secrets."
        )

    provider = GeminiProvider(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_command_model,
        rag_model=settings.llm_rag_model,
        timeout_seconds=settings.ai_request_timeout_seconds,
        embedding_model=settings.embedding_model,
        embedding_dimension=settings.embedding_dimension,
    )

    print("1. Testing command parsing...")
    parsed = await provider.parse_command(
        "I sold 2 notebooks at 50 each"
    )
    print(f"   intent={parsed.intent}")
    print(f"   entities={parsed.entities}")
    print(f"   provider={parsed.provider_used}")
    print(f"   model={parsed.model_used}")

    print("\n2. Testing document embedding...")
    document_vector = await provider.create_embedding(
        "VyaparFlow has 12 notebooks in stock.",
        input_type="passage",
    )
    print(f"   dimension={len(document_vector)}")

    print("\n3. Testing query embedding...")
    query_vector = await provider.create_embedding(
        "How many notebooks are in stock?",
        input_type="query",
    )
    print(f"   dimension={len(query_vector)}")

    print("\n4. Testing RAG answer generation...")
    answer = await provider.generate_rag_answer(
        "How many notebooks are in stock?",
        ["VyaparFlow has 12 notebooks in stock."],
    )
    print(f"   answer={answer}")

    print("\nGemini smoke test passed.")


if __name__ == "__main__":
    asyncio.run(main())