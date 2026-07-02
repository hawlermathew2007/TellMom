local Utils = require(script.Parent.Utils)

local SdkGenerator = {}

function SdkGenerator.Generate(template: Folder)
    for _, serviceFolder: Folder in ipairs(template:GetChildren()) do
        local service = game:GetService(serviceFolder.Name)
        local chatGuardFolder = Utils.FindChatGuard(service)

        if not chatGuardFolder then
            Utils.CreateChatGuardFolder(service)
        elseif service.ClassName == "StarterPlayer" then
            local StarterPlayerScripts = service.StarterPlayerScripts
            if not Utils.FindChatGuard(StarterPlayerScripts) then
                Utils.CreateChatGuardFolder(StarterPlayerScripts)
            end
        else
            print("ChatGuard already initialized in ", service)
        end
    end
end

return SdkGenerator