import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../../../shared/api/client";
import { HomePage } from "../pages/WorkspacePage";

vi.mock("../../../shared/api/client", () => ({
  deleteVideo: vi.fn(),
  fetchClipBlob: vi.fn(),
  getVideo: vi.fn(),
  listVideos: vi.fn(),
  searchVideos: vi.fn(),
  uploadVideo: vi.fn(),
}));

vi.mock("../../auth/context/AuthProvider", () => ({
  useAuth: () => ({ email: "tester@example.com", logout: vi.fn() }),
}));

function video(status: string): api.VideoStatus {
  return {
    video_id: 7,
    filename: "street.mp4",
    status,
    duration: 25,
    error_message: null,
    created_at: "2026-09-27T00:00:00Z",
    indexed_at: null,
    progress: 0.4,
    object_count: 3,
  };
}

function renderPage() {
  const view = render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
  const input = view.container.querySelector('input[type="file"]') as HTMLInputElement;
  fireEvent.change(input, { target: { files: [new File(["x"], "street.mp4", { type: "video/mp4" })] } });
  return view;
}

describe("HomePage upload button", () => {
  beforeEach(() => {
    vi.mocked(api.listVideos).mockResolvedValue([]);
    vi.mocked(api.getVideo).mockResolvedValue(video("processing"));
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("shows Uploading during the request, then Indexing while the video processes", async () => {
    let finishUpload!: (value: { video_id: number; filename: string; status: string }) => void;
    vi.mocked(api.uploadVideo).mockReturnValue(new Promise((resolve) => (finishUpload = resolve)));
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Upload & index" }));
    expect(await screen.findByRole("button", { name: "Uploading…" })).toBeTruthy();

    vi.mocked(api.listVideos).mockResolvedValue([video("processing")]);
    finishUpload({ video_id: 7, filename: "street.mp4", status: "queued" });
    const button = await screen.findByRole("button", { name: "Indexing…" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it("returns to Upload & index once indexing has finished", async () => {
    vi.mocked(api.uploadVideo).mockResolvedValue({ video_id: 7, filename: "street.mp4", status: "queued" });
    vi.mocked(api.listVideos).mockResolvedValueOnce([]).mockResolvedValue([video("completed")]);
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Upload & index" }));
    expect(await screen.findByRole("option", { name: /#7 street\.mp4 \(completed\)/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Upload & index" })).toBeTruthy();
  });

  it("loads saved uploads and searches a selected previous video without uploading again", async () => {
    vi.mocked(api.listVideos).mockResolvedValue([video("completed")]);
    vi.mocked(api.searchVideos).mockResolvedValue({ query: "train", results: [] });
    render(<MemoryRouter><HomePage /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "Open street.mp4" }));
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "train" } });
    fireEvent.click(screen.getByRole("button", { name: "Find moments" }));
    await waitFor(() => expect(api.searchVideos).toHaveBeenCalledWith({ query: "train", video_id: 7, top_k: 8, class_names: null }));
    expect(await screen.findByText("No strong matches found.")).toBeTruthy();
    expect(api.uploadVideo).not.toHaveBeenCalled();
  });

  it("filters the persistent library by filename without hiding the search scope", async () => {
    vi.mocked(api.listVideos).mockResolvedValue([video("completed")]);
    render(<MemoryRouter><HomePage /></MemoryRouter>);
    await screen.findByRole("button", { name: "Open street.mp4" });
    fireEvent.change(screen.getByLabelText("Find a video"), { target: { value: "missing" } });
    expect(screen.queryByRole("button", { name: "Open street.mp4" })).toBeNull();
    expect(screen.getByRole("option", { name: /street.mp4/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Clear filter" }));
    expect(screen.getByRole("button", { name: "Open street.mp4" })).toBeTruthy();
  });

  it("rejects an unsupported file before starting an upload", () => {
    render(<MemoryRouter><HomePage /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText("Choose video"), { target: { files: [new File(["x"], "document.pdf")] } });
    expect(screen.getByRole("alert").textContent).toContain("Choose an MP4");
    expect((screen.getByRole("button", { name: "Upload & index" }) as HTMLButtonElement).disabled).toBe(true);
    expect(api.uploadVideo).not.toHaveBeenCalled();
  });
});
