import type { RetrievedChunk } from "@/lib/api";

// Surfaces exactly what was retrieved and why — the point of this panel is
// that retrieval quality is auditable, not a black box the answer just trusts.
export function RetrievalInspector({ chunks }: { chunks: RetrievedChunk[] }) {
  if (chunks.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-medium text-zinc-700">Retrieved chunks</h3>
      <ul className="flex flex-col gap-1.5">
        {chunks.map((chunk) => (
          <li
            key={chunk.chunk_id}
            className={`flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-xs ${
              chunk.cited ? "border-green-300 bg-green-50" : "border-zinc-200 bg-white"
            }`}
          >
            <div className="flex flex-col gap-0.5 truncate">
              <span className="truncate font-mono text-zinc-800">
                {chunk.file_path}:{chunk.start_line}-{chunk.end_line}
              </span>
              {chunk.symbol && <span className="text-zinc-500">{chunk.symbol}</span>}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {chunk.cited && (
                <span className="rounded-full bg-green-600 px-2 py-0.5 font-medium text-white">
                  cited
                </span>
              )}
              <span className="font-mono text-zinc-500">{chunk.score.toFixed(3)}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
