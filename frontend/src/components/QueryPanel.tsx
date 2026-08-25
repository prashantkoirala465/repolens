"use client";

import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { ApiError, queryRepo, type QueryResult } from "@/lib/api";
import { RetrievalInspector } from "@/components/RetrievalInspector";

export function QueryPanel({ repoId }: { repoId: string }) {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);

  const mutation = useMutation({
    mutationFn: (q: string) => queryRepo(repoId, q),
    onSuccess: setResult,
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (question.trim()) mutation.mutate(question.trim());
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          placeholder="How does authentication work in this repo?"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-zinc-500"
        />
        <button
          type="submit"
          disabled={mutation.isPending || !question.trim()}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {mutation.isPending ? "Asking…" : "Ask"}
        </button>
      </form>

      {mutation.isError && (
        <p className="text-sm text-red-600">
          {mutation.error instanceof ApiError
            ? mutation.error.message
            : "Something went wrong. Try again."}
        </p>
      )}

      {result && (
        <div className="flex flex-col gap-4 rounded-lg border border-zinc-200 bg-white p-4">
          <p className="whitespace-pre-wrap text-sm text-zinc-900">{result.answer}</p>
          {result.rejected_citation_count > 0 && (
            <p className="text-xs text-amber-600">
              {result.rejected_citation_count} citation(s) the model attempted were not
              backed by any retrieved chunk and were dropped.
            </p>
          )}
          <RetrievalInspector chunks={result.retrieved_chunks} />
        </div>
      )}
    </div>
  );
}
