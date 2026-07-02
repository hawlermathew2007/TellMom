local Installer = {}

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerScriptService = game:GetService("ServerScriptService")
local StarterPlayerScripts = game:GetService("StarterPlayer").StarterPlayerScripts

local SdkGenerator = require(script.Parent.SdkGenerator)
local Utils = require(script.Parent.Utils)
local Version = require(script.Parent.Version)

function Installer.Install(chatGuardMain: Script)

    local template = chatGuardMain:WaitForChild("Template")

    SdkGenerator.Generate(template)

    -- Version attributes
    Utils.SetVersion(
        ReplicatedStorage.ChatGuard,
        Version.SDK_VERSION
    )

    Utils.SetVersion(
        ServerScriptService.ChatGuard,
        Version.SDK_VERSION
    )

    Utils.SetVersion(
        StarterPlayerScripts.ChatGuard,
        Version.SDK_VERSION
    )

    print("ChatGuard installed!")

end

return Installer