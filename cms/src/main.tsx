import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import "./styles.css";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const PAGE_SIZE = 8;
const artworkSpecs = {
  poster: ["2:3", "600 x 900 px"],
  banner: ["16:9", "1280 x 720 px"],
  thumbnail: ["16:9", "640 x 360 px"],
} as const;
type Role = "editor" | "admin";
type ArtworkType = keyof typeof artworkSpecs;
type Artwork = {
  id: number;
  artwork_type: ArtworkType;
  storage_key?: string;
  original_filename?: string;
};
type Episode = {
  id: number;
  episode_number: number;
  episode_title: string;
  synopsis?: string;
  duration_seconds: number;
  language: string;
  content_group: string;
  source_episode_id: string;
  status: string;
  artwork: Artwork[];
};
type Season = {
  id: number;
  season_number: number;
  title?: string;
  episodes: Episode[];
};
type Show = {
  id: number;
  title: string;
  slug: string;
  synopsis: string;
  section: string;
  categories: string[];
  status: string;
  artwork: Artwork[];
  seasons?: Season[];
};
type Issue = {
  subject: string;
  message: string;
  action: string;
  show_id?: number;
  episode_id?: number;
  blocker: boolean;
};

async function request(path: string, token: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(`${API}${path}`, { ...options, headers });
  } catch {
    throw new Error("Cannot reach the backend. Start FastAPI on port 8000.");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok)
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : "The backend rejected this request.",
    );
  return data;
}
function errorText(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Try again.";
}

function Login({ onLogin }: { onLogin: (token: string, role: Role) => void }) {
  const [email, setEmail] = useState("editor@example.com");
  const [password, setPassword] = useState("peblo-dev-password");
  const login = useMutation({
    mutationFn: () =>
      request("/auth/login", "", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    onSuccess: (data) =>
      onLogin(
        data.access_token,
        email.startsWith("admin") ? "admin" : "editor",
      ),
  });
  return (
    <main className="login-page">
      <form
        className="login-card"
        onSubmit={(event) => {
          event.preventDefault();
          login.mutate();
        }}
      >
        <span className="eyebrow">PEBLO TV MINI</span>
        <h1>Internal CMS</h1>
        <p className="muted">Catalogue, artwork, and publishing control.</p>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <button disabled={login.isPending}>
          {login.isPending ? "Signing in..." : "Sign in"}
        </button>
        <div className="dev-logins">
          <button
            type="button"
            className="quiet"
            onClick={() => {
              setEmail("editor@example.com");
              setPassword("peblo-dev-password");
            }}
          >
            Use editor
          </button>
          <button
            type="button"
            className="quiet"
            onClick={() => {
              setEmail("admin@example.com");
              setPassword("peblo-dev-password");
            }}
          >
            Use admin
          </button>
        </div>
        {login.isError && (
          <div className="notice error">{errorText(login.error)}</div>
        )}
      </form>
    </main>
  );
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("peblo_token") || "");
  const [role, setRole] = useState<Role | null>(
    (localStorage.getItem("peblo_role") as Role) || null,
  );
  const [tab, setTab] = useState<"content" | "publish">("content");
  const [selected, setSelected] = useState<number | null>(null);
  const [notice, setNotice] = useState("");
  if (!token)
    return (
      <Login
        onLogin={(value, nextRole) => {
          localStorage.setItem("peblo_token", value);
          localStorage.setItem("peblo_role", nextRole);
          setToken(value);
          setRole(nextRole);
        }}
      />
    );
  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <span className="eyebrow">PEBLO TV MINI</span>
          <h1>Internal CMS</h1>
        </div>
        <div className="header-actions">
          <span className="role-badge">{role}</span>
          <button
            className="quiet"
            onClick={() => {
              localStorage.clear();
              setToken("");
            }}
          >
            Log out
          </button>
        </div>
      </header>
      <nav className="tabs">
        <button
          className={tab === "content" ? "active" : ""}
          onClick={() => setTab("content")}
        >
          Content
        </button>
        <button
          className={tab === "publish" ? "active" : ""}
          onClick={() => setTab("publish")}
        >
          Validation & publish
        </button>
        <a href="http://localhost:5174" target="_blank" rel="noreferrer">
          Open viewer
        </a>
      </nav>
      {notice && <div className="notice success">{notice}</div>}
      {tab === "content" ? (
        <Content
          token={token}
          selected={selected}
          setSelected={setSelected}
          setNotice={setNotice}
        />
      ) : (
        <Publish token={token} role={role} setNotice={setNotice} />
      )}
    </main>
  );
}

function Content({
  token,
  selected,
  setSelected,
  setNotice,
}: {
  token: string;
  selected: number | null;
  setSelected: (id: number | null) => void;
  setNotice: (value: string) => void;
}) {
  const [q, setQ] = useState("");
  const [section, setSection] = useState("");
  const [status, setStatus] = useState("");
  const [language, setLanguage] = useState("");
  const [page, setPage] = useState(1);
  const client = useQueryClient();
  const shows = useQuery({
    queryKey: ["shows", q, section, status, language, page],
    queryFn: () =>
      request(
        `/admin/shows?q=${encodeURIComponent(q)}&section=${section}&status=${status}&language=${language}&page=${page}&page_size=${PAGE_SIZE}`,
        token,
      ),
  });
  const detail = useQuery({
    queryKey: ["show", selected],
    queryFn: () => request(`/admin/shows/${selected}`, token),
    enabled: selected !== null,
  });
  const create = useMutation({
    mutationFn: () =>
      request("/admin/shows", token, {
        method: "POST",
        body: JSON.stringify({
          title: "New show",
          slug: `new-show-${Date.now()}`,
          synopsis: "",
          section: "series",
          categories: [],
          status: "draft",
        }),
      }),
    onSuccess: (show) => {
      client.invalidateQueries({ queryKey: ["shows"] });
      setSelected(show.id);
      setNotice("Show created as a draft.");
    },
    onError: (error) => setNotice(errorText(error)),
  });
  return (
    <section className="workspace">
      <aside className="sidebar">
        <div className="section-heading">
          <div>
            <span className="eyebrow">CATALOGUE</span>
            <h2>Shows</h2>
          </div>
          <button onClick={() => create.mutate()} disabled={create.isPending}>
            +
          </button>
        </div>
        <div className="filters">
          <input
            placeholder="Search titles"
            value={q}
            onChange={(event) => {
              setQ(event.target.value);
              setPage(1);
            }}
          />
          <select
            value={section}
            onChange={(event) => {
              setSection(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All sections</option>
            {["featured", "series", "minisodes", "songs"].map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All statuses</option>
            <option>draft</option>
            <option>published</option>
          </select>
          <select
            value={language}
            onChange={(event) => {
              setLanguage(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All languages</option>
            <option>en</option>
            <option>hi</option>
          </select>
        </div>
        {shows.isLoading ? (
          <p className="muted">Loading shows...</p>
        ) : shows.isError ? (
          <div className="notice error">{errorText(shows.error)}</div>
        ) : shows.data?.items?.length ? (
          <>
            {shows.data.items.map((show: Show) => (
              <button
                className={`show-row ${selected === show.id ? "selected" : ""}`}
                key={show.id}
                onClick={() => setSelected(show.id)}
              >
                <strong>{show.title}</strong>
                <span>
                  {show.section} Â· {show.status}
                </span>
              </button>
            ))}
            <div className="pagination">
              <button disabled={page === 1} onClick={() => setPage(page - 1)}>
                Previous
              </button>
              <span>Page {page}</span>
              <button
                disabled={page * PAGE_SIZE >= shows.data.total}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          </>
        ) : (
          <div className="empty">
            <strong>No shows found</strong>
            <span>Change the filters or create a show.</span>
          </div>
        )}
      </aside>
      <section className="editor-pane">
        {detail.isLoading ? (
          <p className="muted">Loading content...</p>
        ) : detail.isError ? (
          <div className="notice error">{errorText(detail.error)}</div>
        ) : detail.data ? (
          <ShowEditor
            token={token}
            show={detail.data}
            setNotice={setNotice}
            refresh={() => {
              client.invalidateQueries({ queryKey: ["show", selected] });
              client.invalidateQueries({ queryKey: ["shows"] });
            }}
          />
        ) : (
          <div className="empty large">
            <strong>Select a show</strong>
            <span>Choose a show to edit its seasons and episodes.</span>
          </div>
        )}
      </section>
    </section>
  );
}

function ShowEditor({
  token,
  show,
  refresh,
  setNotice,
}: {
  token: string;
  show: Show;
  refresh: () => void;
  setNotice: (value: string) => void;
}) {
  const [draft, setDraft] = useState(show);
  const [seasonId, setSeasonId] = useState(show.seasons?.[0]?.id || 0);
  const save = useMutation({
    mutationFn: () =>
      request(`/admin/shows/${show.id}`, token, {
        method: "PATCH",
        body: JSON.stringify(draft),
      }),
    onSuccess: () => {
      refresh();
      setNotice("Show saved.");
    },
    onError: (error) => setNotice(errorText(error)),
  });
  const addSeason = useMutation({
    mutationFn: () =>
      request(`/admin/shows/${show.id}/seasons`, token, {
        method: "POST",
        body: JSON.stringify({
          season_number: (show.seasons?.length || 0) + 1,
          title: "New season",
        }),
      }),
    onSuccess: (season) => {
      refresh();
      setSeasonId(season.id);
      setNotice("Season created.");
    },
  });
  const season = show.seasons?.find((item) => item.id === seasonId);
  return (
    <div className="editor">
      <div className="editor-title">
        <div>
          <span className="eyebrow">SHOW</span>
          <h2>{show.title}</h2>
        </div>
        <button onClick={() => save.mutate()} disabled={save.isPending}>
          {save.isPending ? "Saving..." : "Save show"}
        </button>
      </div>
      <div className="form-grid">
        <label>
          Title
          <input
            value={draft.title}
            onChange={(event) =>
              setDraft({ ...draft, title: event.target.value })
            }
          />
        </label>
        <label>
          Slug
          <input
            value={draft.slug}
            onChange={(event) =>
              setDraft({ ...draft, slug: event.target.value })
            }
          />
        </label>
        <label>
          Section
          <select
            value={draft.section}
            onChange={(event) =>
              setDraft({ ...draft, section: event.target.value })
            }
          >
            {["featured", "series", "minisodes", "songs"].map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select
            value={draft.status}
            onChange={(event) =>
              setDraft({ ...draft, status: event.target.value })
            }
          >
            <option>draft</option>
            <option>published</option>
          </select>
        </label>
        <label className="wide">
          Synopsis
          <textarea
            value={draft.synopsis}
            onChange={(event) =>
              setDraft({ ...draft, synopsis: event.target.value })
            }
          />
        </label>
      </div>
      <ArtworkSlots
        token={token}
        owner={`show_id=${show.id}`}
        artworks={show.artwork}
        refresh={refresh}
        setNotice={setNotice}
      />
      <div className="subsection-heading">
        <div>
          <span className="eyebrow">SEASONS & EPISODES</span>
          <h3>Content structure</h3>
        </div>
        <button className="secondary" onClick={() => addSeason.mutate()}>
          Add season
        </button>
      </div>
      {show.seasons?.length ? (
        <div className="season-tabs">
          {show.seasons.map((item) => (
            <button
              className={seasonId === item.id ? "active" : ""}
              key={item.id}
              onClick={() => setSeasonId(item.id)}
            >
              Season {item.season_number}
            </button>
          ))}
        </div>
      ) : (
        <div className="empty">No seasons yet.</div>
      )}
      {season ? (
        <SeasonEditor
          token={token}
          season={season}
          refresh={refresh}
          setNotice={setNotice}
        />
      ) : null}
    </div>
  );
}

function SeasonEditor({
  token,
  season,
  refresh,
  setNotice,
}: {
  token: string;
  season: Season;
  refresh: () => void;
  setNotice: (value: string) => void;
}) {
  const [title, setTitle] = useState(season.title || "");
  const save = useMutation({
    mutationFn: () =>
      request(`/admin/seasons/${season.id}`, token, {
        method: "PATCH",
        body: JSON.stringify({ season_number: season.season_number, title }),
      }),
    onSuccess: () => {
      refresh();
      setNotice("Season saved.");
    },
  });
  const add = useMutation({
    mutationFn: () =>
      request(`/admin/seasons/${season.id}/episodes`, token, {
        method: "POST",
        body: JSON.stringify({
          source_episode_id: `episode-${Date.now()}`,
          episode_number: season.episodes.length + 1,
          episode_title: "New episode",
          synopsis: "",
          duration_seconds: 0,
          language: "en",
          content_group: `group-${Date.now()}`,
          status: "draft",
        }),
      }),
    onSuccess: () => {
      refresh();
      setNotice("Episode created as a draft.");
    },
  });
  return (
    <div className="season-editor">
      <div className="inline-form">
        <label>
          Season title
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <button className="secondary" onClick={() => save.mutate()}>
          Save season
        </button>
        <button onClick={() => add.mutate()}>Add episode</button>
      </div>
      {season.episodes.length ? (
        season.episodes.map((episode) => (
          <EpisodeEditor
            key={episode.id}
            token={token}
            episode={episode}
            refresh={refresh}
            setNotice={setNotice}
          />
        ))
      ) : (
        <div className="empty">No episodes in this season.</div>
      )}
    </div>
  );
}

function EpisodeEditor({
  token,
  episode,
  refresh,
  setNotice,
}: {
  token: string;
  episode: Episode;
  refresh: () => void;
  setNotice: (value: string) => void;
}) {
  const [draft, setDraft] = useState(episode);
  const save = useMutation({
    mutationFn: () =>
      request(`/admin/episodes/${episode.id}`, token, {
        method: "PATCH",
        body: JSON.stringify(draft),
      }),
    onSuccess: () => {
      refresh();
      setNotice("Episode saved.");
    },
    onError: (error) => setNotice(errorText(error)),
  });
  return (
    <article className="episode-card">
      <div className="episode-heading">
        <strong>Episode {episode.episode_number}</strong>
        <span className={`status ${draft.status}`}>{draft.status}</span>
        <button onClick={() => save.mutate()} disabled={save.isPending}>
          Save episode
        </button>
      </div>
      <div className="form-grid compact">
        <label>
          Title
          <input
            value={draft.episode_title}
            onChange={(event) =>
              setDraft({ ...draft, episode_title: event.target.value })
            }
          />
        </label>
        <label>
          Language
          <select
            value={draft.language}
            onChange={(event) =>
              setDraft({ ...draft, language: event.target.value })
            }
          >
            <option>en</option>
            <option>hi</option>
          </select>
        </label>
        <label>
          Duration seconds
          <input
            type="number"
            min="0"
            value={draft.duration_seconds}
            onChange={(event) =>
              setDraft({
                ...draft,
                duration_seconds: Number(event.target.value),
              })
            }
          />
        </label>
        <label>
          Status
          <select
            value={draft.status}
            onChange={(event) =>
              setDraft({ ...draft, status: event.target.value })
            }
          >
            <option>draft</option>
            <option>published</option>
          </select>
        </label>
        <label className="wide">
          Content group
          <input
            value={draft.content_group}
            onChange={(event) =>
              setDraft({ ...draft, content_group: event.target.value })
            }
          />
        </label>
      </div>
      <ArtworkSlots
        token={token}
        owner={`episode_id=${episode.id}`}
        artworks={episode.artwork}
        refresh={refresh}
        setNotice={setNotice}
      />
    </article>
  );
}

function ArtworkSlots({
  token,
  owner,
  artworks,
  refresh,
  setNotice,
}: {
  token: string;
  owner: string;
  artworks: Artwork[];
  refresh: () => void;
  setNotice: (value: string) => void;
}) {
  return (
    <div className="artwork-section">
      <div className="subsection-heading">
        <div>
          <span className="eyebrow">ARTWORK</span>
          <h3>Required media</h3>
        </div>
        <small>Backend validates type, ratio, size, and dimensions</small>
      </div>
      <div className="artwork-grid">
        {(Object.keys(artworkSpecs) as ArtworkType[]).map((type) => (
          <ArtworkSlot
            key={type}
            type={type}
            token={token}
            owner={owner}
            artwork={artworks.find((item) => item.artwork_type === type)}
            refresh={refresh}
            setNotice={setNotice}
          />
        ))}
      </div>
    </div>
  );
}
function ArtworkSlot({
  type,
  token,
  owner,
  artwork,
  refresh,
  setNotice,
}: {
  type: ArtworkType;
  token: string;
  owner: string;
  artwork?: Artwork;
  refresh: () => void;
  setNotice: (value: string) => void;
}) {
  const [preview, setPreview] = useState("");
  const upload = useMutation({
    mutationFn: async (file: File) => {
      const image = await createImageBitmap(file);
      const ratio = type === "poster" ? 2 / 3 : 16 / 9;
      if (Math.abs(image.width / image.height - ratio) > 0.03)
        throw new Error(
          `${artworkSpecs[type][0]} aspect ratio required for ${type}.`,
        );
      const form = new FormData();
      form.append("file", file);
      return request(
        `/admin/artwork/upload?artwork_type=${type}&${owner}`,
        token,
        { method: "POST", body: form },
      );
    },
    onSuccess: () => {
      refresh();
      setNotice(`${type} uploaded successfully.`);
    },
    onError: (error) => setNotice(errorText(error)),
  });
  return (
    <div className="artwork-slot">
      <div className="slot-head">
        <strong>{type[0].toUpperCase() + type.slice(1)}</strong>
        <span>{artworkSpecs[type][0]}</span>
      </div>
      <p>{artworkSpecs[type][1]} Â· max 200 KB</p>
      {preview || artwork ? (
        <img
          className="preview"
          src={preview || `${API}/media/${artwork?.storage_key}`}
          alt={`${type} preview`}
        />
      ) : (
        <div className="preview placeholder">No image</div>
      )}
      <label className="upload-control">
        {upload.isPending ? "Uploading..." : "Choose image"}
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              setPreview(URL.createObjectURL(file));
              upload.mutate(file);
            }
          }}
        />
      </label>
      {artwork ? (
        <small className="upload-ok">
          Attached: {artwork.original_filename}
        </small>
      ) : (
        <small className="muted">Required for published content</small>
      )}
    </div>
  );
}

function Publish({
  token,
  role,
  setNotice,
}: {
  token: string;
  role: Role | null;
  setNotice: (value: string) => void;
}) {
  const client = useQueryClient();
  const report = useQuery({
    queryKey: ["validation"],
    queryFn: () => request("/admin/validation-report", token),
  });
  const history = useQuery({
    queryKey: ["runs"],
    queryFn: () => request("/admin/publish-runs", token),
  });
  const publish = useMutation({
    mutationFn: () =>
      request("/admin/catalog/publish", token, { method: "POST" }),
    onSuccess: (data) => {
      setNotice(data.message);
      client.invalidateQueries({ queryKey: ["validation"] });
      client.invalidateQueries({ queryKey: ["runs"] });
    },
    onError: (error) => setNotice(errorText(error)),
  });
  const issues: Issue[] = report.data?.issues || [];
  const blockers = report.data?.summary?.blocking_issues || 0;
  const groups = issues.reduce<Record<string, Issue[]>>((result, issue) => {
    const key = issue.show_id
      ? `Show ${issue.show_id}${issue.episode_id ? ` Â· Episode ${issue.episode_id}` : ""}`
      : "General";
    (result[key] ||= []).push(issue);
    return result;
  }, {});
  return (
    <section className="publish-page">
      <div className="publish-header">
        <div>
          <span className="eyebrow">RELEASE CONTROL</span>
          <h2>Validation & publish</h2>
          <p className="muted">
            The backend validation report is the source of truth.
          </p>
        </div>
        <button
          disabled={
            role !== "admin" ||
            blockers > 0 ||
            publish.isPending ||
            report.isLoading
          }
          onClick={() => publish.mutate()}
        >
          {publish.isPending ? "Publishing..." : "Publish catalogue"}
        </button>
      </div>
      {role !== "admin" && (
        <div className="notice warning">
          Editor access only. An admin must publish.
        </div>
      )}
      <div className="summary-row">
        <div>
          <strong>{report.isLoading ? "..." : blockers}</strong>
          <span>blocking issues</span>
        </div>
        <div>
          <strong>{report.data?.summary?.total_issues ?? "..."}</strong>
          <span>total issues</span>
        </div>
        <div>
          <strong>{report.data?.valid ? "Ready" : "Blocked"}</strong>
          <span>release status</span>
        </div>
      </div>
      <div className="publish-columns">
        <section className="panel">
          <h3>Problems to fix</h3>
          {report.isLoading ? (
            <p className="muted">Loading report...</p>
          ) : Object.entries(groups).length ? (
            Object.entries(groups).map(([key, group]) => (
              <div className="issue-group" key={key}>
                <h4>{key}</h4>
                {group.map((issue, index) => (
                  <div className="issue" key={index}>
                    <strong>{issue.subject}</strong>
                    <p>{issue.message}</p>
                    <small>{issue.action}</small>
                  </div>
                ))}
              </div>
            ))
          ) : (
            <div className="empty">
              <strong>No validation issues</strong>
              <span>Ready to publish.</span>
            </div>
          )}
        </section>
        <section className="panel">
          <h3>Publish history</h3>
          {history.isLoading ? (
            <p className="muted">Loading history...</p>
          ) : history.data?.items?.length ? (
            history.data.items.map((run: any) => (
              <div className="history-row" key={run.id}>
                <div>
                  <strong>Run #{run.id}</strong>
                  <span>{new Date(run.started_at).toLocaleString()}</span>
                </div>
                <span className={`status ${run.status}`}>{run.status}</span>
              </div>
            ))
          ) : (
            <div className="empty">
              <strong>No publish runs</strong>
              <span>Attempts will appear here.</span>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={new QueryClient()}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
