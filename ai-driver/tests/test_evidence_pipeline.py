import json
import os
import unittest

from backend.agent_manager import AgentManager
from schemas.analysis_response import AnalysisResponse


class FakeClient:
    def __init__(self):
        self.calls = []

    def execute(self, system_prompt, user_prompt, **options):
        payload = json.loads(user_prompt)
        self.calls.append({"payload": payload, "options": options})
        responses = []
        for record in payload["responses"]:
            evidence = []
            if record["evidence_fields"]:
                field = record["evidence_fields"][0]
                evidence.append({
                    "field": field,
                    "quote": record["fields"][field],
                    "topic": "Практика",
                    "kind": "suggestion" if field == "topics_to_add_comment" else "positive",
                    "priority": "Low",
                })
            responses.append({
                "response_id": record["response_id"],
                "sentiment": "positive",
                "evidence": evidence,
            })
        return json.dumps({"responses": responses}, ensure_ascii=False)


class FakeFactory:
    def __init__(self, client):
        self.client = client

    def create_queue(self, model):
        return [self.client, self.client, self.client]


class FlakyClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.failures_remaining = 1

    def execute(self, system_prompt, user_prompt, **options):
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise ConnectionError("model server restarting")
        return super().execute(system_prompt, user_prompt, **options)


class IncompleteBatchClient(FakeClient):
    def execute(self, system_prompt, user_prompt, **options):
        payload = json.loads(user_prompt)
        if len(payload["responses"]) > 1:
            payload["responses"] = payload["responses"][:1]
        return super().execute(system_prompt, json.dumps(payload, ensure_ascii=False), **options)


class EvidencePipelineTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.manager = AgentManager(FakeFactory(self.client))

    def test_invalid_quote_is_rejected_without_losing_valid_atom(self):
        records = [{
            "response_id": "student_1",
            "position_category": "Методист",
            "fields": {"practice_change_comment": "Добавить практические кейсы"},
        }]
        result = {
            "responses": [{
                "response_id": "student_1",
                "sentiment": "negative",
                "evidence": [
                    {
                        "field": "practice_change_comment",
                        "quote": "Добавить практические кейсы",
                        "topic": "Практика",
                        "kind": "suggestion",
                        "priority": "Medium",
                    },
                    {
                        "field": "practice_change_comment",
                        "quote": "Цитата отсутствует",
                        "topic": "Практика",
                        "kind": "problem",
                        "priority": "High",
                    },
                ],
            }],
        }

        accepted, sentiments, rejected = self.manager._validate_evidence_chunk(result, records)

        self.assertEqual(1, len(accepted))
        self.assertEqual({"student_1": "negative"}, sentiments)
        self.assertEqual(1, rejected)

    def test_single_response_root_is_normalized(self):
        records = [{
            "response_id": "student_1",
            "position_category": "Методист",
            "fields": {"topics_to_add_comment": "Больше кейсов"},
        }]
        result = {
            "response_id": "student_1",
            "sentiment": "positive",
            "evidence": [{
                "field": "topics_to_add_comment",
                "quote": "Больше кейсов",
                "topic": "topics_to_add_comment",
                "kind": "positive",
                "priority": "Medium",
            }],
        }

        accepted, sentiments, rejected = self.manager._validate_evidence_chunk(result, records)

        self.assertEqual(0, rejected)
        self.assertEqual("suggestion", accepted[0]["kind"])
        self.assertEqual("Темы к добавлению", accepted[0]["topic"])
        self.assertEqual({"student_1": "positive"}, sentiments)

    def test_non_substantive_comment_cannot_become_evidence(self):
        records = self.manager._prepare_evidence_records([{
            "student_id": "student_1",
            "topics_to_exclude_comment": "нет",
            "interaction_comment": "Всё отлично!",
        }])
        result = {
            "response_id": "student_1",
            "sentiment": "positive",
            "evidence": [{
                "field": "topics_to_exclude_comment",
                "quote": "нет",
                "topic": "Темы к исключению",
                "kind": "suggestion",
                "priority": "High",
            }],
        }

        accepted, sentiments, rejected = self.manager._validate_evidence_chunk(result, records)

        self.assertEqual([], records[0]["evidence_fields"])
        self.assertEqual([], accepted)
        self.assertEqual({"student_1": "positive"}, sentiments)
        self.assertEqual(1, rejected)

    def test_positive_change_comment_is_not_forced_to_suggestion(self):
        records = self.manager._prepare_evidence_records([{
            "student_id": "student_1",
            "practice_change_comment": "Практические занятия уже хорошо связаны с рабочими задачами",
        }])
        result = {
            "response_id": "student_1",
            "sentiment": "positive",
            "evidence": [{
                "field": "practice_change_comment",
                "quote": "Практические занятия уже хорошо связаны с рабочими задачами",
                "topic": "Связь практики с работой",
                "kind": "positive",
                "priority": "Low",
            }],
        }

        accepted, _, rejected = self.manager._validate_evidence_chunk(result, records)

        self.assertEqual(0, rejected)
        self.assertEqual("positive", accepted[0]["kind"])

    def test_no_change_answers_are_removed_from_actionable_fields(self):
        records = self.manager._prepare_evidence_records([
            {
                "student_id": "student_8",
                "topics_to_exclude_comment": "Лекция с экспертами от Сбера",
                "topics_to_add_comment": "Тема пайплайна",
            },
            {
                "student_id": "student_29",
                "topics_to_exclude_comment": "Все актуальны и интересны.",
                "topics_to_add_comment": "Курс очень органичен как в теории, так и в практике!",
            },
            {
                "student_id": "student_33",
                "topics_to_exclude_comment": "Все полезны",
                "topics_to_add_comment": "Все прекрасно",
            },
            {
                "student_id": "student_35",
                "topics_to_exclude_comment": "Таких тем нет",
                "topics_to_add_comment": "Программа составлена последовательно, четко и ёмко",
            },
            {
                "student_id": "student_37",
                "topics_to_exclude_comment": "Курс содержит достаточное количество теории и практики",
                "topics_to_add_comment": "нет предложений",
            },
        ])

        self.assertEqual(
            ["topics_to_add_comment", "topics_to_exclude_comment"],
            records[0]["evidence_fields"],
        )
        self.assertEqual([], records[1]["evidence_fields"])
        self.assertEqual([], records[2]["evidence_fields"])
        self.assertEqual([], records[3]["evidence_fields"])
        self.assertEqual([], records[4]["evidence_fields"])

    def test_actionable_fields_are_sent_before_general_comments(self):
        records = self.manager._prepare_evidence_records([{
            "student_id": "student_1",
            "motivation_comment": "Хочу применять ИИ в работе",
            "topics_to_exclude_comment": "Убрать повтор вводной теории",
            "topics_to_add_comment": "Добавить работу в платных приложениях",
        }])

        self.assertEqual(
            ["topics_to_add_comment", "topics_to_exclude_comment"],
            records[0]["evidence_fields"][:2],
        )
        self.assertEqual(
            ["topics_to_add_comment", "topics_to_exclude_comment"],
            list(records[0]["fields"])[:2],
        )

    def test_contextual_no_action_phrases_do_not_hide_real_addition(self):
        records = self.manager._prepare_evidence_records([
            {
                "student_id": "student_10",
                "topics_to_exclude_comment": "все полезно и нужно",
                "topics_to_add_comment": "все темы рассмотрены",
            },
            {
                "student_id": "student_12",
                "topics_to_exclude_comment": "Нужно оставить все вопросы.",
                "topics_to_add_comment": "Добавить больше часов для обучения.",
            },
        ])

        self.assertEqual([], records[0]["evidence_fields"])
        self.assertEqual(["topics_to_add_comment"], records[1]["evidence_fields"])

    def test_do_not_exclude_answer_is_not_treated_as_requested_exclusion(self):
        records = self.manager._prepare_evidence_records([{
            "student_id": "student_1",
            "topics_to_exclude_comment": "Не исключать",
        }])

        self.assertEqual([], records[0]["evidence_fields"])

    def test_explicit_problem_language_corrects_model_kind(self):
        records = self.manager._prepare_evidence_records([{
            "student_id": "student_1",
            "accessibility_comment": "Слишком быстрый темп, не хватало времени на вопросы",
        }])
        result = {
            "response_id": "student_1",
            "sentiment": "negative",
            "evidence": [{
                "field": "accessibility_comment",
                "quote": "Слишком быстрый темп, не хватало времени на вопросы",
                "topic": "Темп обучения",
                "kind": "neutral",
                "priority": "High",
            }],
        }

        accepted, _, rejected = self.manager._validate_evidence_chunk(result, records)

        self.assertEqual(0, rejected)
        self.assertEqual("problem", accepted[0]["kind"])

    def test_explicit_problem_is_kept_when_model_spends_limit_on_suggestion(self):
        records = self.manager._prepare_evidence_records([{
            "student_id": "student_1",
            "topics_to_add_comment": "Добавить больше практических кейсов",
            "accessibility_comment": "Слишком быстрый темп, не хватало времени на вопросы",
        }])
        result = {
            "response_id": "student_1",
            "sentiment": "negative",
            "evidence": [{
                "field": "topics_to_add_comment",
                "quote": "Добавить больше практических кейсов",
                "topic": "Практические кейсы",
                "kind": "suggestion",
                "priority": "Medium",
            }],
        }

        accepted, _, rejected = self.manager._validate_evidence_chunk(result, records)

        self.assertEqual(0, rejected)
        problem = next(item for item in accepted if item["kind"] == "problem")
        self.assertEqual("accessibility_comment", problem["field"])
        self.assertEqual(
            "Слишком быстрый темп, не хватало времени на вопросы",
            problem["quote"],
        )
        self.assertEqual("Комментарий о доступности материала", problem["topic"])

    def test_error_word_in_neutral_context_is_not_promoted_to_problem(self):
        self.assertEqual(
            "neutral",
            self.manager._normalize_evidence_kind(
                "logic_sequence_reason",
                "Сначала рассмотрели нормальный сценарий, затем ошибки",
                "neutral",
            ),
        )
        self.assertEqual(
            "suggestion",
            self.manager._normalize_evidence_kind(
                "practice_change_comment",
                "Разобрать ошибки загрузки и некорректные форматы файлов",
                "suggestion",
            ),
        )
        self.assertEqual(
            "problem",
            self.manager._normalize_evidence_kind(
                "detachment_reason_comment",
                "Когда возникла ошибка при загрузке файла",
                "neutral",
            ),
        )

    def test_explicit_suggestion_topic_is_grounded_in_quote(self):
        records = self.manager._prepare_evidence_records([{
            "student_id": "student_1",
            "topics_to_add_comment": "Добавить кейсы из государственного управления",
        }])
        result = {
            "response_id": "student_1",
            "sentiment": "positive",
            "evidence": [{
                "field": "topics_to_add_comment",
                "quote": "Добавить кейсы из государственного управления",
                "topic": "Госудебные кейсы",
                "kind": "suggestion",
                "priority": "High",
            }],
        }

        accepted, _, rejected = self.manager._validate_evidence_chunk(result, records)

        self.assertEqual(0, rejected)
        self.assertEqual("Кейсы из государственного управления", accepted[0]["topic"])

    def test_single_response_cannot_create_high_priority(self):
        extraction = {
            "evidence": [
                {
                    "response_id": "student_1",
                    "field": "topics_to_add_comment",
                    "quote": "Добавить больше примеров",
                    "topic": "Больше примеров",
                    "kind": "suggestion",
                    "priority": "High",
                },
                {
                    "response_id": "student_2",
                    "field": "accessibility_comment",
                    "quote": "Слишком быстрый темп",
                    "topic": "Темп обучения",
                    "kind": "problem",
                    "priority": "High",
                },
            ],
            "sentiments": {},
        }

        aggregated = self.manager._aggregate_evidence(extraction, 12)

        priorities = {item["target"]: item["priority"] for item in aggregated["recommendations"]}
        self.assertEqual("Low", priorities["Больше примеров"])
        self.assertEqual("Medium", priorities["Темп обучения"])
        self.assertEqual("Medium", aggregated["key_problems"][0]["severity"])

    def test_preferred_format_is_not_reported_as_actual_education_form(self):
        metadata = self.manager._build_metadata({"Очно": 8, "Онлайн": 4})

        self.assertIsNone(metadata["education_form"])
        self.assertIn("education_form", metadata["missing_fields"])

    def test_real_dataset_no_action_variants_are_filtered_without_hiding_video_request(self):
        records = self.manager._prepare_evidence_records([
            {
                "student_id": "student_17",
                "topics_to_exclude_comment": "все очень важно",
                "topics_to_add_comment": "всего достаточно, можно больше внимания уделить созданию видео",
            },
            {
                "student_id": "student_19",
                "topics_to_exclude_comment": "ничего не нужно исключать",
                "topics_to_add_comment": "все актуально и познавательно",
            },
            {
                "student_id": "student_24",
                "topics_to_exclude_comment": "все",
                "topics_to_add_comment": "Достаточно полно",
            },
            {
                "student_id": "student_28",
                "topics_to_exclude_comment": "все нужны",
                "topics_to_add_comment": "думаю все в полной мере достаточно",
            },
        ])

        self.assertEqual(["topics_to_add_comment"], records[0]["evidence_fields"])
        self.assertEqual([], records[1]["evidence_fields"])
        self.assertEqual([], records[2]["evidence_fields"])
        self.assertEqual([], records[3]["evidence_fields"])

    def test_transport_failure_is_retried_once(self):
        client = FlakyClient()
        records = self.manager._prepare_evidence_records([{
            "student_id": "student_1",
            "motivation_comment": "Хочу применять ИИ в работе",
        }])
        previous_delay = os.environ.get("AI_EVIDENCE_RETRY_DELAY_SECONDS")
        os.environ["AI_EVIDENCE_RETRY_DELAY_SECONDS"] = "0"
        try:
            extraction = self.manager._extract_evidence(client, records, "qwen_local")
        finally:
            if previous_delay is None:
                os.environ.pop("AI_EVIDENCE_RETRY_DELAY_SECONDS", None)
            else:
                os.environ["AI_EVIDENCE_RETRY_DELAY_SECONDS"] = previous_delay

        self.assertEqual(0, extraction["chunks_failed"])
        self.assertEqual(1, len(extraction["evidence"]))
        self.assertEqual({"student_1": "positive"}, extraction["sentiments"])
        self.assertEqual(2, extraction["model_requests"])

    def test_incomplete_batch_falls_back_only_for_missing_response(self):
        client = IncompleteBatchClient()
        records = self.manager._prepare_evidence_records([
            {"student_id": "student_1", "motivation_comment": "Хочу применять ИИ в работе"},
            {"student_id": "student_2", "motivation_comment": "Нужны навыки анализа данных"},
        ])

        previous_batch_size = os.environ.get("AI_EVIDENCE_BATCH_SIZE")
        os.environ["AI_EVIDENCE_BATCH_SIZE"] = "2"
        try:
            extraction = self.manager._extract_evidence(client, records, "qwen_local")
        finally:
            if previous_batch_size is None:
                os.environ.pop("AI_EVIDENCE_BATCH_SIZE", None)
            else:
                os.environ["AI_EVIDENCE_BATCH_SIZE"] = previous_batch_size

        self.assertEqual(0, extraction["chunks_failed"])
        self.assertEqual(2, extraction["model_requests"])
        self.assertEqual(1, extraction["fallback_responses"])
        self.assertEqual({"student_1", "student_2"}, set(extraction["sentiments"]))
        self.assertEqual(2, len(extraction["evidence"]))

    def test_per_response_extraction_aggregation_and_contract(self):
        responses = []
        for index in range(1, 7):
            responses.append({
                "student_id": f"student_{index}",
                "position_category": "Методист",
                "usefulness_score": 9,
                "practicality_score": 8,
                "accessibility_score": 9,
                "interaction_score": 8,
                "preferred_format": "онлайн",
                "is_detached": False,
                "topics_to_add_comment": f"Добавить кейс {index}",
            })
        request = {
            "batch_id": "test-batch",
            "courses": [{
                "course_name": "Тестовый курс",
                "period": "01.01-02.01",
                "responses": responses,
            }],
        }

        raw = self.manager.start_qwen_local_processing(json.dumps(request, ensure_ascii=False))
        validated = AnalysisResponse.model_validate_json(raw)
        course = validated.courses_analysis[0]

        self.assertEqual(6, len(self.client.calls))
        self.assertTrue(all(len(call["payload"]["responses"]) == 1 for call in self.client.calls))
        self.assertTrue(all(call["options"]["response_schema"] for call in self.client.calls))
        self.assertEqual(6, course.text_analysis.top_topics[0].frequency)
        self.assertEqual(6, len(course.text_analysis.top_topics[0].evidence.rows))
        self.assertEqual(100.0, course.text_analysis.sentiment.positive)
        self.assertEqual(6, course.analytical_report.section3_suggestions.added_topics[0].count)
        self.assertIn("принято evidence 6", course.processing_log[-1].message)
        self.assertIn("запросов к модели 6", course.processing_log[-1].message)


if __name__ == "__main__":
    unittest.main()
