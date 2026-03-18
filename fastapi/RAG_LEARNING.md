# RAG Learning Guide — Complete Edition

> Written while building Tarteel, cross-referenced with:
> - [NirDiamant/rag_techniques](https://github.com/NirDiamant/rag_techniques) — 34 runnable notebooks
> - [Danielskry/Awesome-RAG](https://github.com/Danielskry/Awesome-RAG) — full taxonomy + papers
> - Chip Huyen — *AI Engineering* (the RAG chapters)
> - Anthropic, Meta, DeepMind, and Google research papers (2023–2025)
>
> Read this alongside the code. Every technique here maps to either something Tarteel already does,
> or something on the improvement roadmap.

---

## Table of Contents

1. [What is RAG and why does it exist?](#1-what-is-rag-and-why-does-it-exist)
2. [The three core problems RAG solves](#2-the-three-core-problems-rag-solves)
3. [Stage 1 — Chunking: how you slice your documents](#3-stage-1--chunking-how-you-slice-your-documents)
4. [Stage 2 — Indexing: what you store and how](#4-stage-2--indexing-what-you-store-and-how)
5. [Stage 3 — Retrieval: how you search](#5-stage-3--retrieval-how-you-search)
6. [Stage 4 — Query transformation: rephrasing before you search](#6-stage-4--query-transformation-rephrasing-before-you-search)
7. [Stage 5 — Reranking: the careful second pass](#7-stage-5--reranking-the-careful-second-pass)
8. [Stage 6 — Generation: turning context into answers](#8-stage-6--generation-turning-context-into-answers)
9. [Advanced architectures: making the pipeline intelligent](#9-advanced-architectures-making-the-pipeline-intelligent)
10. [Evaluation: measuring before improving](#10-evaluation-measuring-before-improving)
11. [Why not LangChain?](#11-why-not-langchain)
12. [How to read the Tarteel pipeline code](#12-how-to-read-the-tarteel-pipeline-code)
13. [Tarteel's full RAG scorecard](#13-tarteels-full-rag-scorecard)
14. [Resources and papers](#14-resources-and-papers)

---

## 1. What is RAG and why does it exist?

Language models (Qwen3, GPT-4, Claude) are **parametric knowledge stores**. During training, they compress billions of documents into billions of floating-point numbers called **weights** or **parameters**. When you ask a question, the model recalls from these weights.

The problems with pure parametric recall:

| Problem | Technical Name | Example |
|---|---|---|
| Knowledge stops at training date | Knowledge cutoff | "Who won last year's World Cup?" |
| Can't cite sources | Lack of provenance | "Which PMBOK chapter says this?" |
| Makes things up confidently | Hallucination | Wrong risk formulas stated as fact |
| Doesn't know your private docs | Closed-domain gap | Your company's project methodology |
| Expensive to update | Retraining cost | Adding new PMI standards |

**RAG** (Retrieval-Augmented Generation) — term coined by Lewis et al. (Meta AI, 2020) — fixes this by separating storage from generation:

```
Without RAG:  Question → LLM (from weights) → Answer
With RAG:     Question → Search your docs → Inject passages into prompt → LLM reads and summarizes → Answer
```

The LLM's job changes from **"remember and answer"** to **"read and summarize"**. This is strictly easier, more accurate, and auditable.

**The RAG Pipeline — 4 core stages:**

```
                  ┌─────────────────────────────────────┐
OFFLINE (once):   │  Documents → Chunk → Embed → Store  │
                  └─────────────────────────────────────┘

                  ┌─────────────────────────────────────────────────────┐
ONLINE (per query):│ Query → Transform → Retrieve → Rerank → Generate  │
                  └─────────────────────────────────────────────────────┘
```

---

## 2. The three core problems RAG solves

### Problem 1 — Keywords don't capture meaning

"What should I do when my project is behind schedule?" has zero words in common with the PMBOK section titled "Schedule Compression Techniques." Keyword search returns nothing.

**Solution**: Vector/semantic search — represent meaning as numbers, not words.

### Problem 2 — Short queries don't match long passages

A 10-word question and a 100-word paragraph have similar *topics* but very different *statistical shapes* in vector space. The embedder sees length, density, and vocabulary differently.

**Solution**: HyDE — generate a fake long answer, then search for chunks similar to that fake answer.

### Problem 3 — Vocabulary mismatch across languages

Arabic question → English knowledge base. The question "ما هو مسار الحرج؟" and the passage "Critical Path Method (CPM)" share no tokens whatsoever.

**Solution**: Multi-query expansion with cross-lingual translation.

---

## 3. Stage 1 — Chunking: how you slice your documents

Before you can search anything, you split your documents into **chunks** — the searchable units. Chunking strategy is one of the most underestimated decisions in RAG. Wrong chunking breaks everything downstream.

---

### Fixed-size chunking

**What**: Split document every N tokens/characters regardless of sentence or paragraph boundaries.

**Parameters**:
- `chunk_size`: number of tokens per chunk (e.g., 512)
- `chunk_overlap`: tokens shared between adjacent chunks (e.g., 64) — prevents information loss at boundaries

**Analogy**: Cutting a book every 3 pages regardless of chapter or sentence endings. Fast and simple but creates torn contexts.

**Formula**: If document has T tokens with chunk_size C and overlap O, you get approximately `(T - O) / (C - O)` chunks.

**When to use**: Fast prototyping. Baseline before trying semantic chunking.

**Problem**: Chunks can start mid-sentence or mid-thought. The embedder receives incomplete units of meaning.

---

### Semantic chunking

**What**: Instead of fixed sizes, split wherever the *meaning changes*. You embed every sentence, compute the **cosine similarity** between adjacent sentences, and split at semantic "valleys" — places where the topic shifts.

**Technical process**:
1. Split document into sentences with a sentence tokenizer
2. Embed each sentence with your embedding model (bge-m3 in Tarteel)
3. Compute cosine similarity between sentence `i` and sentence `i+1`
4. Find points where similarity drops below a threshold (these are topic boundaries)
5. Merge sentences into chunks between boundaries

**Cosine similarity formula**:
```
similarity(A, B) = (A · B) / (||A|| × ||B||)
```
Where `A · B` is the dot product and `||A||` is the vector's magnitude (L2 norm).

**Analogy**: A librarian who reads your book and cuts it wherever the subject changes, not every third page.

**In Tarteel**: Not currently implemented. Fixed prefix-based chunking in `scripts/pdf_ingest.py`.

---

### Recursive text splitting (LangChain-style)

**What**: Try to split by paragraphs first. If chunks are still too big, split by sentences. If still too big, split by words. Recursively respects document structure.

**Hierarchy**: `\n\n` (paragraphs) → `\n` (lines) → `.` (sentences) → ` ` (words) → character

**When to use**: When you don't have a semantic chunker and need something better than pure fixed-size.

---

### Sentence-window retrieval (aka context enrichment)

**What**: Store each sentence as its own unit for embedding (maximum precision). At retrieval time, fetch not just the matched sentence but its surrounding window (e.g., 3 sentences before + 3 after).

**Two-step indexing**:
- `index`: individual sentences → high-precision embeddings
- `storage`: full paragraphs/windows → rich context for the LLM

**Why it works**: Short sentence = focused vector (one idea). But 1 sentence alone is not enough context for the LLM to write a good answer.

**Analogy**: Use a microscope to find the exact cell you need, then zoom out to see the whole tissue.

---

### Small-to-big retrieval (parent-child chunks)

**What**: Store two granularity levels in the same database:
- **Child chunks** (100–150 words): small, embedded, searchable
- **Parent chunks** (400–500 words): the surrounding section, used for LLM context

At query time: search on child embeddings → get child IDs → look up their parent → pass parent text to LLM.

**Why the split matters**:
- Large chunks embed poorly — one vector tries to represent 5 ideas → the average is meaningless
- Small chunks embed well but give the LLM too little to work with
- Small-to-big gets you precision in finding + richness in answering

**DB schema change**: Add `parent_chunk_id BIGINT REFERENCES pmp_chunks(id)` to `pmp_chunks`.

**In Tarteel**: Planned. Requires DB migration + ingestion rewrite.

---

### Proposition indexing (Dense X Retrieval)

**What**: Instead of chunks of raw text, store **propositions** — atomic, self-contained factual statements extracted by an LLM.

**Example**:
- Raw chunk: "The risk register is updated throughout the project as new risks are identified, existing risks change, and risk responses are implemented or modified."
- Propositions extracted:
  - "The risk register is updated throughout the project lifecycle."
  - "New risks are added to the risk register as they are identified."
  - "Existing risk entries change as risk status evolves."
  - "Risk response implementation is recorded in the risk register."

**Why it works**: Each proposition embeds one idea perfectly. Retrieval is maximally precise.

**Cost**: One LLM call per chunk during ingestion (same as Contextual Retrieval). One-time cost.

**Paper**: *Dense X Retrieval: What Retrieval Granularity Should We Use?* (Chen et al., 2023)

---

### Document summary indexing (RAPTOR)

**What**: Instead of or alongside chunk-level indexing, create summaries of document sections and index those. Then hierarchically summarize the summaries.

**RAPTOR** (Recursive Abstractive Processing for Tree-Organized Retrieval) from Stanford (2024):
1. Cluster all chunks using Gaussian Mixture Models (soft clustering — a chunk can belong to multiple clusters)
2. Summarize each cluster with an LLM
3. Embed the summaries and re-cluster them
4. Repeat until you have a single root summary
5. Index the full tree — leaf nodes are raw chunks, upper nodes are summaries

**Why it works**: A question about "PMBOK risk philosophy" might not match any specific chunk but matches a high-level cluster summary perfectly. RAPTOR lets you search at multiple abstraction levels simultaneously.

**When to use**: Documents with deep hierarchical structure. Long books where individual chunks lose the big picture.

**Not in Tarteel**: Would require significant architectural changes.

---

## 4. Stage 2 — Indexing: what you store and how

### Embedding models: turning text into vectors

An **embedding model** converts text into a **dense vector** — a list of floating-point numbers (e.g., 1024 numbers) representing the text's meaning in a high-dimensional space. Semantically similar texts end up as nearby vectors.

**Key properties**:
- **Dimensionality**: 768 (BERT), 1024 (bge-m3), 1536 (OpenAI text-embedding-3-small), 3072 (text-embedding-3-large)
- **Context window**: Max tokens the model can embed at once (e.g., 512 for many models, 8192 for bge-m3)
- **Multilingual**: Some models are trained on many languages. bge-m3 handles 100+ languages.
- **Training objective**: Most embedders are trained with **contrastive learning** — push similar pairs together, dissimilar pairs apart in vector space.

**Model families**:
- **BERT-family**: bi-encoders (encode query and document separately, compare with cosine)
- **Cross-encoders**: encode query AND document together (slower, more accurate — used for reranking)
- **BGE (BAAI General Embedding)**: FlagEmbedding series, bge-m3 is state-of-the-art multilingual
- **OpenAI text-embedding-**: Fast, good quality, expensive, English-biased

**Tarteel uses**: `bge-m3` — 1024-dim, supports Arabic+English natively. Lives at `app/rag/embeddings.py`.

---

### BM25 — The probabilistic keyword scorer

**What**: **BM25** (Best Match 25) is a bag-of-words retrieval function from 1994, still competitive today. It's the core of Elasticsearch, Solr, and most production search.

**Full formula**:
```
BM25(q, d) = Σ IDF(qi) × [f(qi,d) × (k1+1)] / [f(qi,d) + k1 × (1 - b + b × |d|/avgdl)]
```

Where:
- `qi` = query term i
- `f(qi, d)` = term frequency of qi in document d
- `IDF(qi)` = inverse document frequency = `log((N - n(qi) + 0.5) / (n(qi) + 0.5) + 1)` — rare words score higher
- `|d|` = document length (in words)
- `avgdl` = average document length across all documents
- `k1` ≈ 1.5 (tunable) — controls term frequency saturation (going from 1 occurrence to 2 matters a lot; from 100 to 101 matters almost nothing)
- `b` ≈ 0.75 (tunable) — controls length normalization (longer docs get penalized)

**Intuition**: A word that appears 10 times in a short document is more relevant than the same word appearing 10 times in a book. IDF rewards rare words (technical terms). Length normalization prevents long documents from always winning.

**Tarteel implementation**: BM25 is run as a PostgreSQL query using `ts_rank` and `to_tsvector` / `to_tsquery` in `app/rag/retrieval.py`.

---

### Hybrid search + RRF fusion

**What**: Run BM25 and vector search independently. Each returns a ranked list of chunks. Merge them.

**Why not just average scores?** BM25 scores and cosine similarity scores live on incompatible scales. You can't average them directly.

**RRF — Reciprocal Rank Fusion** (Cormack et al., 2009):
```
RRF_score(d, {R1, R2, ...}) = Σ 1 / (k + rank_in_Ri(d))
```

Where:
- `k` = 60 (constant — empirically found to be optimal across many benchmarks)
- `rank_in_Ri(d)` = position of document d in ranked list Ri

**Why k=60?** Without it, the formula is just `1/rank`. The difference between rank 1 (1.0) and rank 2 (0.5) would be huge. With k=60, rank 1 gives `1/61 ≈ 0.0164` and rank 2 gives `1/62 ≈ 0.0161`. The constant smooths rank differences — a strong rank-1 from one method can be outweighed by appearing in both lists at rank 5.

**Analogy**: Two search engines return ranked results. Trust whatever both recommend over what only one recommends.

**Tarteel implementation**: `_merge_rrf()` in `app/rag/pipeline.py`. Runs BM25 and vector in parallel, merges via RRF.

---

### Contextual chunk headers

**What**: Before embedding, prepend a structured metadata header to each chunk:
```
[PMBOK 8th Edition | Risk Management Planning | Process Domain]
The risk register should include probability, impact, and response strategy...
```

**Why**: The embedding model sees the header as part of the text. Without it, chunks like "The register should be updated throughout the project" embed as generic change-management language. With the header, bge-m3 understands this is specifically about PMBOK risk registers.

**Three header fields in Tarteel**:
1. `{display_source}` — e.g., "PMBOK 8th Edition", "Agile Practice Guide"
2. `{current_header}` — the section/chapter heading where this chunk was found
3. `{domain_label}` — "People Domain", "Process Domain", "Business Environment Domain"

**Tarteel implementation**: `scripts/pdf_ingest.py` — header prepended before `conn.execute()` insert.

---

### Contextual Retrieval (Anthropic, Nov 2024)

**What**: For each chunk, before embedding, call an LLM and ask:
> "Here is the full document: [document]. Here is one chunk from it: [chunk]. In 2 concise sentences, explain what this chunk is about and where it fits in the document."

Prepend that summary to the chunk, THEN embed.

**Before**:
```
The risk register should include probability, impact, and response strategy for each identified risk.
```

**After**:
```
Context: This passage is from PMBOK Chapter 11 (Project Risk Management), specifically the Outputs section
of the Identify Risks process. It describes the mandatory fields in the risk register document.
The risk register should include probability, impact, and response strategy for each identified risk.
```

**Why it works**: Chunks retrieved in isolation lose their document context. Adding the LLM-generated context summary bakes the broader meaning directly into the embedding. The embedding model now understands exactly what knowledge domain this chunk belongs to, not just what words it contains.

**Anthropic benchmark result**: 49% reduction in retrieval failures on their internal test sets.

**Cost model**: One LLM call per chunk, at ingestion time (one-time). Zero additional cost at query time.

**Tarteel plan**: Modify `scripts/pdf_ingest.py` to call Qwen3 once per chunk with the full section as context. Requires full re-ingestion + `redis-cli FLUSHDB`.

---

## 5. Stage 3 — Retrieval: how you search

### Simple RAG (baseline)

**What**: Embed the query → cosine similarity search → return top-k chunks → put in prompt → generate.

**This is the minimum viable RAG**. Everything else in this guide is an improvement on this baseline.

**Tarteel status**: ✅ Live, plus 8 additional improvements on top.

---

### Sparse retrieval (BM25, TF-IDF)

Already covered in Section 4. The key point: sparse means the vector representation is mostly zeros — only dimensions corresponding to actual words are non-zero. Compared to dense vectors where all 1024 dimensions hold meaningful values.

**TF-IDF** (Term Frequency–Inverse Document Frequency) — the simpler predecessor to BM25:
```
TF-IDF(t, d) = TF(t, d) × IDF(t)
TF(t, d) = count(t in d) / total_words(d)
IDF(t) = log(N / df(t))
```

BM25 improves on TF-IDF by adding length normalization and saturation.

---

### Dense retrieval (vector search)

**What**: Both query and documents are embedded into dense vectors. Retrieval = finding the nearest vectors to the query vector in high-dimensional space.

**Distance metrics**:
- **Cosine similarity**: `cos(θ) = (A·B)/(||A||·||B||)` — measures angle between vectors, ignores magnitude. Range: -1 to 1. Most common.
- **Dot product**: `A·B` — magnitude-sensitive. Used when vectors are normalized (then equal to cosine).
- **Euclidean distance (L2)**: `||A-B||₂` — geometric distance. Less common for text.

**HNSW (Hierarchical Navigable Small World)** — the indexing algorithm behind fast vector search:
- Builds a multi-layer graph where each node connects to its nearest neighbors
- Higher layers = fewer nodes, long-range connections (for fast navigation)
- Lower layers = all nodes, short-range connections (for precise search)
- Search: start at top layer, greedily navigate toward query, then descend and refine
- Time complexity: O(log N) — extremely fast even for millions of vectors

**pgvector** (used in Tarteel): PostgreSQL extension that adds vector operations and HNSW index support. The `<=>` operator computes cosine distance.

**ANN vs exact search**: HNSW is Approximate Nearest Neighbor (ANN) — not guaranteed to find the mathematically closest vector, but finds 95–99% of them 100x faster than exact search.

---

### Sparse-dense hybrid with late interaction: ColBERT

**What**: **ColBERT** (Contextualized Late Interaction over BERT) is a retrieval model that represents documents and queries as *multiple vectors* (one per token), rather than one vector for the whole text.

**MaxSim scoring**:
```
ColBERT_score(q, d) = Σᵢ max_j (qᵢ · dⱼ)
```
For each query token `qᵢ`, find the most similar document token `dⱼ`. Sum these max similarities.

**Why it's powerful**: "Critical path method" as a query generates separate vectors for "critical", "path", and "method". The document's token for "path" can match "path" in the query precisely, while "critical" matches "essential" semantically. One-vector-per-text can't do this.

**Cost**: 20–50x more storage than single-vector embeddings (one 128-dim vector per token). Retrieval requires more compute.

**Production use**: Vespa AI uses ColBERT by default. Excellent for technical content.

**Not in Tarteel**: Would require significant infrastructure changes, but worth knowing.

---

## 6. Stage 4 — Query transformation: rephrasing before you search

The user's question as typed is often the *worst* possible search query. Query transformation fixes the vocabulary mismatch between how users ask and how documents are written.

---

### HyDE — Hypothetical Document Embedding

**What**: Before searching, ask the LLM to generate a hypothetical paragraph that *would* be the perfect answer if it existed in your documents. Embed this hypothetical paragraph, not the raw question.

**Full algorithm**:
1. User asks: "What should I do when my project is behind schedule?"
2. LLM generates: "When a project falls behind schedule, project managers typically employ schedule compression techniques. The two primary methods are crashing (adding resources to critical path activities) and fast-tracking (performing activities in parallel that were originally sequential)..."
3. Embed this hypothetical passage → get a vector
4. Search for chunks whose vectors are close to this hypothetical vector

**Why it works mathematically**: A 10-word question and a 100-word PMBOK paragraph are distant in vector space even if semantically related — they have different length, vocabulary density, and linguistic register. A 100-word hypothetical answer and a 100-word PMBOK paragraph are much closer — same length, same domain vocabulary, same declarative tone.

**Critical gotcha in Tarteel**: Qwen3 8B has a "thinking mode" that uses ALL its `num_predict` tokens on internal chain-of-thought reasoning before outputting. Always set:
```python
"think": False,          # skip thinking phase
"options": {"num_predict": 150}  # enough tokens for the hypothetical passage
```
Without `think: False`, Qwen3 uses all 150 tokens on `<think>...</think>` blocks and returns empty response.

**Paper**: *Precise Zero-Shot Dense Retrieval without Relevance Labels* (Gao et al., 2022)

**Tarteel implementation**: `app/rag/hyde.py`

---

### Multi-query expansion

**What**: Rephrase the original question N ways using an LLM. Run retrieval for all N+1 versions. Merge all result lists via RRF.

**Why**: Different phrasings retrieve different chunks. "What is schedule compression?" retrieves PMBOK chapter 7 directly. "How do I speed up a delayed project?" retrieves risk response and resource management sections. Together you get better coverage.

**Variants**:
- **Simple rephrase**: Same language, different vocabulary
- **Cross-lingual**: Translate to English (Tarteel's Arabic→English case)
- **Perspective shift**: "What does a project manager do when..." → "What techniques exist for..."
- **Decomposition**: Break complex questions into sub-questions (see Query Decomposition below)

**Tarteel's Arabic code-switching implementation**: The expansion prompt instructs Qwen3 to produce:
1. One Arabic rewrite (for Arabic-only knowledge or Arabic-language chunks)
2. One English translation (to bridge the gap to the English PMBOK/Agile knowledge base)

This is the most important retrieval innovation in Tarteel — without it, Arabic questions miss most of the knowledge base.

**Tarteel implementation**: `app/rag/query_expansion.py` — called in parallel with HyDE via `asyncio.gather`.

---

### Step-back prompting

**What**: Ask the LLM to rephrase a specific question into a more general/abstract question. Search for the abstract version, retrieve foundational context, then answer the specific question with that context.

**Example**:
- Specific: "What is the formula for Cost Performance Index?"
- Step-back: "How does Earned Value Management measure project cost efficiency?"
- Search for the step-back version → retrieve the full EVM section → use that context to answer the specific formula question

**Why it works**: Specific questions often fail to retrieve the prerequisite foundational context. The step-back version retrieves the broader context that contains the specific answer.

**Paper**: *Take a Step Back: Evoking Reasoning via Abstraction* (Zheng et al., Google DeepMind, 2023)

---

### Query decomposition (sub-question generation)

**What**: If a question requires information from multiple sources or multiple steps, decompose it into independent sub-questions. Retrieve and answer each sub-question separately, then synthesize.

**Example**:
- Complex: "How does the risk management plan affect procurement planning?"
- Sub-questions:
  1. "What is the purpose of the risk management plan?"
  2. "What is included in procurement planning?"
  3. "How do risk responses influence make-or-buy decisions?"
- Answer each sub-question separately → combine into a final answer

**When to use**: Multi-hop questions that require connecting two or more concepts from different parts of the knowledge base.

**Paper**: *Answering Questions by Meta-Reasoning over Multiple Chains of Thought* (Yoran et al., 2023)

---

### FLARE — Forward-Looking Active Retrieval

**What**: Instead of retrieving once at the beginning, the LLM actively decides when to retrieve more information *while generating* the answer.

**Algorithm**:
1. LLM starts generating the answer token by token
2. When it's about to generate a token with low confidence (measured by generation probability), it STOPS
3. It formulates a retrieval query based on what it was about to say
4. Retrieves relevant chunks
5. Continues generating with the new context

**Why it's powerful**: The LLM decides what additional information it needs *after* seeing what it already knows. This is adaptive — it won't retrieve if it already knows the answer, and it retrieves exactly what's needed if it doesn't.

**Trade-off**: Significantly more complex to implement. Multiple retrieval calls per answer.

**Paper**: *Active Retrieval Augmented Generation* (Jiang et al., 2023)

---

### Query routing

**What**: Given a question, classify it and route it to the most appropriate retrieval strategy or knowledge source.

**Example routing logic**:
```python
if question_is_about_process:
    search_pmbok_chunks(domain="process")
elif question_is_about_people_skills:
    search_pmbok_chunks(domain="people")
elif question_needs_formula:
    search_formula_index()
elif question_is_general:
    search_all_chunks()
```

**Metadata filtering in Tarteel**: Tarteel's domain + lesson_id filtering IS a form of query routing — it routes retrieval to the relevant subset of chunks based on the current lesson context.

**Advanced routing**: Use an LLM or a small classifier to select between multiple retrieval strategies, databases, or APIs.

---

## 7. Stage 5 — Reranking: the careful second pass

Retrieval is fast but approximate. Reranking is slow but precise. Standard RAG pattern: retrieve 20–50 candidates, rerank to top 5–10.

---

### Cross-encoder reranking

**What**: A **cross-encoder** model takes a (query, document) pair as a SINGLE input and outputs a relevance score. Unlike bi-encoders (which embed query and document separately), cross-encoders read them together.

**Architecture difference**:
```
Bi-encoder:  Embed(query) → vector_q    }  cosine(vector_q, vector_d) = score
             Embed(doc)   → vector_d    }

Cross-encoder: Concat(query, doc) → BERT → [CLS] vector → Linear → score
```

**Why cross-encoders are more accurate**: The model sees the full interaction between query tokens and document tokens via self-attention. It can recognize when a document says "the opposite of what the query asks about" or "the same concept with different terminology."

**Why cross-encoders can't be used for initial retrieval**: They require one forward pass per (query, document) pair. For 1 million documents, that's 1 million forward passes per query — completely infeasible.

**Common models**:
- `bge-reranker-v2-m3` (Tarteel) — multilingual, handles Arabic
- `cross-encoder/ms-marco-MiniLM-L-6-v2` — English only, fast
- `BAAI/bge-reranker-large` — higher accuracy, slower

**Tarteel implementation**: `app/rag/reranker.py` — receives top-25 to 40 candidates from retrieval, scores each, returns top-8.

---

### LLM-based reranking

**What**: Instead of a specialized cross-encoder model, use the main LLM itself to score relevance. Prompt it: "Given the question: {q}, is this passage relevant? Answer 'relevant' or 'not relevant': {passage}"

**Or use a logprob approach**: Ask the model to answer "yes" or "no" and read the log-probability of "yes" as the relevance score.

**Trade-off**: More accurate than smaller cross-encoders, but 10–100x more expensive and slower.

**When to use**: High-stakes retrieval where accuracy matters more than speed. Medical, legal, exam contexts.

---

### Diversity reranking — MMR (Maximal Marginal Relevance)

**What**: MMR selects documents that are both relevant to the query AND different from each other. Prevents returning 5 chunks that all say the same thing.

**Formula** (Carbonell & Goldstein, 1998):
```
MMR = argmax[λ·sim(dᵢ, q) - (1-λ)·max_{dⱼ∈S} sim(dᵢ, dⱼ)]
```

Where:
- `sim(dᵢ, q)` = similarity of candidate document to query
- `max_{dⱼ∈S} sim(dᵢ, dⱼ)` = similarity to the most similar already-selected document
- `λ` ∈ [0,1] — controls relevance vs diversity trade-off (λ=1 → pure relevance, λ=0 → pure diversity)

**Analogy**: You're picking 5 research papers to read. You want the most relevant ones, BUT you don't want all 5 to make the same point. MMR gives you coverage.

**When this matters in Tarteel**: Without MMR, if you ask a broad question, the top-8 chunks might all come from the same PMBOK chapter and repeat the same information. MMR would force diversity across chapters or sources.

---

### Lost in the Middle — position-aware reranking

**What**: Research (Liu et al., Stanford, 2023) found that LLMs pay significantly less attention to information in the *middle* of long context windows than at the beginning or end.

**Implication**: After reranking, reorder the top-k chunks so that the MOST relevant chunks appear at the START and END of the context, with less relevant chunks in the middle.

**Implementation**: Sort reranked chunks: [rank 1, rank 3, rank 5, rank 6, rank 4, rank 2] — highest relevance at positions 0 and -1, lower relevance in middle.

**Paper**: *Lost in the Middle: How Language Models Use Long Contexts* (Liu et al., 2023)

---

## 8. Stage 6 — Generation: turning context into answers

### Grounding instructions — the anti-hallucination instruction

**What**: The system prompt explicitly restricts the model to only use information from the retrieved context.

**Why this is non-negotiable**: Without grounding instructions, the model answers from its training data whenever the retrieved context is insufficient. You get confident, fluent, wrong answers — defeating the entire purpose of RAG.

**Tarteel's English grounding instruction** (from `app/prompts.py`):
> "If the information is not found in the provided context, say explicitly: 'I don't have enough information in the available source materials on this topic.' Do not use your internal knowledge outside the provided context."

**Tarteel's Arabic grounding instruction**:
> "إذا لم تجد المعلومات في السياق المقدم أعلاه، قل صراحةً: 'لا تتوفر لديّ معلومات كافية في المصادر المتاحة حول هذا الموضوع.' لا تستخدم معلوماتك الداخلية خارج السياق المقدم."

**Language detection**: Tarteel counts Arabic Unicode characters in the query. If >20%, use Arabic prompt.

**Think mode trigger**: Certain question types (exam-style with "best describes", "most appropriate") benefit from Qwen3's thinking mode. These trigger `think: True`.

---

### Prompt engineering for RAG

**Context injection pattern**:
```
System: You are a PMP tutor. Answer only from the provided context. [grounding instruction]

User:
Context:
[Source 1: PMBOK 8th Edition p.342]
The critical path is the longest sequence...

[Source 2: PMBOK 8th Edition p.351]
Float or slack is the amount of time...

Question: What is the critical path method?
```

**Citation prompting**: Instruct the model to cite which source each claim comes from. Reduces hallucination and adds traceability.

**Role prompting**: "You are a senior PMP instructor" vs "You are a helpful assistant" changes the style and confidence of answers significantly.

---

### Streaming generation (SSE)

**What**: Instead of waiting for the full response, send tokens to the client as they're generated using **Server-Sent Events (SSE)**.

**SSE protocol**:
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache

data: {"token": "The"}
data: {"token": " critical"}
data: {"token": " path"}
...
data: [DONE]
```

**Why it matters for UX**: A 3-second wait for a full response feels slower than watching tokens appear immediately even if total time is the same. Streaming feels interactive.

**Tarteel architecture**: FastAPI `StreamingResponse` → Laravel `StreamedResponse` proxy → Next.js `EventSource` in `AiExplanation.tsx`.

---

### Caching LLM responses

**What**: Hash the (query + retrieved chunks) → store LLM response in Redis keyed by that hash → on future identical requests, return cached response instantly.

**Cache key in Tarteel**: SHA256 of (normalized query + chunk IDs or chunk text). Laravel and FastAPI share the same hash format so Laravel can check before forwarding to FastAPI.

**Why chunk content is in the key**: If you re-ingest and chunks change, old cached responses become invalid automatically.

**TTL**: No TTL for factual question answers (PMBOK facts don't change). Set TTL only for time-sensitive content.

**Tarteel implementation**: `app/cache.py` — Redis + `make_cache_key()` function.

---

## 9. Advanced architectures: making the pipeline intelligent

### Corrective RAG (CRAG)

**What**: After retrieval, **score the quality of what you retrieved** before sending it to the LLM. If the scores are too low, your retrieval failed — trigger a corrective action rather than sending garbage context to the model.

**Algorithm**:
1. Retrieve top-k chunks
2. Score each with the reranker: `reranker_score = cross_encoder.score(query, chunk)`
3. Check max score: `max_score = max(reranker_scores)`
4. If `max_score < threshold` (e.g., 0.3): retrieval probably failed
5. Corrective actions:
   - Broaden search: remove metadata filters
   - Try different query: reformulate with LLM
   - Fall back to web search
   - Tell the user: "I couldn't find relevant information on this specific topic"

**Confidence signal in Tarteel**: The reranker scores from `bge-reranker-v2-m3` already exist. No extra computation needed — add a threshold check after reranking in `app/rag/pipeline.py`.

**Paper**: *Corrective Retrieval Augmented Generation* (Yan et al., 2024)

---

### Self-RAG

**What**: The LLM itself evaluates whether it needs to retrieve, evaluates the retrieved documents, evaluates its own generated answer, and decides whether to loop.

**Four special tokens Self-RAG uses**:
- `[Retrieve]` — model decides it needs to search
- `[IsREL]` — model evaluates if retrieved chunk is relevant
- `[IsSUP]` — model evaluates if its answer is supported by the context
- `[IsUSE]` — model evaluates if the answer is useful to the user

**This requires fine-tuning**: The original Self-RAG paper fine-tunes a special model trained to predict these tokens. You can approximate it with a standard LLM by adding evaluation prompts, but it's more expensive.

**When to use**: Accuracy-critical applications where correctness matters more than latency. Medical, legal, exam domains.

**Paper**: *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection* (Asai et al., 2023)

---

### Adaptive RAG

**What**: A router that decides the retrieval strategy based on query complexity:
- **Simple factual question**: Direct LLM answer (no retrieval needed, it's already in training data)
- **Moderate question**: Single retrieval → generate
- **Complex question**: Multi-step retrieval → chain-of-thought → generate

**How to classify query complexity**: Fine-tune a small classifier on labeled query complexity data. Or use the LLM itself: "On a scale of 1-3, how many retrieval steps does this question need?"

**Paper**: *Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity* (Jeong et al., 2024)

---

### Agentic RAG

**What**: Instead of a fixed sequence of steps, an LLM **agent** decides at each step what to do next. It might retrieve twice, formulate follow-up queries, aggregate information from multiple searches, or ask clarifying questions.

**Tool-calling pattern** (OpenAI / Anthropic tool use):
```python
tools = [
    {"name": "search_knowledge_base", "description": "Search PMBOK chunks"},
    {"name": "search_broader", "description": "Search without domain filter"},
    {"name": "ask_clarification", "description": "Ask user for more detail"},
]

# Agent decides: I need to search for risk management first,
# then search for procurement to connect them
response = llm.call(query, tools=tools)
```

**Why LangGraph for this**: LangGraph models the agent as a state machine where:
- **Nodes** = LLM calls, tool calls, decisions
- **Edges** = conditional transitions based on state (e.g., "if confidence is low, go to broader search node")
- **State** = shared context passed between nodes

**When NOT to use**: Simple factual questions. The overhead of agentic reasoning is 3–5x latency compared to a fixed pipeline.

**When to use**: Complex multi-hop questions. "What is the relationship between the risk register, the quality management plan, and the procurement strategy in predictive projects?" — requires understanding 3 concepts and their interactions.

---

### Graph RAG (Microsoft, 2024)

**What**: Instead of searching raw text chunks, build a **knowledge graph** from your documents and query the graph structure.

**Pipeline**:
1. **Entity extraction**: LLM reads each chunk and extracts entities (Risk Register, WBS, Project Charter) and relationships (Risk Register → *is output of* → Identify Risks)
2. **Graph construction**: Build a property graph (Neo4j, NetworkX) where nodes = entities, edges = relationships
3. **Community detection**: Cluster related entities using Leiden algorithm
4. **Hierarchical summarization**: Generate summaries of each community at multiple levels
5. **Query**: Given a question, identify relevant entities → traverse graph → retrieve connected knowledge

**Two query modes**:
- **Local search**: Find the specific entity, traverse immediate neighbors
- **Global search**: Understand the whole knowledge graph structure to answer broad questions

**When Graph RAG beats vector RAG**:
- Questions requiring multi-hop reasoning ("How does A relate to B?")
- Questions about the overall structure of a domain ("What are the main themes in PMBOK?")

**Cost**: Extremely expensive to build. Requires hundreds to thousands of LLM calls for entity extraction. Storage in Neo4j or similar graph database.

**Paper**: *From Local to Global: A Graph RAG Approach to Query-Focused Summarization* (Edge et al., Microsoft, 2024)

**Tarteel status**: ❌ Not planned. Would require completely different architecture.

---

### Speculative RAG

**What**: Use a small, fast model to generate a draft answer (with retrieved context), then verify and refine with a larger, slower model.

**Two-model pipeline**:
1. **Drafter** (small, fast): Retrieve + generate rough answer quickly
2. **Verifier** (large, careful): Read the draft + context, check for errors, output final answer

**Why it can be faster overall**: The verifier model can work with a pre-filled draft rather than generating from scratch. In practice, verification is faster than generation.

**Paper**: *Speculative RAG: Enhancing Retrieval Augmented Generation through Drafting* (Wang et al., 2024)

---

### Fusion RAG

**What**: Generate multiple candidate answers using different retrieved contexts (or different queries), then synthesize them into a final answer.

**Algorithm**:
1. Generate K different queries from the original question
2. Retrieve K different context sets
3. Generate K different answers, one per context
4. Fuse: either select the best answer (voting) or ask LLM to synthesize all K into one comprehensive answer

**Reduces sensitivity to retrieval failures**: If 1 of 3 retrievals fails completely, the other 2 still produce good answers.

**RAG Fusion paper**: *RAG-Fusion: a New Take on Retrieval Augmented Generation* (Rackauckas, 2024)

---

### Multi-modal RAG

**What**: Extend RAG to handle images, tables, charts, and diagrams alongside text.

**Approaches**:
1. **Vision LLM at ingestion**: Use GPT-4V or LLaVA to convert each image/table to a text description. Embed the description. Query time: pure text RAG.
2. **Multi-modal embeddings**: Use CLIP or similar to embed images directly. At query time, embed the question AND search the image embedding space.
3. **Late fusion**: Retrieve text chunks + relevant images separately, inject both into a multi-modal LLM prompt.

**When this matters**: PMBOK has many process flow diagrams, RACI charts, and tables. Currently these are completely missed by Tarteel's PDF parsing (PyMuPDF extracts text only).

---

### Long-context RAG vs. RAG

**Recent development (2024)**: Models like GPT-4 (128K tokens), Claude 3 (200K tokens), and Gemini 1.5 (1M tokens) now have extremely long context windows. Is RAG still needed?

**Yes, RAG is still needed because**:
1. **Cost**: Sending 1M tokens per request = expensive. RAG sends only 5K.
2. **Latency**: Processing 1M tokens is slow even with efficient attention.
3. **Attention dilution**: Even with 1M context, models attend less to information buried in the middle (see "Lost in the Middle" paper).
4. **Hallucination**: Long-context models still hallucinate. RAG with grounding instructions reduces this.
5. **Knowledge update**: Adding a new PDF to a RAG system takes minutes. Fine-tuning or full context inclusion takes hours.

**The right hybrid**: Use long-context for complex, multi-document reasoning. Use RAG for production systems where cost, latency, and accuracy consistency matter.

---

## 10. Evaluation: measuring before improving

> "In God we trust. All others must bring data." — W. Edwards Deming

RAG evaluation is the most skipped step and the most important one. Without baselines, you don't know if your "improvements" actually improve anything.

---

### RAGAS — the standard RAG evaluation framework

**What**: RAGAS (Retrieval-Augmented Generation Assessment) is a library that automatically evaluates RAG pipelines using LLM-as-judge + statistical metrics.

**The 4 core metrics**:

#### Faithfulness (0–1)
Does the generated answer stay within the retrieved context, or does it add claims not supported by the context?

**Algorithm**:
1. Extract all atomic claims from the generated answer
2. For each claim, ask the LLM: "Is this claim supported by the retrieved context?" → yes/no
3. `Faithfulness = supported_claims / total_claims`

**Score of 1.0**: Every sentence in the answer is directly supported by the retrieved chunks.
**Score of 0.0**: The answer is pure hallucination — nothing is grounded in the context.

#### Answer Relevancy (0–1)
Does the answer actually address the question, or does it go off-topic?

**Algorithm**:
1. Ask the LLM to generate N synthetic questions from the answer
2. Embed each synthetic question and the original question
3. `Answer_Relevancy = mean(cosine(synthetic_question_i, original_question))`

**Score of 1.0**: The answer addresses exactly the question asked.
**Score of 0.0**: The answer is irrelevant to the question.

#### Context Recall (0–1)
Did retrieval find ALL the chunks needed to answer the question?

**Requires ground-truth answers to measure**.

**Algorithm**:
1. Take the ground-truth answer
2. Break it into statements
3. For each statement, check if any retrieved chunk contains this information
4. `Context_Recall = statements_covered_by_retrieved_chunks / total_statements`

**Score of 1.0**: Everything needed to answer is in the retrieved chunks.
**Score of 0.0**: None of the needed information was retrieved.

#### Context Precision (0–1)
Are the retrieved chunks actually relevant, or are they noisy filler?

**Algorithm**:
1. For each retrieved chunk, ask the LLM: "Is this chunk relevant to answering the question?"
2. `Context_Precision = relevant_retrieved_chunks / total_retrieved_chunks`

**Score of 1.0**: Every retrieved chunk is directly relevant.
**Score of 0.0**: All retrieved chunks are noise.

---

### The evaluation test set

**How to build a good test set**:
1. Write 20–50 questions manually (or have domain experts write them)
2. Write the expected answer for each question
3. Optionally: tag which chunks should be retrieved for each question (for context recall)
4. Run your pipeline → score with RAGAS

**For Tarteel**: 20 PMP questions covering all 3 domains (7 People, 7 Process, 6 Business Environment), with expected answers grounded in PMBOK content.

**Planned implementation**: `scripts/evaluate_rag.py` — run pipeline, collect (question, context, answer) triplets, score with RAGAS, print report.

**Use before ANY pipeline change**: RAGAS score establishes a baseline. After implementing Contextual Retrieval, run RAGAS again. If context_recall improved → the change worked.

---

### Other evaluation approaches

**Human evaluation**: Have PMP-certified experts rate answers on a 1–5 scale. Gold standard but slow and expensive.

**G-Eval**: Use a powerful LLM (GPT-4) to score on multiple dimensions, chain-of-thought evaluation. More nuanced than simple yes/no.

**BERTScore**: Semantic similarity between generated answer and reference answer. Less accurate than RAGAS for faithfulness measurement.

**BLEURT / ROUGE**: Token-overlap metrics. Largely obsolete for generative evaluation — they miss semantic equivalence.

---

## 11. Why not LangChain?

LangChain is the dominant RAG framework by GitHub stars. Here's the honest analysis:

| Dimension | LangChain | Custom Pipeline (Tarteel) |
|---|---|---|
| Time to first prototype | Hours | Days |
| Learning value | Low — abstractions hide mechanisms | High — you write every component |
| Version stability | Poor — breaking changes every 6–9 months | None — your code doesn't break itself |
| Performance | Overhead from abstraction layers | Direct control, no overhead |
| Debugging | "Which of 12 abstraction layers broke?" | "Which line broke?" |
| Arabic code-switching | Would need custom workarounds | Native in `query_expansion.py` |
| Qwen3 `think: False` fix | Invisible inside LCEL wrapper | Explicit at `hyde.py:40` |
| Understanding HyDE | Hidden in `HypotheticalDocumentEmbedder` | You wrote every line of `hyde.py` |
| Community / resources | Massive | Yours to build |

**The honest comparison**: LangChain exists to solve the "I need a demo in 2 hours" problem. It absolutely solves that problem. But for *learning* RAG — understanding why each component exists and what breaks without it — a custom pipeline is strictly better. You cannot learn to drive by riding in an autonomous car.

**The performance argument**: Tarteel's pipeline calls Ollama directly via `httpx.AsyncClient`. LangChain's LCEL (LangChain Expression Language) adds multiple layers of abstraction: `Runnable`, `RunnableSequence`, `invoke/ainvoke` wrappers, callbacks, and middleware. For a small-scale application, this overhead is negligible. For production at scale, it matters.

**If Tarteel needed a team of 5+ developers**: **Haystack** (by deepset) is the only framework worth evaluating over custom code. It has:
- Clean component-based architecture (not wrapper-around-wrappers like LangChain)
- Stable APIs — deepset takes backwards compatibility seriously
- First-class production tooling (evaluation, monitoring, pipelines as YAML)
- Support for hybrid retrieval out of the box

**LangGraph**: The one legitimate reason to use anything from the LangChain ecosystem. LangGraph models agentic pipelines as state machines — this is the right abstraction for complex multi-step agents. If Tarteel implements Agentic RAG, LangGraph is the correct tool.

---

## 12. How to read the Tarteel pipeline code

Follow the data from user question to streamed answer:

### Entry point: `app/rag/pipeline.py` → `_run_rag_stages()`

```
Line 41–48:  Metadata routing — extract domain/lesson_id from request. No LLM call.
Line 54–57:  asyncio.gather() — HyDE and query expansion run IN PARALLEL.
             Both call Qwen3. 2 sequential calls = 10s. 2 parallel = 5s.
Line 62–67:  Embed hypothesis + each expansion. Also parallel via asyncio.gather().
Line 71–93:  Retrieval loop:
             - BM25 + vector search for the primary (HyDE) embedding
             - Merge each expansion's vector results via _merge_rrf()
Line 95–101: Re-sort by merged RRF score, take top 8.
Line 103–117: Assemble context string with [Source | Page] prefix. Select system prompt
              based on language detection. Build user message.
```

### Then trace into each module:

**`app/rag/hyde.py`**:
- Look for `"think": False` — if you remove it, HyDE produces empty strings
- The hypothetical passage generation prompt: instructs Qwen3 to write a "textbook paragraph"
- `num_predict: 150` — enough for a good passage, not so many Qwen3 "thinks" too long

**`app/rag/query_expansion.py`**:
- The Arabic code-switching prompt — explicitly instructs Qwen3 to output one Arabic + one English version for Arabic queries
- Count how many expansions the function returns (2 by default)

**`app/rag/retrieval.py`**:
- The BM25 query: `ts_rank(to_tsvector('english', content), to_tsquery('english', $1))`
- The pgvector query: `1 - (embedding <=> $1::vector)` (cosine similarity via pgvector's `<=>` operator)
- WHERE clause filtering: `domain = $2 AND lesson_id = $3` — the semantic metadata filter

**`app/rag/reranker.py`**:
- Receives 25–40 candidates from retrieval
- Calls `bge-reranker-v2-m3` with `(query, chunk)` pairs
- Returns scores — `app/rag/pipeline.py` uses these scores to select top-8

**`app/prompts.py`**:
- Two versions of everything: Arabic (`_AR_SYSTEM_PROMPT`) and English (`_EN_SYSTEM_PROMPT`)
- The grounding instruction — the most important single line in the whole codebase
- Language detection function: counts Arabic Unicode characters, threshold at 20%

**`app/cache.py`**:
- SHA256 hash of (query + chunk IDs) → Redis key
- Cache hit: return stored response without calling Ollama at all
- Cache miss: call pipeline, store result, return result

---

## 13. Tarteel's full RAG scorecard

| Technique | Status | File | Notes |
|---|---|---|---|
| Simple RAG (baseline) | ✅ Live | `pipeline.py` | Foundation |
| BM25 keyword search | ✅ Live | `retrieval.py` | PostgreSQL `ts_rank` |
| Vector search (bge-m3) | ✅ Live | `embeddings.py` | 1024-dim, multilingual |
| Hybrid search + RRF | ✅ Live | `retrieval.py` + `pipeline.py` | k=60 |
| HyDE | ✅ Live | `hyde.py` | `think: False` critical |
| Multi-query expansion (Arabic↔English) | ✅ Live | `query_expansion.py` | Core Arabic innovation |
| Multi-vector RRF merge | ✅ Live | `pipeline.py` | Merges 3+ ranked lists |
| Cross-encoder reranking (bge-reranker-v2-m3) | ✅ Live | `reranker.py` | Top-8 after rerank |
| Contextual chunk headers | ✅ Live | `pdf_ingest.py` | `[Source \| Section \| Domain]` |
| Grounding instructions | ✅ Live | `prompts.py` | Arabic + English |
| Semantic metadata filtering | ✅ Live | `retrieval.py` | domain + lesson_id WHERE clause |
| Redis response cache | ✅ Live | `cache.py` | SHA256 key |
| Query routing (metadata) | ✅ Live | `pipeline.py` | domain/lesson routing |
| **RAGAS evaluation** | 🔜 Next | `scripts/evaluate_rag.py` | Build baseline FIRST |
| **Contextual Retrieval** | 🔜 Next | `pdf_ingest.py` | 49% retrieval improvement |
| **Small-to-Big retrieval** | 🔜 Planned | DB migration + pipeline | parent_chunk_id column |
| **CRAG confidence scoring** | 🔜 Planned | `pipeline.py` | Reranker scores as signal |
| Step-back prompting | 💡 Future | `query_expansion.py` | Add abstraction rephrasing |
| MMR diversity reranking | 💡 Future | `reranker.py` | Prevent redundant top-8 |
| Lost-in-the-Middle reorder | 💡 Future | `pipeline.py` | Reorder after rerank |
| Proposition indexing | 💡 Future | `pdf_ingest.py` | Replace chunks with propositions |
| RAPTOR hierarchical summaries | 💡 Future | New script | Cluster + summarize |
| Self-RAG | 💡 Future | `pipeline.py` | LLM self-evaluation loop |
| Agentic RAG | 💡 Future | New service | Needs LangGraph |
| Speculative RAG | 💡 Future | `pipeline.py` | Draft + verify |
| Fusion RAG | 💡 Future | `pipeline.py` | K candidates → synthesize |
| FLARE active retrieval | 💡 Future | `generator.py` | Mid-generation retrieval |
| ColBERT late interaction | 💡 Future | `embeddings.py` | Token-level matching |
| Multi-modal (image/table) | 💡 Future | `pdf_ingest.py` | Needs vision LLM |
| Graph RAG | ❌ Not planned | Separate architecture | Needs Neo4j, expensive |

---

## 14. Resources and papers

### Code repositories to study

| Resource | What to learn |
|---|---|
| [NirDiamant/rag_techniques](https://github.com/NirDiamant/rag_techniques) | 34 Jupyter notebooks, one per technique. Start with `simple_rag.ipynb`, then work up. Each notebook is self-contained with a mini demo. |
| [Danielskry/Awesome-RAG](https://github.com/Danielskry/Awesome-RAG) | Full taxonomy — papers, frameworks, vector databases, evaluation tools. Organized by technique type. |
| [run-llama/llama_index](https://github.com/run-llama/llama_index) | LlamaIndex is cleaner than LangChain. Good for studying how production frameworks implement specific techniques. |

### Essential papers (read in this order)

1. **RAG original** — *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (Lewis et al., Meta AI, 2020). The paper that named the field.
2. **HyDE** — *Precise Zero-Shot Dense Retrieval without Relevance Labels* (Gao et al., CMU, 2022)
3. **Self-RAG** — *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection* (Asai et al., 2023)
4. **CRAG** — *Corrective Retrieval Augmented Generation* (Yan et al., 2024)
5. **Graph RAG** — *From Local to Global: A Graph RAG Approach* (Edge et al., Microsoft, 2024)
6. **RAPTOR** — *RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval* (Sarthi et al., Stanford, 2024)
7. **Lost in the Middle** — *Lost in the Middle: How Language Models Use Long Contexts* (Liu et al., Stanford, 2023)
8. **Contextual Retrieval** — [Anthropic blog post](https://www.anthropic.com/news/contextual-retrieval) (Nov 2024) — required reading before implementing it in Tarteel

### Books

| Book | Relevant chapters |
|---|---|
| Chip Huyen — *AI Engineering* | RAG chapter covers retrieval theory, evaluation metrics, RAG vs fine-tuning decision |

### Evaluation tools

| Tool | Purpose |
|---|---|
| [RAGAS](https://docs.ragas.io) | The standard RAG evaluation framework — faithfulness, answer relevancy, context recall, context precision |
| [TruLens](https://www.trulens.org) | Alternative evaluation — better UI, LLM-as-judge |
| [ARES](https://github.com/stanford-futuredata/ARES) | Stanford's evaluation framework — fewer LLM calls than RAGAS |

### Vector databases (for when you outgrow pgvector)

| DB | Best for |
|---|---|
| pgvector (Tarteel's current) | <10M vectors, co-location with relational data |
| Qdrant | Production, fast, written in Rust, good filtering |
| Weaviate | GraphQL API, good for multi-modal |
| Pinecone | Fully managed, no infrastructure, expensive |
| Milvus | High-volume, distributed |
| Chroma | Lightweight, local development |
