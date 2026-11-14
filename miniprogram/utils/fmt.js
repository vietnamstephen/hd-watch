// 页面共用的格式化小工具（小程序端不做复杂运算，数据已在生成期格式化）

function toNum(v) {
  if (v === null || v === undefined || v === '') return null
  const n = parseFloat(v)
  return isNaN(n) ? null : n
}

function dirOf(v) {
  const n = toNum(v)
  if (n === null || n === 0) return 'flat'
  return n > 0 ? 'up' : 'down'
}

function pct(v, digits) {
  const n = toNum(v)
  if (n === null) return '—'
  const d = (digits === undefined) ? 2 : digits
  return (n > 0 ? '+' : '') + n.toFixed(d) + '%'
}

function cell(k, v, digits) {
  return { k: k, v: pct(v, digits), dir: dirOf(v) }
}

function raw(k, v) {
  const s = (v === null || v === undefined || v === '') ? '—' : String(v)
  return { k: k, v: s, dir: 'flat' }
}

// 复制到剪贴板（小程序不能直接打开外部链接）
function copyText(u) {
  const s = (u || '').trim()
  if (!s) {
    wx.showToast({ title: '该条无公开链接', icon: 'none' })
    return
  }
  wx.setClipboardData({ data: s })
}

const TIER = {
  index: '搜索索引快照',
  media_cited: '媒体引用零售商页面',
  brand_site: '品牌官方站'
}

function tierName(t) {
  return TIER[t] || t || '未标注'
}

module.exports = {
  toNum: toNum,
  dirOf: dirOf,
  pct: pct,
  cell: cell,
  raw: raw,
  copyText: copyText,
  tierName: tierName
}
