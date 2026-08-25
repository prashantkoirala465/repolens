"use client";

import { useQuery } from "@tanstack/react-query";
import { getRepo } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { QueryPanel } from "@/components/QueryPanel";

const TERMINAL_STATUSES = new Set(["ready", "failed"]);

export function RepoWorkspace({ repoId }: { repoId: string }) {
  const { data: repo, isLoading } = useQuery({
    queryKey: ["repo", repoId],
    queryFn: () => getRepo(repoId),
    refetchInterval: (query) =>
      query.state.data && TERMINAL_STATUSES.has(query.state.data.status) ? false : 1500,
  });

  if (isLoading || !repo) {
    return <p className="text-sm text-zinc-500">Loading…</p>;
  }

  return (
    <div className="flex w-full max-w-2xl flex-col gap-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold">
          {repo.owner}/{repo.name}
        </h1>
        <StatusBadge status={repo.status} />
      </div>

      {repo.status === "failed" && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          Indexing failed: {repo.status_detail ?? "unknown error"}
        </p>
      )}

      {repo.status !== "ready" && repo.status !== "failed" && (
        <p className="text-sm text-zinc-500">
          Cloning, chunking, and embedding this repo — this page updates automatically.
        </p>
      )}

      {repo.status === "ready" && (
        <>
          <p className="text-sm text-zinc-500">
            {repo.chunk_count} chunks indexed from commit{" "}
            <span className="font-mono">{repo.commit_sha?.slice(0, 7)}</span>
          </p>
          <QueryPanel repoId={repo.id} />
        </>
      )}
    </div>
  );
}
