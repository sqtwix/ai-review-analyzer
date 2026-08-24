import assert from "node:assert/strict";
import test from "node:test";

import { buildCourseReportViewModel } from "../src/reportViewModel.js";

const metric = (average) => ({
  average,
  median: average,
  std_dev: 1,
  distribution: { low: 0, mid: 50, high: 50 },
});

test("moderate 12-person result is not labelled as requiring a program rebuild", () => {
  const report = {
    result: {
      courses_analysis: [{
        course_name: "Тестовый курс",
        period: "24.08-25.08.2026",
        students_count: 12,
        statistics: {
          usefulness: metric(7.8),
          practicality: metric(6.9),
          accessibility: metric(7.7),
          interaction: metric(7.6),
          overall: metric(7.5),
          involvement: { involved_percent: 66.7, detached_percent: 33.3 },
        },
        text_analysis: {
          top_topics: [],
          key_problems: [],
          quotes: [],
          recommendations: [],
        },
      }],
    },
  };

  const viewModel = buildCourseReportViewModel(report);

  assert.equal(viewModel.decisionSupport.decision.tone, "watch");
  assert.notEqual(viewModel.decisionSupport.decision.title, "Нужна переработка программы");
});
