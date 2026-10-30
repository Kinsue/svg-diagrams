# EXAMPLES

Complete build scripts. Copy one, edit the content lists, run it.

## 1. Sequence diagram — multi-stage pipeline with a risk stage

Shows the shape to aim for: one `band` per stage, short arrow labels, one `note`
per stage carrying the caveat, and `alt`/`else` for the branch in the middle.

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from svgseq import render

ACTORS = ["sa-zeus", "CMDB", "sa-snmp-task", "sa-snmp-work", "Redis", "VictoriaMetrics"]

OPS = [
    ("band", "阶段 0 · 资产获取（周期 Refresh）"),
    ("msg", "sa-zeus", "sa-snmp-task", "GET /api/v1/switch-assets", True),
    ("msg", "sa-zeus", "sa-snmp-task", "switch rows —— 内存按 idc 校验", True),
    ("note", "CMDB", "sa-snmp-task", [
        "仅当上游报错才回落 CMDB：4 组状态过滤；idc_code 走顶层参数",
        "code=0 且 data=[] 视为权威空结果，不回落 —— 隔离边界就在这里",
    ]),
    ("msg", "CMDB", "sa-snmp-task", "OID 定义 / 端口 / Index 快照", True),

    ("band", "阶段 1 · 生成任务 + 固定地址派发"),
    ("self", "sa-snmp-task", "Generate：OID 合并与展开 → 按 step 分桶"),
    ("msg", "sa-snmp-task", "sa-snmp-work", "POST /api/v1/snmp（固定单地址）"),

    ("band", "阶段 2 · 采集执行"),
    ("alt_start", "alt type = index"),
    ("msg", "sa-snmp-work", "Redis", "写 index 快照"),
    ("alt_else", "else type = metric"),
    ("msg", "sa-snmp-work", "Redis", "写 metric 快照 + oct_prev"),
    ("msg", "sa-snmp-work", "VictoriaMetrics", "POST /api/v1/import/prometheus"),
    ("alt_end",),

    ("band", "阶段 3 · 下游消费（缺席即删）", "danger"),
    ("msg", "sa-snmp-work", "sa-zeus", "提供 index 快照", True),
    ("msg", "sa-zeus", "CMDB", "重建 port / lldp；孤儿清理全局删除"),

    ("foot", "注 1：work 全程无机房概念，隔离只发生在上游的设备选择侧。"),
    ("foot", "注 2：删除查询从不按被删行的 idc_code 过滤。"),
]

print(render("主链路时序图", "branch: idc_isolation", ACTORS, OPS, "main-flow.svg"))
```

## 2. Sequence diagram — risk contrast

The same renderer, used to make one failure mode obvious: the safe step is `ok`
(green), every deleting step is `danger` (red) with its reason in a red note.

```python
from svgseq import render

ACTORS = ["调度器", "sa-snmp-work", "Redis", "sa-zeus", "CMDB", "Elasticsearch"]

OPS = [
    ("band", "A · index-port 同步（只 upsert，不删缺席）", "ok"),
    ("msg", "调度器", "sa-zeus", "sync-index-ports-from-snmp-work"),
    ("msg", "sa-zeus", "sa-snmp-work", "拉 index 快照", True),
    ("msg", "sa-zeus", "CMDB", "只 create / update"),
    ("note", "sa-zeus", "CMDB", ["缺席的端口仅被跳过，不删除 —— 这一步没有删除风险"], "ok"),

    ("band", "B · 孤儿清理（全局删除，最锐利）", "danger"),
    ("msg", "调度器", "sa-zeus", "POST cleanup-orphan-switch-ports（dry_run 默认 false）"),
    ("msg", "sa-zeus", "CMDB", "拉全部 ts_switch_port", True),
    ("msg", "sa-zeus", "CMDB", "DeleteInstanceBatch：switch_id 不在有效集"),
    ("self", "CMDB", "物理删除"),
    ("note", "sa-zeus", "CMDB", [
        "全链路无 idc_code 过滤 —— 一次调用即可影响所有机房",
        "有效交换机索引只读第 1 页，超出即被误判为孤儿",
    ], "danger"),

    ("band", "C · LLDP 同步（按 hostname 删缺席行）", "danger"),
    ("self", "sa-zeus", "先记 host，之后才判 LLDP 结果是否为空"),
    ("msg", "sa-zeus", "CMDB", "删除不在 snapshotKeys 的 ts_switch_lldp"),
    ("note", "sa-zeus", "CMDB", ["完整性缺口：快照缺 lldpInfo 时仍进入删除集合"], "danger"),

    ("msg", "CMDB", "Elasticsearch", "resourceindex 镜像 _deleted", True),
    ("foot", "根因：删除语义是「缺席即删」，而缺席判定没有机房边界。"),
]

print(render("删除链路时序图（跨机房误删风险）", "branch: idc_isolation", ACTORS, OPS, "delete-chain.svg"))
```

## 3. Flow / layered architecture

Layers are the flow order. Layer titles become dashed zone frames, so ownership
boundaries are visible without drawing anything extra.

```python
from svgflow import render

LAYERS = [
    {"title": "数据源", "boxes": [
        {"id": "cmdb", "label": "CMDB", "sub": "资产真源", "tone": "store"},
        {"id": "redis", "label": "Redis", "sub": "快照缓存", "tone": "store"},
    ]},
    {"title": "机房 A（隔离边界内）", "boxes": [
        {"id": "task", "label": "sa-snmp-task", "sub": "选设备 + 生成任务", "tone": "info"},
        {"id": "work", "label": "sa-snmp-work", "sub": "执行采集", "tone": "ok"},
    ]},
    {"title": "机房 B（应完全隔离）", "boxes": [
        {"id": "task_b", "label": "sa-snmp-task", "sub": "共享同一 Redis key", "tone": "danger"},
    ]},
]

EDGES = [
    ("cmdb", "task", "按 idc 范围读"),
    ("task", "work", "固定地址 dispatch"),
    ("work", "redis", "写快照（key 无 IDC 段）"),
    {"from": "redis", "to": "task_b", "label": "读到别机房数据", "dashed": True},
]

print(render("SNMP 隔离现状", "branch: idc_isolation", LAYERS, EDGES, "arch.svg",
             direction="LR", notes=["注：机房 A 与 B 共用同一 key 前缀，混用与互删都可能发生。"]))
```

Use `direction="TB"` when the flow is naturally top-down (request path, call stack,
ingest pipeline).