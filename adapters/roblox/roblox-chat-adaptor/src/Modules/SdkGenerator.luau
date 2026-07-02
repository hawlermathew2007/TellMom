local SdkGenerator = {}

local SERVICES = {
    "ReplicatedStorage",
    "ServerScriptService",
    "StarterPlayer"
}

function SdkGenerator.Generate(templates)
    for _, serviceName in ipairs(SERVICES) do
        local service = game:GetService(serviceName)
        local template = templates:FindFirstChild(serviceName)
        if template then
            for _, child in ipairs(template:GetChildren()) do
                child:Clone().Parent = service
            end
        end
    end
end

return SdkGenerator