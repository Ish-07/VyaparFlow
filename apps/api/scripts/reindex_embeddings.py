from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal, engine
from app.models.document import Document, DocumentChunk
from app.services.ai.router import AIRouter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("vyaparflow.reindex")


async def reindex_document(
    document_id,
    ai_router: AIRouter,
    delay_seconds: float,
) -> tuple[str, int, str | None]:
    async with AsyncSessionLocal() as session:
        document = await session.get(Document, document_id)

        if document is None:
            return str(document_id), 0, "document_not_found"

        chunks_result = await session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.created_at)
        )
        chunks = list(chunks_result.scalars().all())

        if not chunks:
            document.status = "FAILED"
            await session.commit()
            return str(document_id), 0, "document_has_no_chunks"

        # Persist PROCESSING before making API calls.
        document.status = "PROCESSING"
        await session.commit()

        try:
            for index, chunk in enumerate(chunks, start=1):
                logger.info(
                    "Document %s: embedding chunk %d/%d",
                    document_id,
                    index,
                    len(chunks),
                )

                chunk.embedding = await ai_router.create_embedding(
                    chunk.chunk_text,
                    input_type="passage",
                )

                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)

            document.status = "INDEXED"
            await session.commit()

            return str(document_id), len(chunks), None

        except Exception as exc:
            logger.exception(
                "Document %s failed during re-indexing",
                document_id,
            )

            await session.rollback()

            # Keep failed documents clearly marked while allowing
            # the remaining documents to continue.
            await session.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(status="FAILED")
            )
            await session.commit()

            return str(document_id), 0, str(exc)


async def main(delay_seconds: float) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Document.id).order_by(Document.created_at)
        )
        document_ids = list(result.scalars().all())

    logger.info("Found %d document(s) to re-index", len(document_ids))

    ai_router = AIRouter()
    successful = 0
    failed = 0

    for document_id in document_ids:
        document_id_text, chunk_count, error = await reindex_document(
            document_id,
            ai_router,
            delay_seconds,
        )

        if error is None:
            successful += 1
            logger.info(
                "Document %s indexed successfully: %d chunk(s)",
                document_id_text,
                chunk_count,
            )
        else:
            failed += 1
            logger.error(
                "Document %s failed: %s",
                document_id_text,
                error,
            )

    logger.info(
        "Re-indexing complete: %d successful, %d failed",
        successful,
        failed,
    )

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Re-index all VyaparFlow document chunks with Gemini."
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Seconds to wait between embedding requests.",
    )
    args = parser.parse_args()

    asyncio.run(main(delay_seconds=args.delay))