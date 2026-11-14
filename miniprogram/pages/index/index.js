// 概览页：HD 股价位置 + 估值 + 相对表现 + 本周新闻/披露
const app = getApp()
const F = require('../../utils/fmt.js')
const dirOf = F.dirOf
const pct = F.pct
const cell = F.cell
const raw = F.raw

Page({
  data: {
    ready: false,
    meta: {}, q: {}, fund: {},
    chgs: [], pos: [], val: [], ops: [], ana: [],
    bench: [], brief: [], news: [], filings: [], ir: []
  },

  onLoad() {
    this.build()
  },

  onShow() {
    if (this.data.ready) {
      // 系统深浅色切换后 canvas 需要重绘（线色不跟随 CSS 变量）
      this.draw()
    }
  },

  build() {
    const g = (app && app.globalData) || {}
    const mini = g.mini || {}
    const q = mini.quote || {}
    const f = mini.fund || {}
    const ma = q.ma || {}
    const chg = q.chg || {}

    const bench = (mini.bench || []).map(function (b) {
      const c = b.chg || {}
      return {
        name: b.name, tag: b.tag, last: b.last, from_hi: b.from_hi,
        w: pct(c.w), dw: dirOf(c.w),
        m: pct(c.m), dm: dirOf(c.m),
        y: pct(c.y), dy: dirOf(c.y)
      }
    })

    this.setData({
      ready: true,
      meta: mini.meta || {},
      q: q,
      fund: f,
      chgs: [
        cell('近 1 周', chg.w),
        cell('近 1 月', chg.m),
        cell('近 3 月', chg.q),
        cell('近 1 年', chg.y)
      ],
      pos: [
        cell('距 52 周高', q.from_hi, 1),
        cell('距 52 周低', q.from_lo, 1),
        cell('相对 MA20', ma.vs20, 1),
        cell('相对 MA60', ma.vs60, 1),
        cell('相对 MA200', ma.vs200, 1),
        raw('60 日波动率', q.vol ? q.vol + '%' : null)
      ],
      val: [
        raw('市值', f.cap),
        raw('市盈率 TTM', f.pe),
        raw('前瞻市盈率', f.fpe),
        raw('股息率', f.dy ? f.dy + '%' : null),
        raw('派息率', f.payout),
        raw('Beta', f.beta)
      ],
      ops: [
        raw('营收 TTM', f.rev),
        raw('营收增速', f.revg),
        raw('毛利率', f.gm),
        raw('营业利润率', f.om),
        raw('净利率', f.pm),
        raw('ROE', f.roe)
      ],
      ana: [
        raw('目标均价', f.tgt ? '$' + f.tgt : null),
        raw('最高目标', f.tgt_h ? '$' + f.tgt_h : null),
        raw('最低目标', f.tgt_l ? '$' + f.tgt_l : null),
        raw('覆盖分析师', f.an),
        raw('自由现金流', f.fcf),
        raw('一年最大回撤', q.mdd ? q.mdd + '%' : null)
      ],
      bench: bench,
      brief: mini.brief || [],
      news: (mini.news || []).map(function (n) {
        return { t: n.t, src: n.src, d: n.d, u: n.u }
      }),
      filings: (mini.filings || []).map(function (x) {
        return { form: x.form, filed: x.filed, period: x.period, u: x.u }
      }),
      ir: (mini.ir || []).map(function (x) {
        return { kind: x.kind, q: x.q, u: x.u }
      })
    }, () => this.draw())
  },

  // ---- 近 120 日收盘走势 ----
  draw() {
    const self = this
    const arr = (this.data.q && this.data.q.spark) || []
    if (arr.length < 2) return
    const qy = wx.createSelectorQuery().in(this)
    qy.select('#spark').fields({ node: true, size: true }).exec(function (res) {
      if (!res || !res[0] || !res[0].node) return
      try {
        self.paint(res[0])
      } catch (e) {
        // 绘制失败不应影响页面其它内容
      }
    })
  },

  paint(node) {
    const arr = this.data.q.spark
    const canvas = node.node
    const w = node.width
    const h = node.height
    let dpr = 2
    try {
      const wi = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync()
      dpr = wi.pixelRatio || 2
    } catch (e) { /* 忽略 */ }
    canvas.width = Math.floor(w * dpr)
    canvas.height = Math.floor(h * dpr)
    const ctx = canvas.getContext('2d')
    ctx.scale(dpr, dpr)
    ctx.clearRect(0, 0, w, h)

    const PAD_L = 4, PAD_R = 4, PAD_T = 22, PAD_B = 20
    const iw = w - PAD_L - PAD_R
    const ih = h - PAD_T - PAD_B

    let mn = Infinity, mx = -Infinity, iMn = 0, iMx = 0
    for (let i = 0; i < arr.length; i++) {
      const v = arr[i]
      if (v < mn) { mn = v; iMn = i }
      if (v > mx) { mx = v; iMx = i }
    }
    const span = (mx - mn) || 1
    const top = mx + span * 0.10
    const bot = mn - span * 0.10
    const rng = top - bot

    const X = (i) => PAD_L + (iw * i) / (arr.length - 1)
    const Y = (v) => PAD_T + ih * (1 - (v - bot) / rng)

    // 网格
    ctx.strokeStyle = 'rgba(128,128,128,0.22)'
    ctx.lineWidth = 1
    for (let g = 0; g <= 2; g++) {
      const yy = PAD_T + (ih * g) / 2
      ctx.beginPath()
      ctx.moveTo(PAD_L, yy)
      ctx.lineTo(w - PAD_R, yy)
      ctx.stroke()
    }

    // 面积渐变
    const grad = ctx.createLinearGradient(0, PAD_T, 0, PAD_T + ih)
    grad.addColorStop(0, 'rgba(249,99,2,0.26)')
    grad.addColorStop(1, 'rgba(249,99,2,0.02)')
    ctx.beginPath()
    ctx.moveTo(X(0), Y(arr[0]))
    for (let i = 1; i < arr.length; i++) ctx.lineTo(X(i), Y(arr[i]))
    ctx.lineTo(X(arr.length - 1), PAD_T + ih)
    ctx.lineTo(X(0), PAD_T + ih)
    ctx.closePath()
    ctx.fillStyle = grad
    ctx.fill()

    // 折线
    ctx.beginPath()
    ctx.moveTo(X(0), Y(arr[0]))
    for (let i = 1; i < arr.length; i++) ctx.lineTo(X(i), Y(arr[i]))
    ctx.strokeStyle = '#F96302'
    ctx.lineWidth = 2
    ctx.lineJoin = 'round'
    ctx.stroke()

    // 端点
    const lastY = Y(arr[arr.length - 1])
    ctx.beginPath()
    ctx.arc(X(arr.length - 1), lastY, 3.2, 0, Math.PI * 2)
    ctx.fillStyle = '#F96302'
    ctx.fill()

    // 最高 / 最低标注
    ctx.font = '11px -apple-system, sans-serif'
    ctx.fillStyle = 'rgba(128,128,128,1)'
    const hiTxt = '$' + mx.toFixed(2)
    const loTxt = '$' + mn.toFixed(2)
    ctx.textAlign = iMx > arr.length * 0.7 ? 'right' : 'left'
    ctx.fillText(hiTxt, Math.max(PAD_L, Math.min(w - PAD_R, X(iMx))), Math.max(12, Y(mx) - 6))
    ctx.textAlign = iMn > arr.length * 0.7 ? 'right' : 'left'
    ctx.fillText(loTxt, Math.max(PAD_L, Math.min(w - PAD_R, X(iMn))), Math.min(h - 6, Y(mn) + 16))

    // 首末价格
    ctx.textAlign = 'left'
    ctx.fillStyle = 'rgba(128,128,128,1)'
    ctx.fillText('$' + arr[0].toFixed(2), PAD_L + 2, h - 6)
    ctx.textAlign = 'right'
    ctx.fillText('$' + arr[arr.length - 1].toFixed(2), w - PAD_R - 2, h - 6)
  },

  copy(e) {
    F.copyText(e.currentTarget.dataset.u)
  }
})
