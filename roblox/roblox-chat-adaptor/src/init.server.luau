local Installer = require(script.Modules.Installer)

local toolbar = plugin:CreateToolbar("ChatGuard")
local chatGuardInitButton = toolbar:CreateButton(
    "ChatGuard init",
    "Install ChatGuard SDK",
    "rbxassetid://112567831254632"
)


chatGuardInitButton.Click:Connect(function()
    Installer.Install(script)
end)
