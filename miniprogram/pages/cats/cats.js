// 品类对标：档次阶梯 / 渠道供给对照 / 品类冠军(实物图) / 差评归纳 / 品类×痛点
const app = getApp()
const F = require('../../utils/fmt.js')

Page({
  data: {
    ready: false,
    ladder: [],
    reading: [],
    cmp: [],
    champs: [],
    themes: [],
    matrix: { cols: [], rows: [] },
    nProducts: 0,
    nNegative: 0,
    note: '',
    openNote: false
  },

  onLoad() {
    this.build()
    const a = getApp()
    if (a && a.whenMiniReady) a.whenMiniReady(() => this.build())
  },

  build() {
    const g = (app && app.globalData) || {}
    const mini = g.mini || {}
    const c = mini.cats || {}

    const ladder = (c.ladder || []).map(function (x) {
      const p = parseFloat(x.posv)
      return {
        rk: x.rk,
        cat: x.cat,
        pos: x.pos,
        posCls: isNaN(p) ? '' : (p >= 0 ? 'up' : 'down'),
        wm: x.wm,
        amz: x.amz,
        rev: x.rev,
        wrat: x.wrat,
        neg: x.neg,
        tier: x.tier,
        tierCls: x.tier === '第一梯队' ? 'red' : (x.tier === '第二梯队' ? 'blue' : ''),
        risk: x.risk,
        riskCls: x.risk === '高' ? 'red' : '',
        lowconf: x.confidence === 'low',
        themes: x.themes,
        posW: Math.max(4, Math.min(100, Math.round(Math.abs(p) * 160)))
      }
    })

    const champs = (c.champs || []).map(function (r) {
      return {
        cat: r.cat,
        ch: (r.ch || []).map(function (x) {
          return {
            ch: x.ch,
            t: x.t,
            img: x.img,
            meta: x.meta,
            u: x.u,
            wm: x.ch === 'Walmart'
          }
        })
      }
    })

    this.setData({
      ready: true,
      ladder: ladder,
      reading: c.reading || [],
      cmp: c.cmp || [],
      champs: champs,
      themes: c.themes || [],
      matrix: c.matrix || { cols: [], rows: [] },
      nProducts: c.n_products || 0,
      nNegative: c.n_negative || 0,
      note: c.note || ''
    })
  },

  toggleNote() {
    this.setData({ openNote: !this.data.openNote })
  },

  copy(e) {
    F.copyText(e.currentTarget.dataset.u)
  }
})
