import { Archive, FileText, LogOutIcon, Menu, PanelLeftClose, PanelLeftOpen, Plus, Search, Settings, User, Users } from "lucide-react";
import logo from "../assets/logo.png";

const formatHistoryMeta = (report) => {
  const createdAt = report.createdAt
    ? new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(report.createdAt))
    : "";
  const title = report.title || "Без названия";
  return createdAt ? `${title} · ${createdAt}` : title;
};

const getReportSourceLabel = (source) => (source === "demo" ? "Демо" : "Создано мной");

export function AppLayout({
  route,
  pageTitle,
  children,
  reports,
  historyQuery,
  onHistoryQueryChange,
  onArchiveReport,
  onNewAnalysis,
  token,
  user,
  userEmail,
  isMenuOpen,
  setIsMenuOpen,
  isProfileMenuOpen,
  setIsProfileMenuOpen,
  setIsSaveMenuOpen,
  profileActionsRef,
  onLogout,
  settings,
  sidebarWidth,
  isSidebarCollapsed,
  onSidebarToggle,
  onSidebarResizeStart,
}) {
  return (
    <div
      className={`app-shell ${isSidebarCollapsed ? "sidebar-collapsed" : ""}`}
      style={{ "--sidebar-width": `${sidebarWidth}px` }}
      data-accessibility={settings?.accessibility?.enabled ? "enabled" : "default"}
      data-density={settings?.minimalUi ? "minimal" : "comfortable"}
    >
      <aside className="sidebar" aria-label="Основная навигация">
        <a className="brand" href="#upload" aria-label="Анализ отзывов студентов">
          <img className="brand-logo" src={logo} alt="Анализ отзывов студентов" />
          <span>
            <strong>
              <span className="brand-full">Анализ отзывов студентов</span>
              <span className="brand-short">Анализ отзывов</span>
            </strong>
            <small>анализ ответов</small>
          </span>
        </a>

        <a href="#upload" className={`new-chat-btn ${route === "upload" ? "active" : ""}`} onClick={onNewAnalysis}>
          <Plus size={18} strokeWidth={2.2} /> Новый анализ
        </a>

        <div className="sidebar-divider"></div>

        <div className="sidebar-history-section">
          <div className="sidebar-section-title">История анализов</div>
          <label className="sidebar-search">
            <Search size={16} strokeWidth={2.2} />
            <input
              type="search"
              value={historyQuery}
              onChange={(e) => onHistoryQueryChange(e.target.value)}
              placeholder="Найти отчет"
              aria-label="Найти отчет в истории"
            />
          </label>

          <div className="sidebar-history" id="reports-sidebar-list">
            {reports.length ? (
              reports.map((report) => (
                <div
                  key={report.id}
                  className={`history-row ${route === `report-detail-${report.id}` ? "active" : ""}`}
                >
                  <a
                    href={`#report-detail-${report.id}`}
                    className="history-item"
                    title={report.title ? `${report.course}: ${report.title}` : report.course}
                    onClick={(e) => {
                      e.preventDefault();
                      window.location.hash = `report-detail-${report.id}`;
                    }}
                  >
                    <FileText size={16} strokeWidth={2.2} />
                    <span className="history-item-copy">
                      <span className="history-item-title">{report.course}</span>
                      <span className="history-item-meta-row">
                        <small className="history-item-meta">{formatHistoryMeta(report)}</small>
                        <small className={`source-badge source-badge-${report.source || "user"}`}>
                          {getReportSourceLabel(report.source)}
                        </small>
                      </span>
                    </span>
                  </a>
                  <button
                    type="button"
                    className="history-archive-button"
                    aria-label={`Архивировать отчет ${report.course}`}
                    title="Архивировать"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      onArchiveReport?.(report.id);
                    }}
                  >
                    <Archive size={15} strokeWidth={2.2} />
                  </button>
                </div>
              ))
            ) : (
              <div className="sidebar-empty">
                {historyQuery ? "Ничего не найдено" : "История пока пуста"}
              </div>
            )}
          </div>
        </div>

        <div className="sidebar-divider"></div>

        <nav className="nav sidebar-nav">
          <a href="#students" className={`secondary-nav-link ${route === "students" ? "active" : ""}`}>
            <Users size={17} strokeWidth={2.2} /> Студенты
          </a>
          <a href="#settings-archive" className={`secondary-nav-link ${route === "settings-archive" ? "active" : ""}`}>
            <Archive size={17} strokeWidth={2.2} /> Архив
          </a>
          <a href="#settings" className={`secondary-nav-link ${route === "settings" ? "active" : ""}`}>
            <Settings size={17} strokeWidth={2.2} /> Настройки
          </a>
        </nav>
        <button
          type="button"
          className="sidebar-resize-handle"
          aria-label="Изменить ширину панели"
          onPointerDown={onSidebarResizeStart}
        ></button>
      </aside>

      <main className="workspace" aria-labelledby="page-title">
        <h1 id="page-title" className="sr-only">{pageTitle}</h1>
        <header className="topbar">
          <button
            className="menu-button"
            type="button"
            aria-label="Открыть меню"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <Menu size={20} strokeWidth={2.2} />
          </button>
          <button
            className="icon-action-button sidebar-toggle-button"
            type="button"
            aria-label={isSidebarCollapsed ? "Показать левую панель" : "Скрыть левую панель"}
            title={isSidebarCollapsed ? "Показать левую панель" : "Скрыть левую панель"}
            onClick={onSidebarToggle}
          >
            {isSidebarCollapsed ? (
              <PanelLeftOpen size={18} strokeWidth={2.2} />
            ) : (
              <PanelLeftClose size={18} strokeWidth={2.2} />
            )}
          </button>
          <div className="top-actions">
            {token ? (
              <div className="profile-actions" ref={profileActionsRef}>
                <button
                  type="button"
                  className="icon-action-button profile-trigger"
                  onClick={() => {
                    setIsSaveMenuOpen(false);
                    setIsProfileMenuOpen((isOpen) => !isOpen);
                  }}
                  aria-expanded={isProfileMenuOpen}
                  aria-haspopup="menu"
                  aria-label={user ? `Профиль: ${user}` : "Профиль"}
                  title={user ? `Профиль: ${user}` : "Профиль"}
                >
                  <User size={18} strokeWidth={2.2} />
                </button>
                {isProfileMenuOpen && (
                  <div className="profile-menu" role="menu">
                    <div className="profile-summary">
                      <span className="profile-summary-icon">
                        <User size={18} strokeWidth={2.2} />
                      </span>
                      <span className="profile-summary-text">
                        <strong>{user || "Пользователь"}</strong>
                        {userEmail && <small>{userEmail}</small>}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="profile-menu-link"
                      role="menuitem"
                      onClick={() => {
                        setIsProfileMenuOpen(false);
                        window.location.hash = "settings";
                      }}
                    >
                      <Settings size={16} strokeWidth={2.2} />
                      Настройки
                    </button>
                    <button
                      type="button"
                      className="profile-menu-danger"
                      role="menuitem"
                      onClick={() => {
                        setIsProfileMenuOpen(false);
                        onLogout();
                      }}
                    >
                      <LogOutIcon size={16} strokeWidth={2.2} />
                      Выйти
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <>
                <a className="ghost-button" href="#login">Войти</a>
                <a className="primary-button" href="#register">Регистрация</a>
              </>
            )}
          </div>
        </header>

        {children}
      </main>
    </div>
  );
}
