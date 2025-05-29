namespace CorebrainCS;

using System;
using System.Diagnostics;
using System.Collections.Generic;

/// <summary>
/// Creates the main corebrain interface.
/// </summary>
///<param name="pythonPath">Path to the python which works with the corebrain cli, for example if you create the ./.venv you pass the path to the ./.venv python executable</param>
/// <param name="scriptPath">Path to the corebrain cli script, if you installed it globally you just pass the `corebrain` path</param>
/// <param name="verbose"></param>
public class CorebrainCS(string pythonPath = "python", string scriptPath = "corebrain", bool verbose = false) {
  private readonly string _pythonPath = Path.GetFullPath(pythonPath);
  private readonly string _scriptPath = Path.GetFullPath(scriptPath);
  private readonly bool _verbose = verbose;

  /// <summary>
  /// Shows help message with all available commands
  /// </summary>
  /// <returns></returns>
  public string Help() {
    return ExecuteCommand("--help");
  }

  /// <summary>
  /// Shows the current version of the Corebrain SDK
  /// </summary>
  /// <returns></returns>
  public string Version() {
    return ExecuteCommand("--version");
  }

  /// <summary>
  /// Checks system status including:
  /// </summary>
  /// <returns></returns>
  /// - API Server status
  /// - Redis status
  /// - SSO Server status
  /// - MongoDB status
  /// - Required libraries installation
  public string CheckStatus() {
    return ExecuteCommand("--check-status");
  }
  /// <summary>
  /// Checks system status with optional API URL and token parameters
  /// </summary>
  /// <param name="apiUrl"></param>
  /// <param name="token"></param>
  /// <returns></returns>
  /// <exception cref="ArgumentException"></exception>
  public string CheckStatus(string? apiUrl = null, string? token = null) {
    var args = new List<string> { "--check-status" };

    if (!string.IsNullOrEmpty(apiUrl)) {
      if (!Uri.IsWellFormedUriString(apiUrl, UriKind.Absolute))
        throw new ArgumentException("Invalid API URL format", nameof(apiUrl));

      args.Add($"--api-url \"{apiUrl}\"");
    }

    if (!string.IsNullOrEmpty(token))
      args.Add($"--token \"{token}\"");

    return ExecuteCommand(string.Join(" ", args));
  }

  /// <summary>
  /// Authenticates with SSO using username and password
  /// </summary>
  /// <param name="username"></param>
  /// <param name="password"></param>
  /// <returns></returns>
  /// <exception cref="ArgumentException"></exception>
  public string Authentication(string username, string password) {
    if (string.IsNullOrWhiteSpace(username)) {
      throw new ArgumentException("Username cannot be empty or whitespace", nameof(username));
    }

    if (string.IsNullOrWhiteSpace(password)) {
      throw new ArgumentException("Password cannot be empty or whitespace", nameof(password));
    }

    var escapedUsername = username.Replace("\"", "\\\"");
    var escapedPassword = password.Replace("\"", "\\\"");


    return ExecuteCommand($"--authentication --username \"{escapedUsername}\" --password \"{escapedPassword}\"");
  }

  /// <summary>
  /// Authenticates with SSO using a token
  /// </summary>
  /// <param name="token"></param>
  /// <returns></returns>
  /// <exception cref="ArgumentException"></exception>
  public string AuthenticationWithToken(string token) {
    if (string.IsNullOrWhiteSpace(token)) {
      throw new ArgumentException("Token cannot be empty or whitespace", nameof(token));
    }

    var escapedToken = token.Replace("\"", "\\\"");
    return ExecuteCommand($"--authentication --token \"{escapedToken}\"");
  }

  /// <summary>
  /// Creates a new user account and generates an associated API Key
  /// </summary>
  /// <returns></returns>
  public string CreateUser() {
    return ExecuteCommand("--create-user");
  }

  /// <summary>
  /// Launches the configuration wizard for setting up database connections
  /// </summary>
  /// <returns></returns>
  public string Configure() {
    return ExecuteCommand("--configure");
  }

  /// <summary>
  /// Lists all available database configurations
  /// </summary>
  /// <returns></returns>
  public string ListConfigs() {
    return ExecuteCommand("--list-configs");
  }

  /// <summary>
  /// Displays the database schema for a configured database
  /// </summary>
  /// <returns></returns>
  public string ShowSchema() {
    return ExecuteCommand("--show-schema");
  }

  /// <summary>
  /// Displays information about the currently authenticated user
  /// </summary>
  /// <returns></returns>
  public string WhoAmI() {
    return ExecuteCommand("--woami");
  }

  /// <summary>
  /// Launches the web-based graphical user interface
  /// </summary>
  /// <returns></returns>
  public string Gui() {
    return ExecuteCommand("--gui");
  }
  private string ExecuteCommand(string arguments) {
    if (_verbose) {
      Console.WriteLine($"Executing: {_pythonPath} {_scriptPath} {arguments}");
    }

    var process = new Process {
      StartInfo = new ProcessStartInfo {
        FileName = _pythonPath,
        Arguments = $"\"{_scriptPath}\" {arguments}",
        RedirectStandardOutput = true,
        RedirectStandardError = true,
        UseShellExecute = false,
        CreateNoWindow = true
      }
    };

    process.Start();
    var output = process.StandardOutput.ReadToEnd();
    var error = process.StandardError.ReadToEnd();
    process.WaitForExit();

    if (_verbose) {
      Console.WriteLine("Command output:");
      Console.WriteLine(output);
      if (!string.IsNullOrEmpty(error)) {
        Console.WriteLine("Error output:\n" + error);
      }
    }

    if (!string.IsNullOrEmpty(error)) {
      throw new InvalidOperationException($"Python CLI error: {error}");
    }

    return output.Trim();
  }
}
