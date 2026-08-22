-- ============================================================
-- Migration 005: 新增 system_config 系统配置表
-- 适用数据库: MySQL 8.0+
-- 创建时间: 2026-08-20
--
-- 背景: 任务完成通知里的 HTML 报告链接与 Job 监控页链接，此前由本机 IP
--       加 BACKEND_PORT/FRONTEND_PORT 拼出，换部署环境或走反向代理时
--       链接不可用。改为可在「系统配置管理」页面维护。
--
-- 变更: 新增 system_config 表，并预置两个配置项。
--       BACKEND_BASE_URL  — 后端对外地址，报告链接前缀
--       FRONTEND_BASE_URL — 前端对外地址，Job 监控页链接前缀
--       两者留空时代码回退为原有本机 IP 逻辑，故老部署无需立即配置。
--
-- 注意: 部分环境残留一张同名旧表（早期引入、无对应后端代码，字段为
--       allowed_to_delete 等），其结构与本表不兼容。迁移检测到旧表时
--       改名为 system_config_legacy_bak 留存，不直接删除，确认无用后可手工清理。
--
-- 幂等性: 用存储过程查 information_schema 判断，预置数据用 INSERT IGNORE
--         配合 uk_key 唯一键，可重复执行。
-- ============================================================

DROP PROCEDURE IF EXISTS `_migration_005`;

DELIMITER $$

CREATE PROCEDURE `_migration_005`()
BEGIN
  -- 旧表以 allowed_to_delete 列为特征；存在则改名留存，让下面重新建表
  IF EXISTS (SELECT 1 FROM information_schema.COLUMNS
             WHERE TABLE_SCHEMA = DATABASE()
               AND TABLE_NAME = 'system_config'
               AND COLUMN_NAME = 'allowed_to_delete') THEN
    DROP TABLE IF EXISTS `system_config_legacy_bak`;
    RENAME TABLE `system_config` TO `system_config_legacy_bak`;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLES
                 WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'system_config') THEN
    CREATE TABLE `system_config` (
      `id`          INT          NOT NULL AUTO_INCREMENT COMMENT '配置项ID',
      `key`         VARCHAR(100) NOT NULL COMMENT '配置项键名',
      `value`       TEXT         NULL     COMMENT '配置项值（统一按字符串存，按 type 解析）',
      `desc`        VARCHAR(500) NULL     COMMENT '配置项描述',
      `type`        VARCHAR(20)  NOT NULL DEFAULT 'STRING' COMMENT '值类型(STRING/NUMBER/BOOLEAN/DICT/LIST)',
      `required`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否必填',
      `verified`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否通过可用性验证',
      `update_user` VARCHAR(100) NULL     COMMENT '更新人',
      `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
      `update_time` DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_key` (`key`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';
  END IF;
END$$

DELIMITER ;

CALL `_migration_005`();

DROP PROCEDURE `_migration_005`;

-- 预置配置项（uk_key 保证重复执行不会插入重复行）
INSERT IGNORE INTO `system_config` (`key`, `value`, `desc`, `type`, `required`) VALUES
('BACKEND_BASE_URL',  '', '后端服务对外访问地址（含协议与端口，如 http://mv.example.com:8080）。通知消息里的 HTML 报告链接以此为前缀。留空则回退为本机 IP + BACKEND_PORT。', 'STRING', 0),
('FRONTEND_BASE_URL', '', '前端页面对外访问地址（含协议与端口，如 http://mv.example.com:5173）。报告中的 Job 监控页跳转链接以此为前缀。留空则回退为本机 IP + FRONTEND_PORT。', 'STRING', 0);
