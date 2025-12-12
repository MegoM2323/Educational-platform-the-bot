-- Migration: 0005_add_broadcast_models
-- Generated for SQLite

-- Create Broadcast table
CREATE TABLE "notifications_broadcast" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "target_group" varchar(20) NOT NULL,
    "target_filter" text NOT NULL,
    "message" text NOT NULL,
    "recipient_count" integer NOT NULL,
    "sent_count" integer NOT NULL,
    "failed_count" integer NOT NULL,
    "status" varchar(20) NOT NULL,
    "scheduled_at" datetime NULL,
    "sent_at" datetime NULL,
    "completed_at" datetime NULL,
    "created_at" datetime NOT NULL,
    "updated_at" datetime NOT NULL,
    "created_by_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Create BroadcastRecipient table
CREATE TABLE "notifications_broadcastrecipient" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "telegram_sent" bool NOT NULL,
    "telegram_message_id" varchar(100) NULL,
    "telegram_error" text NULL,
    "sent_at" datetime NULL,
    "broadcast_id" bigint NOT NULL REFERENCES "notifications_broadcast" ("id") DEFERRABLE INITIALLY DEFERRED,
    "recipient_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Create indexes for Broadcast
CREATE INDEX "notificatio_created_444a5f_idx" ON "notifications_broadcast" ("created_by_id", "created_at" DESC);
CREATE INDEX "notificatio_status_ca8ad6_idx" ON "notifications_broadcast" ("status", "scheduled_at");
CREATE INDEX "notifications_broadcast_created_by_id_b7f7c7a9" ON "notifications_broadcast" ("created_by_id");

-- Create indexes and unique constraint for BroadcastRecipient
CREATE INDEX "notificatio_broadca_2cf2a0_idx" ON "notifications_broadcastrecipient" ("broadcast_id", "telegram_sent");
CREATE INDEX "notificatio_recipie_6365a1_idx" ON "notifications_broadcastrecipient" ("recipient_id", "broadcast_id");
CREATE INDEX "notifications_broadcastrecipient_broadcast_id_75c9c0e8" ON "notifications_broadcastrecipient" ("broadcast_id");
CREATE INDEX "notifications_broadcastrecipient_recipient_id_a3b4c2d1" ON "notifications_broadcastrecipient" ("recipient_id");
CREATE UNIQUE INDEX "notifications_broadcastrecipient_broadcast_id_recipient_id_unique" ON "notifications_broadcastrecipient" ("broadcast_id", "recipient_id");

-- Insert migration record
INSERT INTO django_migrations (app, name, applied) VALUES ('notifications', '0005_add_broadcast_models', datetime('now'));
