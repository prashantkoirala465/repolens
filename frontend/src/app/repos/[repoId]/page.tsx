import { RepoWorkspace } from "@/components/RepoWorkspace";

export default async function RepoPage(props: PageProps<"/repos/[repoId]">) {
  const { repoId } = await props.params;

  return (
    <main className="flex flex-1 flex-col items-center gap-8 px-6 py-16">
      <RepoWorkspace repoId={repoId} />
    </main>
  );
}
