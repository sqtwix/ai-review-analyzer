from fastapi import FastAPI, APIRouter
import os
import logging
import httpx
from fastapi.responses import JSONResponse

from backend.agent_client import AgentClient
from backend.agent_factory import AgentFactory
from backend.agent_manager import AgentManager
from controllers.agent_controller import AgentController
from routes import setup_routes

# ========================= Main Application =========================

# Настройка логирования для отслеживания работы всех модулей
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="Agents API",
    description="Документация к AgentsAPI API. Поддерживает DeepSeek, SberGPT и локальный Qwen.",
    version="1.0.0",
    swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"}
)

# Инициализация компонентов системы
# AgentFactory создает агентов для разных провайдеров
# AgentManager управляет конвейером последовательной обработки
# AgentController обрабатывает HTTP-запросы и валидирует данные
agent_factory = AgentFactory()
agent_manager = AgentManager(agent_factory=agent_factory)
agent_controller = AgentController(agent_manager=agent_manager)

# Регистрация маршрутов с префиксом /agents
app.include_router(setup_routes(agent_controller=agent_controller), prefix="/agents")

@app.get("/health", include_in_schema=False)
def health():
    return {"status": "healthy"}


@app.get("/ready", include_in_schema=False)
def readiness():
    local_ai_enabled = os.getenv("LOCAL_AI_ENABLED", "").strip().lower() == "true"
    providers = {
        "deepseek": {"configured": bool(os.getenv("DEEPSEEK_API_KEY", "").strip())},
        "sbergpt": {"configured": bool(os.getenv("SBERGPT_API_KEY", "").strip())},
        "qwen_local": {"enabled": local_ai_enabled, "available": False},
    }

    if local_ai_enabled:
        health_url = os.getenv("QWEN_LOCAL_URL", "http://localhost:8080/v1").rstrip("/")
        if health_url.endswith("/v1"):
            health_url = health_url[:-3]
        try:
            providers["qwen_local"]["available"] = httpx.get(
                health_url + "/health", timeout=2.0
            ).is_success
        except (httpx.HTTPError, ValueError):
            pass

    model_available = (
        providers["deepseek"]["configured"]
        or providers["sbergpt"]["configured"]
        or providers["qwen_local"]["available"]
    )
    payload = {
        "status": "ready",
        "model_available": model_available,
        "providers": providers,
    }
    return JSONResponse(payload, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
