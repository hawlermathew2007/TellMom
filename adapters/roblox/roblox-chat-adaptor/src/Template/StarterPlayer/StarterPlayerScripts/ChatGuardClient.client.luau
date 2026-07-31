local TextChatService = game:GetService("TextChatService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")

local clientSendMessageEvent: RemoteEvent = ReplicatedStorage.ChatGuard.ClientSendMessage
local onRegisteredEvent: RemoteEvent = ReplicatedStorage.ChatGuard.OnRegistered

TextChatService.SendingMessage:Connect(function(textChatMessage)
    if textChatMessage.Text:sub(1, 9):lower() == "/register" then
        -- Send /register command
        local args = {}
        for arg in textChatMessage.Text:gmatch("%S+") do
            table.insert(args, arg)
        end

        if #args < 3 then
            warn("Usage: /register <id> <password>")
        end

        onRegisteredEvent:FireServer(args[2], args[3])
    else
        -- Send text chat message
        clientSendMessageEvent:FireServer(textChatMessage.Text)
    end
end)
