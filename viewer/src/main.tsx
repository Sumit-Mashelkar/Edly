import { StrictMode, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes, useParams } from "react-router-dom";
import "./styles.css";

type Episode = {
  episode_title: string;
  synopsis?: string;
  duration_seconds?: number;
  language?: string;
  available_languages?: string[];
  content_group?: string;
  artwork?: Record<string, string>;
};

type ShowItem = {
  id: number;
  title: string;
  slug: string;
  synopsis?: string;
  section?: string;
  categories?: string[];
  seasons?: Array<{ season_number: number; episodes: Episode[] }>;
};

type CatalogueResponse = {
  shows?: ShowItem[];
};

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function mediaUrl(storageKey?: string) {
  return storageKey ? `${API_BASE}/media/${storageKey}` : "";
}

async function fetchCatalogue() {
  const response = await fetch(`${API_BASE}/catalog`);
  if (!response.ok) throw new Error("Unable to load catalogue");
  return (await response.json()) as CatalogueResponse;
}

function HomePage() {
  const [catalogue, setCatalogue] = useState<CatalogueResponse>({ shows: [] });
  const [search, setSearch] = useState("");
  const [selectedSection, setSelectedSection] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void fetchCatalogue()
      .then(setCatalogue)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load the catalogue."))
      .finally(() => setLoading(false));
  }, []);

  const visibleShows = useMemo(() => {
    const list = catalogue.shows || [];
    return list.filter((show) => {
      const matchesSearch =
        !search ||
        [show.title, show.synopsis, show.section, ...(show.categories || [])]
          .join(" ")
          .toLowerCase()
          .includes(search.toLowerCase());
      const matchesSection = selectedSection === "all" || show.section === selectedSection;
      return matchesSearch && matchesSection;
    });
  }, [catalogue, search, selectedSection]);

  const sections = Array.from(new Set((catalogue.shows || []).map((show) => show.section).filter(Boolean)));
  const featured = visibleShows.find((show) => show.section === "featured") || visibleShows[0];

  return (
    <main className="viewer-shell">
      <header className="viewer-header">
        <div>
          <p className="eyebrow">Peblo TV Mini</p>
          <h1>Browse the published catalogue</h1>
        </div>
        <div className="search-row">
          <input
            value={search}
            placeholder="Search shows or episodes"
            onChange={(event) => setSearch(event.target.value)}
          />
          <select value={selectedSection} onChange={(event) => setSelectedSection(event.target.value)}>
            <option value="all">All sections</option>
            {sections.map((section) => (
              <option key={section} value={section}>{section}</option>
            ))}
          </select>
        </div>
      </header>

      {loading ? <div className="state-panel">Loading the published catalogue...</div> : null}
      {error ? <div className="state-panel error-state">{error}</div> : null}
      {!loading && !error && !featured ? <div className="state-panel"><strong>No published content yet.</strong><span>An administrator must publish the catalogue before it appears here.</span></div> : null}
      {featured ? (
        <section className="hero">
          <div className="hero-copy">
            <span className="pill">Featured</span>
            <h2>{featured.title}</h2>
            <p>{featured.synopsis}</p>
            <Link to={`/show/${featured.slug}`} className="primary-link">Watch now</Link>
          </div>
          <div className="hero-art" aria-label="featured show artwork">
            {featured.seasons?.[0]?.episodes?.[0]?.artwork?.banner ? <img src={mediaUrl(featured.seasons[0].episodes[0].artwork.banner)} alt={`${featured.title} banner`} /> : "Featured artwork"}
          </div>
        </section>
      ) : null}

      <section className="rows">
        {visibleShows.map((show) => (
          <div key={show.id} className="row-block">
            <div className="row-title-row">
              <h3>{show.title}</h3>
              <Link to={`/show/${show.slug}`}>View all</Link>
            </div>
            <div className="card-row">
              {(show.seasons || []).flatMap((season) => season.episodes || []).slice(0, 5).map((episode, index) => (
                <article key={`${show.id}-${episode.content_group || index}`} className="video-card">
                  <div className="thumb">{episode.artwork?.thumbnail ? <img src={mediaUrl(episode.artwork.thumbnail)} alt={`${episode.episode_title} thumbnail`} /> : "Thumbnail"}</div>
                  <strong>{episode.episode_title}</strong>
                  <span>{episode.language}</span>
                </article>
              ))}
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}

function ShowDetailPage() {
  const { slug } = useParams();
  const [shows, setShows] = useState<ShowItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void fetchCatalogue()
      .then((result) => setShows(result.shows || []))
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load the show."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <main className="viewer-shell"><div className="state-panel">Loading show...</div></main>;
  if (error) return <main className="viewer-shell"><div className="state-panel error-state">{error}</div></main>;
  const show = shows.find((item) => item.slug === slug);
  if (!show) {
    return <main className="viewer-shell"><h2>Show not found.</h2></main>;
  }

  return (
    <main className="viewer-shell">
      <Link to="/" className="back-link">← Back to home</Link>
      <section className="detail-header">
        <div>
          <p className="eyebrow">{show.section}</p>
          <h1>{show.title}</h1>
          <p>{show.synopsis}</p>
        </div>
        <div className="detail-art">{show.seasons?.[0]?.episodes?.[0]?.artwork?.poster ? <img src={mediaUrl(show.seasons[0].episodes[0].artwork.poster)} alt={`${show.title} poster`} /> : "Poster"}</div>
      </section>

      {(show.seasons || []).filter((season) => season.season_number !== 0).map((season) => (
        <section key={season.season_number} className="season-block">
          <h3>Season {season.season_number}</h3>
          <div className="episode-list">
            {(season.episodes || []).map((episode) => (
              <article key={episode.content_group} className="episode-item">
                <div className="thumb small">{episode.artwork?.thumbnail ? <img src={mediaUrl(episode.artwork.thumbnail)} alt={`${episode.episode_title} thumbnail`} /> : "Thumb"}</div>
                <div>
                  <strong>{episode.episode_title}</strong>
                  <p>{episode.synopsis}</p>
                  <small>{episode.available_languages?.join(", ") || episode.language}</small>
                </div>
              </article>
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/show/:slug" element={<ShowDetailPage />} />
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
