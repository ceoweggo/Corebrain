namespace CorebrainCS;

using System;
using System.Diagnostics;

/// <summary>
/// Creates the main corebrain interface.
/// </summary>
/// <param name="pythonPath">Path to the python which works with the corebrain cli, for example if you create the ./.venv you pass the path to the ./.venv python executable</param>
/// <param name="scriptPath">Path to the corebrain cli script, if you installed it globally you just pass the `corebrain` path</param>
/// <param name="verbose"></param>
public class CorebrainCS(string pythonPath = "python", string scriptPath = "corebrain", bool verbose = false) {
  private readonly string _pythonPath = Path.GetFullPath(pythonPath);
  private readonly string _scriptPath = Path.GetFullPath(scriptPath);
  private readonly bool _verbose = verbose;

  /// <summary>
  /// Executes the CLI with the "--help" flag.
  /// </summary>
  /// <returns>Help text from the Corebrain CLI.</returns>
  public string Help() {
    return ExecuteCommand("--help");
  }

  /// <summary>
  /// Executes the CLI with the "--version" flag.
  /// </summary>
  /// <returns>The version of the Corebrain CLI.</returns>
  public string Version()
  {
    return ExecuteCommand("--version");
  }

  /// <summary>
  /// Starts interactive configuration of the Corebrain CLI.
  /// </summary>
  /// <returns>Output from the configuration process.</returns>
  public string Configure()
  {
    return ExecuteCommand("--configure");
  }

  /// <summary>
  /// Lists all stored configurations.
  /// </summary>
  /// <returns>Configuration listing.</returns>
  public string ListConfigs()
  {
    return ExecuteCommand("--list-configs");
  }

  /// <summary>
  /// Removes a stored configuration.
  /// </summary>
  /// <returns>Result of the remove operation.</returns>
  public string RemoveConfig()
  {
    return ExecuteCommand("--remove-config");
  }

  /// <summary>
  /// Shows the schema used by Corebrain.
  /// </summary>
  /// <returns>The current schema as a string.</returns>
  public string ShowSchema()
  {
    return ExecuteCommand("--show-schema");
  }

  /// <summary>
  /// Extracts the current schema to the console.
  /// </summary>
  /// <returns>The extracted schema.</returns>
  public string ExtractSchema()
  {
    return ExecuteCommand("--extract-schema");
  }

  /// <summary>
  /// Extracts schema and saves it to a default file ("test").
  /// </summary>
  /// <returns>CLI output from the extract operation.</returns>
  public string ExtractSchemaToDefaultFile()
  {
    return ExecuteCommand("--extract-schema --output-file test");
  }
  
  /// <summary>
  /// Extracts schema with a specific configuration ID.
  /// </summary>
  /// <returns>CLI output from the operation.</returns>
  public string ConfigID()
  {
    return ExecuteCommand("--extract-schema --config-id config");
  }

  /// <summary>
  /// Sets the authentication token.
  /// </summary>
  /// <param name="token">Authentication token.</param>
  /// <returns>Result of setting the token.</returns>
  public string SetToken(string token)
  {
    return ExecuteCommand($"--token {token}");
  }

  /// <summary>
  /// Sets the API key.
  /// </summary>
  /// <param name="apikey">API key string.</param>
  /// <returns>Result of setting the API key.</returns>
  public string ApiKey(string apikey)
  {
    return ExecuteCommand($"--api-key {apikey}");
  }
  
  /// <summary>
  /// Sets the API URL.
  /// </summary>
  /// <param name="apiurl">A valid HTTP or HTTPS URL.</param>
  /// <returns>CLI output after setting the URL.</returns>
  public string ApiUrl(string apiurl)
  {
    if (string.IsNullOrWhiteSpace(apiurl))
    {
      throw new ArgumentException("API URL cannot be empty or whitespace", nameof(apiurl));
    }

    if (!Uri.TryCreate(apiurl, UriKind.Absolute, out var uriResult) ||
        (uriResult.Scheme != Uri.UriSchemeHttp && uriResult.Scheme != Uri.UriSchemeHttps))
    {
      throw new ArgumentException("Invalid API URL format. Must be a valid HTTP/HTTPS URL", nameof(apiurl));
    }

    var escapedUrl = apiurl.Replace("\"", "\\\"");
    return ExecuteCommand($"--api-url \"{escapedUrl}\"");
  } 
  
  /// <summary>
  /// Sets the Single Sign-On (SSO) URL.
  /// </summary>
  /// <param name="ssoUrl">A valid SSO URL.</param>
  /// <returns>CLI output after setting the SSO URL.</returns>
  public string SsoUrl(string ssoUrl)
  {
    if (string.IsNullOrWhiteSpace(ssoUrl))
    {
      throw new ArgumentException("SSO URL cannot be empty or whitespace", nameof(ssoUrl));
    }

    if (!Uri.TryCreate(ssoUrl, UriKind.Absolute, out var uriResult) ||
        (uriResult.Scheme != Uri.UriSchemeHttp && uriResult.Scheme != Uri.UriSchemeHttps))
    {
      throw new ArgumentException("Invalid SSO URL format. Must be a valid HTTP/HTTPS URL", nameof(ssoUrl));
    }

    var escapedUrl = ssoUrl.Replace("\"", "\\\"");
    return ExecuteCommand($"--sso-url \"{escapedUrl}\"");
  }
  
  /// <summary>
  /// Logs in using username and password.
  /// </summary>
  /// <param name="username">User's username.</param>
  /// <param name="password">User's password.</param>
  /// <returns>CLI output from login attempt.</returns>
  public string Login(string username, string password)
  {
    if (string.IsNullOrWhiteSpace(username))
    {
      throw new ArgumentException("Username cannot be empty or whitespace", nameof(username));
    }

    if (string.IsNullOrWhiteSpace(password))
    {
      throw new ArgumentException("Password cannot be empty or whitespace", nameof(password));
    }

    var escapedUsername = username.Replace("\"", "\\\"");
    var escapedPassword = password.Replace("\"", "\\\"");

    return ExecuteCommand($"--login --username \"{escapedUsername}\" --password \"{escapedPassword}\"");
  }

  /// <summary>
  /// Logs in using an authentication token.
  /// </summary>
  /// <param name="token">Authentication token.</param>
  /// <returns>CLI output from login attempt.</returns>
  public string LoginWithToken(string token)
  {
    if (string.IsNullOrWhiteSpace(token))
    {
      throw new ArgumentException("Token cannot be empty or whitespace", nameof(token));
    }

    var escapedToken = token.Replace("\"", "\\\"");
    return ExecuteCommand($"--login --token \"{escapedToken}\"");
  }

  //When youre logged in use this function
  /// <summary>
  /// Tests authentication status for the currently logged-in user.
  /// </summary>
  /// <returns>CLI output from the authentication test.</returns>
  public string TestAuth()
  {
    return ExecuteCommand("--test-auth");
  }

  //Without beeing logged
  /// <summary>
  /// Tests authentication status using provided token and/or API URL.
  /// </summary>
  /// <param name="apiUrl">Optional API URL to use for the test.</param>
  /// <param name="token">Optional token to use for the test.</param>
  /// <returns>CLI output from the authentication test.</returns>
  public string TestAuth(string? apiUrl = null, string? token = null)
  {
    var args = new List<string> { "--test-auth" };

    if (!string.IsNullOrEmpty(apiUrl))
    {
      if (!Uri.IsWellFormedUriString(apiUrl, UriKind.Absolute))
        throw new ArgumentException("Invalid API URL format", nameof(apiUrl));

      args.Add($"--api-url \"{apiUrl}\"");
    }

    if (!string.IsNullOrEmpty(token))
      args.Add($"--token \"{token}\"");

    return ExecuteCommand(string.Join(" ", args));
  }
  /// <summary>
  /// Executes the given CLI command arguments using the configured Python and script paths.
  /// </summary>
  /// <param name="arguments">Command-line arguments for the Corebrain CLI.</param>
  /// <returns>Standard output from the executed command.</returns>
  /// <exception cref="InvalidOperationException">Thrown if there is an error in the CLI output.</exception>
  public string ExecuteCommand(string arguments)
  {
    if (_verbose)
    {
      Console.WriteLine($"Executing: {_pythonPath} {_scriptPath} {arguments}");
    }

    var process = new Process
    {
      StartInfo = new ProcessStartInfo
      {
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

    if (_verbose)
    {
      Console.WriteLine("Command output:");
      Console.WriteLine(output);
      if (!string.IsNullOrEmpty(error))
      {
        Console.WriteLine("Error output:\n" + error);
      }
    }

    if (!string.IsNullOrEmpty(error))
    {
      throw new InvalidOperationException($"Python CLI error: {error}");
    }

    return output.Trim();
  }
}