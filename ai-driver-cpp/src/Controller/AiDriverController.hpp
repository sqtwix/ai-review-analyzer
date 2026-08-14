#ifndef AI_DRIVER_CONTROLLER_HPP
#define AI_DRIVER_CONTROLLER_HPP

#include <string>

class AiDriverController {
    public:
    AiDriverController();
    ~AiDriverController();

    void get_deepseek_data_analysis(const std::string& input_data);
    void get_sbergpt_data_analysis(const std::string& input_data);
    void get_qwen_local_data_analysis(const std::string& input_data);
    
};

#endif