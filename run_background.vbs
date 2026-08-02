Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\AKOBIR\CRM"
WshShell.Run "python start_all.py", 0, False
