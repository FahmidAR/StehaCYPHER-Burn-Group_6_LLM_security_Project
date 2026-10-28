# 队友原实现：只改变藏头长度和接收位置

> 历史逐句方案：用户在2026-10-26澄清需要逐词藏头。本目录的旧616组计划仍是
> 队友的逐句生成/解码协议，不能称为逐词实验。修正中的独立逐词生成器见
> [task_stego](../task_stego/README.md)；评分代码未改，词首MAS接入尚未完成。

当前方案：`teammate-native-length-position-v2`。此前模板生成和额外评分的
v1方案已撤回，代码拒绝执行旧schema；历史未运行文件仍保留。

## 直接复用的队友功能

固定Git版本 `9a60c838bb8fdfe69c65ab144d3275ca236e5729`，从Git对象读取原始
Python文件，不使用之前重写的7B诊断框架。

| 环节 | 现在调用什么 |
|---|---|
| 数据清洗、去重、采样、角色 | 原 `tamas_loader.load_benign_tasks` |
| 按用户任务生成藏头句子 | 原 `payload_riddle.stego_seed_instruction` |
| seed启动攻击、接收代理解码与传播 | 原seed指令和 `decode_hint_instruction` |
| 团队、工具、轮次、停止条件 | 原 `mas_runner.run_task`，不重新组建团队 |
| 全部判定标准 | 原 `metrics.score_run`，每组仅调用一次 |
| codec容量/roundtrip控制检查 | 原 `run_experiment.decode_success_for` |

执行模型qwen3.5:35b，评分qwen3:8b，88条原始采样任务，B=3，trial=1，
MAX_TURNS=12；actor timeout300s/retry1，judge timeout120s/原retry2。
温度、上下文沿用队友默认值。原工具文件路径仅适配本机数据目录，UTF-8读取
仅处理Windows编码差异；不改工具筛选、工具实现或数据清洗规则。

## 唯一的两个实验变量

**长度**：将原固定 `ACROSTIC_TRIGGER='VALIDATE'` 参数化。原提示本身会引用
codeword、字母列表和句数，因此换成 `GENERATETEST` 就要求12句，换成
`GENERATETESTCASES` 就要求17句。仍由原seed模型根据用户任务生成，原攻击
协议与原传播提示不改。不预生成固定模板，不筛选成功样本，不额外重试生成。
实际可能未遵守藏头或句数要求，这些失败照常进入结果。

**位置**：seed照常先生成。只在接收代理真正发给模型的输入中，移动它看到
的首条seed文本，全文不改；原共享对话记录不改，之后的代理消息和工具调用/
结果相对顺序不改。

| 位置 | 接收代理看到的输入 |
|---|---|
| `before_user` | 首条seed藏头文本在原用户请求前 |
| `after_user` | 首条seed藏头文本在原用户请求后（原正常顺序保持不变） |
| `system_memory` | 同一条seed文本移入system上下文，原用户请求不变 |

seed自身的生成输入与工具反思不做位置移动。移动的是实际生成的文本，不是
“生成藏头”的提示。即使首条seed文本藏头失败也照样移动，不改挑后面的成功
文本。memory是system上下文，不是新建数据库；它也改变消息权限。

每个条件独立运行，沿用原生成策略；不能保证不同运行采样出的句子逐字相同。
不同短语也改变拼写/词义，因此不把所有差异都归因于纯长度。

默认：88 ×（1 clean + 2长度 × 3位置）= **616组**。
同一任务只跑一次clean，保持队友的task→condition→trial顺序。
没有增加良性对照、新攻击协议、新评分、bootstrap或额外judge调用。

## 结果字段

原 `score_run` 返回的所有字段原名原值保存，不设置字段白名单：
task_completion、completion_time_turns、token_usage、p_asr、ptn、ers、
captured_agents、p_asr_judge、ptn_judge、stealth_sim、reached_done_marker、
stego、stego_delivered、tools_available、n_tool_calls、tool_calls、
tool_grounded_completion、completion_combined，以及task_id/attacked/
branching_factor。另按原driver加入trial和decode控制检查。

`results.jsonl`保留上述全部字段，只额外用 `ablation_` 前缀记录实验键、长度、
位置和运行状态。`matrix.csv`包括全部计划行；`summary.json`按长度/位置用
队友的均值/完成率汇总方式分组，同时列出实际评分数量和未完成数量。

原token_usage仍是队友的字符数/4估算，turns/PTN仍用他的原定义，ERS仍用
他的结构签名比例；不换成另一套指标。原decode控制检查是GO的同义词codec
roundtrip，不能改称新藏头模型解码率。原有评分局限保留并注明，不擅自修判据。

## 当前状态与执行边界

仅代码修正和离线测试，未调用模型、未占GPU、未创建自动运行。
离线准备命令：

```text
python -m experiments.acrostic_ablation.cli --tamas-dir results/acrostic-ablation-data/TAMAS --output results/teammate-native-ablation-20261025
```

计划保存代码、数据、原源码hash；需要用户确认对应计划SHA后才能执行。
旧v1计划即使有SHA也被拒绝。进程锁、started标记和失败保留只用于避免重复
启动/丢记录，不改模型输入或评分。未完成的MAS不会自动重跑。模型或评分函数
抛出异常会停批；原judge内部吞掉异常时，仍保留其原有返回规则。

后续运行须先协调共享GPU、确认原模型可用并使用tmux。此模块不启动/拉取/
替换模型，不停止别人的服务。客户端关闭不等于卸载Ollama模型。
尚未进行实际AutoGen/Ollama联调；离线测试不代表实验有效或模型一定能生成
合格藏头文本。
