using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace ApiCore.Models;

/*
Моедль для регистрации нового пользователя. 
Содержит обязательные поля "username", "password", "email".
Пароль должен быть не менее 8 символов.
*/

public class RegisterRequest
{
    [Required]
    [StringLength(100, MinimumLength = 2, ErrorMessage = "Имя должно содержать от 2 до 100 символов.")]
    [RegularExpression(@".*\S.*", ErrorMessage = "Имя не может состоять только из пробелов.")]
    [JsonPropertyName("username")]
    public string Username { get; set; } = string.Empty;

    [Required]
    [EmailAddress(ErrorMessage = "Невалидный формат почты")]
    [StringLength(254, ErrorMessage = "Email слишком длинный.")]
    [JsonPropertyName("email")]
    public string Email { get; set; } = string.Empty;

    [Required]
    [StringLength(128, MinimumLength = 8, ErrorMessage = "Пароль должен содержать от 8 до 128 символов.")]
    [JsonPropertyName("password")]
    public string Password { get; set; } = string.Empty;
}
