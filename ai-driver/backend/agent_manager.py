from backend.agent_client import AgentClient
from backend.agent_factory import AgentFactory
import json
import logging
from pathlib import Path
import math
import statistics

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

    def _run_pipeline(self, input_data: str, model_type: str) -> str:
        try:
            req_data = json.loads(input_data)
            batch_id = req_data.get("batch_id", "default_batch")
            courses = req_data.get("courses", [])

            # Создаем очередь агентов
            agent_queue = self.agent_factory.create_queue(model_type)
            qual_analyst = agent_queue[0]       # qualitative-analyst
            synth_creator = agent_queue[1]      # synthesis-creator
            synth_summarizer = agent_queue[2]   # synthesis-summarizer

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

                # 2. Агрегация текстовых отзывов для LLM
                comments = []
                for idx, r in enumerate(responses):
                    student_comments = []
                    for field in [
                        "motivation_comment", "usefulness_comment", "applied_skills_comment", 
                        "expected_effect", "expected_effect_reason", "topics_to_exclude_comment", 
                        "topics_to_add_comment", "practicality_comment", "practice_tuning_comment", 
                        "practice_change_comment", "accessibility_comment", "logic_sequence_reason", 
                        "ask_questions_comment", "ask_questions_reason", "detachment_reason_comment", 
                        "involvement_comment", "interaction_comment"
                    ]:
                        val = r.get(field)
                        if val and str(val).strip():
                            student_comments.append(f"{field}: {str(val).strip()}")
                    if student_comments:
                        pos = r.get("position_category") or "Слушатель"
                        comments.append(f"[Слушатель {idx+1} ({pos})]:\n" + "\n".join(student_comments))
                
                aggregated_text = "\n\n".join(comments)

                # Шаг 1: Качественный анализ текстовых отзывов
                logger.info("[%s] Step 1: qualitative-analyst starting for course %s", model_type, course_name)
                qual_result_str = qual_analyst.execute(
                    self.system_prompts[0]["prompt"],
                    aggregated_text if aggregated_text else "Отзывы отсутствуют."
                )
                qual_result = json.loads(qual_result_str)

                # Шаг 2: Методический синтез и аналитическая записка
                logger.info("[%s] Step 2: synthesis-creator starting for course %s", model_type, course_name)
                creator_input = json.dumps({
                    "course_name": course_name,
                    "statistics": stats,
                    "validation_summary": validation_summary,
                    "score_counts": score_counts,
                    "metadata": metadata,
                    "comment_registry": comment_registry,
                    "processing_log": processing_log,
                    "quality_limitations": quality_limitations,
                    "text_analysis": qual_result
                }, ensure_ascii=False)
                creator_result_str = synth_creator.execute(
                    self.system_prompts[1]["prompt"],
                    creator_input
                )
                creator_result = json.loads(creator_result_str)

                # Шаг 3: Объединение результатов и генерация конкретных рекомендаций
                logger.info("[%s] Step 3: synthesis-summarizer starting for course %s", model_type, course_name)
                summarizer_input = json.dumps({
                    "course_name": course_name,
                    "period": period,
                    "students_count": total_responses,
                    "validation_summary": validation_summary,
                    "score_counts": score_counts,
                    "metadata": metadata,
                    "comment_registry": comment_registry,
                    "processing_log": processing_log,
                    "quality_limitations": quality_limitations,
                    "statistics": stats,
                    "position_distribution": pos_dist,
                    "preferred_formats": fmt_dist,
                    "analytical_report": creator_result.get("analytical_report", {}),
                    "dashboard_data": {
                        "correlation_matrix": corr_matrix,
                        "trend_data": trend_data,
                        "trend_source": trend_source,
                        "has_historical_periods": has_historical_periods
                    },
                    "text_analysis_raw": qual_result
                }, ensure_ascii=False)

                final_course_report_str = synth_summarizer.execute(
                    self.system_prompts[2]["prompt"],
                    summarizer_input
                )
                final_course_report = json.loads(final_course_report_str)

                # Добавляем в итоговый список
                # В зависимости от выдачи ИИ (массив или один объект) извлекаем результат
                deterministic_fields = {
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
                    }
                }

                if isinstance(final_course_report, dict):
                    if "courses_analysis" in final_course_report:
                        for item in final_course_report["courses_analysis"]:
                            if isinstance(item, dict):
                                item.update(deterministic_fields)
                            courses_analysis_results.append(item)
                    else:
                        final_course_report.update(deterministic_fields)
                        courses_analysis_results.append(final_course_report)
                elif isinstance(final_course_report, list):
                    for item in final_course_report:
                        if isinstance(item, dict):
                            item.update(deterministic_fields)
                        courses_analysis_results.append(item)

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
