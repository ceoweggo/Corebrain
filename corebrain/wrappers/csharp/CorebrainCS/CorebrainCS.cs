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


  public string Help() {
    return ExecuteCommand("--help");
  }

  public string Version() {
    return ExecuteCommand("--version");
  }

  public string Configure() {
    return ExecuteCommand("--configure");
  }

  public string ListConfigs() {
    return ExecuteCommand("--list-configs");
  }

  public string RemoveConfig() {
    return ExecuteCommand("--remove-config");
  }

  public string ShowSchema() {
    return ExecuteCommand("--show-schema");
  }

  public string ExtractSchema() {
    return ExecuteCommand("--extract-schema");
  }

  public string ExtractSchemaToDefaultFile() {
    return ExecuteCommand("--extract-schema --output-file test");
  }

  public string ConfigID() {
    return ExecuteCommand("--extract-schema --config-id config");
  }

  public string SetToken(string token) {
    return ExecuteCommand($"--token {token}");
  }

  public string ApiKey(string apikey) {
    return ExecuteCommand($"--api-key {apikey}");
  }

  public string ApiUrl(string apiurl) {
    if (string.IsNullOrWhiteSpace(apiurl)) {
      throw new ArgumentException("API URL cannot be empty or whitespace", nameof(apiurl));
    }

    if (!Uri.TryCreate(apiurl, UriKind.Absolute, out var uriResult) ||
        (uriResult.Scheme != Uri.UriSchemeHttp && uriResult.Scheme != Uri.UriSchemeHttps)) {
      throw new ArgumentException("Invalid API URL format. Must be a valid HTTP/HTTPS URL", nameof(apiurl));
    }

    var escapedUrl = apiurl.Replace("\"", "\\\"");
    return ExecuteCommand($"--api-url \"{escapedUrl}\"");
  } 
  public string SsoUrl(string ssoUrl) {
    if (string.IsNullOrWhiteSpace(ssoUrl)) {
        throw new ArgumentException("SSO URL cannot be empty or whitespace", nameof(ssoUrl));
    }

    if (!Uri.TryCreate(ssoUrl, UriKind.Absolute, out var uriResult) ||
        (uriResult.Scheme != Uri.UriSchemeHttp && uriResult.Scheme != Uri.UriSchemeHttps))  {
        throw new ArgumentException("Invalid SSO URL format. Must be a valid HTTP/HTTPS URL", nameof(ssoUrl));
    }

    var escapedUrl = ssoUrl.Replace("\"", "\\\"");
    return ExecuteCommand($"--sso-url \"{escapedUrl}\"");
  }
  public string Login(string username, string password){
    if (string.IsNullOrWhiteSpace(username)){
        throw new ArgumentException("Username cannot be empty or whitespace", nameof(username));
    }

    if (string.IsNullOrWhiteSpace(password)){
        throw new ArgumentException("Password cannot be empty or whitespace", nameof(password));
    }

    var escapedUsername = username.Replace("\"", "\\\"");
    var escapedPassword = password.Replace("\"", "\\\"");

    return ExecuteCommand($"--login --username \"{escapedUsername}\" --password \"{escapedPassword}\"");
  }

  public string LoginWithToken(string token) {
      if (string.IsNullOrWhiteSpace(token)) {
          throw new ArgumentException("Token cannot be empty or whitespace", nameof(token));
      }

      var escapedToken = token.Replace("\"", "\\\"");
      return ExecuteCommand($"--login --token \"{escapedToken}\"");
  }

  //When youre logged in use this function
  public string TestAuth() {
    return ExecuteCommand("--test-auth");
  }

  //Without beeing logged
  public string TestAuth(string? apiUrl = null, string? token = null) {
    var args = new List<string> { "--test-auth" };
            
    if (!string.IsNullOrEmpty(apiUrl)) {
        if (!Uri.IsWellFormedUriString(apiUrl, UriKind.Absolute))
            throw new ArgumentException("Invalid API URL format", nameof(apiUrl));
                
        args.Add($"--api-url \"{apiUrl}\"");
        }
            
    if (!string.IsNullOrEmpty(token))
        args.Add($"--token \"{token}\"");

    return ExecuteCommand(string.Join(" ", args));
  }
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