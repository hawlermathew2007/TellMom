local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local ServerStorage = game:GetService("ServerStorage")
local DataStoreService = game:GetService("DataStoreService")

local clientSendMessageEvent: RemoteEvent = ReplicatedStorage.ChatGuard.ClientSendMessage
local onRegisteredEvent: RemoteEvent = ReplicatedStorage.ChatGuard.OnRegistered

local Security = require(ServerStorage.ChatGuard.Modules.Utils.Security)

local tellMomKeyStore = DataStoreService:GetDataStore("TellMomKeys")

-- TODO: Dev URL
local API_URL = "https://unanatomisable-denny-mentalistic.ngrok-free.dev"

-- Helper functions

--#region
local function associateWithLocalServer(id: string, password: string): string
    local success, response = pcall(function()
        return HttpService:RequestAsync({
            Method = "POST",
            Url = API_URL + "/session/associate",
            Headers = {
                ["Content-Type"] = "application/json",
            },
            Body = HttpService:JSONEncode({
                server_id = tostring(game.JobId),
                password_code = password,
                client_id = id,
            }),
        })
    end)

    if not success then
        warn("Failed to associate with local server")
    end

    return response.session_id
end

local function exchangeKeyWithLocalServer(sessionId: string, clientPrivateKey: string): string
    local clientPublicKey = Security.DeriveDhPublicKey(clientPrivateKey)

    local success, response = pcall(function()
        return HttpService:RequestAsync({
            Method = "POST",
            Url = API_URL .. "/session/key-exchange",
            Headers = {
                ["Content-Type"] = "application/json",
            },
            Body = HttpService:JSONEncode({
                session_id = sessionId,
                client_dh_pubkey = clientPublicKey
            })
        })
    end)

    if not success then
        warn("Failed to exchange key with local server")
    end

    return response.server_dh_pubkey
end

local function sendMessageToLocalServer(sessionId: string, encryptedBody)
    local success, response = pcall(function()
        return HttpService:RequestAsync({
            Method = "POST",
            Url = API_URL .. "/session/" .. sessionId .. "/forward/message/ingest",
            Headers = {
                ["Content-Type"] = "application/json",
            },
            Body = HttpService:JSONEncode(encryptedBody)
        })
    end)

    if not success then
        warn("Failed to send message to local server")
    end
end

local function getSessionKeysFromDataStore(player: Player): (buffer, buffer, number)
    local key = "session_" .. player.UserId

    local success, result = pcall(function()
        return tellMomKeyStore:GetAsync(key)
    end)

    if not success then
        warn("Failed to retrieve session keys for " .. player.Name .. ": " .. tostring(result))
        return nil
    end

    return result.sessionId, result.aesKey, result.nonceBase, result.sequence
end

local function incrementSequence(player: Player)
    local key = "session_" .. player.UserId

    local success, result = pcall(function()
        return tellMomKeyStore:UpdateAsync(key, function(oldData)
            if oldData == nil then
                return nil -- nothing to update, no existing session
            end
            oldData.sequence = oldData.sequence + 1
            return oldData
        end)
    end)

    if not success then
        warn("Failed to update sequence for " .. player.Name .. ": " .. tostring(result))
        return nil
    end
end
--#endregion

-- Main protocol
-- Key exchange with local server
onRegisteredEvent.OnServerEvent:Connect(function(player: Player, id: string, password: string)
    -- Associate with local server to get session id
    local sessionId = associateWithLocalServer(id, password)

    -- Exchange key with local server
    local clientPrivateKey = Security.GenerateDHPrivateKey()
    local serverPublicKeyB64 = exchangeKeyWithLocalServer(sessionId, clientPrivateKey)
    local serverPublicKey = Security.Base64ToInt(serverPublicKeyB64)

    local shared = Security.DeriveSharedSecret(clientPrivateKey, serverPublicKey)
    local aesKey, nonceBase, _ = Security.DeriveSessionKeys(shared)
    local sequence = 1

    -- Save TellMom's keys into DataStore
    local key = "session_" .. player.UserId
    local success, error = pcall(function()
        tellMomKeyStore:SetAsync(key, {
            sessionId = sessionId,
            aesKey = aesKey,
            nonceBase = nonceBase,
            sequence = sequence
        })
    end)

    if not success then
        warn("Failed to store session keys for " .. player.Name .. ": " .. tostring(error))
    end
end)

-- Send message to the local server
clientSendMessageEvent.OnServerEvent:Connect(function(player: Player, messageText: string)
    local payload = {
        platform = "roblox",
        user_id = player.UserId,
        server_id = tostring(game.JobId),
        message = messageText,
    }

    local sessionId, aesKey, nonceBase, sequence = getSessionKeysFromDataStore(player)
    local plaintext = HttpService:JSONEncode(payload)

    local encryptedBody = Security.EncryptMessage(
        sequence,
        aesKey,
        nonceBase,
        plaintext,
        sessionId
    )

    -- Send message and increment the sequence for each request
    sendMessageToLocalServer(sessionId, encryptedBody)
    incrementSequence(player)
end)
