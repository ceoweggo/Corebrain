namespace CorebrainCLIAPI;

/// <summary>
/// Represents the configuration settings for the Corebrain CLI wrapper.
/// </summary>
public class CorebrainSettings
{

  /// <summary>
  /// Gets or sets the path to the Python executable (e.g., "./.venv/Scripts/python").
  /// </summary>
  public string PythonPath { get; set; }

  /// <summary>
  /// Gets or sets the path to the Corebrain CLI script or the command name if installed globally (e.g., "corebrain").
  /// </summary>
  public string ScriptPath { get; set; }

  /// <summary>
  /// Gets or sets a value indicating whether verbose logging is enabled.
  /// Default is <c>false</c>.
  /// </summary>
  public bool Verbose { get; set; } = false;
}
