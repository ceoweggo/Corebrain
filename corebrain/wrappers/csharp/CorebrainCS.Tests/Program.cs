using CorebrainCS;

Console.WriteLine("Hello, World!");

// For now it only works on windows
var corebrain = new CorebrainCS.CorebrainCS("../../../../venv/Scripts/python.exe", "../../../cli", false);

Console.WriteLine(corebrain.Version());
