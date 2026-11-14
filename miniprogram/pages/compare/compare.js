// 渠道对标：Amazon vs Walmart（只对标能站内直抓的两家）
// 2026-10-15 口径收敛：Home Depot / Lowe's / Costco 站内不可直抓，已整体移出对比。
const app = getApp()
const F = require('../../utils/fmt.js')

Page({
  data: {
    ready: false,
    channels: [],
    dropped: [],
    droppedText: '',
    disclaimer: ''
  },

  onLoad() {
    this.build()
  },

  build() {
    const g = (app && app.globalData) || {}
    const mini = g.mini || {}
    const dropped = mini.channels_excluded || []

    this.setData({
      ready: true,
      channels: mini.channels || [],
      dropped: dropped,
      droppedText: dropped.join('、'),
      disclaimer: mini.disclaimer || ''
    })
  },

  copy(e) {
    F.copyText(e.currentTarget.dataset.u)
  }
})
