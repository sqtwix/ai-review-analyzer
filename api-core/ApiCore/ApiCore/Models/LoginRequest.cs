using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace ApiCore.Models;

public class LoginRequest
{
    [Required]
    [EmailAddress]
    [StringLength(254)]
    [JsonPropertyName("email")]
    public string Email { get; set; } = string.Empty;

    [Required]
    [StringLength(128, MinimumLength = 1)]
    [JsonPropertyName("password")]
    public string Password { get; set; } = string.Empty;
}
