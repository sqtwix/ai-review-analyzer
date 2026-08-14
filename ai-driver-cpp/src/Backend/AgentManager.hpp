#ifndef AGENTMANAGER_HPP
#define AGENTMANAGER_HPP

#include "AgentFactory.hpp"
class AgentManager {
    private:
        AgentFactory& agent_factory;
        std::string start_deepseek_pipeline(const std::string& user_prompt, const std::string& system_prompt);
        std::string start_sbergpt_pipeline(const std::string& user_prompt, const std::string& system_prompt);
        std::string start_qwenlocal_pipeline(const std::string& user_prompt, const std::string& system_prompt);
        std::pair<std::string, std::string> setup_prompts(const std::string& input);
    public:
        AgentManager(AgentFactory& agent_factory);
        ~AgentManager();
        
        std::string start(const std::string& model, const std::string& input);
}; 

#endif