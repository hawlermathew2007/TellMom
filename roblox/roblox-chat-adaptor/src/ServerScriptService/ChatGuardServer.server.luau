local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HTTPService = game:GetService("HttpService")

local clientSendMessageEvent: RemoteEvent = ReplicatedStorage.ChatGuard.ClientSendMessage
local serverWarningResponseEvent: RemoteEvent = ReplicatedStorage.ChatGuard.ServerWarningResponse

local API_URL = "http://45.151.155.170:8000/api/ingest"

-- Receive messages sent from clients
clientSendMessageEvent.OnServerEvent:Connect(function(player: Player, message)
    local success, response = pcall(function()
        return HTTPService:RequestAsync({
            Url = API_URL,
            Method = "POST",
            Headers = {
                ["Content-Type"] = "application/json",
            },
            Body = HTTPService:JSONEncode({
                platform = "ROBLOX",
                user_id = player.UserId,
                server_id = game.JobId,
                message = message.Text,
                timestamp = message.TimeStampUTC,
            }),
        })
    end)

    if not response.Success then
        warn(`API returned error status {response.StatusCode} for {player.Name}: {response.Body}`)
        return
    end

    local data = HTTPService:JSONDecode(response.Body)

    -- Nothing happens, legit message
    if data.status == "below_threshold" then
        return
    end

    serverWarningResponseEvent:FireClient(player)
end)
