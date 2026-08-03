local DataStoreService = game:GetService("DataStoreService")
local tellMomKeyStore = DataStoreService:GetDataStore("TellMomKeys")


local DataStore = {}

export type TellMomSessionData = {
    sessionId: string?,
    aesKey: buffer?,
    nonceBase: buffer?,
    sequence: number?,
}


local function getTellMomDataStoreKey(player: Player): string
    return "session_" .. player.UserId
end

function DataStore.CreateTellMomSessionData(player: Player, data: TellMomSessionData): nil
    local key = getTellMomDataStoreKey(player)

    local success, errorMessage = pcall(function()
        tellMomKeyStore:SetAsync(key, data)
    end)

    if not success then
        warn("Failed to store session keys for " .. player.UserId .. ": " .. errorMessage)
    end
end

function DataStore.UpdateTellMomSessionData(player: Player, field: string, value: any)
    local key = getTellMomDataStoreKey(player)
    local newValue = nil

    local success, err = pcall(function()
        tellMomKeyStore:UpdateAsync(key, function(old)
            local updated = old or {}
            updated[field] = value
            newValue = updated
            return updated
        end)
    end)

    if not success then
        warn("Failed to update session keys for " .. player.UserId .. ": " .. tostring(err))
        return nil
    end

    return newValue
end

function DataStore.RetrieveTellMomSessionData(player: Player): TellMomSessionData
    local key = getTellMomDataStoreKey(player)

    local success, result = pcall(function()
        return tellMomKeyStore:GetAsync(key)
    end)

    if not success then
        warn("Failed to retrieve session keys for " .. player.UserId)
        return nil
    end

    return {
        sessionId = result.sessionId,
        aesKey = result.aesKey,
        nonceBase = result.nonceBase,
        sequence = result.sequence,
    }
end

function DataStore.DeleteTellMomSessionData(player: Player): nil
    local key = getTellMomDataStoreKey(player)

    local success, _ = pcall(function()
        return tellMomKeyStore:RemoveAsync(key)
    end)

    if not success then
        warn("Failed to delete session keys for ".. player.UserId)
    end
end

return DataStore