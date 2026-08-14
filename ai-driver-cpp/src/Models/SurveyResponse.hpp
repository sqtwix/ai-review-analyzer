#ifndef SURVEY_RESPONSE_HPP
#define SURVEY_RESPONSE_HPP

#include <string>

struct SurveyResponse {
    std::string student_id;
    std::string position_category;
    double usefulness_score;
    double practicality_score;
    double accessibility_score;
    double interaction_score;
    std::string preferred_format;
    bool is_detached;
    std::string motivation_comment; 
    std::string usefullness_comment;
    std::string applied_skills_comment; 
    std::string expected_effet; 
    std::string expected_effect_reason;
    std::string topics_to_exclude_comments;
    std::string topics_to_add_comment;
    std::string practicality_comment;
    std::string practice_tuning_comment;
    std::string practice_change_comment;
    std::string accessibility_comment;
    std::string logic_sequence_reason;
    std::string ask_question_comment;
    std::string ask_question_reason;
    std::string detachment_reason_comment;
    std::string involvement_comment;
    std::string interaction_comment;
    SurveyResponse() {
        this->student_id = "unknown";
        this->position_category = "Не указано";
        this->usefulness_score = 0.0f;
        this->practicality_score = 0.0f;
        this->accessibility_score = 0.0f;
        this->interaction_score = 0.0f; 
        this->preferred_format = 0.0f;
        this->is_detached = false;
    }
};

#endif