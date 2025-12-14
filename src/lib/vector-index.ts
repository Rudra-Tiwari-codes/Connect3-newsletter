/**
 * FAISS-like Vector Index for Event Embeddings
 * 
 * Since FAISS requires native bindings, we implement a simple but efficient
 * in-memory vector index using brute-force search with optimizations.
 * 
 * For production at scale, consider:
 * - Pinecone (managed vector DB)
 * - Weaviate
 * - Milvus
 * - pgvector (PostgreSQL extension)
 * 
 * For Connect3's scale (~1000 events, ~10000 users), this in-memory 
 * approach is perfectly fine and fast.
 */

import { EMBEDDING_DIM } from './embeddings';

export interface VectorEntry {
  id: string;
  vector: number[];
  metadata?: Record<string, any>;
}

export interface SearchResult {
  id: string;
  score: number;
  metadata?: Record<string, any>;
}

export class VectorIndex {
  private vectors: Map<string, VectorEntry> = new Map();
  private dimension: number;

  constructor(dimension: number = EMBEDDING_DIM) {
    this.dimension = dimension;
  }

  /**
   * Add a vector to the index
   */
  add(id: string, vector: number[], metadata?: Record<string, any>): void {
    if (vector.length !== this.dimension) {
      throw new Error(`Vector dimension mismatch: expected ${this.dimension}, got ${vector.length}`);
    }

    this.vectors.set(id, { id, vector, metadata });
  }

  /**
   * Add multiple vectors at once
   */
  addBatch(entries: VectorEntry[]): void {
    for (const entry of entries) {
      this.add(entry.id, entry.vector, entry.metadata);
    }
  }

  /**
   * Remove a vector from the index
   */
  remove(id: string): boolean {
    return this.vectors.delete(id);
  }

  /**
   * Get a vector by ID
   */
  get(id: string): VectorEntry | undefined {
    return this.vectors.get(id);
  }

  /**
   * Check if vector exists
   */
  has(id: string): boolean {
    return this.vectors.has(id);
  }

  /**
   * Get total number of vectors
   */
  size(): number {
    return this.vectors.size;
  }

  /**
   * Search for top-K most similar vectors using cosine similarity
   */
  search(queryVector: number[], topK: number = 10, excludeIds: Set<string> = new Set()): SearchResult[] {
    if (queryVector.length !== this.dimension) {
      throw new Error(`Query vector dimension mismatch: expected ${this.dimension}, got ${queryVector.length}`);
    }

    // Pre-compute query norm for efficiency
    const queryNorm = Math.sqrt(queryVector.reduce((sum, x) => sum + x * x, 0));
    
    const results: SearchResult[] = [];

    for (const [id, entry] of this.vectors) {
      if (excludeIds.has(id)) continue;

      // Cosine similarity
      let dotProduct = 0;
      let vectorNorm = 0;

      for (let i = 0; i < this.dimension; i++) {
        dotProduct += queryVector[i] * entry.vector[i];
        vectorNorm += entry.vector[i] * entry.vector[i];
      }

      const similarity = dotProduct / (queryNorm * Math.sqrt(vectorNorm));

      results.push({
        id,
        score: similarity,
        metadata: entry.metadata,
      });
    }

    // Sort by score descending and take top K
    results.sort((a, b) => b.score - a.score);
    return results.slice(0, topK);
  }

  /**
   * Search with filtering by metadata
   */
  searchWithFilter(
    queryVector: number[],
    topK: number,
    filter: (metadata: Record<string, any> | undefined) => boolean
  ): SearchResult[] {
    if (queryVector.length !== this.dimension) {
      throw new Error(`Query vector dimension mismatch`);
    }

    const queryNorm = Math.sqrt(queryVector.reduce((sum, x) => sum + x * x, 0));
    const results: SearchResult[] = [];

    for (const [id, entry] of this.vectors) {
      // Apply filter
      if (!filter(entry.metadata)) continue;

      let dotProduct = 0;
      let vectorNorm = 0;

      for (let i = 0; i < this.dimension; i++) {
        dotProduct += queryVector[i] * entry.vector[i];
        vectorNorm += entry.vector[i] * entry.vector[i];
      }

      const similarity = dotProduct / (queryNorm * Math.sqrt(vectorNorm));

      results.push({
        id,
        score: similarity,
        metadata: entry.metadata,
      });
    }

    results.sort((a, b) => b.score - a.score);
    return results.slice(0, topK);
  }

  /**
   * Serialize index to JSON for storage
   */
  toJSON(): string {
    const entries = Array.from(this.vectors.values());
    return JSON.stringify({
      dimension: this.dimension,
      entries,
    });
  }

  /**
   * Load index from JSON
   */
  static fromJSON(json: string): VectorIndex {
    const data = JSON.parse(json);
    const index = new VectorIndex(data.dimension);
    index.addBatch(data.entries);
    return index;
  }

  /**
   * Clear all vectors
   */
  clear(): void {
    this.vectors.clear();
  }

  /**
   * Get all IDs in the index
   */
  getAllIds(): string[] {
    return Array.from(this.vectors.keys());
  }
}

// Global singleton index for events
let eventIndex: VectorIndex | null = null;

export function getEventIndex(): VectorIndex {
  if (!eventIndex) {
    eventIndex = new VectorIndex(EMBEDDING_DIM);
  }
  return eventIndex;
}

export function resetEventIndex(): void {
  eventIndex = null;
}
