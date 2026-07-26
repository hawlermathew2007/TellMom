export const DH_P_STR = "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE65381FFFFFFFFFFFFFFFF";
export const DH_P = BigInt("0x" + DH_P_STR);
export const DH_G = 2n;

function modPow(base: bigint, exp: bigint, mod: bigint): bigint {
    let result = 1n;
    base = base % mod;
    while (exp > 0n) {
        if (exp % 2n === 1n) {
            result = (result * base) % mod;
        }
        exp = exp / 2n;
        base = (base * base) % mod;
    }
    return result;
}

export function intToB64Url(val: bigint): string {
    let hex = val.toString(16);
    if (hex.length % 2 !== 0) hex = '0' + hex;
    const bytes = new Uint8Array(hex.length / 2);
    for (let i = 0; i < bytes.length; i++) {
        bytes[i] = parseInt(hex.substring(i * 2, i * 2 + 2), 16);
    }
    const b64 = btoa(String.fromCharCode.apply(null, bytes as unknown as number[]));
    return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

export function b64UrlToInt(b64url: string): bigint {
    let b64 = b64url.replace(/-/g, '+').replace(/_/g, '/');
    while (b64.length % 4 !== 0) b64 += '=';
    const binary = atob(b64);
    let hex = '';
    for (let i = 0; i < binary.length; i++) {
        const h = binary.charCodeAt(i).toString(16);
        hex += h.length === 1 ? '0' + h : h;
    }
    return BigInt('0x' + hex);
}

export function generateDhPrivateKey(): bigint {
    const bytes = new Uint8Array(256);
    window.crypto.getRandomValues(bytes);
    let hex = '';
    for (let i = 0; i < bytes.length; i++) {
        const h = bytes[i].toString(16);
        hex += h.length === 1 ? '0' + h : h;
    }
    let priv = BigInt('0x' + hex);
    priv = (priv % (DH_P - 3n)) + 2n;
    return priv;
}

export function deriveDhPublicKey(privateKey: bigint): bigint {
    return modPow(DH_G, privateKey, DH_P);
}

export async function deriveSharedSecret(privateKey: bigint, peerPublic: bigint): Promise<Uint8Array> {
    const shared = modPow(peerPublic, privateKey, DH_P);
    let hex = shared.toString(16);
    if (hex.length % 2 !== 0) hex = '0' + hex;
    const bytes = new Uint8Array(hex.length / 2);
    for (let i = 0; i < bytes.length; i++) {
        bytes[i] = parseInt(hex.substring(i * 2, i * 2 + 2), 16);
    }
    const hash = await window.crypto.subtle.digest('SHA-256', bytes);
    return new Uint8Array(hash);
}

async function hmacSha256(key: CryptoKey, data: Uint8Array): Promise<Uint8Array> {
    const signature = await window.crypto.subtle.sign('HMAC', key, data);
    return new Uint8Array(signature);
}

async function hkdfExtract(salt: Uint8Array, ikm: Uint8Array): Promise<CryptoKey> {
    // If salt is 0-length, HMAC typically pads with 0. 
    // To be safe with Web Crypto API, provide a 64-byte zero array for SHA-256 block size.
    const actualSalt = salt.length === 0 ? new Uint8Array(64) : salt;
    const key = await window.crypto.subtle.importKey(
        'raw', actualSalt, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
    );
    const prk = await hmacSha256(key, ikm);
    return window.crypto.subtle.importKey(
        'raw', prk, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
    );
}

async function hkdfExpand(prk: CryptoKey, info: Uint8Array, length: number): Promise<Uint8Array> {
    let result = new Uint8Array(0);
    let previous = new Uint8Array(0);
    let counter = 1;
    while (result.length < length) {
        const block = new Uint8Array(previous.length + info.length + 1);
        block.set(previous, 0);
        block.set(info, previous.length);
        block[previous.length + info.length] = counter;

        previous = await hmacSha256(prk, block);

        const newResult = new Uint8Array(result.length + previous.length);
        newResult.set(result, 0);
        newResult.set(previous, result.length);
        result = newResult;
        counter++;
    }
    return result.slice(0, length);
}

export async function deriveSessionKeys(sharedSecret: Uint8Array) {
    const salt = new Uint8Array(0); // Pass empty, it handles it
    const prk = await hkdfExtract(salt, sharedSecret);
    const aesKey = await hkdfExpand(prk, new TextEncoder().encode("aes-gcm"), 32);
    const nonceBase = await hkdfExpand(prk, new TextEncoder().encode("nonce"), 12);
    const futureKeys = await hkdfExpand(prk, new TextEncoder().encode("future"), 32);
    return { aesKey, nonceBase, futureKeys };
}

export function bytesToBase64(bytes: Uint8Array): string {
    return btoa(String.fromCharCode.apply(null, bytes as unknown as number[]));
}

export function base64ToBytes(b64: string): Uint8Array {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
}

export interface EncryptedMessage {
    sequence: number;
    nonce: string;
    ciphertext: string;
    auth_tag: string;
}

function xorNonce(nonceBase: Uint8Array, sequence: number): Uint8Array {
    const nonce = new Uint8Array(nonceBase.length);
    let tempSeq = BigInt(sequence);
    for (let i = nonceBase.length - 1; i >= 0; i--) {
        nonce[i] = nonceBase[i] ^ Number(tempSeq & 0xffn);
        tempSeq >>= 8n;
    }
    return nonce;
}

export async function encryptMessage(
    sequence: number,
    aesKey: Uint8Array,
    nonceBase: Uint8Array,
    plaintext: string,
    sessionId: string
): Promise<EncryptedMessage> {
    const nonce = xorNonce(nonceBase, sequence);
    const aad = new TextEncoder().encode(`${sessionId}:${sequence}`);
    const key = await window.crypto.subtle.importKey('raw', aesKey, { name: 'AES-GCM' }, false, ['encrypt']);

    const encrypted = await window.crypto.subtle.encrypt(
        { name: 'AES-GCM', iv: nonce, additionalData: aad },
        key,
        new TextEncoder().encode(plaintext)
    );

    const encryptedBytes = new Uint8Array(encrypted);
    const body = encryptedBytes.slice(0, -16);
    const tag = encryptedBytes.slice(-16);

    const btoaSafe = (bytes: Uint8Array) => {
        let bin = '';
        for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
        return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
    };

    return {
        sequence,
        nonce: btoaSafe(nonce),
        ciphertext: btoaSafe(body),
        auth_tag: btoaSafe(tag)
    };
}

export async function decryptMessage(
    aesKey: Uint8Array,
    nonceBase: Uint8Array,
    encryptedMessage: EncryptedMessage,
    aad: Uint8Array
): Promise<string> {
    const nonce = xorNonce(nonceBase, encryptedMessage.sequence);
    const key = await window.crypto.subtle.importKey('raw', aesKey, { name: 'AES-GCM' }, false, ['decrypt']);

    let ciphertextB64 = encryptedMessage.ciphertext.replace(/-/g, '+').replace(/_/g, '/');
    while (ciphertextB64.length % 4 !== 0) ciphertextB64 += '=';
    let tagB64 = encryptedMessage.auth_tag.replace(/-/g, '+').replace(/_/g, '/');
    while (tagB64.length % 4 !== 0) tagB64 += '=';

    const ciphertext = Uint8Array.from(atob(ciphertextB64), c => c.charCodeAt(0));
    const tag = Uint8Array.from(atob(tagB64), c => c.charCodeAt(0));

    const data = new Uint8Array(ciphertext.length + tag.length);
    data.set(ciphertext, 0);
    data.set(tag, ciphertext.length);

    const decrypted = await window.crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: nonce, additionalData: aad },
        key,
        data
    );

    return new TextDecoder().decode(decrypted);
}
