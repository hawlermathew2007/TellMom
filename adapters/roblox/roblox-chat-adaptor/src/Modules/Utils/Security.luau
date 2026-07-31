local Security = {}

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Cryptography = require(ReplicatedStorage.ChatGuard.Packages.cryptography)
local Base64 = Cryptography.Utilities.Base64
local CSPRNG = Cryptography.Utilities.CSPRNG
local AES = Cryptography.Encryption.AES
local SHA256 = Cryptography.Hashing.SHA2.SHA256
local HMAC = Cryptography.Hashing.HMAC

-- TODO: Use this prime for now
local DH_P = 13
local DH_G = 2

export type SessionState = {
    sessionId: string,
    status: string,

    sequence: number,

    aesKey: string?,
    nonceBase: string?,

    serverPrivate: any?,
    serverPublic: any?,
}

export type EncryptedMessage = {
    sequence: number,
    nonce: string,
    ciphertext: string,
    authTag: string
}

-- Helper functions
local function XorNonce(nonceBase: buffer, sequence: number): buffer
    local length = buffer.len(nonceBase)
    local result = buffer.create(length)

    -- Write `sequence` as a big-endian integer into a temp buffer,
    local seqBytes = buffer.create(length)
    for i = 0, length - 1 do
        local shift = (length - 1 - i) * 8
        local byteValue = bit32.band(bit32.rshift(sequence, shift), 0xFF)
        buffer.writeu8(seqBytes, i, byteValue)
    end

    -- XOR byte by byte
    for i = 0, length - 1 do
        local a = buffer.readu8(nonceBase, i)
        local b = buffer.readu8(seqBytes, i)
        buffer.writeu8(result, i, bit32.bxor(a, b))
    end

    return result
end

local function modpow(base, exp, mod)
    base = base % mod
    local result = 1
    while exp > 0 do
        if exp % 2 == 1 then
            result = (result * base) % mod
        end
        exp = math.floor(exp / 2)
        base = (base * base) % mod
    end
    return result
end

local function intToBuffer(n)
    if n == 0 then
        local buf = buffer.create(1)
        buffer.writeu8(buf, 0, 0)
        return buf
    end

    -- figure out byte length first
    local byteCount = 0
    local temp = n
    while temp > 0 do
        byteCount += 1
        temp = math.floor(temp / 256)
    end

    local buf = buffer.create(byteCount)
    for i = byteCount - 1, 0, -1 do
        buffer.writeu8(buf, i, n % 256)
        n = math.floor(n / 256)
    end
    return buf
end

local function hkdfExtract(salt: buffer, ikm: buffer): buffer
    local hexMac, rawMac = HMAC(ikm, salt, SHA256, 64, true)
    return rawMac
end

local function hkdfExpand(prk: buffer, info: buffer, length: number): buffer
    local function bufferConcat(...)
        local buffers = {...}
        local totalLen = 0
        for _, buf in buffers do
            totalLen += buffer.len(buf)
        end

        local result = buffer.create(totalLen)
        local offset = 0
        for _, buf in buffers do
            buffer.copy(result, offset, buf)
            offset += buffer.len(buf)
        end
        return result
    end

    local function bufferSlice(buf, length)
        length = math.min(length, buffer.len(buf))
        local result = buffer.create(length)
        buffer.copy(result, 0, buf, 0, length)
        return result
    end

    local result = buffer.create(0)
    local previous = buffer.create(0)
    local counter = 1

    while buffer.len(result) < length do
        local counterByte = buffer.create(1)
        buffer.writeu8(counterByte, 0, counter)

        local input = bufferConcat(previous, info, counterByte)
        local hexMac, rawMac = HMAC(input, prk, SHA256, 64, true)

        previous = rawMac
        result = bufferConcat(result, previous)
        counter += 1
    end

    return bufferSlice(result, length)
end

-- Module functions
function Security.IntToBase64(value: number): string
    return buffer.tostring(Base64.Encode(value))
end

function Security.Base64ToInt(value: string): number
    local decoded = Base64.Decode(value)
    return tonumber(buffer.tostring(decoded))
end

function Security.GenerateDHPrivateKey(): number
    return CSPRNG.RandomInt(DH_P - 2) + 2
end

function Security.DeriveDhPublicKey(privateKey: number): number
    return modpow(DH_G, privateKey, DH_P)
end

function Security.DeriveSharedSecret(privateKey: number, peerPublic: number): buffer
    local shared = modpow(peerPublic, privateKey, DH_P)
    local secretBuffer = intToBuffer(shared)
    local hexDigest, rawDigest = SHA256(secretBuffer)
    return rawDigest
end

function Security.DeriveSessionKeys(sharedSecret: buffer): (buffer, buffer, buffer)
    local prk = hkdfExtract(buffer.create(0), sharedSecret)
    local aesKey = hkdfExpand(prk, buffer.fromstring("aes-gcm"), 32)
    local nonceBase = hkdfExpand(prk, buffer.fromstring("nonce"), 12)
    local futureKeys = hkdfExpand(prk, buffer.fromstring("future"), 32)
    return aesKey, nonceBase, futureKeys
end


function Security.EncryptMessage(
    sequence: number,
    aesKey: buffer,
    nonceBase: buffer,
    plaintext: string,
    sessionId: string
): EncryptedMessage
    local nonce = XorNonce(nonceBase, sequence)
    local aad = buffer.fromstring(`{sessionId}:{sequence}`)

    local ciphertext, tag = AES.Encrypt(buffer.fromstring(plaintext), aesKey, nonce, aad)

    return {
        sequence = sequence,
        nonce = nonce,
        ciphertext = ciphertext,
        authTag = tag
    }
end



return Security