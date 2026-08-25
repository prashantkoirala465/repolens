import { RepoForm } from "@/components/RepoForm";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-8 px-6 py-24">
      <div className="flex max-w-xl flex-col gap-3 text-center">
        <h1 className="text-3xl font-semibold tracking-tight">RepoLens</h1>
        <p className="text-zinc-600">
          Ask questions about any public GitHub repo. Answers cite the exact file and
          line range they come from, and every retrieval is measured against a real
          precision/recall benchmark, not vibes.
        </p>
      </div>
      <RepoForm />
    </main>
  );
}
