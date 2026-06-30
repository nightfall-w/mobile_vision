-- ============================================================
-- MobileVision 数据库初始化脚本
-- 适用数据库: MySQL 8.0+
-- 创建时间: 2026-06-18
-- ============================================================

-- 创建数据库（如未创建）
-- CREATE DATABASE IF NOT EXISTS mobile_vision DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE mobile_vision;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- 1. 用户与认证
-- ============================================================

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id`          INT          NOT NULL AUTO_INCREMENT,
  `username`    VARCHAR(100) NOT NULL,
  `nickname`    VARCHAR(100) NOT NULL,
  `email`       VARCHAR(255) NOT NULL,
  `hashed_password` VARCHAR(255) NOT NULL,
  `is_deleted`  TINYINT(1)   DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`),
  INDEX `idx_username` (`username`),
  INDEX `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

DROP TABLE IF EXISTS `super_admins`;
CREATE TABLE `super_admins` (
  `id`         INT          NOT NULL AUTO_INCREMENT,
  `user_id`    INT          NOT NULL COMMENT '用户ID',
  `created_at` VARCHAR(30)  NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='超级管理员表';

-- ============================================================
-- 2. 工作空间
-- ============================================================

DROP TABLE IF EXISTS `workspace`;
CREATE TABLE `workspace` (
  `workspace_id`   INT           NOT NULL AUTO_INCREMENT COMMENT '工作空间ID',
  `workspace_name` VARCHAR(100)  NOT NULL COMMENT '工作空间名称',
  `workspace_desc` TEXT          NULL     COMMENT '工作空间描述',
  `create_user`    VARCHAR(100)  NOT NULL COMMENT '创建人信息',
  `update_user`    VARCHAR(100)  NOT NULL COMMENT '更新人信息',
  `manager`        JSON          NOT NULL COMMENT '管理员信息',
  `create_time`    DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`    DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted`     INT           DEFAULT 0 COMMENT '是否删除(0=未删除, 1=已删除)',
  PRIMARY KEY (`workspace_id`),
  INDEX `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作空间表';

DROP TABLE IF EXISTS `member_role`;
CREATE TABLE `member_role` (
  `role_id`          INT          NOT NULL AUTO_INCREMENT COMMENT '角色ID',
  `role_name`        VARCHAR(50)  NOT NULL COMMENT '角色名称',
  `role_description` TEXT         NULL     COMMENT '角色描述',
  `create_time`      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `uk_role_name` (`role_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='成员角色表';

DROP TABLE IF EXISTS `workspace_member`;
CREATE TABLE `workspace_member` (
  `id`           INT      NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `workspace_id` INT      NOT NULL COMMENT '工作空间ID',
  `username`     VARCHAR(100) NOT NULL COMMENT '成员username',
  `role_id`      INT      NOT NULL COMMENT '角色ID',
  `join_time`    DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间',
  `is_deleted`   INT      DEFAULT 0 COMMENT '是否删除(0=未删除, 1=已删除)',
  `create_time`  DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_workspace_id` (`workspace_id`),
  KEY `idx_username` (`username`),
  KEY `idx_role_id` (`role_id`),
  CONSTRAINT `fk_member_workspace` FOREIGN KEY (`workspace_id`) REFERENCES `workspace` (`workspace_id`),
  CONSTRAINT `fk_member_role`      FOREIGN KEY (`role_id`)      REFERENCES `member_role` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作空间成员表';

-- ============================================================
-- 3. 测试用例
-- ============================================================

DROP TABLE IF EXISTS `test_case`;
CREATE TABLE `test_case` (
  `case_id`            INT           NOT NULL AUTO_INCREMENT COMMENT '用例ID',
  `workspace_id`       INT           NOT NULL COMMENT '工作空间ID',
  `case_name`          VARCHAR(200)  NOT NULL COMMENT '用例名称',
  `case_desc`          TEXT          NULL     COMMENT '用例描述',
  `content`            TEXT          NULL     COMMENT '测试任务正文（支持Markdown）',
  `usage_instructions` TEXT          NULL     COMMENT 'APP使用说明（支持Markdown）',
  `author`             VARCHAR(100)  NOT NULL COMMENT '创建人用户名',
  `updater`            VARCHAR(100)  NOT NULL COMMENT '更新人用户名',
  `level`              ENUM('P0','P1','P2','P3') NOT NULL DEFAULT 'P2' COMMENT '优先级',
  `status`             ENUM('debugging','completed','disabled') NOT NULL DEFAULT 'debugging' COMMENT '状态',
  `is_deleted`         INT           DEFAULT 0 COMMENT '是否删除(0=未删除, 1=已删除)',
  `create_time`        DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`        DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`case_id`),
  KEY `idx_workspace_id` (`workspace_id`),
  KEY `idx_level` (`level`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`),
  CONSTRAINT `fk_case_workspace` FOREIGN KEY (`workspace_id`) REFERENCES `workspace` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试用例表';

-- ============================================================
-- 4. 测试计划
-- ============================================================

DROP TABLE IF EXISTS `test_plan`;
CREATE TABLE `test_plan` (
  `plan_id`      INT           NOT NULL AUTO_INCREMENT,
  `name`         VARCHAR(200)  NOT NULL COMMENT '计划名称',
  `description`  TEXT          NULL     COMMENT '计划描述',
  `workspace_id` INT           NOT NULL COMMENT '工作空间ID',
  `author`       VARCHAR(100)  NOT NULL COMMENT '创建人',
  `create_time`  DATETIME      DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`   TINYINT(1)    DEFAULT 0,
  PRIMARY KEY (`plan_id`),
  KEY `idx_workspace_id` (`workspace_id`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试计划表';

DROP TABLE IF EXISTS `plan_case_relation`;
CREATE TABLE `plan_case_relation` (
  `id`                INT           NOT NULL AUTO_INCREMENT,
  `plan_id`           INT           NOT NULL COMMENT '计划ID',
  `case_id`           INT           NOT NULL COMMENT '用例ID',
  `device_id`         VARCHAR(100)  NOT NULL COMMENT '设备ID',
  `device_name`       VARCHAR(200)  NULL     COMMENT '设备名称',
  `device_android_id` VARCHAR(64)   NULL     COMMENT '设备Android ID',
  `llm_credential_id` INT           NOT NULL COMMENT 'LLM凭证ID',
  `yolo_model_id`     VARCHAR(50)   NULL     COMMENT 'YOLO模型ID',
  `ocr_engine`        VARCHAR(20)   DEFAULT 'easyocr' COMMENT 'OCR引擎',
  `reasoning_effort`  VARCHAR(20)   DEFAULT 'none' COMMENT '推理强度',
  `is_deleted`        TINYINT(1)    DEFAULT 0,
  `create_time`       DATETIME      DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_plan_id` (`plan_id`),
  KEY `idx_case_id` (`case_id`),
  KEY `idx_device_id` (`device_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='计划用例关联表';

DROP TABLE IF EXISTS `device_lock`;
CREATE TABLE `device_lock` (
  `id`         INT           NOT NULL AUTO_INCREMENT,
  `device_id`  VARCHAR(100)  NOT NULL COMMENT '设备ID',
  `task_id`    INT           NULL,
  `plan_id`    INT           NULL,
  `locked_by`  VARCHAR(100)  NULL,
  `locked_at`  DATETIME      NULL,
  `expires_at` DATETIME      NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_device_id` (`device_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备锁表';

-- ============================================================
-- 5. 测试任务与执行
-- ============================================================

DROP TABLE IF EXISTS `test_task`;
CREATE TABLE `test_task` (
  `task_id`        INT           NOT NULL AUTO_INCREMENT,
  `workspace_id`   INT           DEFAULT 0  COMMENT '工作空间ID',
  `plan_id`        INT           NOT NULL COMMENT '计划ID',
  `task_name`      VARCHAR(200)  NOT NULL COMMENT '任务名称',
  `author`         VARCHAR(100)  NOT NULL COMMENT '创建人',
  `status`         VARCHAR(50)   DEFAULT 'pending' COMMENT '任务状态',
  `total_jobs`     INT           DEFAULT 0  COMMENT '总Job数',
  `completed_jobs` INT           DEFAULT 0  COMMENT '已完成Job数',
  `failed_jobs`    INT           DEFAULT 0  COMMENT '失败Job数',
  `aborted_jobs`   INT           DEFAULT 0  COMMENT '中止Job数',
  `running_jobs`   INT           DEFAULT 0  COMMENT '运行中Job数',
  `total_duration` INT           DEFAULT 0  COMMENT '总耗时(秒)',
  `is_deleted`     TINYINT(1)    DEFAULT 0,
  `create_time`    DATETIME      DEFAULT CURRENT_TIMESTAMP,
  `end_time`       DATETIME      NULL,
  `update_time`    DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`),
  KEY `idx_workspace_id` (`workspace_id`),
  KEY `idx_plan_id` (`plan_id`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试任务表';

DROP TABLE IF EXISTS `test_job`;
CREATE TABLE `test_job` (
  `job_id`            INT           NOT NULL AUTO_INCREMENT,
  `task_id`           INT           NOT NULL COMMENT '任务ID',
  `case_id`           INT           NOT NULL COMMENT '用例ID',
  `device_id`         VARCHAR(100)  NOT NULL COMMENT '设备ID',
  `device_name`       VARCHAR(200)  NULL     COMMENT '设备名称',
  `device_android_id` VARCHAR(100)  NULL     COMMENT '设备Android ID',
  `llm_credential_id` INT           NOT NULL COMMENT 'LLM凭证ID',
  `yolo_model_id`     VARCHAR(50)   NULL     COMMENT 'YOLO模型ID',
  `ocr_engine`        VARCHAR(20)   DEFAULT 'easyocr' COMMENT 'OCR引擎',
  `reasoning_effort`  VARCHAR(20)   DEFAULT 'none' COMMENT '推理强度',
  `is_deleted`        TINYINT(1)    DEFAULT 0,
  `status`            VARCHAR(50)   DEFAULT 'pending' COMMENT '执行状态',
  `result`            TEXT          NULL     COMMENT '执行结果',
  `start_time`        DATETIME      NULL     COMMENT '开始时间',
  `end_time`          DATETIME      NULL     COMMENT '结束时间',
  `duration`          INT           DEFAULT 0  COMMENT '耗时(秒)',
  `create_time`       DATETIME      DEFAULT CURRENT_TIMESTAMP,
  `update_time`       DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`job_id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_case_id` (`case_id`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`),
  CONSTRAINT `fk_job_task` FOREIGN KEY (`task_id`) REFERENCES `test_task` (`task_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试Job表（对应具体用例执行）';

-- ============================================================
-- 6. 设备管理
-- ============================================================

DROP TABLE IF EXISTS `android_devices`;
CREATE TABLE `android_devices` (
  `id`                VARCHAR(64)  NOT NULL COMMENT '设备ID',
  `android_id`        VARCHAR(64)  NULL     COMMENT '设备唯一标识(adb android_id)',
  `brand`             VARCHAR(100) DEFAULT 'Unknown' COMMENT '品牌',
  `model`             VARCHAR(100) DEFAULT 'Unknown' COMMENT '型号',
  `resolution`        VARCHAR(20)  DEFAULT 'Unknown' COMMENT '分辨率',
  `android_version`   VARCHAR(50)  DEFAULT 'Unknown' COMMENT '系统版本',
  `system_type`       VARCHAR(20)  DEFAULT 'android' COMMENT '系统类型(android/harmonyos)',
  `status`            VARCHAR(20)  DEFAULT 'disconnected' COMMENT '连接状态(connected/offline/disconnected)',
  `last_connected_at` DATETIME     NULL     COMMENT '最后连接时间',
  `is_deleted`        INT          DEFAULT 0 COMMENT '是否删除(0=未删除, 1=已删除)',
  `created_at`        DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '首次连接时间',
  `updated_at`        DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Android设备表';

-- ============================================================
-- 7. LLM 凭证
-- ============================================================

DROP TABLE IF EXISTS `llm_credential`;
CREATE TABLE `llm_credential` (
  `id`            INT           NOT NULL AUTO_INCREMENT COMMENT '凭证ID',
  `model`         VARCHAR(100)  NOT NULL COMMENT '模型名称',
  `api_key`       VARCHAR(500)  NOT NULL COMMENT 'API密钥',
  `base_url`      VARCHAR(500)  NOT NULL COMMENT '基础URL',
  `api_protocol`  VARCHAR(50)   NOT NULL COMMENT 'API协议类型(Anthropic/OpenAI)',
  `workspace_id`  INT           NULL     COMMENT '工作空间ID，为空表示系统级别配置',
  `is_active`     INT           DEFAULT 1  COMMENT '是否启用(1=启用, 0=禁用)',
  `is_deleted`    INT           DEFAULT 0  COMMENT '是否删除(0=未删除, 1=已删除)',
  `create_user`   VARCHAR(100)  NOT NULL COMMENT '创建人',
  `update_user`   VARCHAR(100)  NOT NULL COMMENT '更新人',
  `create_time`   DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`   DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_workspace_id` (`workspace_id`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_is_deleted` (`is_deleted`),
  CONSTRAINT `fk_llm_workspace` FOREIGN KEY (`workspace_id`) REFERENCES `workspace` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='LLM凭证表';

-- ============================================================
-- 8. YOLO 数据集、训练、模型
-- ============================================================

DROP TABLE IF EXISTS `yolo_datasets`;
CREATE TABLE `yolo_datasets` (
  `id`              VARCHAR(8)   NOT NULL COMMENT '数据集ID',
  `name`            VARCHAR(255) NOT NULL COMMENT '数据集名称',
  `description`     TEXT         NULL     COMMENT '数据集描述',
  `classes`         JSON         NOT NULL COMMENT '类别列表',
  `class_count`     INT          DEFAULT 0  COMMENT '类别数量',
  `image_count`     INT          DEFAULT 0  COMMENT '图片数量',
  `label_count`     INT          DEFAULT 0  COMMENT '标注数量',
  `data_yaml_path`  VARCHAR(512) NULL     COMMENT '生成的data.yaml路径',
  `created_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted`      INT          DEFAULT 0  COMMENT '是否删除(0=未删除, 1=已删除)',
  PRIMARY KEY (`id`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='YOLO数据集表';

DROP TABLE IF EXISTS `yolo_tasks`;
CREATE TABLE `yolo_tasks` (
  `id`                VARCHAR(8)    NOT NULL COMMENT '任务ID',
  `dataset_id`        VARCHAR(8)    NOT NULL COMMENT '数据集ID',
  `model_name`        VARCHAR(512)  DEFAULT 'yolov8n.pt' COMMENT '预训练模型名称',
  `config`            JSON          NOT NULL COMMENT '训练配置',
  `status`            VARCHAR(20)   DEFAULT 'pending' COMMENT '任务状态',
  `progress`          FLOAT         DEFAULT 0.0 COMMENT '训练进度 0-100',
  `current_epoch`     INT           DEFAULT 0  COMMENT '当前轮次',
  `total_epochs`      INT           DEFAULT 0  COMMENT '总轮次',
  `start_time`        DATETIME      NULL     COMMENT '开始时间',
  `end_time`          DATETIME      NULL     COMMENT '结束时间',
  `metrics`           JSON          NULL     COMMENT '训练指标',
  `error_message`     TEXT          NULL     COMMENT '错误信息',
  `result_model_path` VARCHAR(512)  NULL     COMMENT '训练结果模型路径',
  `train_dir`         VARCHAR(512)  NULL     COMMENT '训练目录路径',
  `created_at`        DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`        DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted`        INT           DEFAULT 0  COMMENT '是否删除(0=未删除, 1=已删除)',
  PRIMARY KEY (`id`),
  KEY `idx_dataset_id` (`dataset_id`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='YOLO训练任务表';

DROP TABLE IF EXISTS `yolo_models`;
CREATE TABLE `yolo_models` (
  `id`         VARCHAR(8)    NOT NULL COMMENT '模型ID',
  `task_id`    VARCHAR(8)    NULL     COMMENT '训练任务ID',
  `dataset_id` VARCHAR(8)    NOT NULL COMMENT '数据集ID',
  `name`       VARCHAR(255)  NOT NULL COMMENT '模型名称',
  `path`       VARCHAR(512)  NOT NULL COMMENT '模型文件路径',
  `size`       INT           DEFAULT 0  COMMENT '模型大小(字节)',
  `metrics`    JSON          NULL     COMMENT '模型指标',
  `classes`    JSON          NOT NULL COMMENT '类别列表',
  `created_at` DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `is_deleted` INT           DEFAULT 0  COMMENT '是否删除(0=未删除, 1=已删除)',
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_dataset_id` (`dataset_id`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='YOLO模型表';

-- ============================================================
-- 9. 任务执行记录（持久化）
-- ============================================================

DROP TABLE IF EXISTS `task_execution_record`;
CREATE TABLE `task_execution_record` (
  `id`            INT       NOT NULL AUTO_INCREMENT,
  `task_id`       INT       NOT NULL COMMENT '任务ID',
  `status`        VARCHAR(50) NOT NULL COMMENT '任务状态',
  `total_steps`   INT       DEFAULT 0,
  `success_steps` INT       DEFAULT 0,
  `failed_steps`  INT       DEFAULT 0,
  `task_list`     JSON      NULL     COMMENT '任务列表快照',
  `start_time`    DATETIME  NULL,
  `end_time`      DATETIME  NULL,
  `created_at`    DATETIME  DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务执行记录表';

DROP TABLE IF EXISTS `task_execution_log`;
CREATE TABLE `task_execution_log` (
  `id`        INT          NOT NULL AUTO_INCREMENT,
  `task_id`   INT          NOT NULL COMMENT '任务ID',
  `level`     VARCHAR(20)  NOT NULL COMMENT '日志级别',
  `message`   TEXT         NOT NULL COMMENT '日志内容',
  `timestamp` DATETIME     NOT NULL COMMENT '日志时间',
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务执行日志表';

-- ============================================================
-- 10. 初始化默认数据
-- ============================================================

-- 默认角色（使用 IGNORE 避免重复插入）
INSERT IGNORE INTO `member_role` (`role_id`, `role_name`, `role_description`) VALUES
(1, '开发', '负责软件开发工作的技术人员'),
(2, '测试', '负责软件测试工作的技术人员'),
(3, '产品', '负责产品设计和规划的人员'),
(4, '项目经理', '负责项目管理和协调的人员'),
(7, '管理员', '拥有workspace下所有权限');

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 完成！
-- ============================================================
