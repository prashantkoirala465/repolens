"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ApiError, createRepo } from "@/lib/api";

export function RepoForm() {
  const [githubUrl, setGithubUrl] = useState("");
  const router = useRouter();

  const mutation = useMutation({
    mutationFn: () => createRepo(githubUrl.trim()),
    onSuccess: (repo) => router.push(`/repos/${repo.id}`),
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (githubUrl.trim()) mutation.mutate();
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-xl flex-col gap-3">
      <label htmlFor="github-url" className="text-sm font-medium text-zinc-700">
        Public GitHub repo URL
      </label>
      <div className="flex gap-2">
        <input
          id="github-url"
          type="text"
          placeholder="https://github.com/psf/requests"
          value={githubUrl}
          onChange={(event) => setGithubUrl(event.target.value)}
          className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-zinc-500"
        />
        <button
          type="submit"
          disabled={mutation.isPending || !githubUrl.trim()}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {mutation.isPending ? "Indexing…" : "Index repo"}
        </button>
      </div>
      {mutation.isError && (
        <p className="text-sm text-red-600">
          {mutation.error instanceof ApiError
            ? mutation.error.message
            : "Something went wrong. Try again."}
        </p>
      )}
    </form>
  );
}
