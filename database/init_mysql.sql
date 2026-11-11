-- =====================================================================
-- WARISCRYPT Database Initialization Script for MySQL 8.0 / MariaDB
-- Character Set: utf8mb4, Collation: utf8mb4_unicode_ci
-- Storage Engine: InnoDB
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `wariscrypt`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `wariscrypt`;

SET FOREIGN_KEY_CHECKS = 0;

-- 1. users
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `user_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(50) NOT NULL,
  `email` VARCHAR(150) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` ENUM('owner', 'beneficiary') NOT NULL DEFAULT 'owner',
  `account_status` ENUM('active', 'suspended', 'disabled') NOT NULL DEFAULT 'active',
  `email_verified_at` DATETIME NULL,
  `last_login_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uq_users_username` (`username`),
  UNIQUE KEY `uq_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. user_profiles
DROP TABLE IF EXISTS `user_profiles`;
CREATE TABLE `user_profiles` (
  `profile_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `full_name` VARCHAR(120) NOT NULL,
  `phone_number` VARCHAR(25) NULL,
  `profile_photo_path` VARCHAR(500) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`profile_id`),
  UNIQUE KEY `uq_profiles_user_id` (`user_id`),
  CONSTRAINT `fk_profiles_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. biometric_templates
DROP TABLE IF EXISTS `biometric_templates`;
CREATE TABLE `biometric_templates` (
  `biometric_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `template_path` VARCHAR(500) NOT NULL,
  `template_version` VARCHAR(30) NULL,
  `consent_status` BOOLEAN NOT NULL DEFAULT FALSE,
  `consented_at` DATETIME NULL,
  `status` ENUM('active', 'revoked', 'deleted') NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`biometric_id`),
  KEY `idx_bio_user_id` (`user_id`),
  CONSTRAINT `fk_biometrics_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. usb_devices
DROP TABLE IF EXISTS `usb_devices`;
CREATE TABLE `usb_devices` (
  `device_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `device_name` VARCHAR(100) NULL,
  `device_fingerprint` VARCHAR(255) NOT NULL,
  `public_key_fingerprint` VARCHAR(255) NULL,
  `device_status` ENUM('active', 'revoked', 'lost') NOT NULL DEFAULT 'active',
  `registered_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_used_at` DATETIME NULL,
  PRIMARY KEY (`device_id`),
  UNIQUE KEY `uq_usb_fingerprint` (`device_fingerprint`),
  KEY `idx_usb_user_status` (`user_id`, `device_status`),
  CONSTRAINT `fk_usb_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. beneficiaries
DROP TABLE IF EXISTS `beneficiaries`;
CREATE TABLE `beneficiaries` (
  `beneficiary_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `owner_id` BIGINT UNSIGNED NOT NULL,
  `beneficiary_user_id` BIGINT UNSIGNED NOT NULL,
  `relationship` VARCHAR(50) NULL,
  `status` ENUM('active', 'inactive', 'revoked') NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`beneficiary_id`),
  UNIQUE KEY `uq_owner_beneficiary` (`owner_id`, `beneficiary_user_id`),
  KEY `idx_ben_user_status` (`beneficiary_user_id`, `status`),
  CONSTRAINT `fk_ben_owner` FOREIGN KEY (`owner_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ben_user` FOREIGN KEY (`beneficiary_user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. beneficiary_reference_images
DROP TABLE IF EXISTS `beneficiary_reference_images`;
CREATE TABLE `beneficiary_reference_images` (
  `image_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `beneficiary_id` BIGINT UNSIGNED NOT NULL,
  `image_path` VARCHAR(500) NOT NULL,
  `consent_confirmed` BOOLEAN NOT NULL DEFAULT FALSE,
  `uploaded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status` ENUM('active', 'revoked', 'deleted') NOT NULL DEFAULT 'active',
  PRIMARY KEY (`image_id`),
  KEY `idx_ref_img_ben` (`beneficiary_id`),
  CONSTRAINT `fk_ref_img_ben` FOREIGN KEY (`beneficiary_id`) REFERENCES `beneficiaries` (`beneficiary_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. encryption_keys
DROP TABLE IF EXISTS `encryption_keys`;
CREATE TABLE `encryption_keys` (
  `key_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `key_identifier` VARCHAR(255) NOT NULL,
  `algorithm` VARCHAR(50) NOT NULL,
  `key_version` INT UNSIGNED NOT NULL DEFAULT 1,
  `key_status` ENUM('active', 'rotated', 'revoked') NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `rotated_at` DATETIME NULL,
  PRIMARY KEY (`key_id`),
  UNIQUE KEY `uq_key_identifier` (`key_identifier`),
  KEY `idx_key_user_status` (`user_id`, `key_status`),
  CONSTRAINT `fk_keys_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. digital_assets
DROP TABLE IF EXISTS `digital_assets`;
CREATE TABLE `digital_assets` (
  `asset_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `owner_id` BIGINT UNSIGNED NOT NULL,
  `asset_name` VARCHAR(150) NOT NULL,
  `asset_type` ENUM('message', 'document') NOT NULL,
  `original_filename` VARCHAR(255) NULL,
  `encrypted_file_path` VARCHAR(500) NOT NULL,
  `mime_type` VARCHAR(100) NULL,
  `file_size` BIGINT UNSIGNED NULL,
  `encryption_algorithm` VARCHAR(50) NOT NULL,
  `key_id` BIGINT UNSIGNED NULL,
  `nonce` VARCHAR(255) NULL,
  `auth_tag` VARCHAR(255) NULL,
  `asset_status` ENUM('active', 'archived', 'deleted') NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`asset_id`),
  KEY `idx_asset_owner_status` (`owner_id`, `asset_status`),
  CONSTRAINT `fk_asset_owner` FOREIGN KEY (`owner_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_asset_key` FOREIGN KEY (`key_id`) REFERENCES `encryption_keys` (`key_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. asset_permissions
DROP TABLE IF EXISTS `asset_permissions`;
CREATE TABLE `asset_permissions` (
  `permission_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `asset_id` BIGINT UNSIGNED NOT NULL,
  `beneficiary_id` BIGINT UNSIGNED NOT NULL,
  `access_status` ENUM('pending', 'authorized', 'revoked') NOT NULL DEFAULT 'authorized',
  `release_status` ENUM('locked', 'released') NOT NULL DEFAULT 'locked',
  `released_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`permission_id`),
  UNIQUE KEY `uq_asset_beneficiary` (`asset_id`, `beneficiary_id`),
  KEY `idx_perm_ben_release` (`beneficiary_id`, `release_status`),
  CONSTRAINT `fk_perm_asset` FOREIGN KEY (`asset_id`) REFERENCES `digital_assets` (`asset_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_perm_beneficiary` FOREIGN KEY (`beneficiary_id`) REFERENCES `beneficiaries` (`beneficiary_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. claim_tokens
DROP TABLE IF EXISTS `claim_tokens`;
CREATE TABLE `claim_tokens` (
  `token_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `beneficiary_id` BIGINT UNSIGNED NOT NULL,
  `asset_id` BIGINT UNSIGNED NULL,
  `token_hash` VARCHAR(255) NOT NULL,
  `token_ciphertext` TEXT NULL,
  `expiry_date` DATETIME NULL,
  `token_status` ENUM('active', 'used', 'revoked', 'expired') NOT NULL DEFAULT 'active',
  `used_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`token_id`),
  UNIQUE KEY `uq_token_hash` (`token_hash`),
  KEY `idx_token_ben_status_exp` (`beneficiary_id`, `token_status`, `expiry_date`),
  CONSTRAINT `fk_token_ben` FOREIGN KEY (`beneficiary_id`) REFERENCES `beneficiaries` (`beneficiary_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_token_asset` FOREIGN KEY (`asset_id`) REFERENCES `digital_assets` (`asset_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. inheritance_claims
DROP TABLE IF EXISTS `inheritance_claims`;
CREATE TABLE `inheritance_claims` (
  `claim_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `beneficiary_id` BIGINT UNSIGNED NOT NULL,
  `token_id` BIGINT UNSIGNED NOT NULL,
  `uploaded_image_path` VARCHAR(500) NULL,
  `claim_status` ENUM('pending', 'approved', 'rejected', 'expired') NOT NULL DEFAULT 'pending',
  `reviewed_at` DATETIME NULL,
  `submitted_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`claim_id`),
  KEY `idx_claim_ben_status` (`beneficiary_id`, `claim_status`),
  KEY `idx_claim_token` (`token_id`),
  CONSTRAINT `fk_claim_ben` FOREIGN KEY (`beneficiary_id`) REFERENCES `beneficiaries` (`beneficiary_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_claim_token` FOREIGN KEY (`token_id`) REFERENCES `claim_tokens` (`token_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. claim_verifications
DROP TABLE IF EXISTS `claim_verifications`;
CREATE TABLE `claim_verifications` (
  `verification_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `claim_id` BIGINT UNSIGNED NOT NULL,
  `verification_type` ENUM('token', 'face_matching', 'additional') NOT NULL,
  `verification_result` ENUM('pending', 'passed', 'failed') NOT NULL DEFAULT 'pending',
  `similarity_score` DECIMAL(6, 5) NULL,
  `failure_reason_code` VARCHAR(50) NULL,
  `verified_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`verification_id`),
  KEY `idx_verif_claim_type` (`claim_id`, `verification_type`),
  CONSTRAINT `fk_verif_claim` FOREIGN KEY (`claim_id`) REFERENCES `inheritance_claims` (`claim_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. audit_logs (Simple Blockchain / Tamper-evident ledger)
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs` (
  `log_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NULL,
  `activity_type` VARCHAR(100) NOT NULL,
  `entity_type` VARCHAR(50) NULL,
  `entity_id` BIGINT UNSIGNED NULL,
  `event_metadata` JSON NULL,
  `previous_hash` CHAR(64) NULL,
  `current_hash` CHAR(64) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`log_id`),
  KEY `idx_audit_user_created` (`user_id`, `created_at`),
  KEY `idx_audit_entity` (`entity_type`, `entity_id`),
  KEY `idx_audit_created` (`created_at`),
  CONSTRAINT `fk_audit_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
