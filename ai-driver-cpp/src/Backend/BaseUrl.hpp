#ifndef BASEURL_HPP
#define BASEURL_HPP

#include <string>

struct BaseUrl {
    std::string host;
    std::string port;
    std::string target;
    BaseUrl() {}
    BaseUrl(const std::string& host, const std::string& port, const std::string& target) : host(host), port(port), target(target) {}
};

#endif