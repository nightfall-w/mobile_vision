-- ============================================================
-- Migration 003: test_plan 表支持 Cron 定时调度
-- 适用数据库: MySQL 8.0+
-- 创建时间: 2026-08-04
--
-- 背景: 测试计划支持按 Cron 表达式定时/周期执行，无需人工点击执行。
--       定时任务基于 funboost 的 ApsJobAdder，jobstore 使用 Redis，
--       数据库仅需持久化计划的定时配置本身。
--
-- 变更: test_plan 表新增三列。
--       enable_schedule          — 定时开关，默认关闭，不影响存量计划
--       schedule_cron_expression — 6 段 Cron 表达式（秒 分 时 日 月 周）
--       schedule_task_id         — APScheduler job id，格式 testplan_{plan_id}
--
-- 注意: MySQL 不支持 ALTER TABLE ... ADD COLUMN IF NOT EXISTS（那是 MariaDB 语法），
--       故用存储过程判断 information_schema 实现幂等，可重复执行。
-- ============================================================

DROP PROCEDURE IF EXISTS `_migration_003`;

DELIMITER $$

CREATE PROCEDURE `_migration_003`()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS
                 WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'test_plan'
                   AND COLUMN_NAME = 'enable_schedule') THEN
    ALTER TABLE `test_plan`
      ADD COLUMN `enable_schedule` TINYINT(1) NOT NULL DEFAULT 0
      COMMENT '是否启用定时执行' AFTER `author`;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS
                 WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'test_plan'
                   AND COLUMN_NAME = 'schedule_cron_expression') THEN
    ALTER TABLE `test_plan`
      ADD COLUMN `schedule_cron_expression` VARCHAR(200) NULL
      COMMENT 'Cron表达式(6段: 秒 分 时 日 月 周)' AFTER `enable_schedule`;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS
                 WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'test_plan'
                   AND COLUMN_NAME = 'schedule_task_id') THEN
    ALTER TABLE `test_plan`
      ADD COLUMN `schedule_task_id` VARCHAR(100) NULL
      COMMENT 'APScheduler任务ID，格式 testplan_{plan_id}' AFTER `schedule_cron_expression`;
  END IF;

  -- 便于按开关快速筛出启用了定时的计划（服务启动时需重建定时任务）
  IF NOT EXISTS (SELECT 1 FROM information_schema.STATISTICS
                 WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'test_plan'
                   AND INDEX_NAME = 'idx_enable_schedule') THEN
    ALTER TABLE `test_plan` ADD INDEX `idx_enable_schedule` (`enable_schedule`);
  END IF;
END$$

DELIMITER ;

CALL `_migration_003`();

DROP PROCEDURE `_migration_003`;
