-- ============================================================
-- Telegram 聊天记录分析系统 - MySQL 数据库
-- ============================================================

-- 1. 用户表 (user)
CREATE TABLE IF NOT EXISTS `user` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `first_name` VARCHAR(100) NOT NULL,
    `username` VARCHAR(100) NOT NULL UNIQUE,
    `phone` VARCHAR(20) DEFAULT NULL,
    `chats_count` INT DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `is_active` INT DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX `idx_user_username` ON `user`(`username`);
CREATE INDEX `idx_user_phone` ON `user`(`phone`);

-- 2. 联系人/群组表 (contact)
CREATE TABLE IF NOT EXISTS `contact` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `is_group` INT DEFAULT 0,
    `message_count` INT DEFAULT 0,
    `ignore` INT DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `is_active` INT DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX `idx_contact_ignore` ON `contact`(`ignore`);
CREATE INDEX `idx_contact_user_id` ON `contact`(`user_id`);

-- ============================================================
-- 消息表 (message) - 整合 chat_message 功能
-- ============================================================
CREATE TABLE IF NOT EXISTS `message` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `task_id` INT,
    `user_id` INT NOT NULL,
    `contact_id` INT NOT NULL,
    `sender` VARCHAR(200) NOT NULL,
    `content` TEXT NOT NULL,
    `timestamp` DATETIME NOT NULL,
    `message_type` VARCHAR(20) DEFAULT 'text',
    `raw_content` TEXT,
    `clean_content` TEXT,
    `path` VARCHAR(500) DEFAULT NULL,
    `extra_info` TEXT,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX `idx_message_task_id` ON `message`(`task_id`);
CREATE INDEX `idx_message_contact_id` ON `message`(`contact_id`);
CREATE INDEX `idx_message_user_contact` ON `message`(`user_id`, `contact_id`);
CREATE INDEX `idx_message_send_time` ON `message`(`timestamp`);
CREATE INDEX `idx_message_msg_type` ON `message`(`message_type`);

-- ============================================================
-- 分析结果表 (analysis_result) - 整合 ai_analysis_result 功能
-- ============================================================
CREATE TABLE IF NOT EXISTS `analysis_result` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `task_id` INT,
    `contact_id` INT NOT NULL,
    `result_type` VARCHAR(50) NOT NULL,
    `analysis_type` VARCHAR(50) NOT NULL,
    `map_summary` TEXT,
    `summary` TEXT,
    `content` TEXT,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `is_active` INT DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX `idx_analysis_task_id` ON `analysis_result`(`task_id`);
CREATE INDEX `idx_analysis_contact_id` ON `analysis_result`(`contact_id`);

-- ============================================================
-- 任务表 (task)
-- ============================================================
CREATE TABLE IF NOT EXISTS `task` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(200) NOT NULL,
    `status` VARCHAR(20) DEFAULT 'pending',
    `message_count` INT DEFAULT 0,
    `error_message` TEXT,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX `idx_task_status` ON `task`(`status`);

-- ============================================================
-- 敏感信息表 (extracted_info)
-- ============================================================
CREATE TABLE IF NOT EXISTS `extracted_info` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `task_id` INT NOT NULL,
    `message_id` INT,
    `contact_id` INT,
    `info_type` VARCHAR(50) NOT NULL,
    `value` TEXT NOT NULL,
    `context` TEXT,
    `confidence` REAL DEFAULT 0.0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `is_active` INT DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX `idx_extracted_info_task_id` ON `extracted_info`(`task_id`);
CREATE INDEX `idx_extracted_info_type` ON `extracted_info`(`info_type`);
CREATE INDEX `idx_extracted_info_message_id` ON `extracted_info`(`message_id`);
CREATE INDEX `idx_extracted_info_contact_id` ON `extracted_info`(`contact_id`);
