#ifndef AGENTCLIENT_HPP
#define AGENTCLIENT_HPP

#include <string>
#include "BaseUrl.hpp"

// Definition of AgentClient class

class AgentClient {
    private:
        std::string api_key;
        BaseUrl base_url;
        std::string agent_model;
        std::string specialization;

    public:
        AgentClient(
            const std::string& api_key,
            const BaseUrl& base_url,    // Using BaseUrl structure
                                        // because boost resolver, ssl-stream
                                        // and other stuff works with
                                        // host, port, target.
            const std::string& agent_model,
            const std::string& specialization
        );

        ~AgentClient();

        std::string execute(const std::string& system_prompt, const std::string& user_prompt); 
};

#endif