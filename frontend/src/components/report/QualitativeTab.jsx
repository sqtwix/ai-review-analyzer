import { Quote } from "lucide-react";

const formatPercent = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(0)}%` : "-";
};

const getPriorityClass = (priority) => {
  const normalizedPriority = String(priority).toLowerCase();
  if (normalizedPriority === "high" || normalizedPriority === "высокий") return "risk";
  if (normalizedPriority === "medium" || normalizedPriority === "средний") return "watch";
  return "normal";
};

function EvidenceLine({ children }) {
  return <p className="evidence-line">{children}</p>;
}

function EmptyQualitativeState({ title }) {
  return (
    <section className="panel analysis-empty-state">
      <h3>{title}</h3>
      <p className="muted">Backend не передал данные для этого блока качественного анализа.</p>
    </section>
  );
}

export function QualitativeTab({ textAnalysis, activeTab, onTabChange, sourceLimitation }) {
  const tabs = [
    { key: "topics", label: "Темы отзывов" },
    { key: "sentiment", label: "Тональность" },
    { key: "problems", label: "Критичные проблемы" },
    { key: "quotes", label: "Цитаты слушателей" },
    { key: "recommendations", label: "Рекомендации" },
  ];

  if (!textAnalysis) {
    return <EmptyQualitativeState title="Качественный анализ отзывов" />;
  }

  return (
    <div className="qualitative-layout">
      <aside className="qualitative-subnav" aria-label="Разделы качественного анализа">
        {tabs.map((subTab) => (
          <button
            key={subTab.key}
            type="button"
            className={`subtab-btn ${activeTab === subTab.key ? "active" : ""}`}
            onClick={() => onTabChange(subTab.key)}
          >
            {subTab.label}
          </button>
        ))}
      </aside>

      <div className="qualitative-content">
        {activeTab === "topics" && (
          textAnalysis.top_topics?.length ? (
            <div className="qualitative-list">
              {textAnalysis.top_topics.map((topic, index) => (
                <article key={`${topic.topic}-${index}`} className="panel qualitative-card">
                  <div>
                    <h4>{topic.topic}</h4>
                    <p className="muted">{topic.description}</p>
                    <EvidenceLine>Основание: агрегированная тема, частота упоминаний - {topic.frequency}.</EvidenceLine>
                  </div>
                  <span className="badge evidence-badge">Упоминаний: {topic.frequency}</span>
                </article>
              ))}
            </div>
          ) : (
            <EmptyQualitativeState title="Темы отзывов" />
          )
        )}

        {activeTab === "sentiment" && (
          textAnalysis.sentiment ? (
            <section className="panel sentiment-panel">
              <h3>Эмоциональная тональность отзывов</h3>
              <div className="sentiment-grid">
                {[
                  { label: "Позитивные", value: textAnalysis.sentiment.positive, tone: "positive" },
                  { label: "Нейтральные", value: textAnalysis.sentiment.neutral, tone: "neutral" },
                  { label: "Негативные", value: textAnalysis.sentiment.negative, tone: "negative" },
                ].map((sentiment) => (
                  <div key={sentiment.label} className={`sentiment-card ${sentiment.tone}`}>
                    <strong>{formatPercent(sentiment.value)}</strong>
                    <span>{sentiment.label}</span>
                  </div>
                ))}
              </div>
              <EvidenceLine>Основание: агрегированная классификация всех комментариев, переданная backend.</EvidenceLine>
            </section>
          ) : (
            <EmptyQualitativeState title="Тональность" />
          )
        )}

        {activeTab === "problems" && (
          textAnalysis.key_problems?.length ? (
            <div className="qualitative-list">
              {textAnalysis.key_problems.map((problem, index) => (
                <article key={`${problem.problem}-${index}`} className="panel qualitative-card problem-card">
                  <span className={`risk-pill ${getPriorityClass(problem.severity)}`}>{problem.severity}</span>
                  <div>
                    <h4>{problem.problem}</h4>
                    <EvidenceLine>
                      Основание: встречается в {formatPercent(problem.frequency_percent)} отзывов; уровень риска - {problem.severity}.
                    </EvidenceLine>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyQualitativeState title="Критичные проблемы" />
          )
        )}

        {activeTab === "quotes" && (
          textAnalysis.quotes?.length ? (
            <div className="qualitative-list">
              {textAnalysis.quotes.map((quote, index) => (
                <article key={`${quote.quote}-${index}`} className="panel quote-card qualitative-quote-card">
                  <Quote size={20} className="muted" />
                  <p>«{quote.quote}»</p>
                  <EvidenceLine>Основание: частота схожих формулировок - {quote.frequency}; {sourceLimitation}</EvidenceLine>
                </article>
              ))}
            </div>
          ) : (
            <EmptyQualitativeState title="Цитаты слушателей" />
          )
        )}

        {activeTab === "recommendations" && (
          textAnalysis.recommendations?.length ? (
            <div className="qualitative-list">
              {textAnalysis.recommendations.map((recommendation, index) => (
                <article key={`${recommendation.target}-${index}`} className="panel qualitative-card recommendation-card">
                  <div>
                    <span className="badge recommendation-target">Объект: {recommendation.target}</span>
                    <h4>{recommendation.action_item}</h4>
                    <EvidenceLine>
                      Основание: рекомендация сформирована из агрегированных проблем и тем; точные ссылки на строки недоступны до расширения backend-контракта.
                    </EvidenceLine>
                  </div>
                  <span className={`risk-pill ${getPriorityClass(recommendation.priority)}`}>
                    Приоритет: {recommendation.priority}
                  </span>
                </article>
              ))}
            </div>
          ) : (
            <EmptyQualitativeState title="Рекомендации" />
          )
        )}
      </div>
    </div>
  );
}
