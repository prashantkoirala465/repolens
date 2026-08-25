// Mirrors backend/src/repolens/schemas/{repo,query}.py — keep these in sync by hand
// until the project is big enough to justify generating this from the OpenAPI schema.

export type IndexStatus = "queued" | "cloning" | "chunking" | "embedding" | "ready" | "failed";

export interface Repo {
  id: string;
  github_url: string;
  owner: string;
  name: string;
  commit_sha: string | null;
  status: IndexStatus;
  status_detail: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  file_path: string;
  start_line: number;
  end_line: number;
  symbol: string | null;
  score: number;
  cited: boolean;
}

export interface QueryResult {
  query_id: string;
  answer: string;
  retrieved_chunks: RetrievedChunk[];
  rejected_citation_count: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
  return response.json() as Promise<T>;
}

export function createRepo(githubUrl: string): Promise<Repo> {
  return request<Repo>("/repos", {
    method: "POST",
    body: JSON.stringify({ github_url: githubUrl }),
  });
}

export function getRepo(repoId: string): Promise<Repo> {
  return request<Repo>(`/repos/${repoId}`);
}

export function queryRepo(repoId: string, question: string): Promise<QueryResult> {
  return request<QueryResult>(`/repos/${repoId}/query`, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export { ApiError };
