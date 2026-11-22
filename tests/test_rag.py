import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from rag import KNOWLEDGE_BASE, retrieve_chunks


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


if __name__ == "__main__":
    unittest.main()
