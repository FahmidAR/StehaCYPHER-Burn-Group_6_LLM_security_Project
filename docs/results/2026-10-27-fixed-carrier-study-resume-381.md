# 保留三组真实失败后继续381组

用户获知496 completed、3 runtime_error、381 unstarted后明确要求“继续啊”。本次仅运行381未开始key，原三组真实失败原样保留，不重跑或补分。生成、parser、模型、thinking、温度、context、timeout、retries和原评分均不变。

启动：UTC 2026-10-27T21:33:50.641573+00:00；Chicago 2026-10-27T16:33:50.641573-05:00。

- 管理代码f3deac5；冻结experiments仍1e09f49，原plan/task/source/data校验通过。
- 唯一tmux：scb-fixed-resume-381-20261027；session：parallel/sessions/resume-20261027-c/；主日志logs/resume-20261027-c.log。
- Controller2483770；workers2484647/2484648；自建Ollama2483925/2483973。原授权GPU0/1和11435/11436，两个endpoint除地址外runtime一致。
- 新领取07e6ff2bd9a93af7c78888fd、a4b653f3e329a5e4c9161e4c两个不同未开始key；PID+OS birth/exe/cwd/领取归属核实，验证时两卡各27452MiB、约78%。
- 原499组+plan/runtime共1499文件对本地stopped499归档SHA一致，并封存在新authorization.before_sha256。所有历史结果、失败与session台账保留。新helper只增加exact profile499started/381pending/3fixedfailedkeys/previous-b。
- 三个历史failed key：9e26e7176ccc820d55761adf、88699a66c4c865a3cc78c8d0、a6def086abf1b1b0f74b46ef。最后一个result SHA94b2037aca825c8f63ea6c95513d039676867e0d6caadf6ebe173745abcc2c34；前两个SHA沿旧台账保留。任何第四个新失败仍停止领取，不自动豁免。
- 新测试先失败再实现；本地19项中16通过、3项POSIX测试在Linux全部通过，Linux19/19。独立只读审查无material finding；冻结experiments无diff。

最终完整覆盖要求880唯一terminal=877 completed+3真实runtime_error，且其他原I/O/评分/导出/source/data/plan检查无issue。原native audit仍应列三错误、ok=false，独立coverage条件通过不代表880全成功；每条件88分母保留失败格，不补造无效分数。此处只记录启动，尚未完成381组。

本地启动证据：results/fixed-study-resume-381-20261027/。已恢复15分钟安静监控fixed-carrier-remaining381-follow-up；正常进度保持安静，完成或新故障才通知。
