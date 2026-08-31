import json
import os
import unittest
from unittest.mock import patch
import httpx

from backend.agent_factory import AgentFactory
from backend.agent_manager import AgentManager
from controllers.agent_controller import AgentController
from main import readiness
from schemas.analysis_request import AnalysisRequest


class UnavailableQwenManager:
    def start_qwen_local_processing(self, input_data):
        raise ConnectionError("qwen-local is unavailable")


class RuntimeHealthTests(unittest.TestCase):
    def test_platform_readiness_is_not_blocked_without_any_provider(self):
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "",
            "SBERGPT_API_KEY": "",
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
