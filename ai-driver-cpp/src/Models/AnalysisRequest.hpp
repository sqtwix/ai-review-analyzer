#ifndef ANALYSIS_REQUEST_HPP
#define ANALYSIS_REQUEST_HPP

#include <string>
#include "CourseSurvey.hpp"
#include <list>

struct AnalyasisRequest {
    std::string batch_str;
    std::list<CourseSurvey> courses;
    AnalyasisRequest() {}
};

#endif 