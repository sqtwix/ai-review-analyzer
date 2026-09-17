using ApiCore.Services;
using ApiCore.Models;
using ApiCore.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;

namespace ApiCore.Controllers;


[ApiController]
[Route("api/v1/analysis")]
public class AnalysisController : ControllerBase
{
    private const int MaxUploadFileCount = 20;
    private const long MaxTotalUploadBytes = 50L * 1024 * 1024;
    private const long MaxRequestBodyBytes = 52L * 1024 * 1024;
    private const int MaxUploadFileNameLength = 200;

    private static readonly HashSet<string> AllowedUploadExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".csv", ".xlsx", ".xls", ".zip"
    };
    private static readonly HashSet<string> AllowedModelTypes = new(StringComparer.OrdinalIgnoreCase)
    {
        "deepseek", "gigachat", "sbergpt", "qwen_local", "qwen", "local"
    };

    private readonly AnalysisService _analysisService;
    private readonly AppDbContext _context;
    private readonly IServiceScopeFactory _serviceScopeFactory;
    private readonly ReportsService _reportsService;
    private readonly IHttpClientFactory _httpClientFactory;

    public AnalysisController(
        AnalysisService analysisService,
        AppDbContext context,
        IServiceScopeFactory serviceScopeFactory,
        ReportsService reportsService,
        IHttpClientFactory httpClientFactory)
    {
        _analysisService = analysisService;
        _context = context;
        _serviceScopeFactory = serviceScopeFactory;
        _reportsService = reportsService;
        _httpClientFactory = httpClientFactory;
    }

    [HttpGet("availability")]
    public async Task<IActionResult> GetAvailability()
    {
        try
        {
            var response = await _httpClientFactory.CreateClient("AiDriverStatus").GetAsync("ready");
            var payload = await response.Content.ReadAsStringAsync();
            return new ContentResult
            {
                StatusCode = (int)response.StatusCode,
                Content = payload,
                ContentType = "application/json; charset=utf-8"
            };
        }
        catch (HttpRequestException)
        {
            return StatusCode(StatusCodes.Status503ServiceUnavailable, new
            {
                status = "unavailable",
                model_available = false,
                message = "Сервис качественного анализа недоступен."
            });
        }
        catch (TaskCanceledException)
        {
            return StatusCode(StatusCodes.Status503ServiceUnavailable, new
            {
                status = "unavailable",
                model_available = false,
                message = "Проверка доступности модели превысила лимит времени."
            });
        }
    }

    [HttpPost("upload")]
    [EnableRateLimiting("uploads")]
    [RequestSizeLimit(MaxRequestBodyBytes)]
    [RequestFormLimits(MultipartBodyLengthLimit = MaxRequestBodyBytes)]
    public async Task<IActionResult> UploadFiles(
        [FromForm] List<IFormFile> userResponseFiles,    // Массив файлов с реальными отзывами/анкетами
        [FromForm] string modelType = "qwen_local")
    {
        // 1. Быстрая валидация (Критерий ТЗ: Обработка ошибок)
        if (userResponseFiles == null || !userResponseFiles.Any())
            return BadRequest(new { error = "Необходимо загрузить хотя бы один файл с отзывами пользователей." });

        if (userResponseFiles.Count > MaxUploadFileCount)
        {
            return BadRequest(new { error = $"За один запуск можно загрузить не более {MaxUploadFileCount} файлов." });
        }

        var totalUploadBytes = userResponseFiles.Sum(file => file.Length);
        if (totalUploadBytes > MaxTotalUploadBytes)
        {
            return BadRequest(new { error = "Суммарный размер файлов не должен превышать 50 МБ." });
        }

        modelType = modelType?.Trim().ToLowerInvariant() ?? string.Empty;
        if (!AllowedModelTypes.Contains(modelType))
        {
            return BadRequest(new { error = "Неподдерживаемая ИИ-модель. Допускаются deepseek, gigachat и qwen_local." });
        }

        var invalidFiles = userResponseFiles
            .Where(file => file.Length == 0
                || file.FileName.Length > MaxUploadFileNameLength
                || !AllowedUploadExtensions.Contains(Path.GetExtension(file.FileName)))
            .Select(file => Path.GetFileName(file.FileName))
            .ToArray();
        if (invalidFiles.Length > 0)
        {
            return BadRequest(new
            {
                error = $"Пустые, неподдерживаемые или имеющие слишком длинное имя файлы: {string.Join(", ", invalidFiles)}. Допускаются .csv, .xlsx, .xls и .zip; имя — до 200 символов."
            });
        }

        var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
        if (string.IsNullOrEmpty(userIdClaim) || !Guid.TryParse(userIdClaim, out var userId))
        {
            return Unauthorized(new { error = "Пользователь не авторизован." });
        }

        // 2. Генерируем уникальный ID для этой задачи анализа
        var taskId = Guid.NewGuid().ToString();

        // Создаем временную папку для сохранения файлов в пределах запроса
        var tempDir = Path.Combine(Directory.GetCurrentDirectory(), "temp_uploads", taskId);
        Directory.CreateDirectory(tempDir);

        var userResponsePaths = new List<string>();
        var usedFileNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var file in userResponseFiles)
        {
            var safeFileName = Path.GetFileName(file.FileName);
            if (string.IsNullOrWhiteSpace(safeFileName))
            {
                return BadRequest(new { error = "Имя загруженного файла некорректно." });
            }

            var uniqueFileName = safeFileName;
            var duplicateIndex = 1;
            while (!usedFileNames.Add(uniqueFileName))
            {
                uniqueFileName = $"{Path.GetFileNameWithoutExtension(safeFileName)}_{duplicateIndex++}{Path.GetExtension(safeFileName)}";
            }
            var path = Path.Combine(tempDir, uniqueFileName);
            using (var stream = new FileStream(path, FileMode.Create))
            {
                await file.CopyToAsync(stream);
            }
            userResponsePaths.Add(path);
        }

        // Сохраняем информацию об отчете в базу данных
        var courseName = FileParser.ExtractCourseName(userResponseFiles[0].FileName);
        var report = new AnalysisReport
        {
            Id = taskId,
            UserId = userId,
            CourseName = courseName,
            Status = "Processing",
            CreatedAt = DateTime.UtcNow
        };
        _context.AnalysisReports.Add(report);
        await _context.SaveChangesAsync();

        AnalysisService.UpdateTaskProgress(
            taskId,
            "Processing",
            "accepted",
            1,
            "Файлы загружены и поставлены в очередь на серверную проверку.");

        // 3. Отдаем парсинг и отправку в фоновый сервис БЕЗ await, чтобы не блокировать фронтенд
        // Используем IServiceScopeFactory, чтобы scoped-зависимости (такие как AppDbContext) не уничтожались при завершении HTTP-запроса
        _ = Task.Run(async () =>
        {
            using var scope = _serviceScopeFactory.CreateScope();
            var scopedService = scope.ServiceProvider.GetRequiredService<AnalysisService>();
            await scopedService.ProcessAnalysisAsync(taskId, userId, userResponsePaths, modelType, tempDir);
        });

        // Возвращаем фронту ID задачи. Фронт начнет слушать WebSocket/SignalR с этим ID
        return Accepted(new
        {
            task_id = taskId,
            message = "Файлы опросов успешно прошли первичную валидацию и приняты в обработку ИИ-агентами."
        });
    }

    [HttpGet("status/{taskId}")]
    public async Task<IActionResult> GetStatus(string taskId)
    {
        var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
        if (string.IsNullOrEmpty(userIdClaim) || !Guid.TryParse(userIdClaim, out var userId))
        {
            return Unauthorized(new { error = "Пользователь не авторизован." });
        }

        var report = await _context.AnalysisReports
            .FirstOrDefaultAsync(r => r.Id == taskId && r.UserId == userId);

        if (report != null)
        {
            AnalysisService.TaskTracker.TryGetValue(taskId, out var progress);
            CourseBatchAnalysisResult? result = null;
            if (!string.IsNullOrEmpty(report.ResultJson))
            {
                result = System.Text.Json.JsonSerializer.Deserialize<CourseBatchAnalysisResult>(
                    report.ResultJson, 
                    new System.Text.Json.JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                );
            }

            return Ok(new
            {
                status = report.Status,
                result = result,
                error = report.Error,
                stage = progress?.Stage ?? (report.Status == "Completed" ? "completed" : report.Status == "Failed" ? "failed" : "accepted"),
                stage_index = progress?.StageIndex ?? (report.Status == "Completed" ? 5 : 1),
                total_stages = progress?.TotalStages ?? 5,
                stage_message = progress?.Message ?? (report.Status == "Completed" ? "Отчёт сформирован и сохранён." : "Задача принята сервером."),
                started_at = progress?.StartedAt ?? report.CreatedAt,
                updated_at = progress?.UpdatedAt ?? report.CreatedAt
            });
        }

        return NotFound(new { error = $"Задача с ID {taskId} не найдена." });
    }

    [HttpGet("history")]
    public async Task<IActionResult> GetHistory([FromQuery] bool includeArchived = false, [FromQuery] bool onlyArchived = false)
    {
        var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
        if (string.IsNullOrEmpty(userIdClaim) || !Guid.TryParse(userIdClaim, out var userId))
        {
            return Unauthorized(new { error = "Пользователь не авторизован." });
        }

        var reports = await _reportsService.GetHistoryAsync(userId, includeArchived, onlyArchived);
        return Ok(reports);
    }

    [HttpPut("rename/{taskId}")]
    public async Task<IActionResult> RenameReport(string taskId, [FromBody] RenameReportRequest request)
    {
        var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
        if (string.IsNullOrEmpty(userIdClaim) || !Guid.TryParse(userIdClaim, out var userId))
        {
            return Unauthorized(new { error = "Пользователь не авторизован." });
        }

        if (string.IsNullOrWhiteSpace(request.Name) || request.Name.Trim().Length > 255)
        {
            return BadRequest(new { error = "Название должно содержать от 1 до 255 символов." });
        }

        var success = await _reportsService.RenameReportAsync(taskId, userId, request.Name);
        if (!success)
        {
            return NotFound(new { error = "Отчет не найден." });
        }

        return Ok(new { message = "Отчет успешно переименован.", courseName = request.Name.Trim() });
    }

    [HttpPut("archive/{taskId}")]
    public async Task<IActionResult> ArchiveReport(string taskId)
    {
        var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
        if (string.IsNullOrEmpty(userIdClaim) || !Guid.TryParse(userIdClaim, out var userId))
        {
            return Unauthorized(new { error = "Пользователь не авторизован." });
        }

        var success = await _reportsService.ArchiveReportAsync(taskId, userId);
        if (!success)
        {
            return NotFound(new { error = "Отчет не найден." });
        }

        return Ok(new { message = "Отчет успешно архивирован." });
    }

    [HttpPut("unarchive/{taskId}")]
    public async Task<IActionResult> UnarchiveReport(string taskId)
    {
        var userIdClaim = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
        if (string.IsNullOrEmpty(userIdClaim) || !Guid.TryParse(userIdClaim, out var userId))
        {
            return Unauthorized(new { error = "Пользователь не авторизован." });
        }

        var success = await _reportsService.UnarchiveReportAsync(taskId, userId);
        if (!success)
        {
            return NotFound(new { error = "Отчет не найден." });
        }

        return Ok(new { message = "Отчет успешно разархивирован." });
    }
}

public class RenameReportRequest
{
    public string Name { get; set; } = string.Empty;
}
