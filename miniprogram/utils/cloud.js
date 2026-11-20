// 唯一云客户端：endpoint / publishableKey 均取自 publicConfig（见 cloud-config.js）
const { createMiniProgramWorkBuddyCloud } = require('@tencent-ai/workbuddy-cloud-sdk/miniprogram')
const { createDiagnosticWx } = require('./workbuddy-cloud-diagnostics')
const PUB = require('./cloud-config')

const cloud = createMiniProgramWorkBuddyCloud({
  endpoint: PUB.endpoint,
  publishableKey: PUB.publishableKey,
  wx: createDiagnosticWx(wx)
})

module.exports = { cloud }
