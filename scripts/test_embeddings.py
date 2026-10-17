import asyncio
from app.integrations.embeddings.client import EmbeddingClient


async def main() -> None:
    client = EmbeddingClient()
    try:
        texts = [
            "2 bedroom apartment in Dubai Marina",
            "villa with private pool",
        ]
        vectors = await client.embed_documents(texts)
        print(f"Success! Generated {len(vectors)} embeddings.")
        print(f"Dimension of first vector: {len(vectors[0])}")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
