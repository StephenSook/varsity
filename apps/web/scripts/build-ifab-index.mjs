// Re-emit the Docling-ingested IFAB Law corpus as a static browser asset so the
// offline path can run REAL retrieval in-browser (Orama BM25) instead of a hardcoded
// Law string. Source of truth is the committed FAISS-sidecar chunks the backend uses.
//   node scripts/build-ifab-index.mjs
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const src = resolve(here, '../../../services/app/rag/index/chunks.json')
const out = resolve(here, '../public/ifab-index.json')

const chunks = JSON.parse(readFileSync(src, 'utf8')).map((c) => ({
  law: c.law,
  title: c.title,
  text: c.text,
}))
writeFileSync(out, JSON.stringify(chunks))
console.log(`wrote ${out} (${chunks.length} IFAB chunks, ${(JSON.stringify(chunks).length / 1024) | 0} KB)`)
