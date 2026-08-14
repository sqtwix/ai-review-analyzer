#ifndef COURSE_SURVEY_HPP
#define COURSE_SURVEY_HPP

#include <string>
#include <list>
#include "SurveyResponse.hpp"

struct CourseSurvey {
    std::string course_name;
    std::string period;
    int students_count;
    std::list<SurveyResponse> responses;
    CourseSurvey() {
        this->period = "Не указан";
        this->students_count = 0;
    }
};

#endif