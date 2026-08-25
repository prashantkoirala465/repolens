import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, createRepo, getRepo, queryRepo } from "./api";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("createRepo posts to /repos and returns the parsed body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "abc", owner: "psf", name: "requests" }), {
        status: 201,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const repo = await createRepo("https://github.com/psf/requests");

    expect(repo).toMatchObject({ id: "abc", owner: "psf" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/repos");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ github_url: "https://github.com/psf/requests" });
  });

  it("getRepo hits the repo-by-id endpoint", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ id: "abc" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await getRepo("abc");

    expect(fetchMock.mock.calls[0][0]).toContain("/repos/abc");
  });

  it("queryRepo posts the question to the repo's query endpoint", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ answer: "x" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await queryRepo("abc", "how does auth work?");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/repos/abc/query");
    expect(JSON.parse(init.body)).toEqual({ question: "how does auth work?" });
  });

  it("throws ApiError with the server-provided detail on non-2xx responses", async () => {
    const fetchMock = vi.fn().mockImplementation(
      async () =>
        new Response(JSON.stringify({ detail: "repo not found" }), {
          status: 404,
          statusText: "Not Found",
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const error = await getRepo("missing").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toHaveProperty("message", "repo not found");
  });
});
