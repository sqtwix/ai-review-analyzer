#ifndef AGENTFACTORY_HPP
#define AGENTFACTORY_HPP

#include <list>
#include <string> 
#include "AgentClient.hpp"

class AgentFactory {
    public:
    AgentFactory();
    ~AgentFactory();

    // Idk if it really need to return
    // queue as STL type, int python
    // realization it return just basic list
    // so i think we can use std::list<AgentClient>
    // instead. Also, we are not using queue idea, becouse we
    // want to make parallel executing, so lets use std::list 
    // instead lol.

    // setup bsaic std::list for this

    std::list<AgentClient> create_queue(const std::string& model);
};

#endif