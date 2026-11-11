def vigenere_encrypt(plaintext: str, key: str) -> str:
    """
    Educational demonstration cipher: Vigenère cipher.
    NOTE: As stated in PRD 4.4, this cipher is for educational purposes only
    and is not cryptographically secure for real data.
    """
    key = "".join([c.upper() for c in key if c.isalpha()])
    if not key:
        key = "WARISCRYPT"
    
    result = []
    key_idx = 0
    for char in plaintext:
        if char.isalpha():
            is_upper = char.isupper()
            base = ord('A') if is_upper else ord('a')
            shift = ord(key[key_idx % len(key)]) - ord('A')
            encrypted_char = chr((ord(char) - base + shift) % 26 + base)
            result.append(encrypted_char)
            key_idx += 1
        else:
            result.append(char)
    return "".join(result)

def vigenere_decrypt(ciphertext: str, key: str) -> str:
    """Decrypt educational Vigenère ciphertext."""
    key = "".join([c.upper() for c in key if c.isalpha()])
    if not key:
        key = "WARISCRYPT"
    
    result = []
    key_idx = 0
    for char in ciphertext:
        if char.isalpha():
            is_upper = char.isupper()
            base = ord('A') if is_upper else ord('a')
            shift = ord(key[key_idx % len(key)]) - ord('A')
            decrypted_char = chr((ord(char) - base - shift + 26) % 26 + base)
            result.append(decrypted_char)
            key_idx += 1
        else:
            result.append(char)
    return "".join(result)
