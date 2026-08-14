#include "AgentClient.hpp"

// Including Boost Libraries

#include <boost/beast/core.hpp>
#include <boost/beast/ssl.hpp>
#include <boost/beast/http.hpp>
#include <boost/beast/version.hpp>
#include <boost/json.hpp>
#include <string>

namespace beast = boost::beast;         // Common Boost.Beast types
namespace http = beast::http;           // HTTP-specific types
namespace net = boost::asio;            // Networking (Asio)
namespace ssl = boost::asio::ssl;       // SSL/TLS
namespace json = boost::json;           // JSON handling
using tcp = boost::asio::ip::tcp;       // TCP networking

AgentClient::AgentClient(
    const std::string& api_key,
    const BaseUrl& base_url,
    const std::string& agent_model,
    const std::string& specialization
) : api_key(api_key), 
    base_url(base_url),
    agent_model(agent_model), 
    specialization(specialization) {}

AgentClient::~AgentClient() {}

std::string AgentClient::execute(const std::string& system_prompt, const std::string& user_prompt) {
    std::string result;
    net::io_context ioc;
    ssl::context ctx{ ssl::context::sslv23_client };
    
    ctx.set_default_verify_paths();
    ctx.set_verify_mode(ssl::verify_peer);

    beast::ssl_stream<beast::tcp_stream> stream { ioc, ctx};

    if (!SSL_set_tlsext_host_name(stream.native_handle(), base_url.host.c_str()))
        throw beast::system_error {
            beast::error_code {
                static_cast<int>(::ERR_get_error()), net::error::get_ssl_category()
            }
        };

    tcp::resolver resolver { ioc };
    auto const results = resolver.resolve(base_url.host, base_url.port);
    beast::get_lowest_layer(stream).connect(results);
    stream.handshake(ssl::stream_base::client);

    json::array messages;
    messages.push_back({{"role", "user"}, {"content", system_prompt + user_prompt}});
    
    json::object body;
    body["model"] = agent_model;
    body["messages"] = messages;

    std::string body_str = json::serialize(body);

    http::request<http::string_body> req { http::verb::post, base_url.target, 11 };
    req.set(http::field::host, base_url.host);
    req.set(http::field::user_agent, BOOST_BEAST_VERSION_STRING);
    req.set(http::field::authorization, "Bearer " + api_key);
    req.set(http::field::content_type, "application/json");
    req.set(http::field::accept, "application/json");
    req.body() = body_str;
    req.prepare_payload();

    {
        http::request<http::string_body> masked_req = req;
        masked_req.set(http::field::authorization, "Bearer ***********************");
        masked_req.set("OpenAI-Organization", "***********************");
    }

    http::write(stream, req);
    
    beast::flat_buffer buffer; 
    http::response<http::string_body> res;
    http::read(stream, buffer, res);

    beast::error_code ec;
    stream.shutdown();
    if (ec == net::error::eof || ec == ssl::error::stream_truncated)
        ec.assign(0, ec.category());
    if (ec)
        throw beast::system_error { ec };

    auto parsed = json::parse(res.body());

    if (parsed.as_object().if_contains("choices")) {
        auto& choices = parsed.at("choices").as_array();
        if (!choices.empty()) {
            auto& msg = choices[0].as_object().at("message").as_object();
            if (msg.if_contains("content")) {
                result = std::string(msg.at("content").as_string().c_str());
            }
        }
        return "[No content find in choices]";
    }

    else if (parsed.as_object().if_contains("error")) {
        auto& err = parsed.at("error").as_object();
        return "[Api Error] " + std::string(err.at("message").as_string().c_str());
    }
    else {
        return "[Unexpected API response " + res.body() + "]";
    }

    return result;
}