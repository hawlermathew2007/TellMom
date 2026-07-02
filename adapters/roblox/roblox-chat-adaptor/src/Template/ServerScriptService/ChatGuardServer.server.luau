local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HTTPService = game:GetService("HttpService")

local clientSendMessageEvent: RemoteEvent = ReplicatedStorage.ChatGuard.ClientSendMessage

local API_URL = "http://45.151.155.170:8000/api/ingest"

-- Receive messages sent from clients
clientSendMessageEvent.OnServerEvent:Connect(function(player: Player, messageText: string) 
    local success, response = pcall(function()
        return HTTPService:RequestAsync({
            Url = API_URL,
            Method = "POST",
            Headers = {
                ["Content-Type"] = "application/json",
            },
            Body = HTTPService:JSONEncode({
                platform = "roblox",
                user_id = tostring(player.UserId),
                server_id = tostring(game.JobId),
                message = messageText,
            }),
        })
    end)

    if not success then
        warn("HTTP request failed:", response)
    end
end)
