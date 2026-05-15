Set oShell = CreateObject ("Wscript.Shell")
strArgs = "cmd /c python -u f:\Antigravity\brain2\vault\Projects\ad-facebook\telegram-bot-listener.py > f:\Antigravity\brain2\vault\Projects\ad-facebook\logs\telegram-bot.log 2>&1"
oShell.Run strArgs, 0, false
