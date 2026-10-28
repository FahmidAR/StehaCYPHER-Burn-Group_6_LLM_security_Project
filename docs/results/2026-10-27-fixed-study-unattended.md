# 最新用户授权：单组失败保留并继续，无定时监控

用户明确要求“设置成失败了也继续跑”“不用监控”“明天我问你结束没有”。这覆盖此前每个新runtime_error都停止并等待逐次批准的规则。以后个别模型/判分失败原样保存，不重跑、不补分，继续领取未开始key；冻结模型、parser、thinking、温度、context、timeout/retries、原评分和880计划保持不变。

已删除唯一自动监控fixed-carrier-remaining381-follow-up；不创建新定时任务、不定时唤醒LLM、不主动推送进度。原后台controller仍负责本地调度、写文件和结束后的自建服务清理，不消耗对话监控token。

用户提出时确认621 completed+3 runtime_error。经验证只向原controller2483770（birth233308625/session-c/exe/cwd均匹配）发出排空信号，未中断在途推理。自然结束后封存633终态：630 completed、3 runtime_error、247 unstarted，共1901旧attempt/plan/runtime文件SHA保持。

已实际启动并验证新session `parallel/sessions/resume-20261027-unattended/`：

- tmux `scb-fixed-unattended-20261027`；主日志`logs/unattended-transition.log`。
- Controller2815221；workers2817616/2817617；自建Ollama2816962/2817009；原GPU0/1与11435/11436。
- 新authorization的continue_on_error=true、全部旧终态和plan/runtime SHA固定；两个模型端点除地址外runtime与原runtime完全一致。
- 两个不同的新key f0a94d992300261e32ad2281、7e1adf08ae72bb3235ad29db 已实际领取，均不在原633组中。
- 管理代码84ff19a及证据异常分类修复0d2a0c2；冻结experiments无diff。Linux22项调度测试全通过，包含真实并发中多次runtime/scoring错误后继续、旧记录不变、未知started及证据异常仍阻断、完整覆盖不冒称native audit成功；只读审查问题已修复并确认。

允许继续的终态仅runtime_error/scoring_error；未知owner/证据损坏/管理进程或服务退出等无法安全执行的情况仍停止，不能丢数据或盲目重跑。最终原native audit保留所有真实错误、评分缺失与限制；独立coverage只在全部880唯一terminal且所有其他原审计无issue时可通过。错误数可能多于3，不再硬编码877成功。原始失败仍在每条件88分母，rawscore不伪装成有效完成。

本地切换证据：results/fixed-study-unattended-20261027/{verified.json,authorization.json,verify.py}。后续用户询问时只读检查此新session和真实attempts；旧session-c的stop/exit1是本次授权排空的历史记录，不能当新job失败，也不能重新启动旧控制器。完整本地归档/最终表格可在用户下次询问后继续处理。
