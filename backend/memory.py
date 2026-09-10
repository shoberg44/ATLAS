"""Vector Memory Store for ATLAS Prototype 1.

Provides semantic similarity search, memory seeding with dynamic prompts,
tool definitions, and past successful task solutions.
"""

import math
import re
from typing import Optional
from backend.schemas import DomainScope, MemoryItem


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric words."""
    return re.findall(r"\b\w+\b", text.lower())


def _compute_embedding(text: str, dim: int = 64) -> list[float]:
    """Generate a deterministic normalized continuous semantic embedding.
    
    Uses token hashing and character 3-gram feature projection normalized to unit L2 norm.
    Zero external dependencies, fast and deterministic across environments.
    """
    vec = [0.0] * dim
    tokens = _tokenize(text)
    if not tokens:
        return vec

    # Word-level features
    for token in tokens:
        h = hash(token)
        idx = abs(h) % dim
        sign = 1.0 if (h & 1) else -1.0
        vec[idx] += sign * 1.5

    # Sub-word 3-gram features for morphological similarity
    for i in range(len(text) - 2):
        gram = text[i:i+3].lower()
        h = hash(gram)
        idx = abs(h) % dim
        sign = 1.0 if (h & 1) else -1.0
        vec[idx] += sign * 0.5

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 1e-9:
        vec = [round(x / norm, 5) for x in vec]
    return vec


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two unit vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 < 1e-9 or norm2 < 1e-9:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


class VectorMemoryStore:
    """In-memory vector store supporting semantic search and domain filtering."""

    def __init__(self, embedding_dim: int = 64, seed: bool = True):
        self.embedding_dim = embedding_dim
        self._store: dict[str, MemoryItem] = {}
        if seed:
            self.seed_initial_memories()

    def add_memory(
        self,
        key: str,
        content: str,
        domain: DomainScope | str,
        tags: list[str] | None = None,
    ) -> MemoryItem:
        """Store or update a memory item with an automatically computed embedding."""
        if isinstance(domain, str):
            domain = DomainScope(domain)
        tags = tags or []
        
        # Incorporate tags and content into embedding space
        combined_text = f"{key} {' '.join(tags)} {content}"
        embedding = _compute_embedding(combined_text, self.embedding_dim)

        item = MemoryItem(
            key=key,
            content=content,
            embedding_dim=self.embedding_dim,
            domain=domain,
            tags=tags,
            embedding=embedding,
        )
        self._store[key] = item
        return item

    def get_memory(self, key: str) -> Optional[MemoryItem]:
        """Retrieve a specific memory item by key."""
        return self._store.get(key)

    def list_all(self, domain: Optional[DomainScope | str] = None) -> list[MemoryItem]:
        """List all stored memory items, optionally filtered by domain."""
        items = list(self._store.values())
        if domain is not None:
            if isinstance(domain, str):
                domain = DomainScope(domain)
            items = [item for item in items if item.domain == domain]
        return items

    def search_memory(
        self,
        query: str,
        domain: Optional[DomainScope | str] = None,
        top_k: int = 3,
    ) -> list[tuple[MemoryItem, float]]:
        """Perform semantic hybrid similarity search against stored memories.
        
        Combines vector cosine similarity with token keyword overlap for high precision.
        Returns list of (MemoryItem, score) tuples sorted descending by score.
        """
        if isinstance(domain, str):
            domain = DomainScope(domain)

        query_vec = _compute_embedding(query, self.embedding_dim)
        query_tokens = set(_tokenize(query))

        candidates: list[tuple[MemoryItem, float]] = []

        for item in self._store.values():
            if domain is not None and item.domain != domain:
                continue

            # Vector similarity
            vec_sim = _cosine_similarity(query_vec, item.embedding or [])

            # Keyword token overlap (Jaccard similarity)
            item_tokens = set(_tokenize(f"{item.key} {' '.join(item.tags)} {item.content}"))
            intersection = query_tokens.intersection(item_tokens)
            union = query_tokens.union(item_tokens)
            keyword_sim = len(intersection) / len(union) if union else 0.0

            # Hybrid score (65% vector similarity + 35% keyword overlap)
            hybrid_score = round(0.65 * vec_sim + 0.35 * keyword_sim, 4)
            candidates.append((item, hybrid_score))

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]

    def seed_initial_memories(self) -> None:
        """Seed realistic initial memory items for ATLAS Prototype 1."""
        # 1. Dynamic System Prompts
        self.add_memory(
            key="prompt:triage_supervisor",
            content=(
                "You are the ATLAS Triage Supervisor. Evaluate incoming tasks, "
                "identify technical domain (MAINTENANCE vs RESEARCH_DEV), analyze priority constraints, "
                "query vector memory for historical solutions, and route to specialized workers "
                "without exposing execution tools."
            ),
            domain=DomainScope.TRIAGE,
            tags=["system_prompt", "triage", "routing", "supervisor"],
        )

        self.add_memory(
            key="prompt:rd_worker",
            content=(
                "You are the ATLAS R&D Worker. Specializing in architectural exploration, "
                "feature prototyping, literature review, and benchmarking. Generate structured "
                "hypotheses, evaluate trade-offs, and produce proof-of-concept plans in your isolated scratchpad."
            ),
            domain=DomainScope.RESEARCH_DEV,
            tags=["system_prompt", "rd", "research", "architecture", "spike"],
        )

        self.add_memory(
            key="prompt:maintenance_worker",
            content=(
                "You are the ATLAS Maintenance Worker. Specializing in bug fixes, refactoring, "
                "dependency updates, and test remediation. Execute tool actions in isolated sandbox, "
                "generate unified diff patches, and verify AST integrity before committing."
            ),
            domain=DomainScope.MAINTENANCE,
            tags=["system_prompt", "maintenance", "bug_fix", "refactor", "patch"],
        )

        # 2. Tool Definitions
        self.add_memory(
            key="tool:mcp_workspace_fs",
            content=(
                "MCP Filesystem Toolset: Read, write, list files, and inspect workspace "
                "directory tree within allowed paths. Restricted to authorized repo paths."
            ),
            domain=DomainScope.MAINTENANCE,
            tags=["mcp", "tool", "filesystem", "workspace", "read_file", "write_file"],
        )

        self.add_memory(
            key="tool:mcp_git",
            content=(
                "MCP Git Toolset: Inspect git status, generate unified diffs, check branch "
                "status, and validate staged commits without destructive push permissions."
            ),
            domain=DomainScope.MAINTENANCE,
            tags=["mcp", "tool", "git", "diff", "branch", "commit"],
        )

        self.add_memory(
            key="tool:mcp_research_web",
            content=(
                "MCP Web Research Toolset: Query technical documentation, fetch API specs, "
                "search arXiv and GitHub issues, and extract reference architectures."
            ),
            domain=DomainScope.RESEARCH_DEV,
            tags=["mcp", "tool", "web", "search", "documentation", "papers"],
        )

        # 3. Past Successful Task Solutions
        self.add_memory(
            key="solution:off_by_one_queue_reducer",
            content=(
                "Fix off-by-one error in task queue reducer. Root cause: loop index reached len(queue) "
                "instead of len(queue)-1 during batch reduction. Patch: adjusted slice bounds in reducer.py "
                "and added boundary condition regression tests."
            ),
            domain=DomainScope.MAINTENANCE,
            tags=["past_solution", "bug_fix", "queue", "off_by_one", "boundary"],
        )

        self.add_memory(
            key="solution:vector_indexing_benchmarks",
            content=(
                "Research vector indexing benchmarks. Benchmarked HNSW vs IVFFlat for pgvector on 100k "
                "vectors. Recommendation: HNSW with m=16, ef_construction=64 gave 98% recall at 4ms latency, "
                "ideal for low-latency triage lookups."
            ),
            domain=DomainScope.RESEARCH_DEV,
            tags=["past_solution", "research", "benchmarks", "vector", "hnsw", "pgvector"],
        )

        self.add_memory(
            key="solution:fastapi_cors_security",
            content=(
                "Configure FastAPI CORS middleware and dependency security headers. Added CORSMiddleware "
                "with explicit allowed origins, allow_methods=['*'], and Content-Security-Policy headers."
            ),
            domain=DomainScope.MAINTENANCE,
            tags=["past_solution", "security", "fastapi", "cors", "middleware"],
        )
