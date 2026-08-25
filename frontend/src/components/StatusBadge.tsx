import type { IndexStatus } from "@/lib/api";

const LABELS: Record<IndexStatus, string> = {
  queued: "Queued",
  cloning: "Cloning",
  chunking: "Chunking",
  embedding: "Embedding",
  ready: "Ready",
  failed: "Failed",
};

const COLORS: Record<IndexStatus, string> = {
  queued: "bg-zinc-100 text-zinc-700",
  cloning: "bg-blue-100 text-blue-700",
  chunking: "bg-blue-100 text-blue-700",
  embedding: "bg-blue-100 text-blue-700",
  ready: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export function StatusBadge({ status }: { status: IndexStatus }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${COLORS[status]}`}>
      {LABELS[status]}
    </span>
  );
}
