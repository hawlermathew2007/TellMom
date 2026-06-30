local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HTTPService = game:GetService("HttpService")
local clientSendMessageEvent: RemoteEvent = ReplicatedStorage.ChatGuard.ClientSendMessage


local function sendMessageForAnalyzing()
    
end

-- Receive messages sent from clients
clientSendMessageEvent.OnServerEvent:Connect(function(player: Player, message)
    print(player.Name, " said:")
    print("Message: ", message.Text)
    print("Timestamp: ", message.TimeStampUTC)
end)

print("server started")