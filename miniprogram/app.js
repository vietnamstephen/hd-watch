// Home Depot 户外生活品类周报
// 数据优先级：云数据库 weekly_report 最新一期 > 包内 data/mini.js（离线基线）
const MINI = require('./data/mini.js')
const { cloud } = require('./utils/cloud.js')
const { createTableAccess } = require('./utils/workbuddy-data-access.js')

const reports = createTableAccess(cloud, {
  table: 'weekly_report',
  columns: ['week', 'generated_at', 'payload'],
  orderBy: { column: 'generated_at', ascending: false }
})

function usable(m) {
  return !!(m && m.meta && m.quote && m.patio && m.cats && m.channels && m.news)
}

App({
  globalData: {
    mini: MINI,
    source: 'local',
    week: (MINI.meta || {}).week || '',
    cloudError: ''
  },
  ready: false,
  _waiters: [],

  onLaunch() {
    // 跟随系统深浅色
    try {
      const info = wx.getAppBaseInfo ? wx.getAppBaseInfo() : wx.getSystemInfoSync()
      this.globalData.theme = info.theme || 'light'
      wx.onThemeChange && wx.onThemeChange((res) => {
        this.globalData.theme = res.theme
      })
    } catch (e) {
      // 老版本基础库忽略即可，CSS media query 仍会生效
    }
    this.refresh()
  },

  // 页面在 onLoad 先用内置数据渲染，云端数据回来后再重建一次
  whenMiniReady(cb) {
    if (this.ready) return cb(this.globalData.source)
    this._waiters.push(cb)
  },

  refresh() {
    if (this._pending) return this._pending
    this._pending = reports.list().then((res) => {
      const row = (res.data || []).find((r) => r && usable(r.payload))
      const localWeek = (MINI.meta || {}).week || ''
      const cloudWeek = row ? (row.week || (row.payload.meta || {}).week || '') : ''
      if (!res.error && row && cloudWeek >= localWeek) {
        this.globalData.mini = row.payload
        this.globalData.source = 'cloud'
        this.globalData.week = cloudWeek
        this.globalData.cloudError = ''
      } else {
        this.globalData.source = 'local'
        this.globalData.week = localWeek
        this.globalData.cloudError = res.error
          ? (res.error.message || '云端读取失败')
          : (row ? '内置周报更新' : '云端暂无完整周报')
        if (res.error) this.warn()
      }
      this.finish()
    }).catch((e) => {
      this.globalData.source = 'local'
      this.globalData.cloudError = e && e.message ? e.message : '云端读取异常'
      this.warn()
      this.finish()
    })
    return this._pending
  },

  warn() {
    try {
      wx.showToast({ title: '云端周报暂不可用，已用内置数据', icon: 'none' })
    } catch (e) { /* 预览环境无 toast 时忽略 */ }
  },

  finish() {
    this.ready = true
    const waiters = this._waiters
    this._waiters = []
    waiters.forEach((cb) => {
      try { cb(this.globalData.source) } catch (e) { /* 单个页面失败不影响其它页面 */ }
    })
  }
})
