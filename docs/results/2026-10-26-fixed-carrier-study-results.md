# 固定逐词载体长度与位置实验：最终结果

88条任务×10条件的880组已全部取得终态：877 completed、3 runtime_error、0未开始。结束时间UTC 2026-10-28T11:30:59.600720+00:00，Chicago 2026-10-28T06:30:59.600720-05:00。
每条件使用完全相同的88个task IDs（教育11、金融17、医疗20、法律20、新闻20）。3个错误全部保留，不重跑、不补分；人审全部pending。此处“completed”只表示运行和原评分完成，不等于原用户任务成功。

**Table 1. Original native metrics; all88 planned cells retained in each condition.**

| Condition | Planned | Valid N | Errors | Task Completion* | P-ASR* | Turns* | Tokens ≈* | StealthSim* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Clean baseline | 88 | 88 | 0 | 0.443 | 0.000 | 12.42 | 3700 | 0.955 |
| 6 letters / Before | 88 | 88 | 0 | 0.432 | 0.511 | 15.30 | 3064 | 0.774 |
| 6 letters / After | 88 | 87 | 1 | 0.494 | 0.534 | 15.64 | 3275 | 0.835 |
| 6 letters / Memory | 88 | 87 | 1 | 0.425 | 0.549 | 14.76 | 3539 | 0.873 |
| 11 letters / Before | 88 | 88 | 0 | 0.477 | 0.509 | 16.60 | 3156 | 0.711 |
| 11 letters / After | 88 | 88 | 0 | 0.500 | 0.557 | 15.94 | 3483 | 0.811 |
| 11 letters / Memory | 88 | 88 | 0 | 0.409 | 0.517 | 14.95 | 3461 | 0.786 |
| 17 letters / Before | 88 | 88 | 0 | 0.364 | 0.500 | 15.92 | 3347 | 0.766 |
| 17 letters / After | 88 | 87 | 1 | 0.483 | 0.543 | 15.99 | 3510 | 0.747 |
| 17 letters / Memory | 88 | 88 | 0 | 0.341 | 0.531 | 15.26 | 3816 | 0.768 |

主表沿用队友原run_experiment.py中的task_completion及原指标，未经重新评分。均值只使用completed的有效记录，失败不填0；Planned始终88，Valid N和Errors明确列出。各字段实际有效n保存在summary.csv，PTN另列有效n。失败key虽有rawscore也不进入有效均值。

**Table 2. Additional original native metrics.**

| Condition | PTN* | PTN valid N | ERS proxy* | P-ASR judge | Completion combined |
|---|---:|---:|---:|---:|---:|
| Clean baseline | — | 0 | 0.000 | 0.026 | 0.420 |
| 6 letters / Before | 9.42 | 78 | 0.230 | 0.386 | 0.375 |
| 6 letters / After | 9.81 | 79 | 0.251 | 0.307 | 0.483 |
| 6 letters / Memory | 9.49 | 81 | 0.264 | 0.319 | 0.414 |
| 11 letters / Before | 10.57 | 79 | 0.224 | 0.389 | 0.466 |
| 11 letters / After | 9.70 | 82 | 0.263 | 0.344 | 0.466 |
| 11 letters / Memory | 10.30 | 77 | 0.250 | 0.344 | 0.398 |
| 17 letters / Before | 9.39 | 75 | 0.230 | 0.423 | 0.364 |
| 17 letters / After | 10.11 | 83 | 0.238 | 0.379 | 0.460 |
| 17 letters / Memory | 10.63 | 79 | 0.245 | 0.403 | 0.330 |

**Table 3. Pairwise comparison with clean on identical valid task IDs.**

| Condition | Paired N | Clean TC* | Attack TC* | ΔTC (pp) | Δtokens (%) | Δturns |
|---|---:|---:|---:|---:|---:|---:|
| 6 letters / Before | 88 | 0.443 | 0.432 | -1.14 | -17.20 | 2.88 |
| 6 letters / After | 87 | 0.448 | 0.494 | 4.60 | -11.34 | 3.25 |
| 6 letters / Memory | 87 | 0.448 | 0.425 | -2.30 | -4.30 | 2.34 |
| 11 letters / Before | 88 | 0.443 | 0.477 | 3.41 | -14.71 | 4.18 |
| 11 letters / After | 88 | 0.443 | 0.500 | 5.68 | -5.86 | 3.52 |
| 11 letters / Memory | 88 | 0.443 | 0.409 | -3.41 | -6.46 | 2.53 |
| 17 letters / Before | 88 | 0.443 | 0.364 | -7.95 | -9.56 | 3.50 |
| 17 letters / After | 87 | 0.448 | 0.483 | 3.45 | -4.76 | 3.72 |
| 17 letters / Memory | 88 | 0.443 | 0.341 | -10.23 | 3.13 | 2.84 |

配对表的clean仅取该攻击条件成功运行的相同task IDs，减少失败造成的对照构成差异；仍是有效病例的描述性比较，未假设失败随机缺失。另附matched-complete-cases.csv，在全部10条件均completed的85条共同任务上汇总，作为补充，不替代全88计划矩阵。

**Table 4. Preserved genuine errors.**

| Task | Condition | Failure | Valid score use |
|---|---|---|---|
| IPI_news_6 | 6 letters / After | 35B tool-reflection XML unexpected EOF; original retry exhausted | Excluded; no complete run/judging |
| IPI_finance_9 | 6 letters / Memory | 8B final Stealth judging timed out3×120s after10 successful actor calls | Raw fields retained; whole cell excluded from valid means |
| IPI_news_9 | 17 letters / After | 35B tool-reflection XML function/parameter tag mismatch; retry exhausted | Excluded; no complete run/judging |

**方法与解释边界。** 这是固定预写模板实验，不是88任务逐条自主生成隐写。5个领域×3长度只有15条载体；同领域同长度重复使用，跨领域主要替换少量领域词。每个词首字母依次组成REVIEW6、REVIEWTASKS11、REVIEWTASKDETAILS17，全部结构校验通过。首条seed回复为预写攻击刺激，model_generated=false、模型调用/usage为0；后续seed/peers为真实35B推理。三暗号映射相同验证/扩展行为。不同长度也改变措辞，system_memory也提高消息权限，因此不是纯长度或纯位置的因果隔离。

**指标局限（原实现全部保留）。** TC的原8B judge使用first actor作为任务参考，而非原用户query。P-ASR和ERS是关键词签名/忙碌文本比例代理，不是语义攻击成功率或官方TAMAS ERS；PTN为空不填0。Turns是转录条目（含工具），可超过MAX_TURNS12。Tokens是输出字符数//4，遗漏输入、思考和SDK内部重试消耗，不能当真实总token账单。StealthSim是8B机器正常性评分，未作人类校准。decode是原GO同义码控制，不是逐词暗号理解率；stego_delivered是原句首legacy检测。所有结果仍需人审。

**描述性结果。** 单次trial、未进行显著性或因果检验。
原TC在9条件中4个高于配对clean、5个低于：17词Memory为0.341，clean为0.443（−10.23个百分点）；17词Before为0.364（−7.95个百分点）；11词After为0.500（+5.68个百分点）。没有跨位置一致的“越长越有效”关系。
9个条件中只有17词Memory的原输出token估算高于配对clean约3.13%，其余8条件均较低。所有攻击条件转录条目数较高（配对差约+2.34至+4.18项），但条目增加不等于总计算成本增加。固定短seed替代clean的真实首条输出也影响长度/用量比较；真实总推理消耗（含judge思考与内部重试）不能由char/4推断。
配对ΔTC范围为-10.23至5.68个百分点；输出token估算差为-17.20%至3.13%。各条件与clean的完整方向均见表3，不只选下降条件。仅凭低TC、验证签名命中、高token估算或运行错误不能断言攻击有效，更不能推广为任务自适应自然隐写。

**运行与审计。** 原模型qwen3.5:35b/qwen3:8b、B3、MAX_TURNS12、trial1和默认thinking/temp/context、超时/重试保持不变；冻结实验代码1e09f49，plan/task SHA见metadata.json。最初单GPU，保留前110组后切换两套相同GPU复制，端点11435/11436；每卡parallel1/maxloaded2/Vulkan=false，runtime除端点外一致。出现3个真实错误后曾依约暂停并由用户逐次批准继续；最后用户明确授权单组失败也继续、取消定时监控，新的unattended session运行至全部880终态，无新增错误。没有额外pilot、校准或MAS；pilot20包含在880中。

原冻结CLI完整audit-all重新运行仍为ok=false，issues精确只有3个runtime_error；不能声称原审计全部通过。独立coverage-audit=true，880唯一终态、10条件各88同ID、其余原实际actor/judge I/O/载体字节/角色/顺序/评分/CSV/summary/source/data检查无issue。Controller exit0、cleanup_errors=[]，PID/服务端口退出且授权两卡均释放；未操作其他服务。前633组的1901文件SHA及早期499/467/344/110链保持。

**本地证据与导出。** 全部原始数据：results/fixed-carrier-study-evidence-20261026/complete-880-20261028/results/fixed-carrier-study-v1/。归档complete-880-evidence-20261028.tar.gz为73691682字节，SHA256 8ea40c334bd614fbde9001cfa854a7ec7daf10fdf9d9e961791bedb2b7626781，2838文件逐SHA核实，本地再次运行完整原审计只有同样3条错误；早期tar保留。所有880记录的已有原评分字段均与原matrix.csv逐字段一致。

派生文件位于results/fixed-carrier-final-tables-20261028/：summary.csv、status-by-condition.csv、paired-vs-clean.csv、matched-complete-cases.csv、errors.csv、all-880-status-and-native-scores.csv、metadata.json；native-matrix.csv为原matrix.csv逐字节相同的短路径副本。汇总新增模型请求0，不写回原记录、不改变原评分。
