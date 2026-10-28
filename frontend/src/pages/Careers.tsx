import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileSpreadsheet, Plus } from "lucide-react";
import { useState } from "react";
import { Button } from "../components/ui/button";
import { api, post, type Career, type Preview } from "../shared/api";
import { Feedback } from "../shared/components";

export function Careers({
  careers,
  current,
  onSelect,
}: {
  careers: Career[];
  current: number | null;
  onSelect: (id: number) => void;
}) {
  const client = useQueryClient();
  const [name, setName] = useState("");
  const [year, setYear] = useState(2023);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [replace, setReplace] = useState(false);
  const [message, setMessage] = useState("");
  const create = useMutation({
    mutationFn: () => post<Career>("/careers", { name, start_year: year }),
    onSuccess: (career) => {
      void client.invalidateQueries();
      onSelect(career.id);
      setName("");
      setPreview(null);
    },
  });
  const upload = useMutation({
    mutationFn: (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return api<Preview>(`/careers/${current}/imports/preview`, {
        method: "POST",
        body,
      });
    },
    onSuccess: (p) => {
      setPreview(p);
      setReplace(false);
      setMessage("");
    },
  });
  const commit = useMutation({
    mutationFn: () =>
      post<{ duplicate: boolean }>(`/careers/${current}/imports/commit`, {
        preview_token: preview?.preview_token,
        strategy: replace ? "replace" : "reject",
      }),
    onSuccess: (result) => {
      setMessage(
        result.duplicate
          ? "Этот файл уже импортирован. Итоги не изменились."
          : "История импортирована. Показатели рассчитаны из БД.",
      );
      setPreview(null);
      void client.invalidateQueries();
    },
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">YOUR FOOTBALL STORIES</div>
          <h1>Карьеры и источники</h1>
          <p>
            Каждая карьера — отдельная история со своими игроками и
            сохранениями.
          </p>
        </div>
      </div>
      <div className="two-columns">
        <section className="panel">
          <div className="panel-heading">
            <h2>Мои карьеры</h2>
            <span className="pill">{careers.length}</span>
          </div>
          {careers.map((c) => (
            <button
              key={c.id}
              className={`career-card ${current === c.id ? "selected" : ""}`}
              onClick={() => {
                onSelect(c.id);
                setPreview(null);
                setMessage("");
              }}
            >
              <span className="mini-crest">LC</span>
              <span>
                <strong>{c.name}</strong>
                <small>{c.game_version} · отдельная база показателей</small>
              </span>
              {current === c.id && <CheckCircle2 size={20} />}
            </button>
          ))}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate();
            }}
            className="form-stack"
          >
            <h3>
              <Plus size={16} /> Новая карьера
            </h3>
            <label className="field">
              Название
              <input
                required
                maxLength={120}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Например, Leicester City"
              />
            </label>
            <label className="field">
              Начальный сезон
              <input
                type="number"
                min={2000}
                max={2200}
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
              />
            </label>
            <Button disabled={create.isPending}>Создать карьеру</Button>
            <Feedback error={create.error} />
          </form>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>
              <FileSpreadsheet size={18} /> Исторические данные
            </h2>
            <span className="pill">XLSX / CSV</span>
          </div>
          <p className="muted">
            Разовая загрузка истории. Для Excel читается только лист «Все
            сезоны». Итоги и Г+П рассчитывает приложение.
          </p>
          <label className="upload">
            <FileSpreadsheet size={30} />
            <strong>
              {current
                ? "Выберите исторический файл"
                : "Сначала создайте карьеру"}
            </strong>
            <span>До 5 MiB · CSV UTF-8 или XLSX</span>
            <input
              aria-label="Исторический Excel или CSV"
              disabled={!current}
              type="file"
              accept=".xlsx,.csv"
              onChange={(e) => {
                if (e.target.files?.[0]) {
                  setPreview(null);
                  upload.mutate(e.target.files[0]);
                }
              }}
            />
          </label>
          <Feedback
            loading={upload.isPending || commit.isPending}
            error={upload.error || commit.error}
          />
          {message && (
            <div className="success" role="status">
              {message}
            </div>
          )}
          {preview && (
            <div className="import-preview">
              <h3>Предпросмотр: {preview.rows_count} строк</h3>
              <p className="muted">
                Охват: {preview.coverage}.{" "}
                {preview.duplicate
                  ? "Повторный файл: суммы останутся прежними."
                  : "Проверьте строки перед импортом."}
              </p>
              {preview.errors.map((e) => (
                <div role="alert" className="alert" key={e.row}>
                  Строка {e.row}: {e.message}
                </div>
              ))}
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Сезон</th>
                      <th>Игрок</th>
                      <th>Голы</th>
                      <th>Ассисты</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.slice(0, 6).map((r, i) => (
                      <tr key={i}>
                        <td>{String(r.season)}</td>
                        <td>{String(r.name)}</td>
                        <td>{r.goals == null ? "—" : String(r.goals)}</td>
                        <td>{r.assists == null ? "—" : String(r.assists)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {preview.conflicts.length > 0 && (
                <>
                  <div className="alert">
                    Конфликтующих строк: {preview.conflicts.length}. Они могут
                    быть заменены только явно.
                  </div>
                  <details>
                    <summary>Показать конфликты</summary>
                    {preview.conflicts.map((c, i) => (
                      <pre key={i}>
                        {c.player} · {c.season}
                        {"\n"}
                        {JSON.stringify(
                          { existing: c.existing, incoming: c.incoming },
                          null,
                          2,
                        )}
                      </pre>
                    ))}
                  </details>
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={replace}
                      onChange={(e) => setReplace(e.target.checked)}
                    />
                    Подтверждаю замену перечисленных строк
                  </label>
                </>
              )}
              <Button
                disabled={
                  !preview.preview_token ||
                  commit.isPending ||
                  (preview.conflicts.length > 0 && !replace)
                }
                onClick={() => commit.mutate()}
              >
                Подтвердить импорт
              </Button>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
