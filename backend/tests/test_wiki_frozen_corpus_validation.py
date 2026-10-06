import pytest
import test_wiki_docs_mcp as fixtures

from app.modules.wiki.mcps.docs.corpus import corpus_digest, load_corpus

frozen_corpus = fixtures.corpus


@pytest.mark.parametrize("excluded_path", [None, "../secret.md", "docs/secrets/private.md"])
def test_excluded_entries_are_preserved_without_authorizing_chunks(
    frozen_corpus, tmp_path, excluded_path
):
    excluded = frozen_corpus.manifest.entries[0].model_copy(
        update={"included": False, "status": "historical", "sha256": None}
    )
    if excluded_path is not None:
        excluded = excluded.model_copy(update={"path": excluded_path})
    frozen_corpus.manifest.entries.insert(0, excluded)
    path = tmp_path / "corpus.json"
    fixtures.save_corpus(path, frozen_corpus)
    assert load_corpus(path) == frozen_corpus


@pytest.mark.parametrize("approved_hash", [None, "", "different"])
def test_approved_document_requires_matching_chunk_hash(frozen_corpus, tmp_path, approved_hash):
    frozen_corpus.manifest.entries[0] = frozen_corpus.manifest.entries[0].model_copy(
        update={"sha256": approved_hash}
    )
    path = tmp_path / "corpus.json"
    fixtures.save_corpus(path, frozen_corpus)
    with pytest.raises(ValueError, match=r"^Chunk outside the approved manifest$"):
        load_corpus(path)


def test_unknown_chunk_path_rejected_even_with_approved_hash(frozen_corpus, tmp_path):
    frozen_corpus.chunks[0] = frozen_corpus.chunks[0].model_copy(
        update={"source_path": "domain-docs/catasto/docs/unknown.md"}
    )
    path = tmp_path / "corpus.json"
    fixtures.save_corpus(path, frozen_corpus)
    with pytest.raises(ValueError, match=r"^Chunk outside the approved manifest$"):
        load_corpus(path)


def test_chunk_ids_are_unique_across_documents(frozen_corpus, tmp_path):
    first = frozen_corpus.chunks[0]
    other_index = next(
        index
        for index, chunk in enumerate(frozen_corpus.chunks)
        if chunk.source_path != first.source_path
    )
    frozen_corpus.chunks[other_index] = frozen_corpus.chunks[other_index].model_copy(
        update={"chunk_id": first.chunk_id}
    )
    path = tmp_path / "corpus.json"
    fixtures.save_corpus(path, frozen_corpus)
    with pytest.raises(ValueError, match=r"^Duplicate chunk ID$"):
        load_corpus(path)


@pytest.mark.parametrize(
    ("integrity_valid", "policy_valid", "message"),
    [
        (False, False, "Frozen corpus integrity check failed"),
        (True, False, "Frozen corpus violates the manifest policy"),
        (True, True, "Chunk outside the approved manifest"),
    ],
)
def test_validation_failure_precedence(
    frozen_corpus, tmp_path, integrity_valid, policy_valid, message
):
    if not policy_valid:
        frozen_corpus.manifest.entries[0] = frozen_corpus.manifest.entries[0].model_copy(
            update={"status": "historical"}
        )
    frozen_corpus.chunks.append(
        frozen_corpus.chunks[0].model_copy(update={"document_hash": "wrong"})
    )
    frozen_corpus.corpus_version = (
        corpus_digest(frozen_corpus.manifest, frozen_corpus.chunks) if integrity_valid else "wrong"
    )
    path = tmp_path / "corpus.json"
    fixtures.save_corpus(path, frozen_corpus, recompute=False)
    with pytest.raises(ValueError, match=rf"^{message}$"):
        load_corpus(path)
