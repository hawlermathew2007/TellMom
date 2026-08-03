local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local ServerStorage = game:GetService("ServerStorage")

local clientSendMessageEvent: RemoteEvent = ReplicatedStorage.ChatGuard.ClientSendMessage
local onRegisteredEvent: RemoteEvent = ReplicatedStorage.ChatGuard.OnRegistered

local Security = require(ServerStorage.ChatGuard.Modules.Utils.Security)
local DataStore = require(ServerStorage.ChatGuard.Modules.Utils.DataStore)
local TellMomProxy = require(ServerStorage.ChatGuard.Modules.Utils.TellMomProxy)


-- Key exchange with local server
onRegisteredEvent.OnServerEvent:Connect(function(player: Player, id: string, password: string)
    -- Associate with local server to get session id
    local sessionId = TellMomProxy.AssociateWithLocalServer(id, password)

    -- Exchange key with local server
    local clientPrivateKey = Security.GenerateDHPrivateKey()
    local serverPublicKey = TellMomProxy.ExchangeKeyWithLocalServer(sessionId, clientPrivateKey)

    local shared = Security.DeriveSharedSecret(clientPrivateKey, serverPublicKey)
    local aesKey, nonceBase, _ = Security.DeriveSessionKeys(shared)
    local sequence = 1

    -- Save TellMom's keys into DataStore
    DataStore.CreateTellMomSessionData(player, {
        sessionId = sessionId,
        aesKey = aesKey,
        nonceBase = nonceBase,
        sequence = sequence,
    })
end)

-- Send message to the local server
clientSendMessageEvent.OnServerEvent:Connect(function(player: Player, messageText: string)
    local payload = {
        platform = "roblox",
        user_id = player.UserId,
        server_id = tostring(game.JobId),
        message = messageText,
    }

    local tellMomSessionData = DataStore.RetrieveTellMomSessionData(player)
    local plaintext = HttpService:JSONEncode(payload)

    local encryptedBody = Security.EncryptMessage(
        tellMomSessionData.sequence,
        tellMomSessionData.aesKey,
        tellMomSessionData.nonceBase,
        plaintext,
        tellMomSessionData.sessionId
    )

    -- Send message and increment the sequence for each request
    TellMomProxy.SendMessageToLocalServer(tellMomSessionData.sessionId, encryptedBody)
    DataStore.UpdateTellMomSessionData(player, "sequence", tellMomSessionData.sequence + 1)
end)
