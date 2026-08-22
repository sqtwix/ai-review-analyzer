from backend.agent_manager import AgentManager
from schemas.analysis_response import (
    AnalysisResponse, CourseAnalysisResult, CourseStatistics, NumericMetric, Distribution,
    InvolvementMetric, AnalyticalReport, Section2KeyCriteria, Section3Suggestions, AddedTopic,
    Section4Trajectory, DashboardData, TrendPoint, TextAnalysis, TopicInfo, SentimentInfo,
    ProblemInfo, QuoteInfo, RecommendationInfo
)
from schemas.analysis_request import AnalysisRequest
from fastapi import HTTPException
from fastapi.responses import JSONResponse
import json
import logging
import math
import statistics

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

class AgentController:
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager

    def get_deepseek_data_analysis(self, input_data: AnalysisRequest):
        try:
            self._validate_request(input_data)
            logger.info("Executing DeepSeek agent pipeline processing...")
            ai_responses = self.agent_manager.start_deepseek_processing(
                input_data=input_data.model_dump_json()
            )
            validated_response = AnalysisResponse.model_validate_json(ai_responses)
            validated_response = self._enrich_and_complete_response(validated_response, input_data)
            return JSONResponse(
                status_code=200,
                content=validated_response.model_dump()
            )
        except Exception as e:
            logger.warning("DeepSeek processing failed or timed out: %s. Falling back to programmatic analysis.", str(e))
            fallback_data = self._generate_programmatic_analysis(input_data)
            return JSONResponse(
                status_code=200,
                content=fallback_data
            )

    def get_sbergpt_data_analysis(self, input_data: AnalysisRequest):
        try:
            self._validate_request(input_data)
            logger.info("Executing SberGPT agent pipeline processing...")
            ai_responses = self.agent_manager.start_sbergpt_processing(
                input_data=input_data.model_dump_json()
            )
            validated_response = AnalysisResponse.model_validate_json(ai_responses)
            validated_response = self._enrich_and_complete_response(validated_response, input_data)
            return JSONResponse(
                status_code=200,
                content=validated_response.model_dump()
            )
        except Exception as e:
            logger.warning("SberGPT processing failed or timed out: %s. Falling back to programmatic analysis.", str(e))
            fallback_data = self._generate_programmatic_analysis(input_data)
            return JSONResponse(
                status_code=200,
                content=fallback_data
            )

    def get_qwen_local_data_analysis(self, input_data: AnalysisRequest):
        try:
            self._validate_request(input_data)
            logger.info("Executing Qwen Local agent pipeline processing...")
            ai_responses = self.agent_manager.start_qwen_local_processing(
                input_data=input_data.model_dump_json()
            )
            validated_response = AnalysisResponse.model_validate_json(ai_responses)
            validated_response = self._enrich_and_complete_response(validated_response, input_data)
            return JSONResponse(
                status_code=200,
                content=validated_response.model_dump()
            )
        except Exception as e:
            logger.warning("Qwen Local processing failed or timed out: %s. Falling back to programmatic analysis.", str(e))
            fallback_data = self._generate_programmatic_analysis(input_data)
            return JSONResponse(
                status_code=200,
                content=fallback_data
            )

    def _enrich_and_complete_response(self, response: AnalysisResponse, input_data: AnalysisRequest) -> AnalysisResponse:
        """
        No extra row completion is required since all statistical criteria and textual reports 
        are fully processed during the pipeline loops. Return response directly.
        """
        return response

    def _validate_request(self, input_data: AnalysisRequest):
        errors: list = []

        if not input_data.courses:
            errors.append("В запросе отсутствуют курсы для анализа")

        for course_idx, course in enumerate(input_data.courses):
            if not course.responses:
                errors.append(
                    f"В курсе '{course.course_name}' отсутствуют анкеты слушателей"
                )
                continue

            for resp_idx, resp in enumerate(course.responses):
                for field in ["usefulness_score", "practicality_score", "accessibility_score", "interaction_score"]:
                    val = getattr(resp, field, None)
                    if val is None:
                        continue
                    try:
                        num_val = float(val)
                    except Exception:
                        setattr(resp, field, None)
                        continue
                    if num_val < 1.0 or num_val > 10.0:
                        setattr(resp, field, None)

        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))

        return input_data

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

    def _calculate_stats_programmatic(self, scores) -> dict:
        valid_scores = self._valid_scores(scores)
        if not valid_scores:
            return {
                "average": 0.0, "median": 0.0, "std_dev": 0.0,
                "distribution": {"low": 0.0, "mid": 0.0, "high": 0.0}
            }
        avg = sum(valid_scores) / len(valid_scores)
        med = statistics.median(valid_scores)
        std = statistics.stdev(valid_scores) if len(valid_scores) > 1 else 0.0
        
        low_cnt = sum(1 for s in valid_scores if s <= 3)
        mid_cnt = sum(1 for s in valid_scores if 4 <= s <= 7)
        high_cnt = sum(1 for s in valid_scores if s >= 8)
        
        total = len(valid_scores)
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

    def _calculate_correlation_programmatic(self, x, y) -> float:
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
                for issue in (getattr(response, "score_validation_issues", None) or [])
                if isinstance(issue, dict)
            }
            for field in ["usefulness_score", "practicality_score", "accessibility_score", "interaction_score"]:
                value = getattr(response, field, None)
                status = issues_by_field.get(field)
                if status == "missing" or (value is None and status != "invalid"):
                    missing_count += 1
                elif status == "invalid":
                    invalid_count += 1
                elif value is not None:
                    valid_count += 1

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
                response.usefulness_score,
                response.practicality_score,
                response.accessibility_score,
                response.interaction_score
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
                value = getattr(response, field, None)
                if value and str(value).strip():
                    rows.append(getattr(response, "student_id", None) or f"row_{index}")

            registry.append({
                "question_id": field,
                "label": label,
                "non_empty_count": len(rows),
                "coverage": round((len(rows) / total) * 100, 1) if total else 0.0,
                "rows": rows,
            })
        return registry

    def _build_metadata(self, course, fmt_dist) -> dict:
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

    def _generate_programmatic_analysis(self, input_data: AnalysisRequest) -> dict:
        """
        Программный анализатор в качестве фоллбека. Рассчитывает только детерминированные
        статистики по фактическим валидным оценкам. Качественные выводы не фабрикуются.
        """
        courses_analysis = []

        for course in input_data.courses:
            course_name = course.course_name
            period = course.period or "Июль 2026"
            responses = course.responses
            total_responses = len(responses)

            if total_responses == 0:
                continue

            # Количественные массивы. None/ошибки исключаются из статистики.
            usefulness = [r.usefulness_score for r in responses]
            practicality = [r.practicality_score for r in responses]
            accessibility = [r.accessibility_score for r in responses]
            interaction = [r.interaction_score for r in responses]
            validation_summary = self._build_validation_summary(responses)
            score_counts = self._build_score_counts(responses)
            comment_registry = self._build_comment_registry(responses)
            
            detached_cnt = sum(1 for r in responses if r.is_detached)
            involved_cnt = total_responses - detached_cnt

            stats = {
                "usefulness": self._calculate_stats_programmatic(usefulness),
                "practicality": self._calculate_stats_programmatic(practicality),
                "accessibility": self._calculate_stats_programmatic(accessibility),
                "interaction": self._calculate_stats_programmatic(interaction),
                "involvement": {
                    "detached_percent": round((detached_cnt / total_responses) * 100, 1),
                    "involved_percent": round((involved_cnt / total_responses) * 100, 1),
                    "yes_count": detached_cnt,
                    "no_count": involved_cnt
                }
            }

            # Распределение категорий и форматов
            pos_dist = {}
            fmt_dist = {}
            for r in responses:
                pos = r.position_category or "Не указано"
                fmt = r.preferred_format or "Не указано"
                pos_dist[pos] = pos_dist.get(pos, 0) + 1
                fmt_dist[fmt] = fmt_dist.get(fmt, 0) + 1
            metadata = self._build_metadata(course, fmt_dist)
            processing_log = self._build_processing_log(True, validation_summary, comment_registry)
            quality_limitations = self._build_quality_limitations(True, metadata, comment_registry)

            # Pearson Correlation
            corr_matrix = {
                "Полезность": {
                    "Полезность": 1.0,
                    "Практика": self._calculate_correlation_programmatic(usefulness, practicality),
                    "Доступность": self._calculate_correlation_programmatic(usefulness, accessibility),
                    "Взаимодействие": self._calculate_correlation_programmatic(usefulness, interaction)
                },
                "Практика": {
                    "Полезность": self._calculate_correlation_programmatic(practicality, usefulness),
                    "Практика": 1.0,
                    "Доступность": self._calculate_correlation_programmatic(practicality, accessibility),
                    "Взаимодействие": self._calculate_correlation_programmatic(practicality, interaction)
                },
                "Доступность": {
                    "Полезность": self._calculate_correlation_programmatic(accessibility, usefulness),
                    "Практика": self._calculate_correlation_programmatic(accessibility, practicality),
                    "Доступность": 1.0,
                    "Взаимодействие": self._calculate_correlation_programmatic(accessibility, interaction)
                },
                "Взаимодействие": {
                    "Полезность": self._calculate_correlation_programmatic(interaction, usefulness),
                    "Практика": self._calculate_correlation_programmatic(interaction, practicality),
                    "Доступность": self._calculate_correlation_programmatic(interaction, accessibility),
                    "Взаимодействие": 1.0
                }
            }

            # Без реальных исторических периодов тренд не строится.
            trend_data = []

            sec1_text = (
                f"Курс: {course_name}\n"
                f"Период проведения: {period}\n"
                f"Анкет обработано: {total_responses}.\n"
                f"Валидных оценок: {validation_summary['valid_count']}; "
                f"пропусков: {validation_summary['missing_count']}; "
                f"ошибочных оценок: {validation_summary['invalid_count']}."
            )
            
            avg_u = stats["usefulness"]["average"]
            avg_p = stats["practicality"]["average"]
            avg_a = stats["accessibility"]["average"]
            avg_i = stats["interaction"]["average"]
            inv_pct = stats['involvement']['involved_percent']
            
            pref_fmt_str = f"Наиболее предпочтительным форматом является {max(fmt_dist, key=fmt_dist.get) if fmt_dist else 'очное обучение'}."

            analytical_report = {
                "section1_general_info": sec1_text,
                "section2_key_criteria": {
                    "usefulness_summary": f"Средняя полезность по валидным оценкам: {avg_u}/10. Пропуски и ошибки исключены из расчета.",
                    "practicality_summary": f"Средняя практико-ориентированность по валидным оценкам: {avg_p}/10. Пропуски и ошибки исключены из расчета.",
                    "accessibility_summary": f"Средняя доступность по валидным оценкам: {avg_a}/10. Пропуски и ошибки исключены из расчета.",
                    "interaction_summary": f"Среднее взаимодействие с КУ по валидным оценкам: {avg_i}/10. Пропуски и ошибки исключены из расчета.",
                    "involvement_summary": f"Вовлеченность рассчитана по фактическим ответам: {inv_pct}% вовлечены, {stats['involvement']['detached_percent']}% отстранены."
                },
                "section3_suggestions": {
                    "unwanted_topics": [],
                    "added_topics": [],
                    "preferred_format_summary": f"{pref_fmt_str} Текстовые предложения не сформированы: модель недоступна."
                },
                "section4_trajectory": {
                    "further_implementation_needed": "Не сформировано: модель недоступна. Используйте только количественные метрики fallback.",
                    "student_selection_correction": "Не сформировано: модель недоступна.",
                    "added_topics_recommendation": "Не сформировано: модель недоступна.",
                    "hours_correction_needed": "Не сформировано: модель недоступна.",
                    "format_correction_needed": "Не сформировано: модель недоступна.",
                    "conclusions": [
                        "Fallback сформировал только детерминированные расчеты.",
                        "Качественные темы, цитаты и рекомендации не сформированы без доступной модели."
                    ]
                }
            }

            sentiment = {
                "positive": 0.0,
                "neutral": 0.0,
                "negative": 0.0
            }

            courses_analysis.append({
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
                "analytical_report": analytical_report,
                "dashboard_data": {
                    "correlation_matrix": corr_matrix,
                    "trend_data": trend_data,
                    "trend_source": "unavailable",
                    "has_historical_periods": False
                },
                "text_analysis": {
                    "top_topics": [],
                    "sentiment": sentiment,
                    "key_problems": [],
                    "quotes": [],
                    "recommendations": []
                }
            })

        return {
            "batch_id": input_data.batch_id,
            "courses_analysis": courses_analysis
        }
