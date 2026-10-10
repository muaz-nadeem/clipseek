import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { deleteVideo, listVideos, searchVideos, uploadVideo, type SearchResult, type VideoStatus } from "../../../shared/api/client";
import { useAuth } from "../../auth/context/AuthProvider";
import { DEV_AUTH_BYPASS } from "../../auth/config";
import { Brand, Icon } from "../../../shared/components/Icon";
import { ClipPlayer } from "../../search/components/ClipPlayer";
import { SearchResults } from "../../search/components/SearchResults";
import { VideoStatusPoll } from "../components/VideoStatus";

const CLASS_OPTIONS = ["person", "car", "truck", "bus", "train", "bicycle", "motorcycle", "dog", "cat"];
function durationLabel(seconds: number | null) {
  if (seconds == null) return "—";
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

export function HomePage() {
  const { email, logout } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [activeVideoId, setActiveVideoId] = useState<number | null>(null);
  const [videos, setVideos] = useState<VideoStatus[]>([]);
  const [query, setQuery] = useState("");
  const [selectedClasses, setSelectedClasses] = useState<string[]>([]);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [indexingId, setIndexingId] = useState<number | null>(null);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [libraryQuery, setLibraryQuery] = useState("");
  const [sort, setSort] = useState("newest");
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const requestId = useRef(0);
  const activeVideo = videos.find((video) => video.video_id === activeVideoId);
  const indexingStatus = videos.find((video) => video.video_id === indexingId)?.status;
  const indexing = indexingId != null && (indexingStatus === undefined || indexingStatus === "queued" || indexingStatus === "processing");
  const processingCount = videos.filter((video) => ["queued", "processing"].includes(video.status)).length;
  const readyCount = videos.filter((video) => video.status === "completed").length;
  const canSearch = activeVideoId == null ? readyCount > 0 : activeVideo?.status === "completed";

  const refreshVideos = useCallback(async () => {
    try { setVideos(await listVideos()); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not load your library"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refreshVideos(); }, [refreshVideos]);
  useEffect(() => {
    if (!indexing && !processingCount) return;
    const timer = window.setInterval(refreshVideos, 3000);
    return () => window.clearInterval(timer);
  }, [indexing, processingCount, refreshVideos]);
  useEffect(() => () => { requestId.current += 1; }, []);

  function resetSearch() {
    requestId.current += 1;
    setResults([]); setSelected(null); setSearched(false); setSearching(false);
  }
  function chooseVideo(id: number | null, scroll = false) {
    setActiveVideoId(id); resetSearch();
    if (scroll) document.getElementById("search")?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }
  function chooseFile(next: File | null) {
    setUploadError(null);
    if (next && !/\.(mp4|mov|avi|mkv|webm)$/i.test(next.name)) { setFile(null); setUploadError("Choose an MP4, MOV, AVI, MKV, or WebM video."); return; }
    if (next && next.size > 2 * 1024 ** 3) { setFile(null); setUploadError("This file exceeds the 2 GB upload limit."); return; }
    setFile(next);
  }
  async function onUpload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setUploading(true); setUploadError(null); setNotice(null);
    try {
      const uploaded = await uploadVideo(file);
      chooseVideo(uploaded.video_id); setIndexingId(uploaded.video_id);
      setFile(null); if (fileInput.current) fileInput.current.value = "";
      setNotice("Upload saved. We’re building its visual index—you can keep browsing your library.");
      await refreshVideos();
    } catch (err) { setUploadError(err instanceof Error ? err.message : "Upload failed. Please try again."); }
    finally { setUploading(false); }
  }
  async function onSearch(event: FormEvent) {
    event.preventDefault();
    if (!query.trim() || !canSearch) return;
    const id = ++requestId.current;
    setSearching(true); setError(null); setSelected(null); setResults([]); setSearched(false);
    try {
      const response = await searchVideos({ query: query.trim(), video_id: activeVideoId, top_k: 8, class_names: selectedClasses.length ? selectedClasses : null });
      if (id !== requestId.current) return;
      setResults(response.results); setSelected(response.results[0] ?? null); setSearched(true);
    } catch (err) { if (id === requestId.current) setError(err instanceof Error ? err.message : "Search failed"); }
    finally { if (id === requestId.current) setSearching(false); }
  }
  async function onDelete(video: VideoStatus) {
    if (!window.confirm(`Delete “${video.filename}” and its search index? This cannot be undone.`)) return;
    setDeletingId(video.video_id); setError(null);
    try {
      await deleteVideo(video.video_id);
      resetSearch();
      if (activeVideoId === video.video_id) setActiveVideoId(null);
      if (indexingId === video.video_id) setIndexingId(null);
      setNotice(`“${video.filename}” was removed from your library.`);
      await refreshVideos();
    } catch (err) { setError(err instanceof Error ? err.message : "Delete failed"); }
    finally { setDeletingId(null); }
  }

  const visibleVideos = videos.filter((video) => video.filename.toLowerCase().includes(libraryQuery.toLowerCase())).sort((a, b) => sort === "name" ? a.filename.localeCompare(b.filename) : new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  return <div className="workspace">
    <a href="#workspace-main" className="skip-link">Skip to workspace</a>
    <aside className="workspace-sidebar">
      <Link to="/" aria-label="Clipseek home"><Brand /></Link>
      <div className="workspace-label">PERSONAL WORKSPACE</div>
      <nav aria-label="Workspace navigation"><a className="sidebar-link current" href="#library"><Icon name="library" />Your library<span>{videos.length}</span></a><a className="sidebar-link" href="#search"><Icon name="search" />Search videos</a><a className="sidebar-link" href="#upload"><Icon name="plus" />Upload video</a></nav>
      <div className="sidebar-tip"><Icon name="film" size={25} /><strong>Your footage, connected.</strong><p>Upload once. Come back with a new question anytime.</p><Link to="/#how-it-works">How it works <Icon name="arrow" size={15} /></Link></div>
      <div className="workspace-account"><span className="avatar">{(email?.[0] || "L").toUpperCase()}</span><div><strong>Personal account</strong><span title={email ?? undefined}>{DEV_AUTH_BYPASS ? "Local testing" : email}</span></div>{!DEV_AUTH_BYPASS && <button className="icon-button" onClick={logout} aria-label="Sign out" title="Sign out"><Icon name="logout" size={18} /></button>}</div>
    </aside>
    <div className="workspace-body">
      <header className="workspace-topbar"><div><span className="muted">Workspace</span><Icon name="chevron" size={14} /><span>Video library</span></div><Link to="/" className="text-link">Back to website<Icon name="arrow" size={15} /></Link></header>
      <main className="workspace-main" id="workspace-main">
        <section className="workspace-heading"><div><p className="eyebrow">A HOME FOR EVERY MOMENT</p><h1>Your video library<span>.</span></h1><p className="muted">All your footage. Ready for your next question.</p></div><button type="button" className="btn primary" disabled={uploading} onClick={() => fileInput.current?.click()}><Icon name="plus" size={18} />Upload a video</button></section>
        <div className="stats-grid"><div><span><Icon name="library" size={17} />Total videos</span><strong>{videos.length.toString().padStart(2, "0")}</strong></div><div><span><Icon name="check" size={17} />Ready to search</span><strong>{readyCount.toString().padStart(2, "0")}</strong></div><div><span><Icon name="clock" size={17} />Processing</span><strong>{processingCount.toString().padStart(2, "0")}</strong></div></div>
        {error && <div className="error banner" role="alert">{error}<button className="linkish" onClick={() => { setError(null); void refreshVideos(); }}>Refresh library</button></div>}
        {notice && <div className="notice notice-row" role="status"><Icon name="check" size={18} /><span>{notice}</span><button className="icon-button" onClick={() => setNotice(null)} aria-label="Dismiss notification"><Icon name="close" size={15} /></button></div>}

        <section id="upload" className="upload-section panel"><div className="upload-description"><span className="section-icon"><Icon name="upload" size={23} /></span><h2>Add something new.</h2><p>Drop a video in. We’ll make it searchable.</p><small>MP4, MOV, AVI, MKV, WebM<br /> Up to 2 GB · 10 minutes per video</small></div><form className="upload-form" onSubmit={onUpload}>
          <label className={`dropzone ${dragging ? "dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); if (!uploading) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); if (!uploading) chooseFile(event.dataTransfer.files[0] ?? null); }}>
            <Icon name={file ? "film" : "plus"} size={25} /><strong>{file ? file.name : "Drop your video here, or browse files"}</strong><span>{file ? `${(file.size / 1024 ** 2).toFixed(1)} MB · Ready to upload` : "Your original video is saved in your library."}</span><input ref={fileInput} type="file" accept=".mp4,.mov,.avi,.mkv,.webm" aria-label="Choose video" disabled={uploading} onChange={(event) => chooseFile(event.target.files?.[0] ?? null)} />
          </label><div className="upload-form-bottom"><span className="muted">AI indexing begins after upload.</span><button className="btn primary small" type="submit" disabled={!file || uploading || indexing}>{uploading ? "Uploading…" : indexing ? "Indexing…" : "Upload & index"}<Icon name="arrow" size={16} /></button></div>
          {uploadError && <p className="error" role="alert">{uploadError}</p>}
        </form></section>

        <section id="library" className="library-section"><div className="subsection-heading"><div><h2>Saved videos <span className="count-badge">{videos.length}</span></h2><p>Your upload history, linked to your account.</p></div><div className="library-controls"><label className="library-filter"><Icon name="search" size={16} /><input aria-label="Find a video" placeholder="Find a video…" value={libraryQuery} onChange={(event) => setLibraryQuery(event.target.value)} /></label><select aria-label="Sort videos" value={sort} onChange={(event) => setSort(event.target.value)}><option value="newest">Newest first</option><option value="name">Name A–Z</option></select></div></div>
          {loading ? <div className="library-empty" role="status">Loading your library…</div> : !videos.length ? <div className="library-empty"><span className="empty-icon"><Icon name="library" size={28} /></span><h3>Your story starts with a video.</h3><p>Upload your first recording to build your searchable library.</p><a href="#upload" className="text-link">Add your first video <Icon name="arrow" size={17} /></a></div> : !visibleVideos.length ? <div className="library-empty"><p>No videos match “{libraryQuery}”.</p><button className="btn secondary small" onClick={() => setLibraryQuery("")}>Clear filter</button></div> : <div className="video-table"><div className="video-table-header"><span>VIDEO</span><span>STATUS</span><span>UPLOADED</span><span>DURATION</span><span className="sr-only">Actions</span></div>{visibleVideos.map((video) => <div key={video.video_id} className={`video-row ${activeVideoId === video.video_id ? "selected" : ""}`}>
            <button className="video-name" onClick={() => chooseVideo(video.video_id, true)} aria-label={`Open ${video.filename}`}><span className="video-file-icon"><Icon name="film" size={21} /></span><span><strong>{video.filename}</strong><small>{video.status === "failed" ? "Indexing failed · open for details" : `${video.object_count ?? 0} indexed appearances`}</small></span></button>
            <span className={`status-pill status-${video.status}`}>{video.status === "completed" ? <><Icon name="check" size={12} />Ready</> : video.status === "processing" ? `Indexing ${Math.round((video.progress ?? 0) * 100)}%` : video.status === "queued" ? "Queued" : "Failed"}</span><span className="video-date">{new Date(video.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}</span><span className="video-duration">{durationLabel(video.duration)}</span><button className="icon-button delete-button" aria-label={`Delete ${video.filename}`} title={`Delete ${video.filename}`} disabled={deletingId === video.video_id || ["queued", "processing"].includes(video.status)} onClick={() => void onDelete(video)}><Icon name="trash" size={17} /></button>
          </div>)}</div>}
        </section>

        <section id="search" className="search-workspace"><div className="subsection-heading"><div><p className="eyebrow">FOLLOW YOUR CURIOSITY</p><h2>What are you looking for?</h2><p>Describe something visible in your footage.</p></div><span className="search-scope-note"><Icon name="film" size={16} />{activeVideo?.filename ?? "Your entire library"}</span></div>
          <form onSubmit={onSearch} className="search-form"><div className="search-bar"><Icon name="search" size={22} /><input aria-label="Query" placeholder="Try “a person wearing a red jacket”" value={query} onChange={(event) => { setQuery(event.target.value); resetSearch(); }} required /><button className="btn primary" type="submit" disabled={searching || !query.trim() || !canSearch}>{searching ? "Searching…" : "Find moments"}<Icon name="arrow" size={17} /></button></div><div className="search-options"><label>Search in<select aria-label="Video scope" value={activeVideoId ?? ""} onChange={(event) => chooseVideo(event.target.value ? Number(event.target.value) : null)}><option value="">All my videos</option>{videos.map((video) => <option key={video.video_id} value={video.video_id}>#{video.video_id} {video.filename} ({video.status})</option>)}</select></label><details className="filter-details"><summary><Icon name="sliders" size={16} />Object filters{selectedClasses.length > 0 && ` (${selectedClasses.length})`}</summary><div className="chips">{CLASS_OPTIONS.map((name) => <button key={name} type="button" aria-pressed={selectedClasses.includes(name)} className={selectedClasses.includes(name) ? "chip on" : "chip"} onClick={() => { setSelectedClasses((prev) => prev.includes(name) ? prev.filter((item) => item !== name) : [...prev, name]); resetSearch(); }}>{name}</button>)}</div></details></div></form>
          {activeVideoId != null && activeVideo?.status !== "completed" && <VideoStatusPoll videoId={activeVideoId} onCompleted={refreshVideos} />}
          {!canSearch && <p className="muted search-hint">{!videos.length ? "Upload a video to start exploring." : "Search is available when indexing finishes. You can select another ready video."}</p>}
          {(searched || searching) ? <div className="results-stage"><div><div className="results-heading"><h3>{searching ? "Finding your moments…" : `${results.length} ${results.length === 1 ? "match" : "matches"}`}</h3><span className="muted">Ranked by relevance</span></div>{searching ? <p className="muted" role="status">Searching the visual index…</p> : <SearchResults results={results} selectedId={selected?.object_id ?? null} onSelect={setSelected} videoNames={Object.fromEntries(videos.map((video) => [video.video_id, video.filename]))} />}</div><ClipPlayer result={selected} /></div> : <div className="search-idle"><Icon name="search" size={27} /><h3>The moment you remember is a search away.</h3><p>Try an object, a color, or a scene. Matching clips will appear here.</p><div className="suggestions">{["A train passing by", "A person wearing red", "Cars on a city street"].map((text) => <button key={text} onClick={() => setQuery(text)}>{text}<Icon name="arrow" size={13} /></button>)}</div></div>}
        </section>
        <footer className="workspace-footer"><span>Clipseek · Find the moment, not the filename.</span><div><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link></div></footer>
      </main>
    </div>
  </div>;
}
