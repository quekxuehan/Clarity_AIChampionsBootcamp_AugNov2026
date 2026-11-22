import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from rag import KNOWLEDGE_BASE, NEA_SOURCE_URLS, fetch_nea_sources, retrieve_chunks


class FakeResponse:
    def __init__(self, content, url):
        self.content = content
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def geturl(self):
        return self.url

    def read(self, size=-1):
        return self.content[:size]


class RetrieveChunksTests(unittest.TestCase):
    def test_returns_chunks_in_similarity_order(self):
        client = Mock()
        client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.0, 1.0])]
        )
        index = (
            (KNOWLEDGE_BASE[0], (1.0, 0.0)),
            (KNOWLEDGE_BASE[1], (0.0, 1.0)),
        )

        result = retrieve_chunks(client, index, "What does PSI mean?", top_k=1)

        self.assertEqual(result, (KNOWLEDGE_BASE[1],))

    def test_rejects_embeddings_with_different_dimensions(self):
        client = Mock()
        client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=[1.0, 0.0])]
        )
        index = ((KNOWLEDGE_BASE[0], (1.0,)),)

        with self.assertRaisesRegex(ValueError, "different dimensions"):
            retrieve_chunks(client, index, "Question")


class FetchNeaSourcesTests(unittest.TestCase):
    def test_extracts_text_from_allowlisted_pages(self):
        html = b"""
            <html><head><title>Hidden</title></head>
            <body>
                <a class="skip-link" href="#main">Skip to main</a>
                <nav>Navigation should be omitted</nav>
                <main><h1>Air quality</h1>
                    <p>NEA publishes air quality information.</p>
                    <script>Ignore this script</script>
                </main>
            </body></html>
        """
        responses = [FakeResponse(html, url) for _, url in NEA_SOURCE_URLS]

        with patch("rag.urlopen", side_effect=responses) as open_url:
            chunks = fetch_nea_sources()

        self.assertEqual(open_url.call_count, len(NEA_SOURCE_URLS))
        self.assertEqual(
            {chunk.url for chunk in chunks},
            {url for _, url in NEA_SOURCE_URLS},
        )
        self.assertTrue(all(chunk.title.startswith("NEA ") for chunk in chunks))
        combined = " ".join(chunk.content for chunk in chunks)
        self.assertIn("Air quality: NEA publishes air quality information.", combined)
        self.assertNotIn("Skip to main", combined)
        self.assertNotIn("Navigation should be omitted", combined)
        self.assertNotIn("Ignore this script", combined)

    def test_rejects_redirect_outside_nea(self):
        response = FakeResponse(
            b"<html><body><p>Content</p></body></html>",
            "https://example.com/content",
        )
        with patch("rag.urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "redirected outside"):
                fetch_nea_sources()


if __name__ == "__main__":
    unittest.main()
