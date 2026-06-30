local TextChatService = game:GetService("TextChatService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local clientSendMessageEvent: RemoteEvent = ReplicatedStorage.ChatGuard.ClientSendMessage
local serverWarningResponseEvent: RemoteEvent = ReplicatedStorage.ChatGuard.ServerWarningResponse

local function convertToUTC(unixTimeStamp: DateTime): string
    return unixTimeStamp:ToIsoDate()
end

-- Send every message to the game server
TextChatService.SendingMessage:Connect(function(textChatMessage)
    local message = {
        Text = textChatMessage.Text,
        TimeStampUTC = convertToUTC(textChatMessage.Timestamp),
    }

    clientSendMessageEvent:FireServer(message)
end)

-- Receive warning response if RequestAsync
serverWarningResponseEvent.OnServerEvent:Connect(function(player)
    print("Your message is flagged for being inappropriate")
end)