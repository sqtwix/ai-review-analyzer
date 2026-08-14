#include "AgentManager.hpp"
#include "AgentClient.hpp"
#include "AgentFactory.hpp"
#include <boost/json/object.hpp>
#include <boost/json/serializer.hpp>
#include <fstream>
#include <future>
#include <iterator>
#include <boost/json.hpp>

namespace json = boost::json;

AgentManager::AgentManager(AgentFactory& agent_factory) : agent_factory(agent_factory) {}
AgentFactory::~AgentFactory() {}

std::string AgentManager::start_deepseek_pipeline(const std::string& user_prompt, const std::string& system_prompt) {
    std::string result;
    std::list group = AgentManager::agent_factory.create_queue("deepseek");
    json::value val = json::parse(system_prompt);
    std::vector<std::string> system_prompts;

    auto start = group.begin();

    auto future_res_1 = std::async(std::launch::async, [&start, user_prompt]{
        return (*start).execute(user_prompt, "");
    });

    auto next = std::next(start, 1);

    auto future_res_2 = std::async(std::launch::async, [&next]{
        return (*next).execute("", "");
    });

    next = std::next(start, 2);

    auto future_res_3 = std::async(std::launch::async, [&next]{
        return (*next).execute("", "");
    });

    // Here we are gonna do some shit
    // with results that we get
    // we need to call .get() method
    // to get std::string from std::future
    // maybe, we do not need to use lambda functions
    // in std::async calls, but i think it is not
    // gonna do a lot of problems, if we gonna use it

    std::string res_1 = future_res_1.get();
    std::string res_2 = future_res_2.get();
    std::string res_3 = future_res_3.get();

    // After we get all three needed results
    // we can create a json structure, that we are
    // gonna send to our handler.

    // So when get_deepseek_data_analasys is called, 
    // the handler calls start() with "deepseek" model
    // and it is get results like as std::string but here we are
    // need to work like it s JSON kinda.

    // Also we will validate our service response
    // in controller, so i think we need to use JSON serialization
    // here

    return result;
}

std::string AgentManager::start_sbergpt_pipeline(const std::string& user_prompt, const std::string& system_prompt) {
    std::string result;
    std::list<AgentClient> group = AgentManager::agent_factory.create_queue("sbergpt");
    auto start = group.begin();

    auto future_res_1 = std::async(std::launch::async, [&start] {
        return (*start).execute("", "");
    });

    auto next = std::next(start, 1);

    auto future_res_2 = std::async(std::launch::async, [&next] {
        return (*next).execute("", "");
    });

    next = std::next(start, 2);

    auto future_res_3 = std::async(std::launch::async, [&next] {
        return (*next).execute("", "");
    });

    std::string res_1 = future_res_1.get();
    std::string res_2 = future_res_2.get();
    std::string res_3 = future_res_3.get();

    return result;
}

std::string AgentManager::start_qwenlocal_pipeline(const std::string& user_prompt, const std::string& system_prompt) {
    std::string result;
    std::list<AgentClient> group = AgentManager::agent_factory.create_queue("qwenlocal");
    auto start = group.begin();

    auto future_res_1 = std::async(std::launch::async, [&start]{
        return (*start).execute("", "");
    });

    auto next = std::next(start, 1);

    auto future_res_2 = std::async(std::launch::async, [&next]{
        return (*next).execute("", "");
    });

    next = std::next(start, 2);

    auto future_res_3 = std::async(std::launch::async, [&next]{
        return (*next).execute("", "");
    });

    std::string res_1 = future_res_1.get();
    std::string res_2 = future_res_2.get();
    std::string res_3 = future_res_3.get();

    return result;
}

std::pair<std::string, std::string> AgentManager::setup_prompts(const std::string& input) {
    std::pair<std::string, std::string> pair;
    std::ifstream s("system_prompts.json");
    std::string buf;
    std::string raw;

    if (!s.is_open()) 
        throw std::logic_error("Erro while openning file");

    while (std::getline(s, buf)) {
        raw += buf + "\n";
    }

    pair.first = input;
    pair.second = raw;

    return pair;
}

std::string AgentManager::start(const std::string& model, const std::string& input) {
    std::string result;
    auto data = AgentManager::setup_prompts(input);

    if (model == "deepseek")
        result = AgentManager::start_deepseek_pipeline(data.first, data.second);
    
    else if (model == "sbergpt")
        result = AgentManager::start_sbergpt_pipeline(data.first, data.second);

    else if (model == "qwenlocal")
        result = AgentManager::start_qwenlocal_pipeline(data.first, data.second);

    else {
        throw std::logic_error("Cannot create queue with model: " + model);
    }

    return result;
}