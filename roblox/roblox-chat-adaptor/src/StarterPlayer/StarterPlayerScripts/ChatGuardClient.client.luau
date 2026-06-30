local TextChatService = game:GetService("TextChatService")

TextChatService.SendingMessage:Connect(function(textChatMessage)
    print("Player: ", textChatMessage.TextSource.UserId)
    print("Message: ", textChatMessage.Text)
end)