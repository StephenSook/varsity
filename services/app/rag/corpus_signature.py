"""SHA-256 signing of the IFAB Law corpus (LLM08 RAG-poisoning defense).

The corpus (``index/chunks.json``) is the grounding for every spoken rule claim, so its
integrity matters: a poisoned chunk would silently corrupt an explanation a blind user
cannot visually fact-check. We hash each chunk at build time into a signed manifest
(``index/chunks.sig.json``) and verify it when the retriever loads, failing CLOSED on any
mismatch.

Deterministic, no model, no network. This is the kind of auditable boundary OWASP wants
paired with the probabilistic Guardian: a tampered corpus is caught by arithmetic, not by
a model that might miss it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ALGORITHM = "sha256"


class CorpusIntegrityError(RuntimeError):
    """Raised when the corpus does not match its signed manifest (fail closed)."""


def chunk_digest(chunk: dict) -> str:
    """A stable SHA-256 over a chunk's canonical content (law + title + text)."""
    canonical = json.dumps(
        {"law": chunk["law"], "title": chunk["title"], "text": chunk["text"]},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def corpus_root(chunks: list[dict]) -> str:
    """A single root hash over the SORTED per-chunk digests (order-independent), so a
    reordered corpus still verifies but any content change flips the root."""
    digests = sorted(chunk_digest(c) for c in chunks)
    return hashlib.sha256("\n".join(digests).encode("utf-8")).hexdigest()


def build_manifest(chunks: list[dict]) -> dict:
    return {
        "algorithm": ALGORITHM,
        "count": len(chunks),
        "root": corpus_root(chunks),
        "chunks": {c["law"]: chunk_digest(c) for c in chunks},
    }


def verify(chunks: list[dict], manifest: dict) -> tuple[bool, list[str]]:
    """Recompute the digests and compare to the signed manifest. Returns (ok, mismatches)."""
    mismatches: list[str] = []
    signed = manifest.get("chunks", {})
    if len(chunks) != manifest.get("count"):
        mismatches.append(f"count {len(chunks)} != signed {manifest.get('count')}")
    for c in chunks:
        want = signed.get(c["law"])
        got = chunk_digest(c)
        if want is None:
            mismatches.append(f"law {c['law']} not in manifest")
        elif want != got:
            mismatches.append(f"law {c['law']} digest mismatch")
    if corpus_root(chunks) != manifest.get("root"):
        mismatches.append("root mismatch")
    return (not mismatches), mismatches


def verify_or_raise(chunks: list[dict], manifest: dict) -> str:
    ok, mismatches = verify(chunks, manifest)
    if not ok:
        raise CorpusIntegrityError("corpus integrity check failed: " + "; ".join(mismatches))
    return str(manifest["root"])


def load_manifest(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def sign_file(corpus_path: Path, out_path: Path) -> dict:
    """Build-time signer: hash the corpus and write the manifest. Re-run after any
    deliberate corpus edit (``python -m app.rag.corpus_signature``)."""
    chunks = json.loads(corpus_path.read_text())
    manifest = build_manifest(chunks)
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


if __name__ == "__main__":
    here = Path(__file__).resolve().parent / "index"
    m = sign_file(here / "chunks.json", here / "chunks.sig.json")
    print(f"signed {m['count']} chunks, root {m['root'][:16]}...")
