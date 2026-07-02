local TextChatService = game:GetService("TextChatService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local clientSendMessageEvent: RemoteEvent = ReplicatedStorage.ChatGuard.ClientSendMessage

-- Send every message to the game server
TextChatService.SendingMessage:Connect(function(textChatMessage)
    clientSendMessageEvent:FireServer(textChatMessage.Text)
end)