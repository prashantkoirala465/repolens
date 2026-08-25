import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RetrievalInspector } from "./RetrievalInspector";
import type { RetrievedChunk } from "@/lib/api";

const chunk = (overrides: Partial<RetrievedChunk> = {}): RetrievedChunk => ({
  chunk_id: "src/foo.py:1-10",
  file_path: "src/foo.py",
  start_line: 1,
  end_line: 10,
  symbol: "foo",
  score: 0.842,
  cited: false,
  ...overrides,
});

describe("RetrievalInspector", () => {
  it("renders nothing when there are no retrieved chunks", () => {
    const { container } = render(<RetrievalInspector chunks={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows file path, line range, and score for each chunk", () => {
    render(<RetrievalInspector chunks={[chunk()]} />);
    expect(screen.getByText("src/foo.py:1-10")).toBeInTheDocument();
    expect(screen.getByText("0.842")).toBeInTheDocument();
  });

  it("marks cited chunks distinctly from uncited ones", () => {
    render(<RetrievalInspector chunks={[chunk({ cited: true })]} />);
    expect(screen.getByText("cited")).toBeInTheDocument();
  });

  it("does not label an uncited chunk as cited", () => {
    render(<RetrievalInspector chunks={[chunk({ cited: false })]} />);
    expect(screen.queryByText("cited")).not.toBeInTheDocument();
  });
});
