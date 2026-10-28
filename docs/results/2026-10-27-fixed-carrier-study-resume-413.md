# 保留两组失败后的413组续跑

用户获知465 completed、2 runtime_error和413 unstarted后明确要求“继续”。只运行413个未开始key，原XML失败与8B Stealth判分超时均原样保留，不重跑、不补分，不修改模型、parser、thinking、temperature、context、timeout、retries或原评分。

UTC启动时间：2026-10-27T18:24:06.304319+00:00；Chicago：2026-10-27T13:24:06.304319-05:00。

- 管理代码5c7c441；冻结experiments仍1e09f49，plan/task/data身份均通过原校验。
- 唯一tmux `scb-fixed-resume-413-20261027`；新session `parallel/sessions/resume-20261027-b/`，主日志`logs/resume-20261027-b.log`。旧session保留。
- Controller2257271；workers2258229/2258230；自建Ollama2257590/2257636；GPU0/1原UUID和11435/11436。两个endpoint的runtime除地址外完全相同于原runtime。
- 初始两个新claim为842a48363a9eefb812fbd881和5ef0d9f1b995ad591f8dc4ce；PID+OS birth/exe/cwd/归属核对通过，原失败未重新领取。
- 原467组+plan/runtime共1403文件与stopped467本地归档SHA一致，并写入新authorization.before_sha256。此前344/110证据保留；stopped467 tar SHA仍8fd697c261bf89aaeec96a2c553492e26533fc9cc96920797872a7cb4352dedd。
- 仅批准9e26e7176ccc820d55761adf和88699a66c4c865a3cc78c8d0两个runtime_error的固定result SHA；第三个新错误仍停止领取并排空其他在途任务。
- 新测试先失败再实现；本地17项中14通过、3项POSIX测试留到Linux，Linux17项全部通过。独立只读审查无material finding。冻结实验模块无diff。

完整覆盖预期为880唯一terminal、878 completed和2真实runtime_error。原native audit仍会列出两条错误、ok=false；独立coverage仅在无其他原I/O/评分/导出/source/data/plan问题且既有证据SHA保持时允许ok=true。不能声称880全成功。每条件88分母保留失败格，缺失/无效测量不补造。

本地启动证据在`results/fixed-study-resume-413-20261027/`。已恢复15分钟安静监控`fixed-carrier-remaining413-follow-up`；正常推进不通知，完成或新故障才通知。此文件只确认实际启动，不表示413组已完成。
