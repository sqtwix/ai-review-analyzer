from openai import OpenAI
import json
import logging
import os

# ========================= Agent Client =========================

# AgentClient - class, that present an Agent.
# AgnetClient class contains a basic constructor
# and execute method that used to get data from
# model API (DeepSeek, Sber GPT, Local Qwen via vLLM).

# ========================= General JSON-Format =========================
# {
#     model: "Model",
#     messages: [
#         {"role": "ROLE", "content": "CONTENT"}
#     ],
#     response_format = {"type" : "json_object"},
#     temperature = 0.3
# }

# Для локальной модели через vllm используется тот же формат,
# так как vllm поднимает OpenAI-совместимый сервер.
# api_key для локальной модели передается как "not-needed".

# Настройка логгера для отслеживания работы агентов
logger = logging.getLogger(__name__)

class AgentClient:
    def __init__(self, api_key: str, base_url: str, agent_model: str, specialization: str):
        # Проверяем обязательные параметры перед инициализацией
        if not base_url or not agent_model:
            raise Exception("AgentClient Initialization Exception: base_url and agent_model are required")
        try:
            self.api_key = api_key
            self.base_url = base_url
            self.model = agent_model
            self.specialization = specialization
            # OpenAI клиент работает для всех совместимых API (DeepSeek, GigaChat, llama.cpp).
            # Retries are handled by the controller fallback path, so the UI does not hang on local model 500s.
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, max_retries=0)
        except Exception as e:
            raise Exception("AgentClient Initialization Exception: agent initialization failed - " + str(e))

    def execute(self, system_prompt: str, user_prompt: str) -> str:
        # Выполняет запрос к модели и возвращает JSON-строку с ответом.
        # Параметры:
        #   system_prompt - системный промпт, определяющий роль агента
        #   user_prompt   - данные для анализа в JSON-формате
        # Возвращает:
        #   str - валидная JSON-строка с результатом работы модели
        # Исключения:
        #   Exception - при ошибках API, таймаутах или невалидном JSON в ответе

        logger.info("Agent [%s] starting with model %s", self.specialization, self.model)

        try:
            # Отправка запроса к API нейросети
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=int(os.getenv("AI_AGENT_MAX_TOKENS", "1536")),
                timeout=float(os.getenv("AI_AGENT_TIMEOUT_SECONDS", "45"))
            )

            # Извлекаем содержимое ответа
            raw_content = response.choices[0].message.content
            json_content = self._extract_json_content(raw_content)

            # Валидация JSON: проверяем, что модель вернула корректный JSON
            # Это критично, так как все модули ожидают JSON на вход
            try:
                json.loads(json_content)
            except json.JSONDecodeError as json_err:
                raise Exception(
                    "AgentClient JSON Validation Exception: model returned invalid JSON. "
                    "Response: " + str(raw_content)[:200] + "... Error: " + str(json_err)
                )

            logger.info("Agent [%s] completed successfully", self.specialization)
            return json_content

        except Exception as e:
            logger.error("Agent [%s] execution failed: %s", self.specialization, str(e))
            raise Exception("AgentClient Execution Exception: prompt execution failed - " + str(e))

    @staticmethod
    def _extract_json_content(raw_content: str) -> str:
        if not raw_content:
            return raw_content

        content = raw_content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        start = content.find("{")
        if start < 0:
            return content

        depth = 0
        in_string = False
        escape_next = False
        for index, char in enumerate(content[start:], start=start):
            if escape_next:
                escape_next = False
                continue
            if char == "\\" and in_string:
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return content[start:index + 1]

        return content[start:]
