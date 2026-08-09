import React from "react";
import { TrendingUp, BarChart3, PieChart, Activity, Layers } from "lucide-react";

const formatNumber = (value, digits = 1) => {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "-";
};

const formatPercent = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(0)}%` : "-";
};

function EmptyChartState({ title, message }) {
  return (
    <section className="panel analysis-empty-state">
      <h3>{title}</h3>
      <p className="muted">{message}</p>
    </section>
  );
}

function DashboardSection({ title, children }) {
  return (
    <div className="dashboard-section" style={{ marginBottom: "28px" }}>
      <h3 className="dashboard-section-title" style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "16px", color: "var(--text)" }}>
        {title}
      </h3>
      <div className="dashboard-section-body">{children}</div>
    </div>
  );
}

function MetricCards({ metricCards, involvement }) {
  return (
    <div className="dashboard-metrics-grid">
      {metricCards.map((card) => (
        <article key={card.key} className="panel dashboard-metric-card">
          <span className="muted">{card.label}</span>
          <strong>
            {formatNumber(card.average)} <span>/ 10</span>
          </strong>
          <small className="muted">
            Медиана: {formatNumber(card.median)} · Отклонение: {formatNumber(card.stdDev)}
          </small>
          <div className="stacked-distribution" aria-label={`Распределение оценок: ${card.label}`}>
            <span className="low" style={{ width: `${card.distribution.low}%` }} title={`1-3: ${formatNumber(card.distribution.low, 0)}%`}></span>
            <span className="mid" style={{ width: `${card.distribution.mid}%` }} title={`4-7: ${formatNumber(card.distribution.mid, 0)}%`}></span>
            <span className="high" style={{ width: `${card.distribution.high}%` }} title={`8-10: ${formatNumber(card.distribution.high, 0)}%`}></span>
          </div>
          <div className="distribution-labels">
            <span>1-3: {formatNumber(card.distribution.low, 0)}%</span>
            <span>4-7: {formatNumber(card.distribution.mid, 0)}%</span>
            <span>8-10: {formatNumber(card.distribution.high, 0)}%</span>
          </div>
        </article>
      ))}

      {involvement && (
        <article className="panel dashboard-metric-card">
          <span className="muted">Вовлеченность слушателей</span>
          <strong>{formatNumber(involvement.involved_percent, 0)}%</strong>
          <small className="muted">
            Вовлечены: {involvement.no_count} чел. · Отстранены: {involvement.yes_count} чел.
          </small>
          <div className="stacked-distribution" aria-label="Распределение вовлеченности">
            <span className="low" style={{ width: `${involvement.detached_percent}%` }} title={`Отстранены: ${formatNumber(involvement.detached_percent, 0)}%`}></span>
            <span className="high" style={{ width: `${involvement.involved_percent}%` }} title={`Вовлечены: ${formatNumber(involvement.involved_percent, 0)}%`}></span>
          </div>
          <div className="distribution-labels">
            <span>Отстранены: {formatNumber(involvement.detached_percent, 0)}%</span>
            <span>Вовлечены: {formatNumber(involvement.involved_percent, 0)}%</span>
          </div>
        </article>
      )}
    </div>
  );
}

/* =========================================================================
   1. SVG Horizontal Bar Chart — Средние баллы по 5 критериям
   ========================================================================= */
function SvgAverageBarChart({ criteria }) {
  const data = criteria.filter((item) => Number.isFinite(item.value));
  if (!data.length) {
    return <EmptyChartState title="Средние баллы по 5 критериям" message="Данные отсутствуют." />;
  }

  const svgWidth = 480;
  const rowHeight = 44;
  const svgHeight = data.length * rowHeight + 36;
  const labelWidth = 140;
  const chartWidth = 260;

  return (
    <section className="panel chart-panel">
      <h3>Средние баллы по 5 критериям</h3>
      <div className="chart-frame" style={{ minHeight: `${svgHeight}px`, height: "auto", display: "flex", justifyContent: "center" }}>
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ width: "100%", maxHeight: "320px" }}>
          {/* Background grid lines for 0, 2.5, 5.0, 7.5, 10 */}
          {[0, 2.5, 5, 7.5, 10].map((val) => {
            const x = labelWidth + (val / 10) * chartWidth;
            return (
              <g key={val}>
                <line x1={x} y1={10} x2={x} y2={svgHeight - 24} stroke="var(--line, #e2e8f0)" strokeDasharray="3 3" strokeWidth="1" />
                <text x={x} y={svgHeight - 8} fill="var(--muted, #64748b)" fontSize="11" textAnchor="middle">
                  {val}
                </text>
              </g>
            );
          })}

          {/* Criteria Horizontal Bars */}
          {data.map((item, idx) => {
            const y = 20 + idx * rowHeight;
            const barWidth = Math.max(4, (Math.min(10, item.value) / 10) * chartWidth);
            return (
              <g key={item.key || idx}>
                {/* Y-Axis Label */}
                <text x={labelWidth - 10} y={y + 20} fill="var(--text, #1e293b)" fontSize="12" fontWeight="600" textAnchor="end">
                  {item.label}
                </text>

                {/* Background Track */}
                <rect x={labelWidth} y={y + 6} width={chartWidth} height={20} rx={4} fill="var(--panel-border, #f1f5f9)" />

                {/* Filled Bar */}
                <rect x={labelWidth} y={y + 6} width={barWidth} height={20} rx={4} fill="url(#barGradient)" />

                {/* Score Text Badge */}
                <text x={labelWidth + barWidth + 8} y={y + 20} fill="var(--accent, #2f6f65)" fontSize="12" fontWeight="700">
                  {formatNumber(item.value, 1)} / 10
                </text>
              </g>
            );
          })}

          {/* Bar Gradient Definition */}
          <defs>
            <linearGradient id="barGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#2f6f65" />
              <stop offset="100%" stopColor="#425f86" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </section>
  );
}

/* =========================================================================
   2. SVG Spider / Radar Chart — Профиль удовлетворенности
   ========================================================================= */
function SvgSatisfactionRadarChart({ criteria }) {
  const data = criteria.filter((item) => Number.isFinite(item.value));
  if (!data.length) {
    return <EmptyChartState title="Профиль удовлетворенности" message="Данные отсутствуют." />;
  }

  const cx = 170;
  const cy = 150;
  const radius = 100;
  const total = data.length;

  // Compute vertex point for an angle index and scale (0 to 1)
  const getCoordinates = (index, scale) => {
    const angle = (Math.PI * 2 * index) / total - Math.PI / 2;
    return {
      x: cx + radius * scale * Math.cos(angle),
      y: cy + radius * scale * Math.sin(angle),
    };
  };

  // Web rings at 0.2, 0.4, 0.6, 0.8, 1.0 (scales corresponding to scores 2, 4, 6, 8, 10)
  const rings = [0.2, 0.4, 0.6, 0.8, 1.0];

  // Compute data polygon points
  const points = data
    .map((item, i) => {
      const scoreScale = Math.max(0, Math.min(10, item.value)) / 10;
      const pt = getCoordinates(i, scoreScale);
      return `${pt.x},${pt.y}`;
    })
    .join(" ");

  return (
    <section className="panel chart-panel">
      <h3>Профиль удовлетворенности</h3>
      <div className="chart-frame chart-frame-square" style={{ minHeight: "310px", height: "auto", display: "flex", justifyContent: "center" }}>
        <svg viewBox="0 0 340 310" style={{ width: "100%", maxHeight: "310px" }}>
          {/* Concentric Web Rings */}
          {rings.map((ringScale) => {
            const ringPoints = Array.from({ length: total })
              .map((_, i) => {
                const pt = getCoordinates(i, ringScale);
                return `${pt.x},${pt.y}`;
              })
              .join(" ");
            return (
              <polygon
                key={ringScale}
                points={ringPoints}
                fill="none"
                stroke="var(--line, #cbd5e1)"
                strokeDasharray={ringScale === 1.0 ? "none" : "3 3"}
                strokeWidth={ringScale === 1.0 ? 1.5 : 1}
              />
            );
          })}

          {/* Radial Axis Lines & Outer Labels */}
          {data.map((item, i) => {
            const outerPt = getCoordinates(i, 1.0);
            const labelPt = getCoordinates(i, 1.22);
            return (
              <g key={item.key || i}>
                <line x1={cx} y1={cy} x2={outerPt.x} y2={outerPt.y} stroke="var(--line, #cbd5e1)" strokeWidth="1" />
                <text
                  x={labelPt.x}
                  y={labelPt.y}
                  fill="var(--text, #1e293b)"
                  fontSize="11"
                  fontWeight="600"
                  textAnchor={labelPt.x > cx + 10 ? "start" : labelPt.x < cx - 10 ? "end" : "middle"}
                  dominantBaseline="middle"
                >
                  {item.label} ({formatNumber(item.value, 1)})
                </text>
              </g>
            );
          })}

          {/* Data Polygon Fill & Outline */}
          <polygon points={points} fill="rgba(47, 111, 101, 0.3)" stroke="#2f6f65" strokeWidth="2.5" />

          {/* Data Vertex Dots */}
          {data.map((item, i) => {
            const scoreScale = Math.max(0, Math.min(10, item.value)) / 10;
            const pt = getCoordinates(i, scoreScale);
            return <circle key={i} cx={pt.x} cy={pt.y} r="4" fill="#2f6f65" stroke="#ffffff" strokeWidth="1.5" />;
          })}
        </svg>
      </div>
      <p className="chart-note muted">Вовлеченность приведена к шкале 0–10 через процент вовлеченных слушателей.</p>
    </section>
  );
}

/* =========================================================================
   3. SVG Correlation Heatmap Grid — Тепловая карта корреляций
   ========================================================================= */
function SvgCorrelationHeatmap({ matrix }) {
  if (!matrix || Object.keys(matrix).length === 0) {
    return <EmptyChartState title="Тепловая карта корреляций" message="Матрица корреляций не передана." />;
  }

  const keys = Object.keys(matrix);
  const cellSize = 54;
  const paddingLeft = 110;
  const paddingTop = 34;
  const svgWidth = paddingLeft + keys.length * cellSize + 20;
  const svgHeight = paddingTop + keys.length * cellSize + 20;

  const getHeatFill = (val) => {
    const num = Number(val || 0);
    if (num >= 0.85) return "#2f6f65"; // Deep Teal
    if (num >= 0.65) return "#3b8276"; // Medium Teal
    if (num >= 0.45) return "#64748b"; // Blue Slate
    if (num >= 0.25) return "#d97706"; // Amber
    return "#e11d48"; // Crimson / Low correlation
  };

  return (
    <section className="panel chart-panel">
      <h3>Тепловая карта корреляций</h3>
      <div className="chart-frame chart-frame-square" style={{ minHeight: `${svgHeight}px`, height: "auto", display: "flex", justifyContent: "center" }}>
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ width: "100%", maxHeight: "310px" }}>
          {/* Top Column Headers */}
          {keys.map((colKey, colIdx) => (
            <text
              key={colKey}
              x={paddingLeft + colIdx * cellSize + cellSize / 2}
              y={paddingTop - 10}
              fill="var(--text, #1e293b)"
              fontSize="11"
              fontWeight="600"
              textAnchor="middle"
            >
              {colKey}
            </text>
          ))}

          {/* Matrix Rows */}
          {keys.map((rowKey, rowIdx) => (
            <g key={rowKey}>
              {/* Row Label */}
              <text
                x={paddingLeft - 10}
                y={paddingTop + rowIdx * cellSize + cellSize / 2 + 4}
                fill="var(--text, #1e293b)"
                fontSize="11"
                fontWeight="600"
                textAnchor="end"
              >
                {rowKey}
              </text>

              {/* Row Cell Quadrants */}
              {keys.map((colKey, colIdx) => {
                const val = Number(matrix[rowKey]?.[colKey] ?? 0);
                const x = paddingLeft + colIdx * cellSize;
                const y = paddingTop + rowIdx * cellSize;
                const fill = getHeatFill(val);
                return (
                  <g key={`${rowKey}-${colKey}`}>
                    <rect x={x + 2} y={y + 2} width={cellSize - 4} height={cellSize - 4} rx={6} fill={fill} opacity={0.9} />
                    <text x={x + cellSize / 2} y={y + cellSize / 2 + 4} fill="#ffffff" fontSize="12" fontWeight="700" textAnchor="middle">
                      {val.toFixed(2)}
                    </text>
                  </g>
                );
              })}
            </g>
          ))}
        </svg>
      </div>
    </section>
  );
}

/* =========================================================================
   4. SVG Overall Distribution Column Chart — Распределение общей оценки (1-3, 4-7, 8-10)
   ========================================================================= */
function SvgOverallDistributionChart({ distribution, limitation }) {
  const buckets = [
    { label: "1–3 (Низкая)", value: Number(distribution?.low || 0), color: "#e11d48" },
    { label: "4–7 (Средняя)", value: Number(distribution?.mid || 0), color: "#d97706" },
    { label: "8–10 (Высокая)", value: Number(distribution?.high || 0), color: "#2f6f65" },
  ];

  const svgWidth = 360;
  const svgHeight = 220;
  const chartHeight = 150;
  const startY = 170;
  const colWidth = 70;
  const gap = 35;

  return (
    <section className="panel chart-panel">
      <h3>Распределение общей оценки</h3>
      <div className="chart-frame" style={{ minHeight: `${svgHeight}px`, height: "auto", display: "flex", justifyContent: "center" }}>
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ width: "100%", maxHeight: "240px" }}>
          {/* Y Ticks (0%, 25%, 50%, 75%, 100%) */}
          {[0, 25, 50, 75, 100].map((pct) => {
            const y = startY - (pct / 100) * chartHeight;
            return (
              <g key={pct}>
                <line x1={45} y1={y} x2={svgWidth - 20} y2={y} stroke="var(--line, #e2e8f0)" strokeDasharray="3 3" strokeWidth="1" />
                <text x={38} y={y + 4} fill="var(--muted, #64748b)" fontSize="10" textAnchor="end">
                  {pct}%
                </text>
              </g>
            );
          })}

          {/* Vertical Columns */}
          {buckets.map((b, i) => {
            const x = 70 + i * (colWidth + gap);
            const height = Math.max(4, (Math.min(100, b.value) / 100) * chartHeight);
            const y = startY - height;

            return (
              <g key={b.label}>
                {/* Column Rect */}
                <rect x={x} y={y} width={colWidth} height={height} rx={6} fill={b.color} opacity={0.9} />

                {/* Top Percentage Label */}
                <text x={x + colWidth / 2} y={y - 6} fill="var(--text, #1e293b)" fontSize="12" fontWeight="700" textAnchor="middle">
                  {b.value.toFixed(0)}%
                </text>

                {/* X-Axis Label */}
                <text x={x + colWidth / 2} y={startY + 18} fill="var(--text, #1e293b)" fontSize="11" fontWeight="600" textAnchor="middle">
                  {b.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <p className="chart-note muted">{limitation}</p>
    </section>
  );
}

/* =========================================================================
   5. SVG Trend Line Chart — Динамика оценок по периодам
   ========================================================================= */
function SvgTrendChart({ trendData }) {
  if (!Array.isArray(trendData) || trendData.length === 0) {
    return (
      <EmptyChartState
        title="Динамика оценок по периодам"
        message="Для данного отчета не переданы временные данные по нескольким периодам."
      />
    );
  }

  const svgWidth = 560;
  const svgHeight = 250;
  const startX = 60;
  const endX = svgWidth - 30;
  const startY = 190;
  const chartHeight = 140;

  const series = [
    { key: "usefulness_avg", name: "Полезность", color: "#2f6f65" },
    { key: "practicality_avg", name: "Практика", color: "#425f86" },
    { key: "accessibility_avg", name: "Доступность", color: "#d97706" },
    { key: "interaction_avg", name: "Взаимодействие", color: "#64748b" },
  ];

  const periodStep = trendData.length > 1 ? (endX - startX) / (trendData.length - 1) : 0;

  return (
    <section className="panel chart-panel chart-panel-wide">
      <div className="section-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h3>Динамика оценок по периодам</h3>
        <span className="badge trend-badge" style={{ display: "inline-flex", alignItems: "center", gap: "4px", background: "var(--soft-accent, #e5f2ec)", color: "var(--accent, #2f6f65)", padding: "4px 8px", borderRadius: "12px", fontSize: "12px", fontWeight: 600 }}>
          <TrendingUp size={14} />
          Тенденция
        </span>
      </div>

      {/* Criteria Color Legend */}
      <div style={{ display: "flex", gap: "16px", marginBottom: "12px", flexWrap: "wrap" }}>
        {series.map((s) => (
          <div key={s.key} style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--text)" }}>
            <span style={{ width: "12px", height: "12px", borderRadius: "3px", backgroundColor: s.color }}></span>
            <span>{s.name}</span>
          </div>
        ))}
      </div>

      <div className="chart-frame" style={{ minHeight: `${svgHeight}px`, height: "auto", display: "flex", justifyContent: "center" }}>
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ width: "100%", maxHeight: "260px" }}>
          {/* Y Ticks (0, 2.5, 5.0, 7.5, 10.0) */}
          {[0, 2.5, 5, 7.5, 10].map((score) => {
            const y = startY - (score / 10) * chartHeight;
            return (
              <g key={score}>
                <line x1={startX} y1={y} x2={endX} y2={y} stroke="var(--line, #e2e8f0)" strokeDasharray="3 3" strokeWidth="1" />
                <text x={startX - 10} y={y + 4} fill="var(--muted, #64748b)" fontSize="10" textAnchor="end">
                  {score}
                </text>
              </g>
            );
          })}

          {/* Period Ticks on X-Axis */}
          {trendData.map((pt, idx) => {
            const x = startX + idx * periodStep;
            return (
              <text key={idx} x={x} y={startY + 20} fill="var(--text, #1e293b)" fontSize="11" fontWeight="600" textAnchor="middle">
                {pt.period}
              </text>
            );
          })}

          {/* Trend Lines */}
          {series.map((s) => {
            const pathPoints = trendData.map((pt, idx) => {
              const x = startX + idx * periodStep;
              const val = Math.max(0, Math.min(10, Number(pt[s.key] || 0)));
              const y = startY - (val / 10) * chartHeight;
              return `${x},${y}`;
            });

            return (
              <g key={s.key}>
                <polyline points={pathPoints.join(" ")} fill="none" stroke={s.color} strokeWidth="2.5" />
                {trendData.map((pt, idx) => {
                  const x = startX + idx * periodStep;
                  const val = Math.max(0, Math.min(10, Number(pt[s.key] || 0)));
                  const y = startY - (val / 10) * chartHeight;
                  return (
                    <g key={idx}>
                      <circle cx={x} cy={y} r="4" fill={s.color} stroke="#ffffff" strokeWidth="1.5" />
                      <text x={x} y={y - 8} fill={s.color} fontSize="10" fontWeight="700" textAnchor="middle">
                        {val.toFixed(1)}
                      </text>
                    </g>
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>
    </section>
  );
}

/* =========================================================================
   Main Exported DashboardTab Component
   ========================================================================= */
export function DashboardTab({ viewModel }) {
  if (!viewModel.statistics) {
    return (
      <EmptyChartState
        title="Панель показателей"
        message="В отчете отсутствуют количественные данные statistics."
      />
    );
  }

  return (
    <div className="dashboard-tab" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Metric Cards Top Row */}
      <MetricCards metricCards={viewModel.metricCards} involvement={viewModel.involvement} />

      {/* Section 1: Main Criteria Visualizations */}
      <DashboardSection title="Критерии и распределение оценок">
        <div className="dashboard-chart-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
          <SvgAverageBarChart criteria={viewModel.fiveCriteria} />
          <SvgSatisfactionRadarChart criteria={viewModel.fiveCriteria} />
          <SvgCorrelationHeatmap matrix={viewModel.dashboardData.correlation_matrix} />
          <SvgOverallDistributionChart
            distribution={viewModel.overallDistribution}
            limitation={viewModel.limitations.exactScoreDistribution}
          />
        </div>
      </DashboardSection>

      {/* Section 2: Period Dynamics */}
      <DashboardSection title="Динамика реализации программы">
        <SvgTrendChart trendData={viewModel.dashboardData.trend_data} />
      </DashboardSection>

      {/* Section 3: Audience Composition & Format Preferences */}
      <DashboardSection title="Состав группы и форматы обучения">
        <div className="dashboard-chart-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "20px" }}>
          <section className="panel compact-breakdown-panel">
            <h3><Layers size={18} style={{ display: "inline", verticalAlign: "sub", marginRight: "6px" }} />Категории слушателей в группе</h3>
            {Object.entries(viewModel.positionDistribution).length > 0 ? (
              Object.entries(viewModel.positionDistribution).map(([position, count]) => {
                const total = Math.max(Object.values(viewModel.positionDistribution).reduce((sum, value) => sum + value, 0), 1);
                const percent = Math.round((count / total) * 100);
                return (
                  <div className="breakdown-row" key={position} style={{ marginBottom: "8px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                      <span>{position}</span>
                      <strong>{count} чел. ({percent}%)</strong>
                    </div>
                    <div className="mini-progress" style={{ height: "6px", borderRadius: "3px", backgroundColor: "var(--panel-border, #e2e8f0)", overflow: "hidden" }}>
                      <span style={{ display: "block", height: "100%", width: `${percent}%`, backgroundColor: "var(--accent, #2f6f65)", borderRadius: "3px" }}></span>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="muted">Нет данных по категориям.</p>
            )}
          </section>

          <section className="panel compact-breakdown-panel">
            <h3><PieChart size={18} style={{ display: "inline", verticalAlign: "sub", marginRight: "6px" }} />Предпочитаемые форматы обучения</h3>
            {Object.entries(viewModel.preferredFormats).length > 0 ? (
              Object.entries(viewModel.preferredFormats).map(([format, count]) => {
                const total = Math.max(Object.values(viewModel.preferredFormats).reduce((sum, value) => sum + value, 0), 1);
                const percent = Math.round((count / total) * 100);
                return (
                  <div className="format-breakdown-row" key={format} style={{ marginBottom: "8px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                      <span>{format}</span>
                      <strong>{percent}%</strong>
                    </div>
                    <div className="mini-progress" style={{ height: "6px", borderRadius: "3px", backgroundColor: "var(--panel-border, #e2e8f0)", overflow: "hidden" }}>
                      <span style={{ display: "block", height: "100%", width: `${percent}%`, backgroundColor: "var(--accent-2, #425f86)", borderRadius: "3px" }}></span>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="muted">Нет данных по форматам.</p>
            )}
          </section>
        </div>
      </DashboardSection>
    </div>
  );
}
