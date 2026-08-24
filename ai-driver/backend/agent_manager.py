from backend.agent_client import AgentClient
from backend.agent_factory import AgentFactory
import json
import logging
import os
from pathlib import Path
import math
import statistics
import time
from collections import Counter, defaultdict

BASE_DIR = Path(__file__).resolve().parent
PATH_TO_JSON = BASE_DIR / "system_prompts.json"

logger = logging.getLogger(__name__)

COMMENT_FIELD_LABELS = {
    "motivation_comment": "Почему слушатель решил пройти программу",
    "usefulness_comment": "Актуальные темы и причины полезности",
    "applied_skills_comment": "Навыки, применимые в работе",
    "expected_effect": "Ожидаемый эффект от обучения",
    "expected_effect_reason": "Причины ожидаемого эффекта",
    "topics_to_exclude_comment": "Темы к исключению",
    "topics_to_add_comment": "Темы к добавлению",
    "practicality_comment": "Комментарий о практической части",
    "practice_tuning_comment": "Что требует большей практической настройки",
    "practice_change_comment": "Что изменить в организации практики",
    "accessibility_comment": "Комментарий о доступности материала",
    "logic_sequence_reason": "Пояснение по логике и последовательности",
    "ask_questions_comment": "Возможность задать вопросы",
    "ask_questions_reason": "Пояснение по вопросам",
    "detachment_reason_comment": "Причины отстраненности",
    "involvement_comment": "Что повысило бы вовлеченность",
    "interaction_comment": "Комментарий о взаимодействии с КУ",
}

class AgentManager:
    EVIDENCE_KINDS = {"positive", "problem", "suggestion", "neutral"}
    SENTIMENTS = {"positive", "neutral", "negative"}
    PRIORITIES = {"High", "Medium", "Low"}
    PRIORITY_RANK = {"Low": 1, "Medium": 2, "High": 3}
    EXPLICIT_SUGGESTION_FIELDS = (
        "topics_to_add_comment",
        "topics_to_exclude_comment",
    )
    GENERIC_TOPIC_ALIASES = {
        "motivation_comment": {"motivation", "мотивация"},
        "usefulness_comment": {"usefulness", "полезность"},
        "involvement_comment": {"involvement", "вовлеченность", "вовлечённость"},
        "practice_change_comment": {"practice_change", "practice change"},
    }
    NON_SUBSTANTIVE_COMMENTS = {
        "-", "—", "нет", "не было", "не знаю", "без комментариев",
        "затрудняюсь ответить", "все хорошо", "всё хорошо", "все отлично",
        "всё отлично", "none", "no", "n/a",
    }
    NO_ACTION_MARKERS = (
        "никакие", "ничего", "не требуется", "не требуются", "исключать не",
        "все темы были актуальны", "все актуальны", "всё актуально",
        "все полезны", "всё полезно", "все прекрасно", "всё прекрасно",
        "курс очень органичен", "нет предложений", "только добавить",
        "таких тем нет", "все нужное", "всё нужное", "программа полная",
        "программа составлена", "курс содержит достаточное количество",
        "нет таких", "не таких", "программу дополнять не надо",
        "достаточно полно",
    )
    NO_EXCLUSION_PATTERNS = (
        ("оставить", "все"),
        ("оставить", "всё"),
        ("все", "полез"),
        ("всё", "полез"),
        ("все", "нуж"),
        ("всё", "нуж"),
        ("все", "актуал"),
        ("всё", "актуал"),
        ("все", "важ"),
        ("всё", "важ"),
    )
    NO_ADDITION_PATTERNS = (
        ("все", "тем", "рассмотр"),
        ("всё", "тем", "рассмотр"),
        ("программ", "достаточ"),
        ("дополн", "не треб"),
        ("все", "актуал"),
        ("всё", "актуал"),
        ("все", "достаточ"),
        ("всё", "достаточ"),
    )
    PLACEHOLDER_MARKERS = (
        "короткое название темы",
        "детальное описание сути темы",
        "текстовый вывод",
        "тема 1 для исключения",
        "метрику x",
        "метрику y",
        "скопируй полностью",
        "объект улучшения",
    )
    EVIDENCE_RESPONSE_SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "required": ["responses"],
        "properties": {
            "responses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["response_id", "sentiment", "evidence"],
                    "properties": {
                        "response_id": {"type": "string"},
                        "sentiment": {
                            "type": "string",
                            "enum": ["positive", "neutral", "negative"],
                        },
                        "evidence": {
                            "type": "array",
                            "maxItems": 3,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["field", "quote", "topic", "kind", "priority"],
                                "properties": {
                                    "field": {"type": "string"},
                                    "quote": {"type": "string"},
                                    "topic": {"type": "string"},
                                    "kind": {
                                        "type": "string",
                                        "enum": ["positive", "problem", "suggestion", "neutral"],
                                    },
                                    "priority": {
                                        "type": "string",
                                        "enum": ["High", "Medium", "Low"],
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    }

    def __init__(self, agent_factory: AgentFactory):
        try:
            self.agent_factory = agent_factory
            with open(PATH_TO_JSON, "r", encoding="utf-8") as f:
                self.system_prompts = json.load(f)
        except Exception as e:
            raise Exception("Agent Manager Initialization Error: " + str(e))

    def start_deepseek_processing(self, input_data: str) -> str:
        return self._run_pipeline(input_data, "deepseek")

    def start_sbergpt_processing(self, input_data: str) -> str:
        return self._run_pipeline(input_data, "sbergpt")

    def start_qwen_local_processing(self, input_data: str) -> str:
        return self._run_pipeline(input_data, "qwen_local")

    def _calculate_stats(self, scores) -> dict:
        scores = self._valid_scores(scores)
        if not scores:
            return {
                "average": 0.0, "median": 0.0, "std_dev": 0.0,
                "distribution": {"low": 0.0, "mid": 0.0, "high": 0.0}
            }
        avg = sum(scores) / len(scores)
        med = statistics.median(scores)
        std = statistics.stdev(scores) if len(scores) > 1 else 0.0
        
        low_cnt = sum(1 for s in scores if s <= 3)
        mid_cnt = sum(1 for s in scores if 4 <= s <= 7)
        high_cnt = sum(1 for s in scores if s >= 8)
        
        total = len(scores)
        return {
            "average": round(avg, 2),
            "median": round(med, 1),
            "std_dev": round(std, 2),
            "distribution": {
                "low": round((low_cnt / total) * 100, 1),
                "mid": round((mid_cnt / total) * 100, 1),
                "high": round((high_cnt / total) * 100, 1)
            }
        }

    def _valid_scores(self, scores) -> list[float]:
        valid_scores = []
        for score in scores:
            if score is None:
                continue
            try:
                numeric_score = float(score)
            except Exception:
                continue
            if 1.0 <= numeric_score <= 10.0:
                valid_scores.append(numeric_score)
        return valid_scores

    def _calculate_correlation(self, x, y) -> float:
        pairs = []
        for xi, yi in zip(x, y):
            if xi is None or yi is None:
                continue
            try:
                x_num = float(xi)
                y_num = float(yi)
            except Exception:
                continue
            if 1.0 <= x_num <= 10.0 and 1.0 <= y_num <= 10.0:
                pairs.append((x_num, y_num))

        if len(pairs) < 2:
            return 0.0
        x = [pair[0] for pair in pairs]
        y = [pair[1] for pair in pairs]
        mean_x = sum(x) / len(x)
        mean_y = sum(y) / len(y)
        
        num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        den_x = sum((xi - mean_x)**2 for xi in x)
        den_y = sum((yi - mean_y)**2 for yi in y)
        
        if den_x == 0 or den_y == 0:
            return 0.0
        return round(num / math.sqrt(den_x * den_y), 2)

    def _build_validation_summary(self, responses) -> dict:
        valid_count = 0
        missing_count = 0
        invalid_count = 0

        for response in responses:
            issues_by_field = {
                issue.get("field"): issue.get("status")
                for issue in (response.get("score_validation_issues") or [])
                if isinstance(issue, dict)
            }
            for field in ["usefulness_score", "practicality_score", "accessibility_score", "interaction_score"]:
                value = response.get(field)
                status = issues_by_field.get(field)
                if status == "missing" or (value is None and status != "invalid"):
                    missing_count += 1
                elif status == "invalid":
                    invalid_count += 1
                elif self._valid_scores([value]):
                    valid_count += 1
                else:
                    invalid_count += 1

        total_issues = missing_count + invalid_count
        return {
            "valid_count": valid_count,
            "missing_count": missing_count,
            "invalid_count": invalid_count,
            "total_issues": total_issues
        }

    def _build_score_counts(self, responses) -> dict:
        counts = {str(score): 0 for score in range(1, 11)}
        for response in responses:
            values = self._valid_scores([
                response.get("usefulness_score"),
                response.get("practicality_score"),
                response.get("accessibility_score"),
                response.get("interaction_score")
            ])
            if not values:
                continue
            overall_score = int(round(sum(values) / len(values)))
            overall_score = max(1, min(10, overall_score))
            counts[str(overall_score)] += 1
        return counts

    def _build_comment_registry(self, responses) -> list[dict]:
        total = len(responses)
        registry = []
        for field, label in COMMENT_FIELD_LABELS.items():
            rows = []
            for index, response in enumerate(responses, start=1):
                value = response.get(field)
                if value and str(value).strip():
                    rows.append(response.get("student_id") or f"row_{index}")

            registry.append({
                "question_id": field,
                "label": label,
                "non_empty_count": len(rows),
                "coverage": round((len(rows) / total) * 100, 1) if total else 0.0,
                "rows": rows,
            })
        return registry

    def _build_metadata(self, fmt_dist) -> dict:
        preferred_format = max(fmt_dist, key=fmt_dist.get) if fmt_dist else None
        missing_fields = []
        if not preferred_format:
            missing_fields.append("education_form")
        missing_fields.extend(["teachers", "confirmed_dates"])
        return {
            "education_form": preferred_format,
            "teachers": [],
            "dates_confirmed": False,
            "missing_fields": missing_fields
        }

    def _build_processing_log(self, fallback_used: bool, validation_summary: dict, comment_registry: list[dict]) -> list[dict]:
        return [
            {"step": "file_parsing", "status": "completed", "message": "Файлы прочитаны, персональные данные маскированы на уровне api-core."},
            {"step": "score_validation", "status": "completed", "message": f"Валидных оценок: {validation_summary['valid_count']}; пропусков: {validation_summary['missing_count']}; ошибок: {validation_summary['invalid_count']}."},
            {"step": "comment_registry", "status": "completed", "message": f"Проверено открытых полей: {len(comment_registry)}; непустые ответы сохранены как ссылки на строки."},
            {"step": "text_analysis", "status": "skipped" if fallback_used else "completed", "message": "Модель недоступна; качественные выводы не сформированы." if fallback_used else "Качественный анализ выполнен моделью."},
        ]

    def _build_quality_limitations(self, fallback_used: bool, metadata: dict, comment_registry: list[dict]) -> list[str]:
        limitations = []
        if fallback_used:
            limitations.append("Качественные темы, тональность, цитаты и рекомендации не сформированы, потому что модель недоступна.")
        if metadata.get("missing_fields"):
            limitations.append("Общая часть отчета содержит неподтвержденные реквизиты: " + ", ".join(metadata["missing_fields"]) + ".")
        if len(comment_registry) < 19:
            limitations.append(f"В текущем контракте найдено {len(comment_registry)} открытых полей; для требования 19 комментариев нужны оставшиеся колонки во входном файле или расширение маппинга.")
        return limitations

    def _validate_qualitative_result(self, result: dict, source_text: str, response_count: int) -> None:
        serialized = json.dumps(result, ensure_ascii=False).lower()
        if any(marker in serialized for marker in self.PLACEHOLDER_MARKERS):
            raise ValueError("qualitative model output contains prompt placeholders")

        normalized_source = " ".join(source_text.lower().split())
        topics = result.get("top_topics", [])
        if not isinstance(topics, list) or len(topics) > 7:
            raise ValueError("qualitative model output contains an unsupported number of topics")

        for topic in topics:
            frequency = topic.get("frequency")
            if not isinstance(frequency, int) or frequency < 1 or frequency > response_count:
                raise ValueError("qualitative model output contains an unsupported topic frequency")

        for quote in result.get("quotes", []):
            quote_text = " ".join(str(quote.get("quote", "")).lower().split())
            if not quote_text or quote_text not in normalized_source:
                raise ValueError("qualitative model output contains a quote absent from source data")
            frequency = quote.get("frequency")
            if not isinstance(frequency, int) or frequency < 1 or frequency > response_count:
                raise ValueError("qualitative model output contains an unsupported quote frequency")

        sentiment = result.get("sentiment", {})
        sentiment_values = [float(sentiment.get(key, 0)) for key in ("positive", "neutral", "negative")]
        if any(value < 0 or value > 100 for value in sentiment_values):
            raise ValueError("qualitative model sentiment is outside the supported range")
        sentiment_total = sum(sentiment_values)
        if abs(sentiment_total - 100.0) > 0.2:
            raise ValueError("qualitative model sentiment does not sum to 100 percent")
        if any(not self._is_supported_percentage(value, response_count) for value in sentiment_values):
            raise ValueError("qualitative model sentiment is not supported by the response count")

        for problem in result.get("key_problems", []):
            frequency_percent = float(problem.get("frequency_percent", -1))
            if not self._is_supported_percentage(frequency_percent, response_count):
                raise ValueError("qualitative model problem frequency is not supported by the response count")
            if problem.get("severity") not in {"High", "Medium", "Low"}:
                raise ValueError("qualitative model problem severity is unsupported")

    @staticmethod
    def _is_supported_percentage(value: float, response_count: int) -> bool:
        if response_count <= 0 or value < 0 or value > 100:
            return False
        nearest_count = round((value / 100.0) * response_count)
        expected = round((nearest_count / response_count) * 100.0, 1)
        return abs(value - expected) <= 0.2

    def _reject_prompt_placeholders(self, result: dict, stage: str) -> None:
        serialized = json.dumps(result, ensure_ascii=False).lower()
        if any(marker in serialized for marker in self.PLACEHOLDER_MARKERS):
            raise ValueError(f"{stage} model output contains prompt placeholders")

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(str(value or "").casefold().split())

    @staticmethod
    def _chunk_items(items: list, size: int) -> list[list]:
        return [items[index:index + size] for index in range(0, len(items), size)]

    def _is_substantive_comment(self, value: str) -> bool:
        normalized = self._normalize_text(value).strip(" .,!?:;()[]{}")
        return len(normalized) >= 3 and normalized not in self.NON_SUBSTANTIVE_COMMENTS

    def _is_evidence_candidate(self, field: str, value: str) -> bool:
        if not self._is_substantive_comment(value):
            return False
        normalized = self._normalize_text(value)
        if field in self.EXPLICIT_SUGGESTION_FIELDS:
            if any(marker in normalized for marker in self.NO_ACTION_MARKERS):
                return False
            field_patterns = (
                self.NO_EXCLUSION_PATTERNS
                if field == "topics_to_exclude_comment"
                else self.NO_ADDITION_PATTERNS
            )
            words = set(normalized.split())
            if field == "topics_to_exclude_comment" and normalized in {"все", "всё"}:
                return False
            return not any(
                all(
                    part in words if part in {"все", "всё"} else part in normalized
                    for part in pattern
                )
                for pattern in field_patterns
            )
        return True

    def _normalize_evidence_topic(self, field: str, topic: str) -> str:
        normalized = self._normalize_text(topic)
        aliases = {
            self._normalize_text(field),
            self._normalize_text(field.removesuffix("_comment")),
            self._normalize_text(COMMENT_FIELD_LABELS.get(field, "")),
            "тема",
            "topic",
            *self.GENERIC_TOPIC_ALIASES.get(field, set()),
        }
        return COMMENT_FIELD_LABELS.get(field, topic) if normalized in aliases else topic

    def _prepare_evidence_records(self, responses: list[dict]) -> list[dict]:
        records = []
        used_ids = set()
        for index, response in enumerate(responses, start=1):
            response_id = str(response.get("student_id") or f"row_{index}").strip()
            if response_id in used_ids:
                response_id = f"{response_id}_{index}"
            used_ids.add(response_id)
            raw_fields = {
                field: str(response.get(field) or "").strip()
                for field in COMMENT_FIELD_LABELS
                if str(response.get(field) or "").strip()
            }
            ordered_fields = [
                field for field in self.EXPLICIT_SUGGESTION_FIELDS
                if field in raw_fields
            ] + [
                field for field in raw_fields
                if field not in self.EXPLICIT_SUGGESTION_FIELDS
            ]
            fields = {field: raw_fields[field] for field in ordered_fields}
            if fields:
                records.append({
                    "response_id": response_id,
                    "position_category": response.get("position_category") or "Не указано",
                    "fields": fields,
                    "evidence_fields": sorted(
                        (
                            field for field, value in fields.items()
                            if self._is_evidence_candidate(field, value)
                        ),
                        key=lambda field: (field not in self.EXPLICIT_SUGGESTION_FIELDS, ordered_fields.index(field)),
                    ),
                })
        return records

    def _validate_evidence_chunk(self, result: dict, records: list[dict]) -> tuple[list[dict], dict[str, str], int]:
        source_by_id = {record["response_id"]: record for record in records}
        accepted = []
        sentiments = {}
        rejected = 0
        seen_atoms = set()
        model_responses = result.get("responses")
        if model_responses is None and result.get("response_id"):
            model_responses = [result]
        elif isinstance(model_responses, dict):
            model_responses = [model_responses]
        if not isinstance(model_responses, list):
            raise ValueError("evidence output does not contain a responses array")

        for model_response in model_responses:
            if not isinstance(model_response, dict):
                rejected += 1
                continue
            response_id = str(model_response.get("response_id") or "")
            source = source_by_id.get(response_id)
            if not source:
                rejected += 1
                continue

            sentiment = model_response.get("sentiment")
            if sentiment in self.SENTIMENTS and response_id not in sentiments:
                sentiments[response_id] = sentiment
            elif sentiment not in self.SENTIMENTS:
                rejected += 1

            evidence_items = model_response.get("evidence")
            if not isinstance(evidence_items, list):
                rejected += 1
                continue

            for item in evidence_items[:3]:
                if not isinstance(item, dict):
                    rejected += 1
                    continue
                field = str(item.get("field") or "")
                quote = str(item.get("quote") or "").strip()
                topic = str(item.get("topic") or "").strip()
                kind = item.get("kind")
                priority = item.get("priority")
                source_value = source["fields"].get(field)
                topic = self._normalize_evidence_topic(field, topic)
                if field in self.EXPLICIT_SUGGESTION_FIELDS:
                    kind = "suggestion"
                normalized_quote = self._normalize_text(quote)
                normalized_source = self._normalize_text(source_value or "")
                serialized = self._normalize_text(json.dumps(item, ensure_ascii=False))

                is_valid = (
                    source_value is not None
                    and field in source.get("evidence_fields", source["fields"].keys())
                    and len(normalized_quote) >= 3
                    and normalized_quote in normalized_source
                    and self._is_substantive_comment(quote)
                    and 2 <= len(topic) <= 120
                    and kind in self.EVIDENCE_KINDS
                    and priority in self.PRIORITIES
                    and not any(marker in serialized for marker in self.PLACEHOLDER_MARKERS)
                )
                if not is_valid:
                    rejected += 1
                    continue

                atom_key = (response_id, field, normalized_quote, self._normalize_text(topic), kind)
                if atom_key in seen_atoms:
                    rejected += 1
                    continue
                seen_atoms.add(atom_key)
                accepted.append({
                    "response_id": response_id,
                    "field": field,
                    "quote": quote,
                    "topic": topic,
                    "kind": kind,
                    "priority": priority,
                })

        return accepted, sentiments, rejected

    def _request_evidence(self, client: AgentClient, records: list[dict]) -> tuple[list[dict], dict[str, str], int]:
        raw = client.execute(
            self.system_prompts[0]["prompt"],
            json.dumps({"responses": records}, ensure_ascii=False),
            max_tokens=int(os.getenv("AI_EVIDENCE_MAX_TOKENS", "768")),
            timeout=float(os.getenv("AI_EVIDENCE_TIMEOUT_SECONDS", "120")),
            response_schema=self.EVIDENCE_RESPONSE_SCHEMA,
        )
        return self._validate_evidence_chunk(json.loads(raw), records)

    def _request_single_with_retry(
        self,
        client: AgentClient,
        record: dict,
        model_type: str,
        response_index: int,
        response_total: int,
        retry_delay: float,
    ) -> tuple[list[dict], dict[str, str], int, bool, int]:
        for attempt in range(2):
            try:
                evidence, sentiments, rejected = self._request_evidence(client, [record])
                return evidence, sentiments, rejected, False, attempt + 1
            except Exception as error:
                if attempt == 0:
                    logger.warning(
                        "[%s] Evidence response %s/%s failed, retrying in %.0fs: %s",
                        model_type, response_index, response_total, retry_delay, str(error)
                    )
                    readiness_wait = max(
                        retry_delay,
                        float(os.getenv("AI_MODEL_READINESS_TIMEOUT_SECONDS", "180")),
                    )
                    wait_until_ready = getattr(client, "wait_until_ready", None)
                    if callable(wait_until_ready):
                        wait_until_ready(readiness_wait)
                    else:
                        time.sleep(retry_delay)
                    continue
                logger.warning(
                    "[%s] Evidence response %s/%s failed after retry: %s",
                    model_type, response_index, response_total, str(error)
                )
        return [], {}, 0, True, 2

    def _extract_evidence(self, client: AgentClient, records: list[dict], model_type: str) -> dict:
        accepted = []
        sentiments = {}
        rejected = 0
        failed_chunks = 0
        model_requests = 0
        fallback_responses = 0
        retry_delay = max(0.0, float(os.getenv("AI_EVIDENCE_RETRY_DELAY_SECONDS", "30")))
        batch_size = max(1, min(4, int(os.getenv("AI_EVIDENCE_BATCH_SIZE", "1"))))
        chunks = self._chunk_items(records, batch_size)

        for chunk_index, chunk in enumerate(chunks, start=1):
            logger.info(
                "[%s] Evidence batch %s/%s starting: responses=%s",
                model_type, chunk_index, len(chunks), len(chunk)
            )
            batch_evidence = []
            batch_sentiments = {}
            batch_rejected = 0
            batch_failed = False
            try:
                model_requests += 1
                batch_evidence, batch_sentiments, batch_rejected = self._request_evidence(client, chunk)
            except Exception as error:
                batch_failed = True
                logger.warning(
                    "[%s] Evidence batch %s/%s failed; splitting into single responses: %s",
                    model_type, chunk_index, len(chunks), str(error)
                )

            accepted.extend(batch_evidence)
            sentiments.update({
                response_id: sentiment
                for response_id, sentiment in batch_sentiments.items()
                if response_id not in sentiments
            })
            rejected += batch_rejected

            missing_records = [
                record for record in chunk
                if record["response_id"] not in batch_sentiments
            ]
            if batch_failed:
                missing_records = chunk

            for record in missing_records:
                fallback_responses += 1
                response_index = records.index(record) + 1
                single_evidence, single_sentiments, single_rejected, failed, attempts = (
                    self._request_single_with_retry(
                        client,
                        record,
                        model_type,
                        response_index,
                        len(records),
                        retry_delay,
                    )
                )
                model_requests += attempts
                accepted.extend(single_evidence)
                sentiments.update({
                    response_id: sentiment
                    for response_id, sentiment in single_sentiments.items()
                    if response_id not in sentiments
                })
                rejected += single_rejected
                if failed:
                    failed_chunks += 1

            logger.info(
                "[%s] Evidence batch %s/%s completed: accepted=%s rejected=%s fallback=%s",
                model_type,
                chunk_index,
                len(chunks),
                len(batch_evidence),
                batch_rejected,
                len(missing_records),
            )

        return {
            "evidence": accepted,
            "sentiments": sentiments,
            "rejected": rejected,
            "chunks_total": len(records),
            "chunks_failed": failed_chunks,
            "model_requests": model_requests,
            "fallback_responses": fallback_responses,
            "batch_size": batch_size,
        }

    def _aggregate_evidence(self, extraction: dict, total_responses: int) -> dict:
        evidence = extraction["evidence"]
        topic_groups = defaultdict(list)
        quote_groups = defaultdict(list)
        problem_groups = defaultdict(list)
        suggestion_groups = defaultdict(list)

        for item in evidence:
            topic_key = self._normalize_text(item["topic"])
            topic_groups[topic_key].append(item)
            quote_groups[self._normalize_text(item["quote"])].append(item)
            if item["kind"] == "problem":
                problem_groups[topic_key].append(item)
            if item["kind"] == "suggestion":
                suggestion_groups[topic_key].append(item)

        def evidence_info(items: list[dict]) -> dict:
            rows = sorted({item["response_id"] for item in items})
            questions = sorted({item["field"] for item in items})
            return {
                "rows": rows,
                "questions": questions,
                "coverage": round((len(rows) / total_responses) * 100.0, 1) if total_responses else 0.0,
            }

        sorted_topics = sorted(
            topic_groups.values(),
            key=lambda items: (-len({item["response_id"] for item in items}), self._normalize_text(items[0]["topic"]))
        )[:7]
        top_topics = []
        for items in sorted_topics:
            rows = {item["response_id"] for item in items}
            representative = items[0]
            top_topics.append({
                "topic": representative["topic"],
                "description": f"Подтверждено ответами {len(rows)} слушателей.",
                "frequency": len(rows),
                "evidence": evidence_info(items),
            })

        key_problems = []
        for items in sorted(
            problem_groups.values(),
            key=lambda group: -len({item["response_id"] for item in group})
        )[:7]:
            rows = {item["response_id"] for item in items}
            representative = items[0]
            priority = max(items, key=lambda item: self.PRIORITY_RANK[item["priority"]])["priority"]
            key_problems.append({
                "problem": representative["topic"],
                "frequency_percent": round((len(rows) / total_responses) * 100.0, 1),
                "severity": priority,
                "evidence": evidence_info(items),
            })

        quotes = []
        for items in sorted(
            quote_groups.values(),
            key=lambda group: (-len({item["response_id"] for item in group}), self._normalize_text(group[0]["quote"]))
        )[:12]:
            rows = {item["response_id"] for item in items}
            quotes.append({
                "quote": items[0]["quote"],
                "frequency": len(rows),
                "evidence": evidence_info(items),
            })

        sentiment_counts = Counter(extraction["sentiments"].values())
        classified = sum(sentiment_counts.values())
        sentiment = {
            key: round((sentiment_counts[key] / classified) * 100.0, 1) if classified else 0.0
            for key in ("positive", "neutral", "negative")
        }

        recommendations = []
        recommendation_groups = {**problem_groups}
        for key, items in suggestion_groups.items():
            recommendation_groups.setdefault(key, []).extend(items)
        for items in sorted(
            recommendation_groups.values(),
            key=lambda group: -len({item["response_id"] for item in group})
        )[:7]:
            rows = {item["response_id"] for item in items}
            representative = items[0]
            priority = max(items, key=lambda item: self.PRIORITY_RANK[item["priority"]])["priority"]
            percent = round((len(rows) / total_responses) * 100.0, 1)
            recommendations.append({
                "target": representative["topic"],
                "action_item": (
                    f"Рассмотреть подтвержденную обратную связь по теме «{representative['topic']}» "
                    f"({len(rows)} из {total_responses}, {percent}%)."
                ),
                "priority": priority,
                "evidence": evidence_info(items),
            })

        return {
            "top_topics": top_topics,
            "sentiment": sentiment,
            "key_problems": key_problems,
            "quotes": quotes,
            "recommendations": recommendations,
            "classified_responses": classified,
            "suggestion_groups": suggestion_groups,
        }

    def _build_grounded_report(
        self,
        course_name: str,
        period: str,
        total_responses: int,
        stats: dict,
        validation_summary: dict,
        fmt_dist: dict,
        text_analysis: dict,
        extraction: dict,
    ) -> dict:
        preferred_format = max(fmt_dist, key=fmt_dist.get) if fmt_dist else "не указан"
        preferred_count = fmt_dist.get(preferred_format, 0)
        preferred_percent = round((preferred_count / total_responses) * 100.0, 1) if total_responses else 0.0
        added_evidence = [
            item for item in extraction["evidence"]
            if item["field"] == "topics_to_add_comment"
        ]
        excluded_evidence = [
            item for item in extraction["evidence"]
            if item["field"] == "topics_to_exclude_comment"
        ]

        def grouped_counts(items: list[dict]) -> list[tuple[str, int]]:
            groups = defaultdict(set)
            labels = {}
            for item in items:
                key = self._normalize_text(item["topic"])
                groups[key].add(item["response_id"])
                labels[key] = item["topic"]
            return sorted(
                ((labels[key], len(rows)) for key, rows in groups.items()),
                key=lambda pair: (-pair[1], self._normalize_text(pair[0]))
            )

        added_topics = [
            {"topic": topic, "count": count}
            for topic, count in grouped_counts(added_evidence)
        ]
        unwanted_topics = [
            f"{topic} (N={count})"
            for topic, count in grouped_counts(excluded_evidence)
        ]
        problem_summary = "; ".join(
            f"{problem['problem']}: {len(problem['evidence']['rows'])} из {total_responses}"
            for problem in text_analysis["key_problems"][:3]
        ) or "Подтвержденные проблемы не выделены."
        topic_summary = "; ".join(
            f"{topic['topic']}: N={topic['frequency']}"
            for topic in text_analysis["top_topics"][:3]
        ) or "Подтвержденные темы не выделены."

        return {
            "section1_general_info": (
                f"Курс: {course_name}\nПериод проведения: {period}\n"
                f"Анкет обработано: {total_responses}.\n"
                f"Валидных оценок: {validation_summary['valid_count']}; "
                f"пропусков: {validation_summary['missing_count']}; "
                f"ошибочных оценок: {validation_summary['invalid_count']}."
            ),
            "section2_key_criteria": {
                "usefulness_summary": f"Средняя полезность: {stats['usefulness']['average']}/10.",
                "practicality_summary": f"Средняя практико-ориентированность: {stats['practicality']['average']}/10. {problem_summary}",
                "accessibility_summary": f"Средняя доступность: {stats['accessibility']['average']}/10.",
                "interaction_summary": f"Среднее взаимодействие с КУ: {stats['interaction']['average']}/10.",
                "involvement_summary": (
                    f"Вовлечены {stats['involvement']['involved_percent']}%; "
                    f"отстранены {stats['involvement']['detached_percent']}%."
                ),
            },
            "section3_suggestions": {
                "unwanted_topics": unwanted_topics,
                "added_topics": added_topics,
                "preferred_format_summary": (
                    f"Формат «{preferred_format}» выбрали {preferred_count} из {total_responses} "
                    f"({preferred_percent}%)."
                ),
            },
            "section4_trajectory": {
                "further_implementation_needed": (
                    f"Решение требует владельца программы; фактическая средняя полезность составляет "
                    f"{stats['usefulness']['average']}/10."
                ),
                "student_selection_correction": "Подтвержденных данных для изменения отбора слушателей недостаточно.",
                "added_topics_recommendation": (
                    "; ".join(f"Рассмотреть «{item['topic']}» (N={item['count']})" for item in added_topics)
                    or "Подтвержденных предложений о добавлении тем нет."
                ),
                "hours_correction_needed": "Подтвержденные замечания: " + problem_summary,
                "format_correction_needed": (
                    f"Распределение форматов зафиксировано; лидирует «{preferred_format}» "
                    f"({preferred_count} из {total_responses})."
                ),
                "conclusions": [
                    topic_summary,
                    f"Тональность классифицирована для {text_analysis['classified_responses']} из {total_responses} анкет.",
                ],
            },
        }

    def _run_pipeline(self, input_data: str, model_type: str) -> str:
        try:
            req_data = json.loads(input_data)
            batch_id = req_data.get("batch_id", "default_batch")
            courses = req_data.get("courses", [])

            # Создаем очередь агентов
            agent_queue = self.agent_factory.create_queue(model_type)
            qual_analyst = agent_queue[0]

            courses_analysis_results = []

            for course in courses:
                course_name = course.get("course_name", "Неизвестный курс")
                period = course.get("period", "Неизвестный период")
                responses = course.get("responses", [])

                if not responses:
                    continue

                # 1. Программный расчет статистик
                usefulness_scores = [r.get("usefulness_score", 0.0) for r in responses]
                practicality_scores = [r.get("practicality_score", 0.0) for r in responses]
                accessibility_scores = [r.get("accessibility_score", 0.0) for r in responses]
                interaction_scores = [r.get("interaction_score", 0.0) for r in responses]
                validation_summary = self._build_validation_summary(responses)
                score_counts = self._build_score_counts(responses)
                comment_registry = self._build_comment_registry(responses)
                
                detached_count = sum(1 for r in responses if r.get("is_detached", False))
                total_responses = len(responses)
                involved_count = total_responses - detached_count

                stats = {
                    "usefulness": self._calculate_stats(usefulness_scores),
                    "practicality": self._calculate_stats(practicality_scores),
                    "accessibility": self._calculate_stats(accessibility_scores),
                    "interaction": self._calculate_stats(interaction_scores),
                    "involvement": {
                        "detached_percent": round((detached_count / total_responses) * 100, 1),
                        "involved_percent": round((involved_count / total_responses) * 100, 1),
                        "yes_count": detached_count,
                        "no_count": involved_count
                    }
                }

                # Расчет распределения должностей и форматов
                pos_dist = {}
                fmt_dist = {}
                for r in responses:
                    pos = r.get("position_category") or "Не указано"
                    fmt = r.get("preferred_format") or "Не указано"
                    pos_dist[pos] = pos_dist.get(pos, 0) + 1
                    fmt_dist[fmt] = fmt_dist.get(fmt, 0) + 1
                metadata = self._build_metadata(fmt_dist)
                processing_log = self._build_processing_log(False, validation_summary, comment_registry)
                quality_limitations = self._build_quality_limitations(False, metadata, comment_registry)

                # Расчет корреляции
                corr_matrix = {
                    "Полезность": {
                        "Полезность": 1.0,
                        "Практика": self._calculate_correlation(usefulness_scores, practicality_scores),
                        "Доступность": self._calculate_correlation(usefulness_scores, accessibility_scores),
                        "Взаимодействие": self._calculate_correlation(usefulness_scores, interaction_scores)
                    },
                    "Практика": {
                        "Полезность": self._calculate_correlation(practicality_scores, usefulness_scores),
                        "Практика": 1.0,
                        "Доступность": self._calculate_correlation(practicality_scores, accessibility_scores),
                        "Взаимодействие": self._calculate_correlation(practicality_scores, interaction_scores)
                    },
                    "Доступность": {
                        "Полезность": self._calculate_correlation(accessibility_scores, usefulness_scores),
                        "Практика": self._calculate_correlation(accessibility_scores, practicality_scores),
                        "Доступность": 1.0,
                        "Взаимодействие": self._calculate_correlation(accessibility_scores, interaction_scores)
                    },
                    "Взаимодействие": {
                        "Полезность": self._calculate_correlation(interaction_scores, usefulness_scores),
                        "Практика": self._calculate_correlation(interaction_scores, practicality_scores),
                        "Доступность": self._calculate_correlation(interaction_scores, accessibility_scores),
                        "Взаимодействие": 1.0
                    }
                }

                # Подготовка трендов по нескольким периодам
                batch_periods = []
                for c_idx, c_item in enumerate(courses):
                    c_period = c_item.get("period") or f"Поток {c_idx+1}"
                    c_resps = c_item.get("responses", [])
                    c_u = self._valid_scores([r.get("usefulness_score") for r in c_resps])
                    c_p = self._valid_scores([r.get("practicality_score") for r in c_resps])
                    c_a = self._valid_scores([r.get("accessibility_score") for r in c_resps])
                    c_i = self._valid_scores([r.get("interaction_score") for r in c_resps])
                    c_total = len(c_resps)
                    c_detached = sum(1 for r in c_resps if r.get("is_detached", False))
                    c_involvement = round(((c_total - c_detached) / c_total) * 100, 1) if c_total else 0.0
                    
                    batch_periods.append({
                        "period": c_period,
                        "usefulness_avg": round(sum(c_u)/len(c_u), 1) if c_u else 0.0,
                        "practicality_avg": round(sum(c_p)/len(c_p), 1) if c_p else 0.0,
                        "accessibility_avg": round(sum(c_a)/len(c_a), 1) if c_a else 0.0,
                        "interaction_avg": round(sum(c_i)/len(c_i), 1) if c_i else 0.0,
                        "involvement_avg": c_involvement
                    })

                if len(batch_periods) > 1:
                    trend_data = batch_periods
                    trend_source = "historical"
                    has_historical_periods = True
                else:
                    trend_data = []
                    trend_source = "unavailable"
                    has_historical_periods = False

                records = self._prepare_evidence_records(responses)
                if records:
                    extraction = self._extract_evidence(qual_analyst, records, model_type)
                    if not extraction["evidence"]:
                        raise ValueError("evidence pipeline produced no validated evidence")
                else:
                    extraction = {
                        "evidence": [],
                        "sentiments": {},
                        "rejected": 0,
                        "chunks_total": 0,
                        "chunks_failed": 0,
                        "model_requests": 0,
                        "fallback_responses": 0,
                        "batch_size": 0,
                    }

                aggregated = self._aggregate_evidence(extraction, total_responses)
                analytical_report = self._build_grounded_report(
                    course_name,
                    period,
                    total_responses,
                    stats,
                    validation_summary,
                    fmt_dist,
                    aggregated,
                    extraction,
                )
                processing_log[-1] = {
                    "step": "text_analysis",
                    "status": "completed" if extraction["chunks_failed"] == 0 else "partial",
                    "message": (
                        f"Evidence-first обработка: анкет {extraction['chunks_total']}; "
                        f"ошибок обработки {extraction['chunks_failed']}; "
                        f"принято evidence {len(extraction['evidence'])}; "
                        f"отклонено evidence {extraction['rejected']}; "
                        f"тональность классифицирована для {aggregated['classified_responses']} "
                        f"из {total_responses} анкет; запросов к модели {extraction['model_requests']}; "
                        f"fallback на одиночную обработку {extraction['fallback_responses']}."
                    ),
                }
                if extraction["rejected"]:
                    quality_limitations.append(
                        f"Отклонено неподтвержденных или некорректных evidence: {extraction['rejected']}."
                    )
                if extraction["chunks_failed"]:
                    quality_limitations.append(
                        f"Не обработано анкет: {extraction['chunks_failed']} из {extraction['chunks_total']}."
                    )
                if aggregated["classified_responses"] < total_responses:
                    quality_limitations.append(
                        f"Тональность классифицирована для {aggregated['classified_responses']} "
                        f"из {total_responses} анкет."
                    )

                text_analysis = {
                    key: aggregated[key]
                    for key in ("top_topics", "sentiment", "key_problems", "quotes", "recommendations")
                }
                courses_analysis_results.append({
                    "course_name": course_name,
                    "period": period,
                    "students_count": total_responses,
                    "statistics": stats,
                    "position_distribution": pos_dist,
                    "preferred_formats": fmt_dist,
                    "validation_summary": validation_summary,
                    "score_counts": score_counts,
                    "metadata": metadata,
                    "comment_registry": comment_registry,
                    "processing_log": processing_log,
                    "quality_limitations": quality_limitations,
                    "dashboard_data": {
                        "correlation_matrix": corr_matrix,
                        "trend_data": trend_data,
                        "trend_source": trend_source,
                        "has_historical_periods": has_historical_periods
                    },
                    "analytical_report": analytical_report,
                    "text_analysis": text_analysis,
                })

            final_batch_response = {
                "batch_id": batch_id,
                "courses_analysis": courses_analysis_results
            }

            logger.info("[%s] Pipeline completed successfully for batch %s", model_type, batch_id)
            return json.dumps(final_batch_response, ensure_ascii=False)

        except json.JSONDecodeError as e:
            raise Exception("[%s] Pipeline JSON Error: invalid JSON from agent - %s" % (model_type, str(e)))
        except Exception as e:
            raise Exception("[%s] Pipeline Processing Error: %s" % (model_type, str(e)))
