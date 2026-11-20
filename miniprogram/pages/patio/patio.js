// Patio 明星榜：三层分组 + 综合明星榜 + 新星榜
const app = getApp()
const F = require('../../utils/fmt.js')

function fmtItem(it, i) {
  const buzz = parseFloat(it.buzz)
  const b = isNaN(buzz) ? 0 : buzz
  return {
    rk: i + 1,
    t: it.t,
    brand: it.brand || '',
    cat: it.cat || '',
    rating: it.rating ? it.rating + '★' : '',
    reviews: it.reviews ? it.reviews + ' 条评价' : '',
    price: it.price || '',
    buzz: it.buzz,
    bw: Math.max(2, Math.round(b * 100)),
    v: it.v,
    q: it.q,
    m: it.m,
    board: it.board || '',
    u: it.u || '',
    top: i < 3
  }
}

Page({
  data: {
    ready: false,
    gtab: 0,
    groups: [],
    cur: null,
    stars: [],
    newcomers: [],
    method: {},
    notes: [],
    cats: [],
    maxCat: 1,
    openMethod: false
  },

  onLoad() {
    this.build()
    const a = getApp()
    if (a && a.whenMiniReady) a.whenMiniReady(() => this.build())
  },

  build() {
    const g = (app && app.globalData) || {}
    const mini = g.mini || {}
    const p = mini.patio || {}

    const groups = (p.groups || []).map(function (x) {
      return {
        key: x.key,
        name: x.name,
        desc: x.desc,
        cats: x.cats,
        items: (x.items || []).map(fmtItem)
      }
    })

    let maxCat = 1
    ;(p.cats || []).forEach(function (c) {
      const n = parseFloat(c.n)
      if (!isNaN(n) && n > maxCat) maxCat = n
    })

    this.setData({
      ready: true,
      groups: groups,
      gtab: 0,
      cur: groups[0] || null,
      stars: (p.stars || []).map(fmtItem),
      newcomers: (p.newcomers || []).map(fmtItem),
      method: p.method || {},
      notes: (p.notes || []).filter(function (n) { return n && n.b }),
      cats: (p.cats || []).map(function (c) {
        return {
          label: c.label,
          n: c.n,
          share: c.share,
          reviews: c.reviews,
          bw: Math.max(2, Math.round((parseFloat(c.n) / maxCat) * 100))
        }
      })
    })
  },

  tab(e) {
    const i = Number(e.currentTarget.dataset.i)
    this.setData({ gtab: i, cur: this.data.groups[i] || null })
  },

  toggleMethod() {
    this.setData({ openMethod: !this.data.openMethod })
  },

  copy(e) {
    F.copyText(e.currentTarget.dataset.u)
  }
})
