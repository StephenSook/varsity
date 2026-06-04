"""Tests for SHA-256 corpus signing (LLM08 RAG-poisoning defense)."""

import json

import pytest

from app.rag import corpus_signature as cs
from app.rag.retriever import CORPUS, SIGNATURE, LawRetriever

_CHUNKS = [
    {"law": "11", "title": "Offside", "text": "An attacker is offside if..."},
    {"law": "12", "title": "Fouls and Misconduct", "text": "A direct free kick is..."},
]


def test_chunk_digest_is_deterministic_and_content_bound() -> None:
    d1 = cs.chunk_digest(_CHUNKS[0])
    d2 = cs.chunk_digest(dict(_CHUNKS[0]))
    assert d1 == d2 and len(d1) == 64  # sha256 hex
    tampered = {**_CHUNKS[0], "text": "An attacker is NEVER offside."}
    assert cs.chunk_digest(tampered) != d1


def test_build_and_verify_roundtrip() -> None:
    manifest = cs.build_manifest(_CHUNKS)
    ok, mismatches = cs.verify(_CHUNKS, manifest)
    assert ok is True and mismatches == []
    assert manifest["count"] == 2 and manifest["algorithm"] == "sha256"


def test_verify_fails_closed_on_tamper() -> None:
    manifest = cs.build_manifest(_CHUNKS)
    poisoned = [{**_CHUNKS[0], "text": "Offside is now legal."}, _CHUNKS[1]]
    ok, mismatches = cs.verify(poisoned, manifest)
    assert ok is False
    assert any("digest mismatch" in m for m in mismatches)
    assert any("root mismatch" in m for m in mismatches)
    with pytest.raises(cs.CorpusIntegrityError):
        cs.verify_or_raise(poisoned, manifest)


def test_verify_fails_closed_on_added_chunk() -> None:
    manifest = cs.build_manifest(_CHUNKS)
    extra = [*_CHUNKS, {"law": "99", "title": "Fake", "text": "Injected rule."}]
    ok, mismatches = cs.verify(extra, manifest)
    assert ok is False
    assert any("count" in m for m in mismatches)


def test_real_corpus_matches_its_committed_signature() -> None:
    chunks = json.loads(CORPUS.read_text())
    manifest = cs.load_manifest(SIGNATURE)
    assert manifest is not None, "the corpus must ship a signed manifest"
    ok, mismatches = cs.verify(chunks, manifest)
    assert ok is True, f"committed corpus does not match its signature: {mismatches}"


def test_retriever_verifies_the_real_corpus_on_load() -> None:
    # The default retriever loads + verifies the signed corpus (no raise == verified).
    r = LawRetriever()
    assert r.corpus_root is not None and len(r.corpus_root) == 64
