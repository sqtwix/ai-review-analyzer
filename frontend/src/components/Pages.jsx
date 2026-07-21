import { useState, useMemo } from "react";
import { 
  ArchiveRestore, ArrowLeft, Construction, Eye, Layers3, Monitor, Moon, PanelLeftClose, 
  PanelLeftOpen, Search, Sun, Pencil, Archive, Save, BookOpen, BarChart3, MessageSquare, 
  AlertTriangle, CheckCircle, HelpCircle, ChevronRight, ThumbsUp, Quote
} from "lucide-react";
import { buildCourseReportViewModel } from "../reportViewModel";
import { DashboardTab } from "./report/DashboardTab";

// ========================= Auth Page Component =========================
export function AuthPage({
  mode,
  authError,
  loginEmail,
  loginPassword,
  registerUsername,
  registerEmail,
  registerPassword,
  onLoginEmailChange,
  onLoginPasswordChange,
  onRegisterUsernameChange,
  onRegisterEmailChange,
  onRegisterPasswordChange,
  onSubmit,
  onClearError,
}) {
  const isLogin = mode === "login";

  return (
    <section className="page auth-page active" id={mode} data-title={isLogin ? "Авторизация" : "Регистрация"}>
      <form className="auth-card" onSubmit={onSubmit}>
        <p className="eyebrow">{isLogin ? "Вход" : "Регистрация"}</p>
        <h2>{isLogin ? "Добро пожаловать" : "Создайте рабочее пространство"}</h2>
        {authError && <div className="error-box">{authError}</div>}

        {!isLogin && (
          <label>
            Имя пользователя
            <input
              type="text"
              placeholder="Ирина"
              value={registerUsername}
              onChange={(e) => onRegisterUsernameChange(e.target.value)}
              required
            />
          </label>
        )}

        <label>
          Email
          <input
            type="email"
            placeholder="name@university.ru"
            value={isLogin ? loginEmail : registerEmail}
            onChange={(e) => (isLogin ? onLoginEmailChange(e.target.value) : onRegisterEmailChange(e.target.value))}
            required
          />
        </label>

        <label>
          Пароль
          <input
            type="password"
            placeholder={isLogin ? "Пароль" : "Минимум 6 символов"}
            value={isLogin ? loginPassword : registerPassword}
            onChange={(e) => (isLogin ? onLoginPasswordChange(e.target.value) : onRegisterPasswordChange(e.target.value))}
            required
          />
        </label>

        <button type="submit" className="primary-button wide">
          {isLogin ? "Войти" : "Зарегистрироваться"}
        </button>
        <a href={isLogin ? "#register" : "#login"} onClick={onClearError}>
          {isLogin ? "Создать аккаунт" : "Уже есть аккаунт"}
        </a>
      </form>
    </section>
  );
}

// ========================= Coming Soon Page Component =========================
export function ComingSoonPage({ id, title, message }) {
  return (
    <section className="page active" id={id} data-title={title}>
      <div className="state-panel state-panel-compact">
        <span className="state-icon state-icon-warm">
          <Construction size={28} strokeWidth={2.2} />
        </span>
        <h3>Модуль «{title}» находится в разработке</h3>
        <p className="muted">{message}</p>
      </div>
    </section>
  );
}

// ========================= Settings Page Component =========================
export function SettingsPage({
  settings,
  onSettingsChange,
  sidebarWidth,
  isSidebarCollapsed,
  onSidebarToggle,
  onSidebarResizeStart,
  archivedReports = [],
  onUnarchiveReport,
}) {
  const [activeGroup, setActiveGroup] = useState("interface");
  const [archiveQuery, setArchiveQuery] = useState("");
  const accessibility = settings.accessibility || {};
  const recommendedAccessibility = {
    fontSize: "xxlarge",
    colorScheme: "dark",
  };
  const filteredArchivedReports = useMemo(() => {
    const query = archiveQuery.trim().toLowerCase();
    if (!query) return archivedReports;

    return archivedReports.filter((report) =>
      `${report.course || ""} ${report.title || ""}`.toLowerCase().includes(query)
    );
  }, [archivedReports, archiveQuery]);

  return (
    <section
      className={`settings-shell ${isSidebarCollapsed ? "settings-sidebar-collapsed" : ""}`}
      id="settings"
      data-title="Настройки"
      style={{ "--settings-sidebar-width": `${sidebarWidth}px` }}
    >
      <header className="settings-topbar">
        <a className="ghost-button settings-back" href="#upload">
          <ArrowLeft size={17} strokeWidth={2.2} />
          Назад
        </a>
        <button
          type="button"
          className="icon-action-button settings-sidebar-toggle"
          aria-label={isSidebarCollapsed ? "Показать панель настроек" : "Скрыть панель настроек"}
          title={isSidebarCollapsed ? "Показать панель настроек" : "Скрыть панель настроек"}
          onClick={onSidebarToggle}
        >
          {isSidebarCollapsed ? (
            <PanelLeftOpen size={18} strokeWidth={2.2} />
          ) : (
            <PanelLeftClose size={18} strokeWidth={2.2} />
          )}
        </button>
      </header>
      <div className="settings-screen">
        <aside className="settings-side" aria-label="Группы настроек">
          <button
            type="button"
            className={`settings-group-button ${activeGroup === "interface" ? "active" : ""}`}
            onClick={() => setActiveGroup("interface")}
          >
            Интерфейс
          </button>
          <button
            type="button"
            className={`settings-group-button ${activeGroup === "archive" ? "active" : ""}`}
            onClick={() => setActiveGroup("archive")}
          >
            Архив
          </button>
          <button
            type="button"
            className="sidebar-resize-handle settings-resize-handle"
            aria-label="Изменить ширину панели настроек"
            onPointerDown={onSidebarResizeStart}
          ></button>
        </aside>

        <div className="settings-content">
          {activeGroup === "interface" ? (
            <>
              <div className="settings-content-heading">
                <h2>Интерфейс</h2>
              </div>

              <section className="panel settings-panel">
                <div className="settings-copy">
                  <Sun size={20} strokeWidth={2.2} />
                  <div>
                    <h3>Тема</h3>
                    <p className="muted">Выберите светлую, темную или системную тему.</p>
                  </div>
                </div>
                <div className="theme-options" role="radiogroup" aria-label="Тема интерфейса">
                  {[
                    { value: "system", label: "Системная", icon: Monitor },
                    { value: "light", label: "Светлая", icon: Sun },
                    { value: "dark", label: "Темная", icon: Moon },
                  ].map((option) => {
                    const Icon = option.icon;
                    return (
                      <button
                        key={option.value}
                        type="button"
                        className={settings.theme === option.value ? "selected" : ""}
                        role="radio"
                        aria-checked={settings.theme === option.value}
                        onClick={() => onSettingsChange({ theme: option.value })}
                      >
                        <Icon size={17} strokeWidth={2.2} />
                        {option.label}
                      </button>
                    );
                  })}
                </div>
              </section>

              <section className="panel settings-panel">
                <div className="settings-copy">
                  <Eye size={20} strokeWidth={2.2} />
                  <div>
                    <h3>Режим для слабовидящих</h3>
                    <p className="muted">Включает верхнюю панель для выбора шрифта и контрастной цветовой схемы.</p>
                  </div>
                </div>
                <div className="accessibility-panel">
                  <ToggleSwitch
                    checked={accessibility.enabled}
                    ariaLabel="Режим для слабовидящих"
                    onChange={() =>
                      onSettingsChange({
                        accessibility: accessibility.enabled
                          ? { ...accessibility, enabled: false }
                          : { ...recommendedAccessibility, enabled: true },
                      })
                    }
                  />
                </div>
              </section>

              <section className="panel settings-panel">
                <div className="settings-copy">
                  <Layers3 size={20} strokeWidth={2.2} />
                  <div>
                    <h3>Минимальный интерфейс</h3>
                    <p className="muted">Скрывает вторичные подсказки и декоративные элементы, оставляя рабочие сценарии.</p>
                  </div>
                </div>
                <ToggleSwitch
                  checked={settings.minimalUi}
                  ariaLabel="Минимальный интерфейс"
                  onChange={() => onSettingsChange({ minimalUi: !settings.minimalUi })}
                />
              </section>
            </>
          ) : (
            <>
              <div className="settings-content-heading">
                <h2>Архив</h2>
              </div>

              <section className="panel archive-panel">
                <p className="muted archive-description">Здесь хранятся отчеты, скрытые из основной истории.</p>

                <label className="archive-search">
                  <Search size={18} strokeWidth={2.2} aria-hidden="true" />
                  <input
                    type="search"
                    value={archiveQuery}
                    onChange={(e) => setArchiveQuery(e.target.value)}
                    placeholder="Найти архивированный отчет"
                    aria-label="Найти архивированный отчет"
                  />
                </label>

                {filteredArchivedReports.length ? (
                  <div className="archive-list">
                    {filteredArchivedReports.map((report) => (
                      <article className="archive-item" key={report.id}>
                        <div>
                          <strong>{report.course}</strong>
                          <p className="muted">{report.title}</p>
                        </div>
                        <button
                          type="button"
                          className="icon-action-button archive-restore-button"
                          onClick={() => onUnarchiveReport?.(report.id)}
                          aria-label={`Разархивировать отчет ${report.course}`}
                          title="Разархивировать"
                        >
                          <ArchiveRestore size={17} strokeWidth={2.2} />
                        </button>
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="state-panel state-panel-compact archive-empty">
                    <h3>{archiveQuery.trim() ? "Ничего не найдено" : "Архив пуст"}</h3>
                    <p className="muted">
                      {archiveQuery.trim()
                        ? "Попробуйте изменить поисковый запрос."
                        : "Архивированные отчеты появятся здесь."}
                    </p>
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function ToggleSwitch({ checked, label, ariaLabel, onChange }) {
  return (
    <button
      type="button"
      className={`toggle-switch ${checked ? "checked" : ""}`}
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel || label}
      onClick={onChange}
    >
      <span className="toggle-track">
        <span className="toggle-thumb"></span>
      </span>
      {label && <span>{label}</span>}
    </button>
  );
}

// ========================= Listeners (Students) Page Component =========================
export function StudentsPage({ reports, onNewAnalysis }) {
  const [searchQuery, setSearchQuery] = useState("");

  const aggregatedData = useMemo(() => {
    let totalCount = 0;
    let scoreSum = { usefulness: 0, practicality: 0, accessibility: 0, interaction: 0 };
    let scoreCount = 0;
    let positions = { "Специалист": 0, "Руководитель": 0, "Обеспечивающий специалист": 0 };
    let formats = { "очное": 0, "смешанное": 0, "дистанционное": 0 };
    let totalDetached = 0;
    let detachedCount = 0;

    reports.forEach((report) => {
      if (report.status !== "Completed" || !report.result) return;
      const analyses = report.result.courses_analysis || [];
      analyses.forEach((course) => {
        totalCount += course.students_count || 0;
        
        // Stats
        const stats = course.statistics;
        if (stats) {
          if (stats.usefulness) { scoreSum.usefulness += stats.usefulness.average; }
          if (stats.practicality) { scoreSum.practicality += stats.practicality.average; }
          if (stats.accessibility) { scoreSum.accessibility += stats.accessibility.average; }
          if (stats.interaction) { scoreSum.interaction += stats.interaction.average; }
          scoreCount++;

          if (stats.involvement) {
            totalDetached += stats.involvement.detached_percent;
            detachedCount++;
          }
        }

        // Positions
        if (course.position_distribution) {
          Object.entries(course.position_distribution).forEach(([pos, count]) => {
            const cleanPos = pos.includes("Специалист") && !pos.includes("Обеспечивающий") ? "Специалист" : pos;
            if (positions[cleanPos] !== undefined) {
              positions[cleanPos] += count;
            } else {
              positions[cleanPos] = (positions[cleanPos] || 0) + count;
            }
          });
        }

        // Formats
        if (course.preferred_formats) {
          Object.entries(course.preferred_formats).forEach(([fmt, count]) => {
            let key = "очное";
            if (fmt.toLowerCase().includes("смешан")) key = "смешанное";
            if (fmt.toLowerCase().includes("дистанц") || fmt.toLowerCase().includes("онлайн")) key = "дистанционное";
            formats[key] += count;
          });
        }
      });
    });

    const averageSatisfaction = scoreCount > 0 
      ? ((scoreSum.usefulness + scoreSum.practicality + scoreSum.accessibility + scoreSum.interaction) / (4 * scoreCount)).toFixed(1) 
      : "0";
    
    const averageDetached = detachedCount > 0 ? (totalDetached / detachedCount).toFixed(1) : "0";

    return {
      totalCount,
      averageSatisfaction,
      averageDetached,
      positions,
      formats
    };
  }, [reports]);

  const courseList = useMemo(() => {
    const list = [];
    reports.forEach((report) => {
      if (report.status !== "Completed" || !report.result) return;
      const analyses = report.result.courses_analysis || [];
      analyses.forEach((course) => {
        const stats = course.statistics;
        const avgScore = stats 
          ? ((stats.usefulness?.average + stats.practicality?.average + stats.accessibility?.average + stats.interaction?.average) / 4).toFixed(1)
          : "0.0";
        list.push({
          id: report.id,
          name: course.course_name,
          period: course.period,
          students: course.students_count,
          avgScore,
          detached: stats?.involvement?.detached_percent || 0,
          topTopic: course.text_analysis?.top_topics?.[0]?.topic || "Не определена"
        });
      });
    });
    return list;
  }, [reports]);

  const filteredCourses = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return courseList;
    return courseList.filter(c => c.name.toLowerCase().includes(q) || c.topTopic.toLowerCase().includes(q));
  }, [courseList, searchQuery]);

  return (
    <section className="page active" id="students" data-title="Слушатели">
      <section className="panel students-intro">
        <div>
          <p className="eyebrow">Кабинет методиста</p>
          <h2>Слушатели и курсы</h2>
          <p className="muted">
            Сводные аналитические данные по всем опросам из истории. Индикаторы удовлетворенности, распределение категорий слушателей и форматы обучения.
          </p>
        </div>
        <span className="badge">Все данные</span>
      </section>

      {reports.length === 0 ? (
        <section className="state-panel">
          <h2>Пока нет обработанных данных</h2>
          <p className="muted">Загрузите файлы отзывов, чтобы сформировать сводный профиль слушателей.</p>
          <button className="primary-button state-action" type="button" onClick={onNewAnalysis}>
            Новый анализ
          </button>
        </section>
      ) : (
        <>
          <section className="metrics-grid" aria-label="Сводные метрики слушателей">
            <div className="metric-card">
              <span>Слушателей охвачено</span>
              <strong>{aggregatedData.totalCount}</strong>
              <small>человек по опросам</small>
            </div>
            <div className="metric-card normal">
              <span>Удовлетворенность</span>
              <strong>{aggregatedData.averageSatisfaction} / 10</strong>
              <small>средняя по 4 критериям</small>
            </div>
            <div className="metric-card risk">
              <span>Отстраненность (Detached)</span>
              <strong>{aggregatedData.averageDetached}%</strong>
              <small>чувствовали скуку/отрыв</small>
            </div>
          </section>

          <div className="grid two" style={{ marginTop: "24px" }}>
            <section className="panel">
              <h3>Категории слушателей</h3>
              <div className="stats-breakdown" style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "14px" }}>
                {Object.entries(aggregatedData.positions).map(([pos, count]) => {
                  const total = Math.max(Object.values(aggregatedData.positions).reduce((a, b) => a + b, 0), 1);
                  const pct = Math.round((count / total) * 100);
                  return (
                    <div key={pos} className="breakdown-row">
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px", fontSize: "0.9rem" }}>
                        <span><b>{pos}</b></span>
                        <span className="muted">{count} чел. ({pct}%)</span>
                      </div>
                      <div style={{ background: "var(--border-color)", height: "8px", borderRadius: "4px", overflow: "hidden" }}>
                        <div style={{ width: `${pct}%`, background: "var(--accent-color)", height: "100%" }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="panel">
              <h3>Предпочитаемые форматы обучения</h3>
              <div className="stats-breakdown" style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "14px" }}>
                {Object.entries(aggregatedData.formats).map(([format, count]) => {
                  const total = Math.max(Object.values(aggregatedData.formats).reduce((a, b) => a + b, 0), 1);
                  const pct = Math.round((count / total) * 100);
                  return (
                    <div key={format} className="breakdown-row">
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px", fontSize: "0.9rem" }}>
                        <span style={{ textTransform: "capitalize" }}><b>{format}</b></span>
                        <span className="muted">{pct}%</span>
                      </div>
                      <div style={{ background: "var(--border-color)", height: "8px", borderRadius: "4px", overflow: "hidden" }}>
                        <div style={{ width: `${pct}%`, background: "var(--accent-color)", height: "100%" }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>

          <section className="panel" style={{ marginTop: "24px" }}>
            <div className="section-heading" style={{ marginBottom: "16px" }}>
              <h3>Базы опросов по курсам</h3>
              <div className="control-search" style={{ margin: 0, width: "300px" }}>
                <Search size={16} strokeWidth={2.2} />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Поиск по курсу или теме"
                />
              </div>
            </div>

            <div className="table-responsive" style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.9rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-color)", paddingBottom: "10px" }}>
                    <th style={{ padding: "12px 8px" }}>Название курса</th>
                    <th style={{ padding: "12px 8px" }}>Период</th>
                    <th style={{ padding: "12px 8px" }}>Анкет</th>
                    <th style={{ padding: "12px 8px" }}>Ср. Оценка</th>
                    <th style={{ padding: "12px 8px" }}>Отстраненные</th>
                    <th style={{ padding: "12px 8px" }}>Ключевая тема</th>
                    <th style={{ padding: "12px 8px" }}>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCourses.map((c, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid var(--border-color)", verticalAlign: "middle" }}>
                      <td style={{ padding: "12px 8px" }}><b>{c.name}</b></td>
                      <td style={{ padding: "12px 8px" }}>{c.period}</td>
                      <td style={{ padding: "12px 8px" }}>{c.students}</td>
                      <td style={{ padding: "12px 8px" }}>
                        <span style={{ 
                          background: Number(c.avgScore) >= 8.0 ? "#e6f4ea" : "#fef7e0", 
                          color: Number(c.avgScore) >= 8.0 ? "#137333" : "#b06000",
                          padding: "3px 8px", borderRadius: "4px", fontWeight: "bold" 
                        }}>
                          {c.avgScore}
                        </span>
                      </td>
                      <td style={{ padding: "12px 8px" }}>{c.detached}%</td>
                      <td style={{ padding: "12px 8px" }} className="muted">{c.topTopic}</td>
                      <td style={{ padding: "12px 8px" }}>
                        <a href={`#report-detail-${c.id}`} style={{ display: "inline-flex", alignItems: "center", gap: "2px", textDecoration: "none", color: "var(--accent-color)", fontWeight: "600" }}>
                          Открыть <ChevronRight size={14} />
                        </a>
                      </td>
                    </tr>
                  ))}
                  {filteredCourses.length === 0 && (
                    <tr>
                      <td colSpan="7" style={{ textAlign: "center", padding: "20px", color: "var(--text-muted)" }}>Ничего не найдено.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </section>
  );
}

// ========================= Course Report Details Component =========================
export function CourseReportDetailPage({
  report,
  isEditingTitle,
  editTitleValue,
  setEditTitleValue,
  setIsEditingTitle,
  handleInlineRenameSubmit,
  handleArchiveReport,
  isSaveMenuOpen,
  setIsSaveMenuOpen,
  isProfileMenuOpen,
  setIsProfileMenuOpen,
  handleExportReport,
  saveActionsRef,
}) {
  const [activeTab, setActiveTab] = useState("dashboard"); // dashboard, qualitative, report
  const [qualActiveTab, setQualActiveTab] = useState("topics"); // topics, sentiment, problems, quotes, recommendations

  const reportViewModel = buildCourseReportViewModel(report);
  const {
    reportData,
    textAnalysis,
    courseName,
    period,
    studentsCount,
  } = reportViewModel;

  const getPriorityClass = (priority) => {
    const p = String(priority).toLowerCase();
    if (p === "high" || p === "высокий") return "risk";
    if (p === "medium" || p === "средний") return "watch";
    return "normal";
  };

  return (
    <section className="page active" id="report-detail" data-title="Детали отчёта">
      <div className="report-header">
        <div>
          {isEditingTitle ? (
            <form onSubmit={handleInlineRenameSubmit} className="inline-rename-form">
              <input
                type="text"
                value={editTitleValue}
                onChange={(e) => setEditTitleValue(e.target.value)}
                className="inline-rename-input"
                required
                autoFocus
              />
              <button type="submit" className="primary-button inline-rename-button">
                Сохранить
              </button>
              <button
                type="button"
                className="ghost-button inline-rename-button"
                onClick={() => setIsEditingTitle(false)}
              >
                Отмена
              </button>
            </form>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
              <p className="eyebrow" id="report-course-eyebrow" style={{ margin: 0 }}>{courseName}</p>
              <button
                type="button"
                className="inline-icon-button"
                onClick={() => {
                  setEditTitleValue(courseName);
                  setIsEditingTitle(true);
                }}
                aria-label="Переименовать отчет"
                title="Переименовать отчет"
              >
                <Pencil size={14} strokeWidth={2.2} />
              </button>
            </div>
          )}
          <h2 id="report-title-heading" style={{ margin: 0 }}>{report.title}</h2>
          <p className="muted" style={{ fontSize: "0.85rem", marginTop: "3px" }}>
            Период: <b>{period}</b> · Анкетировано слушателей: <b>{studentsCount} чел.</b>
          </p>
        </div>

        <div className="export-actions">
          <button
            type="button"
            className="icon-action-button archive-action"
            onClick={() => handleArchiveReport(report.id)}
            aria-label="Архивировать"
            title="Архивировать"
          >
            <Archive size={18} strokeWidth={2.2} />
          </button>
          <div className="save-actions" ref={saveActionsRef}>
            <button
              type="button"
              className="icon-action-button save-action"
              onClick={() => {
                setIsProfileMenuOpen(false);
                setIsSaveMenuOpen((isOpen) => !isOpen);
              }}
              aria-expanded={isSaveMenuOpen}
              aria-haspopup="menu"
              aria-label="Сохранить"
              title="Сохранить"
            >
              <Save size={18} strokeWidth={2.2} />
            </button>
            {isSaveMenuOpen && (
              <div className="save-menu" role="menu">
                {["pdf", "excel", "csv", "json"].map((format) => (
                  <button
                    key={format}
                    type="button"
                    role="menuitem"
                    onClick={() => handleExportReport(report, format)}
                    style={{ textTransform: "uppercase" }}
                  >
                    {format}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Tabs Navigation */}
      <nav className="nav tabs" style={{ display: "flex", gap: "16px", borderBottom: "1px solid var(--border-color)", paddingBottom: "8px", marginBottom: "20px" }}>
        {[
          { key: "dashboard", label: "Панель показателей", icon: BarChart3 },
          { key: "qualitative", label: "Качественный анализ отзывов", icon: MessageSquare },
          { key: "report", label: "Аналитическая справка", icon: BookOpen }
        ].map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              type="button"
              className={`tab-btn ${activeTab === t.key ? "active" : ""}`}
              onClick={() => setActiveTab(t.key)}
              style={{
                display: "inline-flex", alignItems: "center", gap: "6px", background: "none", border: "none", 
                padding: "8px 12px", fontSize: "0.95rem", fontWeight: activeTab === t.key ? "bold" : "normal",
                color: activeTab === t.key ? "var(--accent-color)" : "var(--text-muted)", cursor: "pointer",
                borderBottom: activeTab === t.key ? "2.5px solid var(--accent-color)" : "none"
              }}
            >
              <Icon size={16} />
              {t.label}
            </button>
          );
        })}
      </nav>

      {/* Tab 1: Dashboard Panel */}
      {activeTab === "dashboard" && <DashboardTab viewModel={reportViewModel} />}

      {/* Tab 2: Qualitative Insights */}
      {activeTab === "qualitative" && textAnalysis && (
        <div style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: "24px" }}>
          {/* Left Sub-nav */}
          <aside style={{ display: "flex", flexDirection: "column", gap: "4px", borderRight: "1px solid var(--border-color)", paddingRight: "16px" }}>
            {[
              { key: "topics", label: "Темы отзывов" },
              { key: "sentiment", label: "Тональность" },
              { key: "problems", label: "Критичные проблемы" },
              { key: "quotes", label: "Цитаты слушателей" },
              { key: "recommendations", label: "Рекомендации" }
            ].map((subTab) => (
              <button
                key={subTab.key}
                type="button"
                className={`subtab-btn ${qualActiveTab === subTab.key ? "active" : ""}`}
                onClick={() => setQualActiveTab(subTab.key)}
                style={{
                  textAlign: "left", background: "none", border: "none", padding: "8px 10px", fontSize: "0.85rem",
                  color: qualActiveTab === subTab.key ? "var(--accent-color)" : "var(--text-muted)", cursor: "pointer",
                  fontWeight: qualActiveTab === subTab.key ? "bold" : "normal", borderRadius: "4px",
                  background: qualActiveTab === subTab.key ? "var(--hover-color)" : "none"
                }}
              >
                {subTab.label}
              </button>
            ))}
          </aside>

          {/* Right Content Area */}
          <div style={{ minHeight: "300px" }}>
            {/* Sub-tab: Topics */}
            {qualActiveTab === "topics" && textAnalysis.top_topics && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {textAnalysis.top_topics.map((t, idx) => (
                  <article key={idx} className="panel" style={{ padding: "16px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <h4 style={{ fontSize: "1rem", margin: "0 0 6px 0", color: "var(--text-color)" }}>{t.topic}</h4>
                      <p className="muted" style={{ fontSize: "0.85rem", margin: 0 }}>{t.description}</p>
                    </div>
                    <span className="badge" style={{ background: "var(--soft-green)", color: "var(--accent-color)", padding: "4px 10px", borderRadius: "10px", fontWeight: "bold" }}>
                      Упоминаний: {t.frequency}
                    </span>
                  </article>
                ))}
              </div>
            )}

            {/* Sub-tab: Sentiment */}
            {qualActiveTab === "sentiment" && textAnalysis.sentiment && (
              <section className="panel" style={{ padding: "20px" }}>
                <h3>Эмоциональная тональность отзывов</h3>
                <p className="muted" style={{ fontSize: "0.85rem" }}>
                  Распределение комментариев по тональности, определенное с помощью семантического ИИ-анализа.
                </p>
                <div style={{ display: "flex", gap: "16px", marginTop: "20px" }}>
                  {[
                    { label: "Позитивные отзывы", value: textAnalysis.sentiment.positive, color: "var(--accent-color)" },
                    { label: "Нейтральные отзывы", value: textAnalysis.sentiment.neutral, color: "#f4a261" },
                    { label: "Негативные отзывы", value: textAnalysis.sentiment.negative, color: "#e07a5f" }
                  ].map((s, idx) => (
                    <div key={idx} style={{ flex: 1, textAlign: "center", padding: "16px", background: "var(--hover-color)", borderRadius: "6px" }}>
                      <strong style={{ fontSize: "1.8rem", color: s.color }}>{s.value.toFixed(0)}%</strong>
                      <p className="muted" style={{ fontSize: "0.8rem", marginTop: "6px", marginBottom: 0 }}>{s.label}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Sub-tab: Problems */}
            {qualActiveTab === "problems" && textAnalysis.key_problems && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {textAnalysis.key_problems.map((p, idx) => (
                  <article key={idx} className="panel" style={{ display: "flex", alignItems: "center", gap: "16px", padding: "16px" }}>
                    <span className={`risk-pill ${getPriorityClass(p.severity)}`} style={{ minWidth: "70px", textAlign: "center", padding: "4px 8px", fontSize: "0.75rem", borderRadius: "4px", fontWeight: "bold" }}>
                      {p.severity}
                    </span>
                    <div style={{ flex: 1 }}>
                      <strong style={{ fontSize: "0.95rem" }}>{p.problem}</strong>
                    </div>
                    <span className="muted" style={{ fontSize: "0.85rem" }}>
                      Встречается в <b>{p.frequency_percent.toFixed(0)}%</b> отзывов
                    </span>
                  </article>
                ))}
              </div>
            )}

            {/* Sub-tab: Quotes */}
            {qualActiveTab === "quotes" && textAnalysis.quotes && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {textAnalysis.quotes.map((q, idx) => (
                  <article key={idx} className="panel quote-card" style={{ padding: "16px", borderLeft: "4px solid var(--accent-color)" }}>
                    <Quote size={20} className="muted" style={{ opacity: 0.3, marginBottom: "8px" }} />
                    <p style={{ fontStyle: "italic", fontSize: "0.95rem", margin: "0 0 8px 0" }}>«{q.quote}»</p>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      <span>Слушатель курса</span>
                      <span>Частота схожих отзывов: <b>{q.frequency}</b></span>
                    </div>
                  </article>
                ))}
              </div>
            )}

            {/* Sub-tab: Recommendations */}
            {qualActiveTab === "recommendations" && textAnalysis.recommendations && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {textAnalysis.recommendations.map((r, idx) => (
                  <article key={idx} className="panel" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px" }}>
                    <div>
                      <span className="badge" style={{ fontSize: "0.75rem", background: "var(--border-color)", color: "var(--text-color)", padding: "2px 6px", borderRadius: "3px", marginRight: "8px" }}>
                        Объект: {r.target}
                      </span>
                      <strong style={{ fontSize: "0.95rem" }}>{r.action_item}</strong>
                    </div>
                    <span className={`risk-pill ${getPriorityClass(r.priority)}`} style={{ padding: "4px 10px", fontSize: "0.75rem", borderRadius: "4px", fontWeight: "bold" }}>
                      Приоритет: {r.priority}
                    </span>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Analytical Document View */}
      {activeTab === "report" && reportData && (
        <section className="panel" style={{ padding: "30px", background: "#fbfcfb", border: "1px solid var(--border-color)", boxShadow: "0 4px 12px rgba(0,0,0,0.02)", maxWidth: "800px", margin: "0 auto" }}>
          <div className="document-sheet" style={{ fontFamily: "Georgia, serif", color: "#222", lineHeight: "1.6" }}>
            <h3 style={{ borderBottom: "2px solid var(--accent-color)", paddingBottom: "10px", fontFamily: "var(--font-sans)", color: "var(--accent-color)", fontSize: "1.2rem", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Аналитическая записка по итогам анкетирования
            </h3>
            
            {/* Section 1 */}
            <div style={{ marginTop: "24px" }}>
              <h4 style={{ fontFamily: "var(--font-sans)", color: "#111", fontSize: "1rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "4px" }}>
                Раздел 1. Общая информация
              </h4>
              <p style={{ whiteSpace: "pre-line", fontSize: "0.9rem", marginTop: "8px" }}>
                {reportData.section1_general_info}
              </p>
            </div>

            {/* Section 2 */}
            <div style={{ marginTop: "24px" }}>
              <h4 style={{ fontFamily: "var(--font-sans)", color: "#111", fontSize: "1rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "4px" }}>
                Раздел 2. Анализ ключевых критериев программы
              </h4>
              <ul style={{ paddingLeft: "20px", fontSize: "0.9rem", marginTop: "8px", display: "flex", flexDirection: "column", gap: "8px" }}>
                <li><b>Полезность курса:</b> {reportData.section2_key_criteria?.usefulness_summary}</li>
                <li><b>Практическая применимость:</b> {reportData.section2_key_criteria?.practicality_summary}</li>
                <li><b>Доступность материала:</b> {reportData.section2_key_criteria?.accessibility_summary}</li>
                <li><b>Взаимодействие с организаторами КУ:</b> {reportData.section2_key_criteria?.interaction_summary}</li>
                <li><b>Психологическая вовлеченность:</b> {reportData.section2_key_criteria?.involvement_summary}</li>
              </ul>
            </div>

            {/* Section 3 */}
            <div style={{ marginTop: "24px" }}>
              <h4 style={{ fontFamily: "var(--font-sans)", color: "#111", fontSize: "1rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "4px" }}>
                Раздел 3. Предложения слушателей по изменению программы
              </h4>
              <div style={{ fontSize: "0.9rem", marginTop: "8px", display: "flex", flexDirection: "column", gap: "8px" }}>
                {reportData.section3_suggestions?.unwanted_topics?.length > 0 && (
                  <p><b>Темы к исключению:</b> {reportData.section3_suggestions.unwanted_topics.join(", ")}</p>
                )}
                {reportData.section3_suggestions?.added_topics?.length > 0 && (
                  <p>
                    <b>Темы к добавлению:</b>{" "}
                    {reportData.section3_suggestions.added_topics.map(t => `${t.topic} (${t.count} запросов)`).join("; ")}
                  </p>
                )}
                <p><b>Сводка по формату обучения:</b> {reportData.section3_suggestions?.preferred_format_summary}</p>
              </div>
            </div>

            {/* Section 4 */}
            <div style={{ marginTop: "24px" }}>
              <h4 style={{ fontFamily: "var(--font-sans)", color: "#111", fontSize: "1rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "4px" }}>
                Раздел 4. Рекомендации по корректировке траектории программы
              </h4>
              <div style={{ fontSize: "0.9rem", marginTop: "8px", display: "flex", flexDirection: "column", gap: "8px" }}>
                <p><b>Востребованность курса:</b> {reportData.section4_trajectory?.further_implementation_needed}</p>
                <p><b>Рекомендации по отбору:</b> {reportData.section4_trajectory?.student_selection_correction}</p>
                <p><b>Изменения по темам:</b> {reportData.section4_trajectory?.added_topics_recommendation}</p>
                <p><b>Распределение часов:</b> {reportData.section4_trajectory?.hours_correction_needed}</p>
                <p><b>Рекомендованный формат занятий:</b> {reportData.section4_trajectory?.format_correction_needed}</p>
                
                {reportData.section4_trajectory?.conclusions?.length > 0 && (
                  <div style={{ marginTop: "10px" }}>
                    <b>Выводы и заключения:</b>
                    <ul style={{ paddingLeft: "20px", marginTop: "4px", display: "flex", flexDirection: "column", gap: "4px" }}>
                      {reportData.section4_trajectory.conclusions.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>
      )}
    </section>
  );
}
