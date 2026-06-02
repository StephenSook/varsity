import { create, insertMultiple, search } from '@orama/orama'

// Fully in-browser IFAB Law retrieval. The same Docling-ingested corpus the backend
// uses is shipped as a static asset (public/ifab-index.json) and searched on-device
// with Orama (BM25), so the offline path RETRIEVES the governing Law in the browser
// instead of carrying a hardcoded Law string. No network beyond fetching the static
// index once (the service worker caches it for true airplane-mode use).

export type IfabChunk = { law: string; title: string; text: string }

let _db: Awaited<ReturnType<typeof create>> | null = null

async function getDb() {
  if (_db) return _db
  const res = await fetch('/ifab-index.json')
  const chunks = (await res.json()) as IfabChunk[]
  const db = await create({ schema: { law: 'string', title: 'string', text: 'string' } })
  await insertMultiple(db, chunks as unknown as Record<string, unknown>[])
  _db = db
  return db
}

/** Retrieve the single best-matching IFAB Law chunk on-device (Orama BM25). */
export async function retrieveLawOffline(query: string): Promise<IfabChunk | null> {
  const db = await getDb()
  const result = await search(db, {
    term: query,
    properties: ['title', 'text'],
    boost: { title: 3 },
    limit: 1,
  })
  const doc = result.hits[0]?.document as IfabChunk | undefined
  return doc ?? null
}
