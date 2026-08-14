#include "AgentFactory.hpp"
#include "AgentClient.hpp"
#include "BaseUrl.hpp"
#include <boost/exception/exception.hpp>
#include <cstdlib>
#include <dotenv.h>
#include <stdexcept>
#include <vector>

AgentFactory::AgentFactory() {}
AgentFactory::~AgentFactory() {}

std::list<AgentClient> AgentFactory::create_queue(const std::string& model) {
    std::list<AgentClient> result;
    std::vector<std::string> specializations {"qualitative-analyst",
        "synthesis-creator",
        "synthesis-summarizer"};
    dotenv::getenv(".env");

    BaseUrl deepseek_url = BaseUrl(
        std::getenv("DEEPSEEK_HOST"),
        std::getenv("DEEPSEEK_PORT"),
        std::getenv("DEEPSEEK_TARGET")
    );

    BaseUrl sbergpt_url = BaseUrl(
        std::getenv("SBERGPT_HOST"),
        std::getenv("SBERGPT_PORT"),
        std::getenv("SBERGPT_TARGET")
    );

    BaseUrl qwenlocal_url = BaseUrl(
        std::getenv("QWENLOCAL_HOST"),
        std::getenv("QWENLOCAL_PORT"),
        std::getenv("QWENLOCAL_TARGET")
    );

    if (model == "deepseek") {
        for (auto spec : specializations) {
            result.push_back(AgentClient(
                std::getenv("DEEPSEEK_API_KEY"),
                deepseek_url,
                "deepseek",
                spec));
        }
    } else if (model == "sbergpt") {
        for (auto spec : specializations) {
                        result.push_back(AgentClient(
                std::getenv("SBERGPT_API_KEY"),
                sbergpt_url,
                "sbergpt",
                spec));
        }
    } else if (model == "qwen") {
        for (auto spec : specializations) {
                        result.push_back(AgentClient(
                std::getenv("QWENLOCAL_API_KEY"),
                qwenlocal_url,
                "qwenlocal",
                spec));
        }
    } else {
        throw std::logic_error("Not an exisitng model type");
    }

    return result;
}