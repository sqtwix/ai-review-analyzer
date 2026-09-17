import json
import os
import unittest
from unittest.mock import patch
import httpx
from fastapi import HTTPException

from backend.agent_factory import AgentFactory
from backend.agent_manager import AgentManager
from controllers.agent_controller import AgentController
from main import readiness
from schemas.analysis_request import AnalysisRequest


class UnavailableQwenManager:
    def start_qwen_local_processing(self, input_data):
        raise ConnectionError("qwen-local is unavailable")


class RuntimeHealthTests(unittest.TestCase):
    def test_programmatic_result_is_exact_for_single_response(self):
        request = AnalysisRequest.model_validate({
            "batch_id": "single-result-correctness",
            "courses": [{
                "course_name": "Single response",
                "responses": [{
                    "student_id": "student-1",
                    "position_category": "Специалист",
                    "preferred_format": "Очно",
                    "usefulness_score": 9,
                    "practicality_score": 8,
                    "accessibility_score": 10,
                    "interaction_score": 7,
                    "is_detached": False,
                }],
            }],
        })

        course = AgentController(AgentManager(AgentFactory()))._generate_programmatic_analysis(request)["courses_analysis"][0]

        self.assertEqual(1, course["students_count"])
        self.assertEqual(9.0, course["statistics"]["usefulness"]["average"])
        self.assertEqual({"low": 0.0, "mid": 0.0, "high": 100.0}, course["statistics"]["usefulness"]["distribution"])
        self.assertEqual({"detached_percent": 0.0, "involved_percent": 100.0, "yes_count": 0, "no_count": 1}, course["statistics"]["involvement"])
        self.assertEqual({"Специалист": 1}, course["position_distribution"])
        self.assertEqual({"Очно": 1}, course["preferred_formats"])
        self.assertEqual(4, course["validation_summary"]["valid_count"])

    def test_programmatic_result_is_exact_for_large_sequential_batch(self):
        responses = []
        for index in range(1000):
            score = (index % 10) + 1
            responses.append({
                "student_id": f"student-{index + 1}",
                "position_category": "Специалист" if index % 2 == 0 else "Руководитель",
                "preferred_format": "Очно" if index % 4 else "Дистанционно",
                "usefulness_score": score,
                "practicality_score": 11 - score,
                "accessibility_score": 8,
                "interaction_score": 1 if index % 2 == 0 else 10,
                "is_detached": index % 4 == 0,
            })
        request = AnalysisRequest.model_validate({
            "batch_id": "large-result-correctness",
            "courses": [{"course_name": "Large batch", "responses": responses}],
        })

        course = AgentController(AgentManager(AgentFactory()))._generate_programmatic_analysis(request)["courses_analysis"][0]

        self.assertEqual(1000, course["students_count"])
        self.assertEqual(5.5, course["statistics"]["usefulness"]["average"])
        self.assertEqual(5.5, course["statistics"]["usefulness"]["median"])
        self.assertEqual(2.87, course["statistics"]["usefulness"]["std_dev"])
        self.assertEqual({"low": 30.0, "mid": 40.0, "high": 30.0}, course["statistics"]["usefulness"]["distribution"])
        self.assertEqual(8.0, course["statistics"]["accessibility"]["average"])
        self.assertEqual(0.0, course["statistics"]["accessibility"]["std_dev"])
        self.assertEqual({"detached_percent": 25.0, "involved_percent": 75.0, "yes_count": 250, "no_count": 750}, course["statistics"]["involvement"])
        self.assertEqual({"Специалист": 500, "Руководитель": 500}, course["position_distribution"])
        self.assertEqual({"Дистанционно": 250, "Очно": 750}, course["preferred_formats"])
        self.assertEqual({"valid_count": 4000, "missing_count": 0, "invalid_count": 0, "total_issues": 0}, course["validation_summary"])

    def test_empty_batch_is_rejected_instead_of_returning_empty_fallback(self):
        request = AnalysisRequest.model_validate({"batch_id": "empty", "courses": []})

        with self.assertRaises(HTTPException) as raised:
            AgentController(AgentManager(AgentFactory())).get_qwen_local_data_analysis(request)

        self.assertEqual(400, raised.exception.status_code)

    def test_platform_readiness_is_not_blocked_without_any_provider(self):
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "",
            "SBERGPT_API_KEY": "",
            "LOCAL_AI_ENABLED": "false",
            "QWEN_LOCAL_URL": "http://qwen-local:8080/v1",
        }, clear=False), patch("main.httpx.get", side_effect=httpx.ConnectError("offline")):
            response = readiness()

        payload = json.loads(response.body)
        self.assertEqual(200, response.status_code)
        self.assertEqual("ready", payload["status"])
        self.assertFalse(payload["model_available"])
        self.assertFalse(payload["providers"]["qwen_local"]["enabled"])

    def test_readiness_reports_configured_cloud_provider(self):
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "configured",
            "SBERGPT_API_KEY": "",
            "LOCAL_AI_ENABLED": "false",
        }, clear=False), patch("main.httpx.get", side_effect=httpx.ConnectError("offline")):
            response = readiness()

        self.assertEqual(200, response.status_code)
        self.assertTrue(json.loads(response.body)["providers"]["deepseek"]["configured"])

    def test_local_provider_requires_explicit_enablement(self):
        with patch.dict(os.environ, {"LOCAL_AI_ENABLED": "false"}, clear=False):
            with self.assertRaisesRegex(ValueError, "LOCAL_AI_ENABLED is not enabled"):
                AgentFactory().create_queue("qwen_local")

    def test_cloud_provider_without_key_fails_explicitly(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False):
            with self.assertRaisesRegex(ValueError, "DEEPSEEK_API_KEY is not configured"):
                AgentFactory().create_queue("deepseek")

    def test_unavailable_local_model_returns_limited_programmatic_fallback(self):
        request = AnalysisRequest.model_validate({
            "batch_id": "fallback-test",
            "courses": [{
                "course_name": "Runtime test",
                "responses": [{
                    "student_id": "student-1",
                    "usefulness_score": 8,
                    "practicality_score": 7,
                    "accessibility_score": 9,
                    "interaction_score": 8,
                }],
            }],
        })

        response = AgentController(UnavailableQwenManager()).get_qwen_local_data_analysis(request)
        course = json.loads(response.body)["courses_analysis"][0]

        self.assertEqual(200, response.status_code)
        self.assertEqual("skipped", course["processing_log"][-1]["status"])
        self.assertIn("модель недоступна", course["quality_limitations"][0].lower())

    def test_no_ai_runtime_smoke_uses_documented_quantitative_fallback(self):
        request = AnalysisRequest.model_validate({
            "batch_id": "no-ai-smoke",
            "courses": [{
                "course_name": "No AI runtime",
                "responses": [{
                    "student_id": "student-1",
                    "usefulness_score": 8,
                    "practicality_score": 7,
                    "accessibility_score": 9,
                    "interaction_score": 8,
                }],
            }],
        })

        with patch.dict(os.environ, {"LOCAL_AI_ENABLED": "false"}, clear=False):
            response = AgentController(AgentManager(AgentFactory())).get_qwen_local_data_analysis(request)

        course = json.loads(response.body)["courses_analysis"][0]
        self.assertEqual(200, response.status_code)
        self.assertEqual(8.0, course["statistics"]["usefulness"]["average"])
        self.assertEqual("skipped", course["processing_log"][-1]["status"])


if __name__ == "__main__":
    unittest.main()
