/**
 * Cron 表达式工具
 *
 * 重要：后端用 APScheduler，周字段约定 0=周一 … 6=周日；
 * 而前端预览用的 cron-parser 遵循标准 cron，0=周日 … 6=周六。
 * 两者相反，故预览前必须转换周字段，否则"每周一"会预览成周日。
 */
import { CronExpressionParser } from 'cron-parser'

/** 频率类型（简单模式的一级选择） */
export const FREQ = {
  MINUTE: 'minute',   // 每 N 分钟
  HOURLY: 'hourly',   // 每 N 小时的固定分秒
  DAILY: 'daily',     // 每天固定时刻
  WEEKLY: 'weekly',   // 每周指定星期的固定时刻
  MONTHLY: 'monthly', // 每月指定日期的固定时刻
}

export const FREQ_OPTIONS = [
  { value: FREQ.MINUTE, label: '按分钟' },
  { value: FREQ.HOURLY, label: '按小时' },
  { value: FREQ.DAILY, label: '每天' },
  { value: FREQ.WEEKLY, label: '每周' },
  { value: FREQ.MONTHLY, label: '每月' },
]

/** 星期选项，value 按 APScheduler 约定 0=周一 */
export const WEEKDAY_OPTIONS = [
  { value: 0, label: '一' },
  { value: 1, label: '二' },
  { value: 2, label: '三' },
  { value: 3, label: '四' },
  { value: 4, label: '五' },
  { value: 5, label: '六' },
  { value: 6, label: '日' },
]

const WEEKDAY_FULL = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

/** 简单模式的默认配置 */
export function defaultScheduleConfig() {
  return {
    freq: FREQ.DAILY,
    interval: 30,        // 按分钟/小时时的间隔
    weekdays: [0],       // 每周：选中的星期（APScheduler 约定）
    monthDays: [1],      // 每月：选中的日期
    time: '02:00',       // 固定时刻 HH:mm
  }
}

/** 从 'HH:mm' 取出时、分 */
function splitTime(time) {
  const [h = '0', m = '0'] = String(time || '').split(':')
  return { hour: parseInt(h, 10) || 0, minute: parseInt(m, 10) || 0 }
}

/**
 * 简单模式配置 → 6 段 cron 表达式（周字段按 APScheduler 约定 0=周一）
 */
export function configToCron(cfg) {
  const c = { ...defaultScheduleConfig(), ...(cfg || {}) }
  const { hour, minute } = splitTime(c.time)

  switch (c.freq) {
    case FREQ.MINUTE: {
      const n = Math.max(1, Math.min(59, parseInt(c.interval, 10) || 1))
      return `0 */${n} * * * *`
    }
    case FREQ.HOURLY: {
      const n = Math.max(1, Math.min(23, parseInt(c.interval, 10) || 1))
      return `0 ${minute} */${n} * * *`
    }
    case FREQ.WEEKLY: {
      const days = (c.weekdays || []).length ? [...new Set(c.weekdays)].sort((a, b) => a - b) : [0]
      return `0 ${minute} ${hour} * * ${days.join(',')}`
    }
    case FREQ.MONTHLY: {
      const days = (c.monthDays || []).length ? [...new Set(c.monthDays)].sort((a, b) => a - b) : [1]
      return `0 ${minute} ${hour} ${days.join(',')} * *`
    }
    case FREQ.DAILY:
    default:
      return `0 ${minute} ${hour} * * *`
  }
}

const isNum = s => /^\d+$/.test(s)
const isNumList = s => /^\d+(,\d+)*$/.test(s)
const pad2 = n => String(n).padStart(2, '0')

/**
 * 6 段 cron → 简单模式配置；表达式超出简单模式表达力时返回 null（调用方应转高级模式）
 */
export function cronToConfig(expression) {
  const parts = (expression || '').trim().split(/\s+/)
  if (parts.length !== 6) return null
  const [sec, min, hour, day, month, dow] = parts
  if (sec !== '0' || month !== '*') return null

  const base = defaultScheduleConfig()

  // 每 N 分钟：0 */n * * * *
  const minEvery = min.match(/^\*\/(\d+)$/)
  if (minEvery && hour === '*' && day === '*' && dow === '*') {
    return { ...base, freq: FREQ.MINUTE, interval: parseInt(minEvery[1], 10) }
  }

  // 每 N 小时：0 m */n * * *
  const hourEvery = hour.match(/^\*\/(\d+)$/)
  if (hourEvery && isNum(min) && day === '*' && dow === '*') {
    return {
      ...base, freq: FREQ.HOURLY,
      interval: parseInt(hourEvery[1], 10),
      time: `00:${pad2(min)}`,
    }
  }

  if (!isNum(min) || !isNum(hour)) return null
  const time = `${pad2(hour)}:${pad2(min)}`

  // 每周：0 m h * * dow(可多选)
  if (day === '*' && dow !== '*' && isNumList(dow)) {
    const weekdays = dow.split(',').map(Number)
    if (weekdays.some(d => d < 0 || d > 6)) return null
    return { ...base, freq: FREQ.WEEKLY, weekdays, time }
  }

  // 每月：0 m h day(可多选) * *
  if (dow === '*' && day !== '*' && isNumList(day)) {
    const monthDays = day.split(',').map(Number)
    if (monthDays.some(d => d < 1 || d > 31)) return null
    return { ...base, freq: FREQ.MONTHLY, monthDays, time }
  }

  // 每天：0 m h * * *
  if (day === '*' && dow === '*') {
    return { ...base, freq: FREQ.DAILY, time }
  }

  return null
}

/** 简单模式配置能否表达该表达式 */
export function isSimpleCron(expression) {
  return cronToConfig(expression) !== null
}


/** 定时频率预设（value 为 6 段表达式：秒 分 时 日 月 周，周字段按 APScheduler 约定 0=周一） */
export const CRON_PRESETS = [
  { label: '每小时（整点）', value: '0 0 * * * *' },
  { label: '每天凌晨 2:00', value: '0 0 2 * * *' },
  { label: '每天上午 9:00', value: '0 0 9 * * *' },
  { label: '每天 12:00 与 20:00', value: '0 0 12,20 * * *' },
  { label: '每周一凌晨 2:00', value: '0 0 2 * * 0' },
  { label: '每周五下午 18:00', value: '0 0 18 * * 4' },
  { label: '每月 1 日凌晨 2:00', value: '0 0 2 1 * *' },
]

/** 自定义选项的哨兵值 */
export const CRON_CUSTOM = '__custom__'

const WEEK_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

/** 表达式是否匹配某个预设 */
export function matchPreset(expression) {
  if (!expression) return null
  const hit = CRON_PRESETS.find(p => p.value === expression.trim())
  return hit ? hit.value : null
}

/** 拆分为 6 段，不足补 '*'（用于分段展示） */
export function splitCron(expression) {
  const parts = (expression || '').trim().split(/\s+/).filter(Boolean)
  return Array.from({ length: 6 }, (_, i) => parts[i] || '*')
}

/**
 * 把 APScheduler 约定的周字段（0=周一）转成标准 cron（0=周日），供 cron-parser 解析。
 * 仅转换纯数字，范围/间隔/列表中的每个数字也逐个转换；`*` 与 `?` 原样保留。
 */
function apschedulerDowToStandard(dowField) {
  if (!dowField || dowField === '*' || dowField === '?') return dowField
  // 单词形式（mon/tue…）两库一致，无需转换
  if (/[a-zA-Z]/.test(dowField)) return dowField
  // 逐个数字 +1 取模：APScheduler 0(周一) -> 标准 1(周一)
  return dowField.replace(/\d+/g, m => String((parseInt(m, 10) + 1) % 7))
}

/**
 * 校验 6 段表达式
 * @returns {{valid: boolean, message: string}}
 */
export function validateCron(expression) {
  const raw = (expression || '').trim()
  if (!raw) return { valid: false, message: '请填写 Cron 表达式' }

  const parts = raw.split(/\s+/)
  if (parts.length !== 6) {
    return { valid: false, message: `需为 6 段（秒 分 时 日 月 周），当前为 ${parts.length} 段` }
  }

  try {
    parts[5] = apschedulerDowToStandard(parts[5])
    CronExpressionParser.parse(parts.join(' '), { tz: 'Asia/Shanghai' })
    return { valid: true, message: '' }
  } catch (e) {
    return { valid: false, message: `表达式非法：${e.message || e}` }
  }
}

/**
 * 计算接下来 N 次执行时间
 * @returns {{times: string[], error: string}}
 */
export function nextRunTimes(expression, count = 5) {
  const check = validateCron(expression)
  if (!check.valid) return { times: [], error: check.message }

  try {
    const parts = (expression || '').trim().split(/\s+/)
    parts[5] = apschedulerDowToStandard(parts[5])
    const it = CronExpressionParser.parse(parts.join(' '), {
      currentDate: new Date(),
      tz: 'Asia/Shanghai',
    })
    const times = []
    for (let i = 0; i < count; i++) {
      const d = it.next().toDate()
      const text = d.toLocaleString('zh-CN', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        hour12: false, timeZone: 'Asia/Shanghai',
      })
      times.push(`${text} ${WEEK_NAMES[d.getDay()]}`)
    }
    return { times, error: '' }
  } catch (e) {
    return { times: [], error: `解析失败：${e.message || e}` }
  }
}

/** 把表达式描述成人话，列表页展示用；命中预设则用预设名 */
export function describeCron(expression) {
  if (!expression) return ''
  const raw = expression.trim()

  // 能被简单模式表达的，一律用配置反推出人话（覆盖面比逐个匹配预设广）
  const cfg = cronToConfig(raw)
  if (cfg) {
    const { hour, minute } = splitTime(cfg.time)
    const hhmm = `${pad2(hour)}:${pad2(minute)}`
    switch (cfg.freq) {
      case FREQ.MINUTE:
        return `每 ${cfg.interval} 分钟`
      case FREQ.HOURLY:
        return cfg.interval === 1
          ? `每小时 ${pad2(minute)} 分`
          : `每 ${cfg.interval} 小时（${pad2(minute)} 分）`
      case FREQ.WEEKLY: {
        const days = cfg.weekdays.map(d => WEEKDAY_FULL[d]).join('、')
        return `每${days} ${hhmm}`
      }
      case FREQ.MONTHLY:
        return `每月 ${cfg.monthDays.join('、')} 日 ${hhmm}`
      case FREQ.DAILY:
      default:
        return `每天 ${hhmm}`
    }
  }

  // 高级表达式：命中预设用预设名，否则回显原始表达式
  const hit = CRON_PRESETS.find(p => p.value === raw)
  return hit ? hit.label : raw
}
