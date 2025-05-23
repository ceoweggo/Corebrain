namespace CorebrainCLIAPI;

using CorebrainCS;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;

/// <summary>
/// Controller for executing Corebrain CLI commands
/// </summary>
[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class CommandController : ControllerBase {
  private readonly CorebrainCS _corebrain;

  public CommandController(IOptions<CorebrainSettings> settings) {
    var config = settings.Value;
    _corebrain = new CorebrainCS(
        config.PythonPath,
        config.ScriptPath,
        config.Verbose
    );
  }

  /// <summary>
  /// Executes a Corebrain CLI command
  /// </summary>
  /// <remarks>
  /// Sample request:
  ///
  ///     POST /api/command
  ///     {
  ///         "arguments": "--help"
  ///     }
  ///
  /// </remarks>
  /// <param name="request">Command request containing the arguments</param>
  /// <returns>The output of the executed command</returns>
  /// <response code="200">Returns the command output</response>
  /// <response code="400">If the arguments are empty</response>
  /// <response code="500">If there was an error executing the command</response>
  [HttpPost]
  [ProducesResponseType(StatusCodes.Status200OK)]
  [ProducesResponseType(StatusCodes.Status400BadRequest)]
  [ProducesResponseType(StatusCodes.Status500InternalServerError)]
  public IActionResult ExecuteCommand([FromBody] CommandRequest request) {
    if (string.IsNullOrWhiteSpace(request.Arguments)) {
      return BadRequest("Command arguments are required");
    }

    try {
      var result = _corebrain.ExecuteCommand(request.Arguments);
      return Ok(result);
    }
    catch (Exception ex) {
      return StatusCode(500, $"Error executing command: {ex.Message}");
    }
  }

  /// <summary>
  /// Command request model
  /// </summary>
  public class CommandRequest {
    /// <summary>
    /// The arguments to pass to the Corebrain CLI
    /// </summary>
    /// <example>--help</example>
    public required string Arguments { get; set; }
  }
}
