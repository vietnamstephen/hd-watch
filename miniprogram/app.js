// Home Depot 户外生活品类周报
// 数据在 data/mini.js 内随包发布（微信小程序不允许直连未备案域名，故数据内置）
const MINI = require('./data/mini.js')

App({
  globalData: {
    mini: MINI,
    theme: 'light'
  },

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
  }
})
