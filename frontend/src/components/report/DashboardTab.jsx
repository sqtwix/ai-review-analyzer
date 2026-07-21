import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { TrendingUp } from "lucide-react";

const chartColors = {
  primary: "var(--accent)",
  secondary: "var(--accent-2)",
  tertiary: "var(--accent-3)",
  low: "var(--danger)",
  mid: "var(--warning)",
  high: "var(--accent)",
};

const axisTick = {
  fill: "var(--text)",
  fontSize: "var(--font-size-xs)",
  fontWeight: "var(--font-weight-secondary)",
};

const mutedAxisTick = {
  ...axisTick,
  fill: "var(--muted)",
};

const formatNumber = (value, digits = 1) => {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "-";
};

const getHeatColor = (value) => {
  if (value >= 0.85) return "var(--accent)";
  if (value >= 0.65) return "rgba(47, 111, 101, 0.72)";
  if (value >= 0.45) return "rgba(66, 95, 134, 0.58)";
  if (value >= 0.25) return "rgba(201, 101, 69, 0.46)";
  return "rgba(201, 101, 69, 0.24)";
};

function EmptyChartState({ title, message }) {
  return (
    <section className="panel chart-panel chart-panel-empty">
      <h3>{title}</h3>
      <p className="muted">{message}</p>
    </section>
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

function AverageBarChart({ criteria }) {
  const data = criteria.filter((item) => Number.isFinite(item.value));

  return (
    <section className="panel chart-panel">
      <h3>Средние баллы по 5 критериям</h3>
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 8, right: 18, left: 16, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
            <XAxis type="number" domain={[0, 10]} tick={mutedAxisTick} />
            <YAxis type="category" dataKey="label" width={118} tick={axisTick} />
            <Tooltip formatter={(value) => [`${formatNumber(value)} / 10`, "Среднее"]} />
            <Bar dataKey="value" fill={chartColors.primary} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function SatisfactionRadarChart({ criteria }) {
  const data = criteria.filter((item) => Number.isFinite(item.value));

  return (
    <section className="panel chart-panel">
      <h3>Профиль удовлетворенности</h3>
      <div className="chart-frame chart-frame-square">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="70%">
            <PolarGrid stroke="var(--line)" />
            <PolarAngleAxis dataKey="label" tick={axisTick} />
            <PolarRadiusAxis angle={90} domain={[0, 10]} tick={mutedAxisTick} />
            <Tooltip formatter={(value, _name, item) => [item.payload.displayValue, "Значение"]} />
            <Radar dataKey="value" fill="rgba(47, 111, 101, 0.28)" stroke={chartColors.primary} strokeWidth={2} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-note muted">Вовлеченность приведена к шкале 0-10 через процент вовлеченных слушателей.</p>
    </section>
  );
}

function CorrelationHeatmap({ matrix }) {
  if (!matrix || Object.keys(matrix).length === 0) {
    return (
      <EmptyChartState
        title="Тепловая карта корреляций"
        message="Backend не передал матрицу корреляций для этого отчета."
      />
    );
  }

  const keys = Object.keys(matrix);
  const data = keys.flatMap((rowKey) =>
    keys.map((colKey) => ({
      x: colKey,
      y: rowKey,
      value: Number(matrix[rowKey]?.[colKey] || 0),
    }))
  );

  return (
    <section className="panel chart-panel">
      <h3>Тепловая карта корреляций</h3>
      <div className="chart-frame chart-frame-square">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 16, right: 24, bottom: 18, left: 28 }}>
            <XAxis dataKey="x" type="category" allowDuplicatedCategory={false} tick={axisTick} />
            <YAxis dataKey="y" type="category" tick={axisTick} width={96} />
            <ZAxis range={[260, 260]} />
            <Tooltip formatter={(value, name) => (name === "value" ? [formatNumber(value, 2), "Корреляция"] : value)} />
            <Scatter data={data} shape="square">
              {data.map((entry) => (
                <Cell key={`${entry.x}-${entry.y}`} fill={getHeatColor(entry.value)} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function OverallDistributionChart({ distribution, limitation }) {
  const data = [
    { label: "1-3", value: distribution.low, fill: chartColors.low },
    { label: "4-7", value: distribution.mid, fill: chartColors.mid },
    { label: "8-10", value: distribution.high, fill: chartColors.high },
  ];

  return (
    <section className="panel chart-panel">
      <h3>Распределение общей оценки</h3>
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 18, left: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
            <XAxis dataKey="label" tick={axisTick} />
            <YAxis domain={[0, 100]} tick={mutedAxisTick} />
            <Tooltip formatter={(value) => [`${formatNumber(value, 0)}%`, "Доля"]} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {data.map((entry) => (
                <Cell key={entry.label} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-note muted">{limitation}</p>
    </section>
  );
}

function TrendChart({ trendData }) {
  if (!Array.isArray(trendData) || trendData.length === 0) {
    return (
      <EmptyChartState
        title="График тренда"
        message="Для отчета нет данных по нескольким периодам; тренд появится после передачи временного ряда от backend."
      />
    );
  }

  return (
    <section className="panel chart-panel chart-panel-wide">
      <div className="section-heading">
        <h3>Динамика оценок по периодам</h3>
        <span className="badge trend-badge">
          <TrendingUp size={12} />
          Тенденция
        </span>
      </div>
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={trendData} margin={{ top: 8, right: 18, left: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
            <XAxis dataKey="period" tick={axisTick} />
            <YAxis domain={[0, 10]} tick={mutedAxisTick} />
            <Tooltip formatter={(value) => [`${formatNumber(value)} / 10`, ""]} />
            <Legend />
            <Line type="monotone" dataKey="usefulness_avg" name="Полезность" stroke={chartColors.primary} strokeWidth={2} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="practicality_avg" name="Практика" stroke={chartColors.secondary} strokeWidth={2} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="accessibility_avg" name="Доступность" stroke={chartColors.tertiary} strokeWidth={2} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="interaction_avg" name="Взаимодействие" stroke="var(--warning)" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export function DashboardTab({ viewModel }) {
  if (!viewModel.statistics) {
    return (
      <EmptyChartState
        title="Панель показателей"
        message="В отчете нет блока statistics, поэтому количественный дашборд недоступен."
      />
    );
  }

  return (
    <div className="dashboard-tab">
      <MetricCards metricCards={viewModel.metricCards} involvement={viewModel.involvement} />

      <div className="dashboard-chart-grid">
        <AverageBarChart criteria={viewModel.fiveCriteria} />
        <SatisfactionRadarChart criteria={viewModel.fiveCriteria} />
        <CorrelationHeatmap matrix={viewModel.dashboardData.correlation_matrix} />
        <OverallDistributionChart
          distribution={viewModel.overallDistribution}
          limitation={viewModel.limitations.exactScoreDistribution}
        />
      </div>

      <TrendChart trendData={viewModel.dashboardData.trend_data} />

      <div className="dashboard-chart-grid">
        <section className="panel compact-breakdown-panel">
          <h3>Категории слушателей в партии</h3>
          {Object.entries(viewModel.positionDistribution).map(([position, count]) => {
            const total = Math.max(Object.values(viewModel.positionDistribution).reduce((sum, value) => sum + value, 0), 1);
            const percent = Math.round((count / total) * 100);
            return (
              <div className="breakdown-row" key={position}>
                <span>{position}</span>
                <strong>{count} чел. ({percent}%)</strong>
              </div>
            );
          })}
        </section>

        <section className="panel compact-breakdown-panel">
          <h3>Предпочитаемые форматы обучения</h3>
          {Object.entries(viewModel.preferredFormats).map(([format, count]) => {
            const total = Math.max(Object.values(viewModel.preferredFormats).reduce((sum, value) => sum + value, 0), 1);
            const percent = Math.round((count / total) * 100);
            return (
              <div className="format-breakdown-row" key={format}>
                <div>
                  <span>{format}</span>
                  <strong>{percent}%</strong>
                </div>
                <div className="mini-progress">
                  <span style={{ width: `${percent}%` }}></span>
                </div>
              </div>
            );
          })}
        </section>
      </div>
    </div>
  );
}
