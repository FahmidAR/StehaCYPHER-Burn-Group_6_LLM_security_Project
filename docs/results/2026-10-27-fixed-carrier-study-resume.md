# 固定逐词载体实验：保留真实失败后的续跑

用户在分析解析错误、查看中期表格后明确要求“那你继续跑吧？”。本次仅继续536个未开始key，保留343 completed和1 runtime_error；未修解析器、换模型、改评分或重跑失败组。

续跑管理代码提交8cde2d2；冻结实验代码仍1e09f49。原冻结CLI的失败阻断保持原样，通过新增独立operations session记录这一次用户批准的例外。所有新失败仍停止领取，已在途任务自然完成。

## 已核实的启动

- UTC 2026-10-27T13:29:20.810875+00:00；Chicago 2026-10-27T08:29:20.810875-05:00。
- 唯一tmux：`scb-fixed-resume-20261027`；controller1905220。
- GPU0/1 worker1906088/1906089，自建Ollama1905369/1905414，端口11435/11436。
- 新session：`results/fixed-carrier-study-v1/parallel/sessions/resume-20261027/`；主日志`logs/resume-20261027.log`。
- 初始新key：`56196061f10d61f6b1ac7e9c`与`7bff6cf92c7435d01400dba7`，两张卡各27452MiB、约80%利用率。PID+OS birth、exe、cwd和领取归属均核实，两个endpoint除地址外runtime完全等同原runtime。
- 原344组及plan/runtime共1034文件对本地停止存档逐SHA一致，原110tar与stopped344tar SHA仍一致；所有旧stop、queue、PID、结果及日志保留。局部归档manifest路径统一用`/`后跨平台核验通过，未改原始文件。
- 已知失败key `9e26e7176ccc820d55761adf`，result SHA `5181ddf97de1aa9684699b6223d3a01ae080565b0886a6bcca5d0adfa4434398`。新authorization以SHA锁定唯一例外和全部既有attempt/plan/runtime，不允许新增失败被自动豁免。

## 验证与收尾口径

Linux14项operations测试全通过，本地14项中11通过、3项POSIX部署专用测试跳过；原实验15项测试通过。新增测试先失败再实现，包含真实双进程唯一领取、失败不重跑、旧stop保留、新失败阻断、修改结果/plan拒绝以及完整覆盖和原生审计区分。独立只读审查无material finding。

原生partial审计只有唯一历史runtime_error issue；原20项pilot审计仍通过。最后原`audit-all`必须诚实保留此错误，不能声称880全部completed或原生审计ok=true。另存`coverage-audit.json`仅在880唯一terminal、879completed+1已知失败、所有其他原审计无issue且旧记录SHA保持时允许通过。失败保留在每条件88分母，缺失评分不得补造或从矩阵删除。

本地启动证据：`results/fixed-study-resume-20261027/{launch-verified.json,authorization.json,controller-started.json,pre-resume-344-sha256.json}`。已创建每15分钟安静跟进`fixed-carrier-remaining536-follow-up`；正常推进无需用户操作，新故障或最终完整收尾再通知。此文件记录启动，不代表536组已经完成。
