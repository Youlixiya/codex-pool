-- Store full API key for admin UI copy / CC Switch deep link (self-hosted).
ALTER TABLE api_keys
    ADD COLUMN key_secret VARCHAR(512) NULL AFTER key_prefix;
