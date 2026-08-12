import { AlertTriangle, CheckCircle, ClipboardCheck, Lightbulb, ShieldCheck } from "lucide-react";

const statusIcons = {
  done: CheckCircle,
  warning: AlertTriangle,
  info: ShieldCheck,
};

const getPriorityClass = (priority) => {
  if (priority === "high") return "risk";
  if (priority === "medium") return "watch";
  return "normal";
};

export function DecisionSupportTab({ decisionSupport }) {
  if (!decisionSupport) {
    return (
      <section className="panel analysis-empty-state">
        <h3>Решение и план действий</h3>
        <p className="muted">Для этого отчета пока не хватает данных, чтобы собрать управленческое резюме.</p>
      </section>
    );
  }

  const {
    decision,
    decisionReasons,
    confidenceScore,
    confidenceLabel,
    confidenceNotes,
    evidenceHighlights,
    actionPlan,
    qualityChecklist,
  } = decisionSupport;

  return (
    <div className="decision-support-tab">
      <section className={`panel decision-hero decision-hero-${decision.tone}`}>
        <div className="decision-hero-copy">
          <p className="eyebrow">Решение по курсу</p>
          <h3>{decision.title}</h3>
          <p>{decision.summary}</p>
          {decisionReasons.length > 0 && (
            <ul className="decision-reasons" aria-label="Причины решения">
              {decisionReasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
        </div>

        <aside className="confidence-card" aria-label="Надежность анализа">
          <span>Надежность анализа</span>
          <strong>{confidenceScore}%</strong>
          <small>{confidenceLabel}</small>
        </aside>
      </section>

      <div className="decision-grid">
        <section className="panel decision-card decision-actions-panel">
          <div className="decision-card-heading">
            <ClipboardCheck size={20} strokeWidth={2.2} aria-hidden="true" />
            <h3>Что сделать дальше</h3>
          </div>
          {actionPlan.length > 0 ? (
            <ol className="action-plan-list">
              {actionPlan.map((action) => (
                <li key={action.title} className="action-plan-item">
                  <span className={`risk-pill ${getPriorityClass(action.priority)}`}>
                    {action.priorityLabel}
                  </span>
                  <div>
                    <h4>{action.title}</h4>
                    <p>{action.detail}</p>
                    <small>{action.owner} · {action.timing}</small>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="muted">Явных действий не найдено. Проверьте аналитическую справку и добавьте ручные корректировки.</p>
          )}
        </section>

        <section className="panel decision-card decision-checklist-panel">
          <div className="decision-card-heading">
            <ShieldCheck size={20} strokeWidth={2.2} aria-hidden="true" />
            <h3>Контроль качества</h3>
          </div>
          <ul className="quality-checklist">
            {qualityChecklist.map((item) => {
              const Icon = statusIcons[item.status] || ShieldCheck;
              return (
                <li key={item.label} className={`quality-check quality-check-${item.status}`}>
                  <Icon size={18} strokeWidth={2.2} aria-hidden="true" />
                  <div>
                    <strong>{item.label}</strong>
                    <p>{item.detail}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      </div>

      <section className="decision-evidence-section" aria-labelledby="decision-evidence-title">
        <div className="section-heading decision-section-heading">
          <div>
            <p className="eyebrow">Проверяемость</p>
            <h3 id="decision-evidence-title">Чем подтвержден вывод</h3>
          </div>
          <span className="badge evidence-badge">{evidenceHighlights.length} сигналов</span>
        </div>

        {evidenceHighlights.length > 0 ? (
          <div className="evidence-grid">
            {evidenceHighlights.map((item) => (
              <article key={`${item.type}-${item.title}`} className={`evidence-item evidence-item-${item.tone}`}>
                <span>{item.type}</span>
                <h4>{item.title}</h4>
                <p>{item.detail}</p>
                <small>{item.support}</small>
              </article>
            ))}
          </div>
        ) : (
          <section className="panel analysis-empty-state">
            <h3>Подтверждения не найдены</h3>
            <p className="muted">В отчете пока нет тем, цитат или проблем, которые можно показать как основание вывода.</p>
          </section>
        )}
      </section>

      <section className="panel confidence-notes-panel">
        <div className="decision-card-heading">
          <Lightbulb size={20} strokeWidth={2.2} aria-hidden="true" />
          <h3>Как читать надежность</h3>
        </div>
        <ul className="confidence-notes">
          {confidenceNotes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
