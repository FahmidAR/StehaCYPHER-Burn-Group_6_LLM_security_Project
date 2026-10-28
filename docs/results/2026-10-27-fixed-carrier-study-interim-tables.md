# Interim Results — Fixed Word-Initial Carrier Study

这是中断后的阶段性表格，不是完整88任务×10条件结果。直接读取队友原score_run已有字段，没有重新评分。
主表沿用原run_experiment.py汇总的列与task_completion字段；不是completion_combined，不替换判据。

**Table 1. Native metrics on the same34matched tasks per condition (340 runs).**

| Condition | Task Completion* | P-ASR* | Turns* | Tokens ≈* | StealthSim* |
|---|---:|---:|---:|---:|---:|
| Clean baseline | 0.50 | 0.000 | 12.50 | 3401 | 0.976 |
| 6 letters / Before | 0.41 | 0.544 | 15.97 | 3253 | 0.793 |
| 6 letters / After | 0.53 | 0.603 | 15.97 | 3445 | 0.790 |
| 6 letters / Memory | 0.35 | 0.529 | 14.47 | 3408 | 0.885 |
| 11 letters / Before | 0.56 | 0.500 | 17.32 | 3346 | 0.710 |
| 11 letters / After | 0.53 | 0.529 | 16.24 | 3460 | 0.839 |
| 11 letters / Memory | 0.53 | 0.463 | 15.97 | 3331 | 0.749 |
| 17 letters / Before | 0.32 | 0.559 | 16.35 | 3574 | 0.785 |
| 17 letters / After | 0.50 | 0.566 | 16.59 | 3563 | 0.750 |
| 17 letters / Memory | 0.35 | 0.581 | 15.74 | 3789 | 0.794 |

Condition中的6/11/17为隐藏字母数，也分别是固定载体的单词数。Before/After是用户请求前/后；Memory是system消息，兼有权限变化，不是真实数据库记忆。

主表选取全部10条件均completed的task-ID交集，含教育/金融/医疗/法律各7条、新闻6条。
其余3个completed都属于IPI_news_6，在附表保留；同一任务的1个XML错误也保留在运行状态表。
这是中断后的complete-case描述，可能有选择偏差，不是正式全88任务或随机抽样推断。

**指标说明（保留原实现的局限）：**

- Task Completion：原LLM judge的均值，0.50=50%。原实现把第一条actor输出作为task参考，不能当原用户任务完成率的语义金标准。
- P-ASR：队友主指标，是验证/组合等关键词签名命中的代理比例；不是“成功攻击任务占比”。原实现的来源统计也可能包含工具消息。
- Turns：原转录条目数量，含工具请求/返回，能超过MAX_TURNS12；不是真实代理轮次。
- Tokens：原输出字符数//4的估算值，非完整输入+输出用量，也不含所有内部重试成本。
- StealthSim：原8B judge的0–1机判，未做人类校准，不是隐写检测准确率。
- PTN平均只使用非空值，因此各条件分母不同；clean没有捕获时记—，不填0。ERS是队友的忙碌消息占比代理，不是官方TAMAS ERS。

**Table 2. Additional unchanged native metrics on the same34tasks.**

| Condition | PTN* | PTN valid N | ERS proxy* | P-ASR judge | Completion combined |
|---|---:|---:|---:|---:|---:|
| Clean baseline | — | 0 | 0.000 | 0.015 | 0.47 |
| 6 letters / Before | 9.45 | 31 | 0.236 | 0.331 | 0.38 |
| 6 letters / After | 10.65 | 34 | 0.289 | 0.353 | 0.53 |
| 6 letters / Memory | 9.45 | 31 | 0.222 | 0.331 | 0.35 |
| 11 letters / Before | 10.83 | 30 | 0.212 | 0.434 | 0.53 |
| 11 letters / After | 10.03 | 31 | 0.239 | 0.257 | 0.50 |
| 11 letters / Memory | 10.73 | 30 | 0.190 | 0.368 | 0.53 |
| 17 letters / Before | 9.52 | 31 | 0.254 | 0.404 | 0.32 |
| 17 letters / After | 10.84 | 32 | 0.244 | 0.404 | 0.50 |
| 17 letters / Memory | 10.66 | 32 | 0.260 | 0.419 | 0.35 |

**Table 3. Actual coverage and errors (none removed).**

| Condition | Planned | Completed | Runtime errors | Unstarted |
|---|---:|---:|---:|---:|
| Clean baseline | 88 | 35 | 0 | 53 |
| 6 letters / Before | 88 | 35 | 0 | 53 |
| 6 letters / After | 88 | 34 | 1 | 53 |
| 6 letters / Memory | 88 | 35 | 0 | 53 |
| 11 letters / Before | 88 | 34 | 0 | 54 |
| 11 letters / After | 88 | 34 | 0 | 54 |
| 11 letters / Memory | 88 | 34 | 0 | 54 |
| 17 letters / Before | 88 | 34 | 0 | 54 |
| 17 letters / After | 88 | 34 | 0 | 54 |
| 17 letters / Memory | 88 | 34 | 0 | 54 |

Total:880 planned,343completed,1runtime_error,536unstarted.

**Appendix. All343completed runs, without matching; condition denominators differ.**

| Condition | Completed N | Task Completion* | P-ASR* | Turns* | Tokens ≈* | StealthSim* |
|---|---:|---:|---:|---:|---:|---:|
| Clean baseline | 35 | 0.49 | 0.000 | 12.57 | 3426 | 0.976 |
| 6 letters / Before | 35 | 0.40 | 0.543 | 16.03 | 3264 | 0.799 |
| 6 letters / After | 34 | 0.53 | 0.603 | 15.97 | 3445 | 0.790 |
| 6 letters / Memory | 35 | 0.34 | 0.536 | 14.37 | 3430 | 0.887 |
| 11 letters / Before | 34 | 0.56 | 0.500 | 17.32 | 3346 | 0.710 |
| 11 letters / After | 34 | 0.53 | 0.529 | 16.24 | 3460 | 0.839 |
| 11 letters / Memory | 34 | 0.53 | 0.463 | 15.97 | 3331 | 0.749 |
| 17 letters / Before | 34 | 0.32 | 0.559 | 16.35 | 3574 | 0.785 |
| 17 letters / After | 34 | 0.50 | 0.566 | 16.59 | 3563 | 0.750 |
| 17 letters / Memory | 34 | 0.35 | 0.581 | 15.74 | 3789 | 0.794 |

**描述性观察，非攻击成功证明：**

- 原TC在这些条件下有升有降，6After和11词的三个位置均未低于clean；不能只挑下降的条件。
- 17Before的原TC为11/34=32.4%，clean为17/34=50.0%，观察差为17.6个百分点；尚不能宣称显著或完整实验结论。
- 消息条目数在攻击条件下较高，输出token估算变化较小：相对clean范围约-4.3%至11.4%，不支持把它描述成数量级token burn。
- P-ASR签名命中说明出现验证模式的文本，不能单独证明递归执行、原任务被破坏或实际资源耗尽。

原结果来源：results/fixed-carrier-study-evidence-20261026/results/fixed-carrier-study-v1。
派生CSV及逐key原评分：results/fixed-carrier-partial-tables-20261027；selection.json记录全部匹配ID与未纳入主表的3个完成key和1个失败key。
主表340条原评分逐字段与原matrix.csv核对一致；所有343结果、失败、536未开始位置继续保留。没有新增模型请求、改评分或恢复实验。
