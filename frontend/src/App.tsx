import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowLeftRight,
  ChevronRight,
  CircleHelp,
  FolderOpen,
  LayoutDashboard,
  Users,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { Careers } from "./pages/Careers";
import { Compare } from "./pages/Compare";
import { PlayerDrawer, PlayerProfile } from "./pages/Player";
import { Squad } from "./pages/Squad";
import { Summary } from "./pages/Summary";
import { Sync } from "./pages/Sync";
import {
  api,
  type Career,
  type Filters,
  type Season,
  type Sync as SyncDTO,
} from "./shared/api";
import { Feedback } from "./shared/components";
import { ScopeContext } from "./shared/context";

export function App() {
  const [careerId, setCareerId] = useState<number | null>(
    () => Number(localStorage.getItem("careerId")) || null,
  );
  const [filters, setFilters] = useState<Filters>({});
  const [selected, setSelected] = useState<number | null>(null);
  const selectPlayer = useCallback((id: number | null) => setSelected(id), []);
  const careers = useQuery({
    queryKey: ["careers"],
    queryFn: () => api<Career[]>("/careers"),
  });
  const career =
    careers.data?.find((c) => c.id === careerId) || careers.data?.[0];
  const seasons = useQuery({
    queryKey: ["seasons", career?.id],
    queryFn: () => api<Season[]>(`/careers/${career!.id}/seasons`),
    enabled: !!career,
  });
  const sync = useQuery({
    queryKey: ["sync", career?.id],
    queryFn: () => api<SyncDTO>(`/careers/${career!.id}/sync/status`),
    enabled: !!career,
  });
  const competitions = useQuery({
    queryKey: ["competitions", career?.id],
    queryFn: () =>
      api<{ id: number; name: string }[]>(
        `/careers/${career!.id}/competitions`,
      ),
    enabled: !!career,
  });
  const location = useLocation();
  useEffect(() => {
    setFilters({});
    setSelected(null);
  }, [career?.id]);
  const choose = (id: number) => {
    localStorage.setItem("careerId", String(id));
    setCareerId(id);
    setFilters({});
    setSelected(null);
  };
  const nav = [
    ["/", LayoutDashboard, "Обзор карьеры"],
    ["/squad", Users, "Состав и история"],
    ["/compare", ArrowLeftRight, "Сравнение"],
    ["/sync", Activity, "Синхронизация"],
    ["/careers", FolderOpen, "Мои карьеры"],
  ] as const;
  const careerPage = (
    <Careers
      key={career?.id || "new"}
      careers={careers.data || []}
      current={career?.id || null}
      onSelect={choose}
    />
  );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/">
          <span className="crest">
            <svg viewBox="0 0 48 48" aria-hidden="true">
              <path
                d="M24 3 41 12v22L24 45 7 34V12Z"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              />
              <path
                d="m14 16 5 3 5-5 5 5 5-3-3 15-7 5-7-5Z"
                fill="currentColor"
                opacity=".8"
              />
            </svg>
          </span>
          <span>
            LEICESTER CITY<small>CAREER ANALYTICS</small>
          </span>
        </a>
        <div className="sidebar-label">ВАШ КЛУБ. ВАША ИСТОРИЯ.</div>
        <nav>
          {nav.map(([to, Icon, label]) => (
            <NavLink key={to} to={to} end={to === "/"}>
              <Icon size={18} />
              {label}
              {to === "/sync" && <span className="nav-dot" />}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-status">
            <span className="green-dot" /> Локальное приложение
          </div>
          <p>
            Ваши данные хранятся
            <br />
            на этом компьютере.
          </p>
          <div className="version">
            <CircleHelp size={15} /> MVP 0.2 · без облака
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            Аналитика <ChevronRight size={14} />
            <strong>
              {nav.find(([p]) => p === location.pathname)?.[2] ||
                "Профиль игрока"}
            </strong>
          </div>
          <div className="topbar-right">
            <span className="collector-status">
              <span
                className={sync.data?.connected ? "green-dot" : "amber-dot"}
              />
              Collector:{" "}
              {sync.data?.collector === "verified by user evidence"
                ? "verified"
                : "not verified"}
            </span>
            <span className="user-mark">LC</span>
          </div>
        </header>
        <div className="scopebar">
          <div className="club-context">
            <span className="mini-crest">LC</span>
            <label>
              <small>КАРЬЕРА</small>
              <select
                aria-label="Карьера"
                value={career?.id || ""}
                onChange={(e) => choose(Number(e.target.value))}
              >
                <option value="" disabled>
                  Выберите карьеру
                </option>
                {careers.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="scope-filters">
            <label>
              <span>Период</span>
              <select
                aria-label="Сезон"
                value={filters.season_id || ""}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    season_id: Number(e.target.value) || undefined,
                  })
                }
              >
                <option value="">За всю карьеру</option>
                {seasons.data?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.start_year}/{String(s.end_year).slice(2)}
                  </option>
                ))}
              </select>
            </label>
            {!!competitions.data?.length && (
              <label>
                <span>Турнир</span>
                <select
                  aria-label="Турнир"
                  value={filters.competition_id || ""}
                  onChange={(e) =>
                    setFilters({
                      ...filters,
                      competition_id: Number(e.target.value) || undefined,
                    })
                  }
                >
                  <option value="">Все турниры</option>
                  {competitions.data.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {(sync.data?.saves.length || 0) > 1 && (
              <label>
                <span>Сохранение</span>
                <select
                  aria-label="Сохранение"
                  value={filters.save_id || ""}
                  onChange={(e) =>
                    setFilters({
                      ...filters,
                      save_id: Number(e.target.value) || undefined,
                    })
                  }
                >
                  <option value="">Выберите save</option>
                  {sync.data?.saves.map((s) => (
                    <option key={s.id} value={s.id}>
                      Save #{s.id}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {sync.data?.last_synced_at && (
              <label>
                <span>На момент (Live)</span>
                <input
                  aria-label="Дата снимка"
                  type="datetime-local"
                  onChange={(e) =>
                    setFilters({
                      ...filters,
                      as_of: e.target.value
                        ? new Date(e.target.value).toISOString()
                        : undefined,
                    })
                  }
                />
              </label>
            )}
          </div>
        </div>
        <main>
          <Feedback loading={careers.isLoading} error={careers.error} />
          {!careers.isLoading &&
            !careers.error &&
            (career ? (
              <ScopeContext.Provider
                value={{ career, filters, selected, selectPlayer }}
              >
                <Routes>
                  <Route path="/" element={<Summary />} />
                  <Route path="/squad" element={<Squad key={career.id} />} />
                  <Route path="/players/:id" element={<PlayerProfile />} />
                  <Route
                    path="/compare"
                    element={<Compare key={career.id} />}
                  />
                  <Route path="/sync" element={<Sync key={career.id} />} />
                  <Route path="/careers" element={careerPage} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
                <PlayerDrawer />
              </ScopeContext.Provider>
            ) : (
              careerPage
            ))}
        </main>
        <footer>
          LEICESTER CITY ANALYTICS{" "}
          <span>История — в данных. Решения — за вами.</span>
        </footer>
      </div>
    </div>
  );
}
