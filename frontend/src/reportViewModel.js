const numericMetricKeys = [
  {
    key: "usefulness",
    label: "Полезность",
    shortLabel: "Полезность",
    summaryKey: "usefulness_summary",
  },
  {
    key: "practicality",
    label: "Практико-ориентированность",
    shortLabel: "Практика",
    summaryKey: "practicality_summary",
  },
  {
    key: "accessibility",
    label: "Доступность",
    shortLabel: "Доступность",
    summaryKey: "accessibility_summary",
  },
  {
    key: "interaction",
    label: "Взаимодействие с КУ",
    shortLabel: "Взаимодействие",
    summaryKey: "interaction_summary",
  },
];

const toNumber = (value, fallback = 0) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

const formatPercent = (value) => `${toNumber(value).toFixed(0)}%`;

const getMetricValue = (metric, field) => {
  if (!metric || metric[field] === undefined || metric[field] === null) return null;
  return toNumber(metric[field], null);
};

const normalizeDistribution = (distribution) => ({
  low: toNumber(distribution?.low),
  mid: toNumber(distribution?.mid),
  high: toNumber(distribution?.high),
});

const averageNumbers = (values) => {
  const validValues = values.filter((value) => Number.isFinite(value));
  if (!validValues.length) return null;
  return validValues.reduce((sum, value) => sum + value, 0) / validValues.length;
};

const clampNumber = (value, min, max) => Math.min(max, Math.max(min, value));

const normalizePriority = (value) => {
  const priority = String(value || "").toLowerCase();
  if (priority === "high" || priority === "высокий") return "high";
  if (priority === "medium" || priority === "средний") return "medium";
  return "low";
};

const priorityLabels = {
  high: "Высокий",
  medium: "Средний",
  low: "Низкий",
};

const priorityOrder = {
  high: 0,
  medium: 1,
  low: 2,
};

const dedupeByTitle = (items) => {
  const seen = new Set();
  return items.filter((item) => {
    const key = String(item.title || "").toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const buildDecisionSupport = ({
  textAnalysis,
  metricCards,
  overallSatisfaction,
  involvement,
  studentsCount,
}) => {
  const topics = textAnalysis?.top_topics || [];
  const problems = textAnalysis?.key_problems || [];
  const quotes = textAnalysis?.quotes || [];
  const recommendations = textAnalysis?.recommendations || [];

  const lowMetrics = metricCards
    .filter((card) => Number.isFinite(card.average) && card.average < 8)
    .sort((a, b) => a.average - b.average);
  const highProblems = problems.filter((problem) => normalizePriority(problem.severity) === "high");
  const detachedPercent = getMetricValue(involvement, "detached_percent") ?? getMetricValue(involvement, "DetachedPercent");
  const hasDetachedRisk = Number.isFinite(detachedPercent) && detachedPercent >= 20;
  const issueCount = lowMetrics.length + highProblems.length + (hasDetachedRisk ? 1 : 0);

  let decision = {
    tone: "watch",
    title: "Доработать курс перед следующим запуском",
    summary: "Есть полезные сильные стороны, но отчет показывает зоны, которые лучше исправить до масштабирования.",
  };

  if (Number.isFinite(overallSatisfaction) && overallSatisfaction >= 8 && issueCount <= 1) {
    decision = {
      tone: "good",
      title: "Курс можно продолжать с точечными правками",
      summary: "Оценки стабильные, критичных сигналов немного. Главная задача - не потерять сильные элементы программы.",
    };
  } else if ((Number.isFinite(overallSatisfaction) && overallSatisfaction < 7) || issueCount >= 4) {
    decision = {
      tone: "risk",
      title: "Нужна переработка программы",
      summary: "В отчете накопилось несколько риск-сигналов. Перед новым запуском стоит пересобрать проблемные блоки и формат практики.",
    };
  }

  const decisionReasons = [
    Number.isFinite(overallSatisfaction)
      ? `Средняя удовлетворенность: ${overallSatisfaction.toFixed(1)} / 10.`
      : "",
    lowMetrics[0] ? `Самый слабый критерий: ${lowMetrics[0].label} (${lowMetrics[0].average.toFixed(1)} / 10).` : "",
    highProblems[0] ? `Критичный сигнал: ${highProblems[0].problem}.` : "",
    hasDetachedRisk ? `Отстраненность слушателей: ${detachedPercent.toFixed(0)}%.` : "",
  ].filter(Boolean);

  const filledMetricCount = metricCards.filter((card) => Number.isFinite(card.average)).length;
  const evidenceCount = topics.length + problems.length + quotes.length + recommendations.length;
  const sampleScore = studentsCount > 0 ? clampNumber((studentsCount / 40) * 35, 8, 35) : 0;
  const metricScore = (filledMetricCount / Math.max(metricCards.length, 1)) * 25;
  const evidenceScore = clampNumber(evidenceCount * 4, 0, 25);
  const actionScore = clampNumber(recommendations.length * 5, 0, 15);
  const confidenceScore = Math.round(sampleScore + metricScore + evidenceScore + actionScore);
  const confidenceLabel =
    confidenceScore >= 80 ? "Высокая" :
    confidenceScore >= 60 ? "Достаточная" :
    confidenceScore >= 40 ? "Средняя" :
    "Низкая";

  const confidenceNotes = [
    studentsCount < 30
      ? "Выборка меньше 30 слушателей: выводы стоит подтвердить на следующем запуске."
      : "Размер выборки достаточен для первичной управленческой оценки.",
    quotes.length === 0
      ? "В данных нет репрезентативных цитат, поэтому качественные выводы менее проверяемы."
      : "Есть цитаты и повторяющиеся формулировки, которые подтверждают качественные выводы.",
    "Точные номера строк и вопросов появятся после передачи детальных ссылок из анализа.",
  ];

  const evidenceHighlights = [
    ...problems.slice(0, 2).map((problem) => ({
      type: "Проблема",
      title: problem.problem || "Проблема без названия",
      detail: `Встречается в ${formatPercent(problem.frequency_percent)} отзывов.`,
      support: `Риск: ${priorityLabels[normalizePriority(problem.severity)]}.`,
      tone: normalizePriority(problem.severity) === "high" ? "risk" : "watch",
    })),
    ...topics.slice(0, 2).map((topic) => ({
      type: "Тема",
      title: topic.topic || "Тема без названия",
      detail: topic.description || "Описание темы не передано.",
      support: `Упоминаний: ${topic.frequency}.`,
      tone: "normal",
    })),
    ...quotes.slice(0, 2).map((quote) => ({
      type: "Цитата",
      title: `«${quote.quote || "Текст цитаты не передан"}»`,
      detail: `Схожих формулировок: ${quote.frequency}.`,
      support: "Подтверждает язык слушателей, а не только агрегированные метрики.",
      tone: "good",
    })),
    ...lowMetrics.slice(0, 2).map((metric) => ({
      type: "Метрика",
      title: metric.label,
      detail: `Средний балл ${metric.average.toFixed(1)} / 10.`,
      support: metric.summary || "Критерий ниже целевого уровня 8.0.",
      tone: "watch",
    })),
  ].slice(0, 6);

  const recommendationActions = recommendations
    .map((recommendation) => {
      const priority = normalizePriority(recommendation.priority);
      return {
        priority,
        priorityLabel: priorityLabels[priority],
        title: recommendation.action_item || recommendation.action || recommendation.title || "Уточнить рекомендацию",
        detail: recommendation.target ? `Зона: ${recommendation.target}.` : "Зона уточняется методистом.",
        owner: priority === "high" ? "Методист и куратор программы" : "Методист программы",
        timing: priority === "high" ? "До следующего запуска" : "В план ближайших правок",
      };
    })
    .sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);

  const metricActions = lowMetrics.slice(0, 2).map((metric) => ({
    priority: metric.average < 7.5 ? "high" : "medium",
    priorityLabel: metric.average < 7.5 ? priorityLabels.high : priorityLabels.medium,
    title: `Разобрать критерий «${metric.label}»`,
    detail: metric.summary || `Средний балл ниже целевого уровня: ${metric.average.toFixed(1)} / 10.`,
    owner: "Методист программы",
    timing: "Перед согласованием следующей версии",
  }));

  const engagementAction = hasDetachedRisk
    ? [{
        priority: "high",
        priorityLabel: priorityLabels.high,
        title: "Снизить отстраненность слушателей",
        detail: "Добавить больше интерактива, практических заданий или коротких проверок понимания.",
        owner: "Куратор программы",
        timing: "До следующего запуска",
      }]
    : [];

  const actionPlan = dedupeByTitle([
    ...recommendationActions,
    ...metricActions,
    ...engagementAction,
  ]).slice(0, 6);

  const qualityChecklist = [
    {
      label: "Ключевые метрики заполнены",
      detail: `${filledMetricCount} из ${metricCards.length} количественных критериев доступны в отчете.`,
      status: filledMetricCount === metricCards.length ? "done" : "warning",
    },
    {
      label: "Выборка пригодна для решения",
      detail: studentsCount >= 30
        ? `${studentsCount} слушателей: можно принимать первичное решение по курсу.`
        : `${studentsCount} слушателей: желательно подтвердить выводы на большей группе.`,
      status: studentsCount >= 30 ? "done" : "warning",
    },
    {
      label: "Качественные выводы подтверждены",
      detail: quotes.length > 0 || topics.length > 0
        ? `Есть ${topics.length} тем(ы) и ${quotes.length} цитат(ы) для проверки выводов.`
        : "Нет тем и цитат, которые показывают основание качественных выводов.",
      status: quotes.length > 0 || topics.length > 0 ? "done" : "warning",
    },
    {
      label: "Есть план корректировок",
      detail: actionPlan.length
        ? `Сформировано ${actionPlan.length} действие(й) для следующего запуска.`
        : "Добавьте хотя бы одну практическую рекомендацию перед отправкой отчета.",
      status: actionPlan.length ? "done" : "warning",
    },
    {
      label: "Проверка перед экспортом",
      detail: "Проверьте название курса, период, формулировки выводов и отсутствие персональных данных.",
      status: "info",
    },
  ];

  return {
    decision,
    decisionReasons,
    confidenceScore,
    confidenceLabel,
    confidenceNotes,
    evidenceHighlights,
    actionPlan,
    qualityChecklist,
  };
};

export const getCourseAnalysis = (report) => {
  if (!report) return null;
  let res = report.result || report;
  if (typeof res === "string") {
    try {
      res = JSON.parse(res);
    } catch (e) {
      console.error("Failed to parse report.result JSON string:", e);
      return null;
    }
  }
  if (res?.courses_analysis?.[0]) return res.courses_analysis[0];
  if (res?.CoursesAnalysis?.[0]) return res.CoursesAnalysis[0];
  if (res?.coursesAnalysis?.[0]) return res.coursesAnalysis[0];
  if (res?.statistics || res?.Statistics) return res;
  return null;
};

export function buildCourseReportViewModel(report) {
  const courseAnalysis = getCourseAnalysis(report);
  const statistics = courseAnalysis?.statistics || courseAnalysis?.Statistics || null;
  const reportData = courseAnalysis?.analytical_report || courseAnalysis?.AnalyticalReport || null;
  const textAnalysis = courseAnalysis?.text_analysis || courseAnalysis?.TextAnalysis || null;
  const dashboardData = courseAnalysis?.dashboard_data || courseAnalysis?.DashboardData || {};
  const involvement = statistics?.involvement || statistics?.Involvement || null;

  const metricCards = numericMetricKeys.map((metricDefinition) => {
    const metric = statistics?.[metricDefinition.key] || statistics?.[metricDefinition.key.charAt(0).toUpperCase() + metricDefinition.key.slice(1)] || null;
    const distribution = normalizeDistribution(metric?.distribution || metric?.Distribution);

    return {
      ...metricDefinition,
      metric,
      average: getMetricValue(metric, "average") ?? getMetricValue(metric, "Average"),
      median: getMetricValue(metric, "median") ?? getMetricValue(metric, "Median"),
      stdDev: getMetricValue(metric, "std_dev") ?? getMetricValue(metric, "StdDev"),
      distribution,
      summary: reportData?.section2_key_criteria?.[metricDefinition.summaryKey] || reportData?.Section2KeyCriteria?.[metricDefinition.summaryKey] || "",
    };
  });

  const numericAverages = metricCards.map((card) => card.average);
  const overallSatisfaction = averageNumbers(numericAverages);
  const overallDistribution = {
    low: averageNumbers(metricCards.map((card) => card.distribution.low)) || 0,
    mid: averageNumbers(metricCards.map((card) => card.distribution.mid)) || 0,
    high: averageNumbers(metricCards.map((card) => card.distribution.high)) || 0,
  };

  const involvementChartMetric = {
    key: "involvement",
    label: "Вовлеченность",
    shortLabel: "Вовлеченность",
    average: involvement ? toNumber(involvement.involved_percent) / 10 : null,
    originalPercent: involvement ? toNumber(involvement.involved_percent) : null,
  };

  const fiveCriteria = [
    ...metricCards.map((card) => ({
      key: card.key,
      label: card.shortLabel,
      value: card.average,
      displayValue: card.average === null ? "-" : card.average.toFixed(1),
    })),
    {
      key: involvementChartMetric.key,
      label: involvementChartMetric.shortLabel,
      value: involvementChartMetric.average,
      displayValue:
        involvementChartMetric.originalPercent === null
          ? "-"
          : `${formatPercent(involvementChartMetric.originalPercent)} (${involvementChartMetric.average.toFixed(1)}/10)`,
    },
  ];

  return {
    courseAnalysis,
    statistics,
    reportData,
    textAnalysis,
    dashboardData,
    courseName: courseAnalysis?.course_name || report?.course || "Электронный курс",
    period: courseAnalysis?.period || "Не указан",
    studentsCount: toNumber(courseAnalysis?.students_count),
    positionDistribution: courseAnalysis?.position_distribution || {},
    preferredFormats: courseAnalysis?.preferred_formats || {},
    metricCards,
    fiveCriteria,
    overallSatisfaction,
    overallDistribution,
    involvement,
    decisionSupport: buildDecisionSupport({
      textAnalysis,
      metricCards,
      overallSatisfaction,
      involvement,
      studentsCount: toNumber(courseAnalysis?.students_count),
    }),
    limitations: {
      exactScoreDistribution:
        "Показано агрегированное распределение оценок по трем диапазонам: низкие, средние и высокие.",
      sourceEvidence:
        "точные номера строк и вопросов пока недоступны в данных отчета.",
    },
  };
}
