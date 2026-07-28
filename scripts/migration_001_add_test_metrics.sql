-- ============================================================
-- Migration 001: YOLO 模型表增加测试集评估字段
-- 适用数据库: MySQL 8.0+
-- 创建时间: 2026-07-28
-- ============================================================

ALTER TABLE `yolo_models`
  ADD COLUMN `test_metrics` JSON NULL COMMENT '测试集指标' AFTER `metrics`,
  ADD COLUMN `test_status` VARCHAR(20) DEFAULT 'untested' COMMENT '测试集评估状态(untested/pending/running/completed/failed)' AFTER `test_metrics`;