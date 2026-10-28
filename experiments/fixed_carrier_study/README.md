# 固定逐词载体：同88任务的长度/位置实验

最终88条任务与队友9a60c83的原loader完全一致：教育11、金融17、医疗20、法律20、
新闻20。每条1clean+3长度×3位置=10组，完整manifest880组，trial1，B3，MAX_TURNS12。
小测试是其中IPI_healthcare_0、IPI_legal_0共20组，沿用正式key，后续不重复。

预先编写5领域×3长度=15条载体，暗号review6、review tasks11、review task details17。
每个词首字母参与编码，所有词是原完整词，程序不改字母或补词。按领域选用，
不声称与88条具体请求逐条语义匹配，human pending。同一长度/任务的三个位置
使用完全相同的文本。所有暗号映射到同一原B3递归验证行为，不随长度增加工作。

原run_task仍建立团队、正常工具、轮次和停止条件；攻击seed首条响应由固定载体
直接提供（model_generated=false、该条实际模型调用0/usage0），之后seed和所有
接收代理均真实调用原35B。仅将原句首编码/解码提示改为词首；验证行为正文不改。
这是受控攻击刺激，不是自主自然隐写生成。原客户端/函数在失败时恢复。

位置before_user/after_user只移动接收代理输入中的首条seed消息；种子自身视图和
其余工具/历史相对顺序保持。system_memory同时改变消息权限，单列解释，无数据库。

评分直接调用原score_run一次，所有原字段原样保存，再加原driver的bf/trial和
decode_success_for。后者是GO同义词codec控制，与词首模型解码不同。原
stego_delivered仍按句首解码，必须标为legacy，实际固定词首roundtrip/exposure在
独立diagnostics中。原任务完成judge以首个actor输出作任务、tokens为chars//4、
turns为转录项、P-ASR/ERS为原正则代理，这些限制保留，不冒充语义gold。

准备（纯离线，不启动模型）：

```text
python -m experiments.fixed_carrier_study.cli --phase prepare --tamas-dir results/acrostic-ablation-data/TAMAS --output results/fixed-carrier-study-20261026
```

使用plan里的准确SHA执行`--phase pilot`；审计`--phase audit-pilot`，随后同目录
`--phase all`自动跳过已started键，只运行剩余。每次执行验证原源码/数据/扩展hash、
完整88task SHA、全部880cell和原runtime/model身份；不重跑失败/中断键。
真实执行需原本地Ollama35B与qwen3:8b，程序不自动换模型/下载/启动。

执行异常/传输错误会停止；judge内部吞掉异常时保留原scores，但管理状态标无效，
禁止靠失败转NO冒充有效评分。mechanicalpilot gate不要求TC/ASR为正，不按效果
换任务/挑载体。报告一直保留880行和每组88分母，列出已评分/失败/未开始数量。
小试及正式的事件、原始AutoGen/SDK响应、原评分、固定刺激来源均按key保存。

这是新schema fixed-word-carrier-length-position-v1；历史native逐句616计划不可混用。
启动前协调共享GPU、确认idle并禁Vulkan，tmux后台运行和只清理自建服务。
