-- ============================================================
-- Migration 002: plan_case_relation 表支持动态分配设备
-- 适用数据库: MySQL 8.0+
-- 创建时间: 2026-08-02
--
-- 背景: 关联测试用例时允许不选择设备（动态分配）和不选择 YOLO 模型
--       （降级为纯 OCR 识别）。旧表结构中 device_id 等列为 NOT NULL，
--       导致插入/更新 device_id = NULL 时抛出:
--       IntegrityError: (1048, "Column 'device_id' cannot be null")
--
-- 修复: 将设备与 YOLO 相关列修改为允许 NULL（与模型定义保持一致）。
-- ============================================================

ALTER TABLE `plan_case_relation`
  MODIFY COLUMN `device_id`         VARCHAR(100) NULL COMMENT '设备ID，为空表示动态分配',
  MODIFY COLUMN `device_name`       VARCHAR(200) NULL COMMENT '设备名称，为空表示动态分配',
  MODIFY COLUMN `device_android_id` VARCHAR(64)  NULL COMMENT '设备Android ID',
  MODIFY COLUMN `yolo_model_id`     VARCHAR(50)  NULL COMMENT 'YOLO模型ID';
