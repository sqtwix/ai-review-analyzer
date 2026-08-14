cmake_minimum_required(VERSION 3.26)
project(AiDriverService)

include(FetchContent)

add_executable(AiDriverService main.cpp)

find_package(Boost REQUIRED COMPONENTS json)
find_package(OpenSSL REQUIRED)

target_sources(AiDriverService
    PUBLIC

    src/Backend/AgentClient.hpp
    src/Backend/AgentFactory.hpp
    src/Backend/AgentManager.hpp
    
    src/Backend/AgentClient.cpp
    src/Backend/AgentFactory.cpp
    src/Backend/AgentManager.cpp

    src/Controller/AiDriverController.hpp
    src/Controller/AiDriverController.cpp
)

FetchContent_Declare(
    pistache
    GIT_REPOSITORY https://github.com/pistacheio/pistache.git
)

FetchContent_Declare(pistache)

FetchContent_Declare(
  dotenv
  GIT_REPOSITORY https://github.com/laserpants/dotenv-cpp.git
  GIT_TAG        master
)

FetchContent_MakeAvailable(dotenv)

target_link_libraries(AiDriverService
    PRIVATE 
    dotenv
    pistache
    Boost::boost 
    Boost::json
    OpenSSL::SSL 
    OpenSSL::Crypto
)