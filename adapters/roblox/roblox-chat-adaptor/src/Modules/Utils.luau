local Utils = {}

function Utils.FindChatGuard(parent)
    return parent:FindFirstChild("ChatGuard")
end

function Utils.SetVersion(folder, version)
    folder:SetAttribute("SDKVersion", version)
end

return Utils