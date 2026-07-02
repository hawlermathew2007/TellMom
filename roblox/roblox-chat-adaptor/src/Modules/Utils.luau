local Utils = {}

function Utils.FindChatGuard(parent: Instance)
    return parent:FindFirstChild("ChatGuard")
end

function Utils.CreateChatGuardFolder(parent: Instance)
    local chatGuardFolder = Instance.new("Folder", parent)
    chatGuardFolder.Name = "ChatGuard"

    return chatGuardFolder
end

function Utils.SetVersion(folder: Folder, version: string)
    folder:SetAttribute("SDKVersion", version)
end

return Utils