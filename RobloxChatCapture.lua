--[[
    RobloxChatCapture.lua
    
    Place this in StarterPlayer > StarterCharacterScripts
    
    This script listens to Roblox TextChatService and sends messages
    to the backend API for grooming detection analysis.
]]

local TextChatService = game:GetService("TextChatService")
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")

-- ===== CONFIGURATION =====
local BACKEND_URL = "http://localhost:8000/api/messages/capture"  -- Change to your backend URL
local ROBLOX_API_KEY = "your-roblox-api-key"  -- Set in backend .env
local ENABLED = true  -- Set to false to disable capturing

-- Get current player
local player = Players:GetPlayerFromCharacter(script.Parent)
if not player then
    warn("RobloxChatCapture: Could not find player")
    return
end

local child_id = tostring(player.UserId)
local username = player.Name

-- Logging helper
local function log(message, level)
    level = level or "INFO"
    print(string.format("[RobloxChatCapture] [%s] %s", level, message))
end

-- ===== CAPTURE CHAT MESSAGES =====

-- Listen for received messages
TextChatService.MessageReceived:Connect(function(textChatMessage)
    if not ENABLED then
        return
    end
    
    local messageText = textChatMessage.Text
    local textSource = textChatMessage.TextSource
    
    -- Skip system messages or empty messages
    if not messageText or messageText == "" then
        return
    end
    
    if not textSource then
        return
    end
    
    -- Get message sender info
    local senderUserId = textSource.UserId
    local senderUsername = textSource.Name or "Unknown"
    
    log(string.format("📨 Message from %s: %s", senderUsername, messageText:sub(1, 50)))
    
    -- Create payload
    local payload = {
        roblox_user_id = tostring(senderUserId),
        username = senderUsername,
        text = messageText,
        child_id = child_id,
        api_key = ROBLOX_API_KEY,
        timestamp = os.time()
    }
    
    -- Send to backend API
    task.spawn(function()
        local success, result = pcall(function()
            return HttpService:PostAsyncWithAuthorizationHeader(
                BACKEND_URL,
                HttpService:JSONEncode(payload),
                Enum.HttpContentType.ApplicationJson,
                false,
                { ["X-Roblox-API-Key"] = ROBLOX_API_KEY }
            )
        end)
        
        if success then
            local response = HttpService:JSONDecode(result)
            local status = response.status or "unknown"
            local risk_level = response.analysis.risk_level or "UNKNOWN"
            
            log(string.format("✅ Analysis complete: %s (risk: %s)", status, risk_level), "SUCCESS")
            
            -- If high risk, you could play a sound or show a warning
            if risk_level == "RED" then
                log("🚨 HIGH RISK MESSAGE DETECTED!", "WARNING")
                -- TODO: Optional - play sound or notify parent
            end
        else
            log(string.format("❌ API Error: %s", tostring(result)), "ERROR")
        end
    end)
end)

log("✅ Chat capture initialized for player: " .. username, "SUCCESS")
