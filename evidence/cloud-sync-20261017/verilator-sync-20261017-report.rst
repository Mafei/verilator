Verilator 双上游同步阶段报告：2026-10-17
======================================

固定候选与执行环境
------------------

最终候选 f663cb23b6d62480ad15fb15448cc85e1d28985a，tree
d82b68edc00f9d29ebd9ba7af8755d72319a5deb。分支 fourstate-sync-20261017。
Draft PR25：https://github.com/Mafei/verilator/pull/25
正式CI：https://github.com/Mafei/verilator/actions/runs/38985119681
以下状态来自该SHA的最终完整日志和独立语义审查；PR仍draft，未合并。

保存的verilator云环境本轮已恢复可执行，实际为Debian13.6/GCC14.2/glibc2.41，
CPUquota4、内存16GiB。编译器make始终-j2；新增33首轮harness与模型make各-j2，
不能据此证明当时全局只占2个CXX。随后启用透明的两个flock编译槽，后续各批验证
均按全局最多2个CXX执行。所有编辑、合并、原生执行及协调均在该云环境，
不需要用户Mac在线。原生Git三次正常push实际raw0/exit0，PR创建
账户为Mafei/id1992089；gh身份API独立返回403，未将其视为认证成功，未改凭据。

本次启动原工作区恢复为干净交付基线d565afb615e3393970d6ce030d75df68b594e6b8。
旧临时工作树及上轮云内部证据未随此主机恢复，不能再次提供旧绝对路径作为
可下载交付。启动时没有其他活动协作代理或native编译；最近Actions无活动作业。
后续创建唯一独立工作树，root独占源码编辑，两个同云子代理分别只读审查源码
和实际CI日志。读取仓库、src/include/test_regress AGENTS，无可用本地.agents
技能文件；原交付工作树保持干净，未强推、删除历史、合并PR或发布release。
未修改日程，也未再次发暂停问题。未获取/上传私有业务代码或受限厂商模型。

固定双上游
----------

实际2026-10-16 23:58UTC观测并fetch固定对象：

* Veripool master：1d0bf5d1d1766ed98693cfa95dce2c0ae4659ef4。
* Antmicro dev/fourstate：dbb8aedaa478389639295e40f16dbc7183d10b48。
* Antmicro feature/4_state_logic：5e132f32db577b3d596b66ce6378ac224ffa38d3。

官方相对PR24有41项，较昨日1272f735再多10项；后续探针48bb已包含其中最早5项。
两个Antmicro头不变且已包含。原PR24的4493ecd2b75e1228302216d7329ffb22a9b4dc50、
原探针48bb13d6042055f4eb6886ab16cb5c5d6bd5a4e7及全部历史保留为祖先。
本轮从48bb另建候选，合并固定官方对象生成627420e2216b93e9fdba04dbdd81e0b0b08b6e28；
随后CI调用修复形成a32，再增加真实dbg编译形成最终f663。后三版439个tracked
src/include输入逐字节相同；最后两次提交仅修复CI调用/构建。没有把原探针的三个
Linux C++14控制结果继承为新跨平台结果。
仓库ci/portable/sync_upstreams.py保留；本轮固定引用在refs/sync-observations/20261017。

收尾只读观测时官方头为8668340f4b7f14af1e0f47f49dd246f27f83a9d7；Git与GitHub
compare均证实比固定1d头前进2项、无回退。581928c5为LowerCtx字段简化，8668340f为
专门化继承成员inline constraint修复；它们在本轮固定之后到达，记录为下一批待整合，
未并入或认证本轮f663。两Antmicro头不变。复用检测脚本不自动push或合回候选。

最终原生ls-remote对fork的宽查询未返回预期保护ref，故该输出不能充当分支保护
证明；已用授权GitHub API逐ref独立确认f663、PR24/4493、交付d565、探针48bb和
PR23/2fb均保持原值。未修改Git配置、凭据、权限或据异常输出重写任何分支。

冲突处理与有界范围
------------------

四个冲突的三方原始全文及未解决片段均保存。AstVar初始化同时保留四态original
dtype/complement/top信息与新libInoutEnable。V3Const保留BufIf1驱动来源和
fourstateHandled条件反转保护，增加官方branch prediction方向修复；将未知packed
文件名X/Z保护适配至通用canFoldUniop，known字符串采用新numberOperate转换。
V3Error保留CASTFOURSTATE/LOGICCAST别名并加入WIDTHDIGITS；V3Timing同时保留
implicit delay预处理与新delayToTicks，未删除既有四态修复。

独立源码审查固定a32：531个未与本轮官方改动重叠的fork路径中，512个现存文件
字节一致、16项历史删除仍删除、3项授权CI改动。22项源码保护检查满足；154项
诊断枚举与名称表逐项一致。源码静态通过不代替实际执行。审查124文件/
1,739,768字节，root逐项重读，manifest SHA256
be7ac05d4a3ecebbff9535954dc12146b172e47ceaac8d10b5357042622bfdf7。
a32到f663的4行CI-only补充审查另封存4文件/99,474字节，manifest SHA256
797bd4008e72850bf780309b9a9c161dd4a93eab3da7cf71a2da784e5527bb0d。

原264个driver/27组及组内次序完全保留，另加33个官方原driver组成一组，合计
297/28，另有MT5。新增22个执行仿真、11个负向或静态控制，均未显式启用fourstate；
不将其PASS扩大为aggregate X/Z语义认证。实际四态覆盖仍由保留的原四态用例、
RAM、VPI、strict、finish及全波形承担。VPI lifecycle测试在同一VerilatedContext
内重建两轮，并检查两个同名模型的不同销毁顺序，不声称双context测试。

整个PR24到候选diff --check实际退出2：21行官方.out golden尾随空格。仅src/
include/ci/.github限定检查退出0。未手工编辑golden，未声称整体格式全通过。

真实失败和修正
--------------

native configure实际PID1690/raw0/exit0。首次native make未激活已保存工具链，
找不到Bison，PID3958/raw512/exit2；失败日志保留。随后显式激活已有Bison3.8.2/
Flex2.6.4及tools路径重试，未改变编译器源码、CPU配额或测试失败判定。

627的原13项门控检查实际捕获build.bash调用遗漏新增组，并发现native缺distro
导入依赖。只给实际调用加upstream_sync_20261017，原BashGateTest单独实际通过；
安装distro1.9.0至workspace工具目录，未更改任何单元测试或放宽skip门。
旧CI38984388388、38984569961在后续正常推送后由既有并发规则取消；完整旧日志明确
operation was canceled，未到主回归和后置门。不能说旧CI实际观察到本地单元断言失败。

原新增VPI interface array驱动显式要求真实debug编译器。首轮原生opt-only构建使
该项失败；最终CI增加make dbg，未复制opt冒充debug、移除原驱动debug标志或降低门槛。

最终执行结果
------------

最终run38985119681的macOS job117254837824和Rocky job117254837962均已终态success，
PR25说明已更新并回读确认head=f663、base=4493、draft=true、merged=false。
完整解码日志Mac7,064,102字节，SHA256
15f16887b26fafbc9e2dfb276c796de5d554db9aa805f81708e35355c6c61a06；
Rocky5,836,119字节，SHA256
266f41ff6aeda659573e3aff24c333e46d8a4024a292bfbb2ba9bc1a990c0dff。
两份最终日志总12,900,221字节；加此前取消两轮共13,846,526字节，没有截断。

两平台分别实际：

* 主回归297个不同driver/28原组完整完成，逐组摘要/原名称/真实返回均核验，0skip；
  另有原MT5/5。主回归包含负向诊断与静态控制，不称297个运行时仿真。
* 原门控单测五份完成摘要分别13/13/11/7/16，各有两次独立结果checker成功；
  不将重复运行的摘要相加为不同测试数。
* RAM原318断言、84报告、30完整历史228记录；完整VCD按原期望独立重解析。
* strict18原54个compile/build/run Popen实际退出0；16匹配与2已知输出差异，
  适用门0、full18门1，未抹去失败或把完整门算绿；无fresh Icarus引擎执行声明。
* finish9原9/9，27个不同wait4 raw0；原字面stdout与9完整q历史独立复核。
* 56对完整VCD均逐字节相同、SHA相同，覆盖SV17、MT2、RAM1、语义7、finish边界20、
  原finish9共9；未截取波形或丢弃重复记录。
* 两平台各176条真实-DVL_DEBUG/-D_GLIBCXX_DEBUG编译命令；原VPI interface array
  实际PASS。macOS使用实际GNU Make4.4.1。Rocky ASAN预检和独立fresh Rocky8.10
  容器迁移通过；fresh生成模型观测到的最高GLIBC需求2.25，不将它冒充整个包上界。

主审PID69538/raw0/exit0，附加debug/MT/元数据审PID69546/raw0/exit0。
CI独立终态审查封存1180文件/17,373,333字节；root已逐文件重读，
manifest SHA256 deecb16d3685565032cc2840791d1e2b80f9ea0f390bb0fed39cc24bde37572e。
独立CI报告SHA256 a970399440738a2c76cf3c557221929ea2a5837966064120822330bc814e4cf4。

macOS编译器SHA256
6a6c2c1aee17ad83d7580f4d001c43a15173fa868a9d70862df7be0a3c9bd31e；
Rocky编译器SHA256
607b36e1ae2b379e2a0b2988775b7704b75ae700a302a46effb08677516de208。
包在迁移前后实际SHA打印一致：

* verilator-fourstate-macos-arm64.tar.gz：
  c71a70c4371ee231b0d4b6e8d75fdc0bad5df79df17ad4fbd83a1b37d8ee35ec。
* verilator-fourstate-rocky8-x86_64.tar.gz：
  329b6c65c72b63ab59ff5b7e053e9c22721f52a9af9f1ad2d611a58966b2c079。

实际Actions附件（需有仓库访问权）：

* macOS： https://github.com/Mafei/verilator/actions/runs/38985119681/artifacts/12085030039
  ZIP metadata497,519,729字节，digest
  8827a434058ba2b7934404b47f67abcb1b8316b5c387810dd20032a52f6121f4。
* Rocky： https://github.com/Mafei/verilator/actions/runs/38985119681/artifacts/12083889322
  ZIP metadata452,541,681字节，digest
  f094df87a2c8f48b29c7c05eb23edfcf379c81f21bd97751b6b16e328f54f68a。

附件metadata有效至2027-01-15；未下载这些近1GB的ZIP，因此上述ZIP大小/digest
是服务端metadata，内部tar的大小未在本轮云端独立测量，不能把两者混用。54份strict
单独原始编译/运行日志亦未从ZIP再次下载；原CI checker在runner验证其收据/全日志
哈希，云端从完整job log重新审核全部审计结果、真实摘要及完整波形。

生成标识符检查：Mac原AST SHA
2abf53008142494411a4c8fc407983326300e4243f482001466ac74122d83c60，
Rocky原AST SHA96f1c153b18e45d29b371c5b535b90be29d844eb984dbc021ba1a14480e476a1；
原enum token分别__Venum_h930a8d09__0、__Venum_ha0f45658__0。仅保留类型身份/
别名关系的八位hash归一后，完整文件同为SHA
959d8454cc445960a9019f338ce559049ba64b526d1d2a9e70cd1dd10497986c。
不声称原始字节本就相同，也不删去数字suffix、literal或其他AST字节。

原生验证
--------

原生Linux与正式跨平台分开记账。首先真实opt构建627版本，PID6206/raw0/exit0；
日志91,343字节，SHA256
5b41e8b3cf3c4eb1d2a3bb30b5bed40574cb5c2dc39e5c83f8ab6bae2cfffad2。
65个不同原driver在该opt版本成功：新增组首轮32/33、保留高风险32/32、AST1/1。
新增组唯一失败为缺debug二进制，原失败status、完整日志及harness返回10均保留。

真实dbg版本f663实际PID53044/raw0/exit0，包含-O0/-ggdb/-DVL_DEBUG/
-D_GLIBCXX_DEBUG，ELF调试信息真实存在。原VPI array在全新_realdbg对象目录恢复
1/1，PID56907/raw0/exit0；不将它改写为首轮33一次全通过。dbg二进制256,344,904
字节，SHA256 7baa1471b211518aceb49e8a42429afe6d0758f688c0139b99f44304d8041615。

高风险32项分为readmem16、capabilities4、plusargs5、resolve5、integration1、
finish coverage1。独立检查未知文件名不加载、未知地址域、算术右移9832次检查、
selected-output plusargs及resolver原truth-table。完整重读resolver四份VCD：
1430个目标信号历史、7408条带精确物理时间戳记录全部一致；保留x/z。另读readmem
四个镜像16条值序列，原oracle未约束其时间戳。finish coverage六profile的30个
DA行计数、六个user bin=0和六个唯一完成标记匹配。独立MAC是公开CC0行为控制，
不代表DSP48E2/glbl厂商实现。原AST控制只使用原enum hash规范化规则后整文件比对。

原失败传播13项检查重跑PID26577/raw0/exit0，13 tests/323.086s/OK，涵盖实际非零
退出配绿色摘要、零退出配失败或不完整摘要，以及实际日志反证伪造JSON成功；未改测试。

最后增量更新opt版本元数据到f663，并非重新编译全部对象。PID57000/raw0/exit0，
最终原生opt SHA256 4664724ae4095f1fe376102ade651e40be35825685bc189020c03c27702f5d87，
coverage SHA256 4db5eeb530e018073915eaf390b91e8d3f3846a14dbe1f7a2adce45895fb452a。
随后原fourstate VPI控制使用-std=c++14/VM_TIMING0在新_cpp14对象目录1/1成功，
其value/mask生成与原aval/bval及callback断言实际执行。只认证这一项C++14控制。

以该最终opt进行的原语义门：

* RAM：318断言、84条文字、30目标历史/228条VCD记录；compile/build/run/check
  四个实际wait4退出均0，完整历史独立重解析相同。
* strict18：18项compile/build/run共54个实际Popen均退出0，0跳过/未跑/超时/
  基础设施失败；16匹配与nb_ec_concat、sv_packed_port1两已知输出差异。适用门0，
  full18门1。29份固定官方输入与81份runtime保护均核验；本轮实际Icarus参考引擎
  执行次数0，使用固定官方gold/self-check契约，不声称重新双引擎对跑。
* finish9：9/9输出及原完整q波形匹配，27个不同实际wait4子进程raw0/exit0。
* MT：首轮4过1失败，trace_basic_cc_vcd实际模型已运行，但wavediff未安装导致比较
  门失败。原bundle STOPPED_FAILED与原5个status均保留。按现有CI配方安装Rust1.88.0/
  wavetools0.1.2后，用原5个driver及新_toolsfix对象目录补测，PID68356/raw0/exit0，
  5/5/0skip。补测没有覆写首轮失败，也未重跑已经成功的RAM/strict/finish。

原生语义补充独立审查封存476文件/3,302,607字节，root已逐文件重读。
manifest SHA256 132f26aa672de3853050ed62c21b13a8f2bb55e92a73d0dbad2e13b5db008a7c。
MT两态/四态共六个目标信号历史51条记录及basic39声明/1459条原始时间记录，
均按原字面条件与完整历史独立精确核对。原生审查并不代替跨平台56对完整波形。

能力矩阵的实际口径
------------------

* RAM/未知地址：保留完整未知地址域保护、原fourstate_mem_index与RAM矩阵；对应
  读写/文字结果及完整历史按原契约检查，不推广为全部存储器与厂商RAM模式。
* $isunknown：原fourstate_isunknown在本轮两个平台的完整日志中均真实PASS。
  本轮额外原生32风险批次不包含它；这里使用新正式CI证据，不移用旧结果。
* 算术右移/宽度：原fourstate_shiftrs在627原生检查9832次；原math_shiftrs及新
  math_pow3/WIDTHDIGITS正负控制继续位于正式选定组。负向预期诊断属于通过，
  不改成禁止所有移位宽度警告或放宽未知有符号移位语义。
* 多驱动/supply/tri：保留pair/triple/event/default解析、驱动来源和释放控制；
  resolver完整历史已原生复核。受支持范围以原公开标量/选定域契约和明确诊断为界，
  不声称任意strength、charge storage、tran/switch网络或全部三态连接语义。
* VPI/SV：保留四态aval/bval及回调，加入官方interface引用数组/生命周期/topology
  原控制；真实debug编译器用于原要求的数组控制。生命周期在同一context内两轮
  重建及不同销毁次序，不是双context认证。新33项大多仍为普通模式，不能将它们
  的通过扩大为任意aggregate X/Z或完整SystemVerilog。
* DSP48E2/glbl：无受限厂商模型输入；只验证公开独立CC0 MAC行为repro。厂商
  器件、primitive库及私有RFSoC业务兼容性没有在本轮认证，也未上传此类输入。

边界与未运行项
--------------

原已知nb_ec_concat与sv_packed_port1两个差异保留，完整18项比较的非零退出
如实记录，不能称strict18全通过。finish9 case5的q=0是
原验收oracle，不推广为同区域NBA/final顺序的普遍IEEE结论。

完整make test、最终全量Cppcheck、70,000字段压力、特殊hierarchical/--lib-create
及CMake PCH模式均不在本轮选定认证范围；solver正向随机化未运行。fullformat
与verible可用性以实际检查为准，没有厂商模型、私有RFSoC或完整SystemVerilog认证。
原四态CC0 MAC行为模型不包含DSP48E2/glbl厂商实现。早期final、trace coverage及
已有其他复杂SV边界没有因本轮同步而宣称解决。

封存与交付
----------

证据归档：verilator-sync-20261017-evidence.tar.gz
大小：18,490,951字节
SHA256：04809da6fa06d0711a48153611146955105a8a0067699f0671111c9e8129b601

归档原始2555文件、74,414,794字节，加内置SEALED_MANIFEST.json共2556成员。
封存进程PID69726/raw0/exit0，实际重新打开每个成员、全字节重算大小/SHA256均一致；
没有改写原始证据。内置manifest SHA256
b48c5ce9e4424bc321d467b6c02f031e80da6426e0adacda95ee6819547913d1。
全部六份独立审查清单共2396条目、26,651,553字节，root在环境恢复后逐项重新核对。

最终报告独立于归档，避免归档自身哈希的循环依赖。归档保留历史候选/草稿/初次失败
及各次真实身份，READ_THIS_FIRST.rst说明证据目录；单独这份报告为最终交付说明。

本阶段固定官方1d的整合与选定双平台认证已完成；strict18的两项差异和较后到达的
两项官方提交明确保留为后续事项。原交付d565、PR24/4493、PR23/2fb与探针48bb
未覆盖，PR25仍draft。没有release、交付分支合并、Mac依赖、额外定时器或新凭据。

文件持久保存结果及可用下载链接，以本次最终答复的实际工具回执为准；云内部路径
不能充当下载地址。报告和证据归档只提交一个有序Library批次，不预先声明保存成功。

报告生成UTC：2026-10-17T01:38:42.277502+00:00
