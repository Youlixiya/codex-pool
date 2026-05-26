-- Per-user upstream isolation: each user manages their own Codex pool.
ALTER TABLE upstreams
    ADD COLUMN user_id BIGINT NULL AFTER id;

UPDATE upstreams u
JOIN (
    SELECT id FROM users ORDER BY id ASC LIMIT 1
) admin ON 1 = 1
SET u.user_id = admin.id
WHERE u.user_id IS NULL;

ALTER TABLE upstreams
    MODIFY COLUMN user_id BIGINT NOT NULL,
    ADD INDEX idx_upstreams_user (user_id),
    ADD CONSTRAINT fk_upstreams_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE upstreams
    DROP INDEX name;

ALTER TABLE upstreams
    ADD UNIQUE KEY uq_upstreams_user_name (user_id, name);
