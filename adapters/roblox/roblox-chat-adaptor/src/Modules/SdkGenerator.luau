local Utils = require(script.Parent.Utils)

local SdkGenerator = {}

local function process(templateFolder: Folder, target: Instance)
    local subFolders = {}
    local leafChildren = {}

    for _, child: Instance in ipairs(templateFolder:GetChildren()) do
        if child:IsA("Folder") then
            table.insert(subFolders, child)
        else
            table.insert(leafChildren, child)
        end
    end

    -- Recurse into matching real instances for any nested folders
    for _, subFolder in ipairs(subFolders) do
        local childTarget = target:FindFirstChild(subFolder.Name)
        if not childTarget then
            warn(("SdkGenerator: could not find '%s' under %s"):format(subFolder.Name, target:GetFullName()))
        else
            process(subFolder, childTarget)
        end
    end

    -- If this folder has actual content, this is where ChatGuard belongs
    if #leafChildren > 0 then
        local chatGuardFolder = Utils.FindChatGuard(target)

        if not chatGuardFolder then
            chatGuardFolder = Utils.CreateChatGuardFolder(target)
        else
            print(("ChatGuard already initialized in %s"):format(target:GetFullName()))
        end

        chatGuardFolder:ClearAllChildren()

        for _, child in ipairs(leafChildren) do
            child:Clone().Parent = chatGuardFolder
        end
    end
end

function SdkGenerator.Generate(template: Folder)
    for _, serviceFolder: Folder in ipairs(template:GetChildren()) do
        local service = game:GetService(serviceFolder.Name)
        process(serviceFolder, service)
    end
end

return SdkGenerator