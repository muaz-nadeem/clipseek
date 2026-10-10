import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../auth/context/AuthProvider";
import { Brand, Icon, type IconName } from "../../../shared/components/Icon";

const features: { icon: IconName; title: string; description: string; tag: string }[] = [
  { icon: "search", title: "Search the way you think.", description: "Describe people, objects, colors, or a scene in everyday language. Find visual matches without remembering a filename.", tag: "NATURAL-LANGUAGE SEARCH" },
  { icon: "play", title: "Go straight to the moment.", description: "Get ranked, timestamped matches. Play a short clip around each result, with context before and after the match.", tag: "TIMESTAMPED PLAYBACK" },
  { icon: "library", title: "One library. Always yours.", description: "Your uploads stay linked to your account. Return to an indexed video and search it again without uploading it twice.", tag: "PERSONAL VIDEO LIBRARY" },
  { icon: "film", title: "Let the AI do the looking.", description: "Object detection, tracking, and visual embeddings turn your footage into a searchable index. Follow progress as it processes.", tag: "AUTOMATIC INDEXING" },
  { icon: "sliders", title: "Less noise. More relevance.", description: "Search one video or your entire library. Narrow by object type, with weaker matches filtered out of your results.", tag: "FOCUSED RESULTS" },
  { icon: "shield", title: "A workspace of your own.", description: "Sign in to access your account’s library. Manage your uploads and delete videos you no longer need, all in one place.", tag: "ACCOUNT-BASED ACCESS" },
];
const questions = [
  ["What can I search for?", "Describe what is visible: a person in a dark jacket, a train, a bicycle, or a street scene. Clipseek searches visual content; it does not currently transcribe speech, answer general questions about a video, or reliably count objects."],
  ["What videos can I upload?", "Upload MP4, MOV, AVI, MKV, or WebM files, up to 2 GB and 10 minutes per video with the current limits. The file must contain a video stream that the server can decode."],
  ["Do I have to wait for indexing every time?", "Only after a new upload or a re-index. Once indexing is complete, the visual index is saved with your video so you can come back and run new searches. Initial processing time depends on the video and server hardware."],
  ["Will it find every single appearance?", "Not always. The index samples approximately five frames per second and search uses AI similarity, so brief appearances can be missed and matches may be imperfect. Use the clip preview to verify a result."],
  ["Can I access my videos later?", "Yes. Sign in to the same account to return to your uploaded library. Your videos and index remain on this deployment until deleted or removed under its storage policy."],
];

export function LandingPage() {
  const { token } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const destination = token ? "/app" : "/signup";
  return <div className="landing">
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="site-header">
      <div className="site-nav container">
        <Link to="/" aria-label="Clipseek home"><Brand /></Link>
        <nav className={menuOpen ? "marketing-nav is-open" : "marketing-nav"} aria-label="Main navigation">
          <a href="#features" onClick={() => setMenuOpen(false)}>Features</a>
          <a href="#how-it-works" onClick={() => setMenuOpen(false)}>How it works</a>
          <a href="#faq" onClick={() => setMenuOpen(false)}>FAQ</a>
        </nav>
        <div className="nav-actions">{!token && <Link className="login-link" to="/login">Log in</Link>}<Link className="btn primary small" to={destination}>{token ? "Open workspace" : "Get started"}<Icon name="arrow" size={16} /></Link><button className="icon-button mobile-menu" aria-label="Toggle navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}><Icon name={menuOpen ? "close" : "menu"} /></button></div>
      </div>
    </header>

    <main id="main">
      <section className="landing-hero container">
        <div className="eyebrow-pill"><span className="tiny-dot" /> A clearer way to search video</div>
        <h1>Your footage.<br /><span>Finally searchable.</span></h1>
        <p className="hero-description">You remember the moment. We help you find it.<br className="desktop-break" /> Turn your videos into a searchable library, using just your words.</p>
        <div className="hero-actions"><Link className="btn primary" to={destination}>{token ? "Go to your library" : "Create your workspace"}<Icon name="arrow" size={18} /></Link><a className="btn secondary" href="#how-it-works"><Icon name="play" size={16} />See how it works</a></div>
        <p className="hero-note">Upload once. Search again and again.</p>
        <div className="product-preview" aria-label="Illustrative preview of the Clipseek workspace">
          <div className="preview-toolbar"><div className="window-dots"><i /><i /><i /></div><span>YOUR VIDEO, A LITTLE MORE INTELLIGENT</span><span className="preview-label">Product preview</span></div>
          <div className="preview-body">
            <aside className="preview-sidebar"><Brand /><div className="preview-nav-item"><Icon name="library" size={16} />My library</div><div className="preview-nav-item active"><Icon name="search" size={16} />Search videos</div><div className="preview-sidebar-bottom"><span className="avatar">JD</span><span>Your workspace<small>Everything in one place</small></span></div></aside>
            <div className="preview-main">
              <div className="preview-title"><span>Find a moment</span><span className="muted">City walk.mp4</span></div>
              <div className="preview-search"><Icon name="search" size={18} /><span>A street with cars and tall buildings</span><span className="preview-enter"><Icon name="arrow" size={16} /></span></div>
              <div className="preview-content"><div className="preview-image"><img src="/city-scene.jpg" alt="Black and white city street with vehicles and tall buildings" fetchPriority="high" /><span className="frame-corner top-left" /><span className="frame-corner bottom-right" /><span className="preview-image-label"><span className="tiny-dot" /> MATCH PREVIEW</span><span className="preview-play"><Icon name="play" size={24} /></span><div className="preview-timeline"><span>00:16</span><div><i /></div><span>00:23</span></div></div>
                <div className="preview-matches"><p className="eyebrow">THE MOMENT YOU MEANT</p><div className="preview-match"><span className="match-number">01</span><div><strong>00:16 – 00:23</strong><p>Street scene</p></div><Icon name="play" size={15} /></div><p className="preview-caption">Relevant moments.<br />Ready to play.</p><span className="preview-example">Illustrative example</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="use-case-strip container" aria-label="Use cases"><span>BUILT FOR THE FOOTAGE YOU WORK WITH</span><div><span>Creative archives</span><span>Research footage</span><span>Everyday recordings</span><span>Visual review</span></div></section>

      <section id="features" className="section container">
        <div className="section-heading"><div><p className="eyebrow">LESS SCRUBBING. MORE FINDING.</p><h2>Everything between<br />“I saw it” and “here it is.”</h2></div><p>A thoughtful set of tools to turn hours of looking into a more focused way of finding.</p></div>
        <div className="feature-grid">{features.map((feature, index) => <article className="feature-card" key={feature.title}><div className="feature-top"><span className="feature-icon"><Icon name={feature.icon} size={23} /></span><span className="feature-number">0{index + 1}</span></div><p className="eyebrow">{feature.tag}</p><h3>{feature.title}</h3><p>{feature.description}</p></article>)}</div>
      </section>

      <section id="how-it-works" className="how-section"><div className="container section"><div className="section-heading"><div><p className="eyebrow">FROM UPLOAD TO AHA.</p><h2>Three steps.<br />A whole new perspective.</h2></div><p>No manual tagging. No complicated timeline.<br />Just your video and a little curiosity.</p></div><div className="steps-grid">{[
        ["01", "Bring your footage.", "Upload a video to your personal library. We save the original and build a visual index in the background.", "upload"],
        ["02", "Describe the moment.", "Once it’s ready, type what you’re looking for. Search one recording or explore your entire indexed library.", "search"],
        ["03", "Press play. Find context.", "Open a matching timeframe and watch the clip. Come back later with a different question—your index is saved.", "play"],
      ].map(([number, title, text, icon]) => <article className="step" key={number}><div className="step-track"><span>{number}</span><Icon name={icon as IconName} size={22} /></div><h3>{title}</h3><p>{text}</p></article>)}</div></div></section>

      <section className="library-story container section"><div><p className="eyebrow">YOUR FOOTAGE HAS A HOME.</p><h2>A growing library.<br />Not another lost file.</h2><p className="section-description">Every upload becomes part of your workspace. Pick up where you left off, find an old recording, or add something new.</p><ul className="check-list"><li><Icon name="check" />Saved uploads and indexing history</li><li><Icon name="check" />Search one video or your whole library</li><li><Icon name="check" />Clear processing status and simple controls</li></ul><Link className="text-link" to={destination}>Make room for your next discovery <Icon name="arrow" size={18} /></Link></div><div className="library-illustration"><div className="illustration-heading"><Icon name="library" /><strong>Your library</strong><span>Sample workspace</span></div>{[["City walk.mp4", "00:24", "Ready to search"], ["Afternoon commute.mov", "02:18", "Ready to search"], ["Weekend footage.mp4", "04:32", "Indexing · 64%"]].map(([name, duration, status], i) => <div className="illustration-file" key={name}><span className={`file-art art-${i}`}><Icon name="film" size={22} /></span><div><strong>{name}</strong><small>{duration} · {status}</small></div><Icon name={i === 2 ? "clock" : "check"} size={17} /></div>)}<div className="illustration-bottom"><Icon name="shield" size={16} />Connected to your account. Ready when you return.</div></div></section>

      <section id="faq" className="faq-section container section"><div><p className="eyebrow">A LITTLE MORE CLARITY.</p><h2>Good questions.<br />Straight answers.</h2></div><div className="faq-list">{questions.map(([question, answer]) => <details key={question}><summary>{question}<Icon name="plus" size={18} /></summary><p>{answer}</p></details>)}</div></section>

      <section className="final-cta container"><span className="eyebrow">LESS SEEKING. MORE SEEING.</span><h2>Your next discovery<br />is already in your footage.</h2><Link className="btn primary" to={destination}>{token ? "Open your workspace" : "Get started with Clipseek"}<Icon name="arrow" size={18} /></Link></section>
    </main>
    <footer className="site-footer container"><div><Link to="/" aria-label="Clipseek home"><Brand /></Link><p>Find the moment, not the filename.</p></div><div className="footer-links"><a href="#features">Features</a><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link><Link to={token ? "/app" : "/login"}>{token ? "Workspace" : "Log in"}</Link></div><span className="copyright">© {new Date().getFullYear()} Clipseek</span></footer>
  </div>;
}
