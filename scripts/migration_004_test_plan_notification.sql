-- ============================================================
-- Migration 004: test_plan 表支持任务完成通知
-- 适用数据库: MySQL 8.0+
-- 创建时间: 2026-08-06
--
-- 背景: 测试计划执行完成后，可通过 Webhook 推送结果到企业微信、
--       飞书、钉钉等团队协作平台，实现无人值守的自动化测试闭环。
--
-- 变更: test_plan 表新增 6 列。
--       enable_notification    — 通知开关，默认关闭
--       notify_on_failure_only — 仅失败时通知
--       wecom_webhooks         — 企业微信机器人 Webhook URL 列表
--       lark_webhooks          — 飞书机器人 Webhook URL 列表
--       dingtalk_webhooks      — 钉钉机器人 Webhook URL 列表
--
-- 幂等性: 使用存储过程查 information_schema 判断，可重复执行。
-- ============================================================

DROP PROCEDURE IF EXISTS `_migration_004`;

DELIMITER $$

CREATE PROCEDURE `_migration_004`()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS
                 WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'test_plan'
                   AND COLUMN_NAME = 'enable_notification') THEN
    ALTER TABLE `test_plan`
      ADD COLUMN `enable_notification`    TINYINT(1) NOT NULL DEFAULT 0
      COMMENT '是否发送通知' AFTER `schedule_task_id`;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS
                 WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'test_plan'
                   AND COLUMN_NAME = 'notify_on_failure_only') THEN
    ALTER TABLE `test_plan`
      ADD COLUMN `notify_on_failure_only` TINYINT(1) NOT NULL DEFAULT 0
      COMMENT '仅失败时通知' AFTER `enable_notification`;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS
                 WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'test_plan'
                   AND COLUMN_NAME = 'wecom_webhooks') THEN
    ALTER TABLE `test_plan`
      ADD COLUMN `wecom_webhooks`    JSON NULL
      COMMENT '企微机器人webhook列表' AFTER `notify_on_failure_only`;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS
                 WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'test_plan'
                   AND COLUMN_NAME = 'lark_webhooks') THEN
    ALTER TABLE `test_plan`
      ADD COLUMN `lark_webhooks`     JSON NULL
      COMMENT '飞书机器人webhook列表' AFTER `wecom_webhooks`;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS
                 WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'test_plan'
                   AND COLUMN_NAME = 'dingtalk_webhooks') THEN
    ALTER TABLE `test_plan`
      ADD COLUMN `dingtalk_webhooks` JSON NULL
      COMMENT '钉钉机器人webhook列表' AFTER `lark_webhooks`;
  END IF;
END$$

DELIMITER ;

CALL `_migration_004`();

DROP PROCEDURE `_migration_004`;