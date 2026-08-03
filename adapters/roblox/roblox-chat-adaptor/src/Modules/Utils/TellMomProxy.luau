local HttpService = game:GetService("HttpService")

local Security = require(script.Parent.Security)
local API_URL = "https://unanatomisable-denny-mentalistic.ngrok-free.dev"


local TellMomProxy = {}

local function raiseNetworkingError()
    error("Http not enabled or networking error. Please check the network or Http configuration in Experience settings")
end

function TellMomProxy.AssociateWithLocalServer(id: string, password: string): string
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
        raiseNetworkingError()
    end

    return response.session_id
end

function TellMomProxy.ExchangeKeyWithLocalServer(sessionId: string, clientPrivateKey: string): number
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
        raiseNetworkingError()
    end

    local serverPublicKey = Security.Base64ToInt(response.server_dh_pubkey)

    return serverPublicKey
end

function TellMomProxy.SendMessageToLocalServer(sessionId: string, encryptedBody): nil
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

return TellMomProxy