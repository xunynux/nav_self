# Point-LIO 点云地图原理详解

## 问题：点云地图是单次保存还是叠加保存？

**答案：叠加保存（累积所有帧）**

---

## 📊 工作原理图解

```
建图时间线：
┌──────────────────────────────────────────────────────────────┐
│  t=0s    t=1s    t=2s    t=3s    ...    t=60s    退出保存   │
│   ↓       ↓       ↓       ↓       ↓       ↓         ↓       │
│ Frame1  Frame2  Frame3  Frame4   ...  Frame600   scans.pcd  │
│   │       │       │       │       │       │         │       │
│   └───────┴───────┴───────┴───────┴───────┴─────────┘       │
│            累积到 pcl_wait_save 缓存中                       │
│            (每帧都叠加，不是替换)                            │
└──────────────────────────────────────────────────────────────┘

最终 scans.pcd = Frame1 + Frame2 + ... + Frame600 (所有帧的并集)
```

---

## 💻 代码实现（laserMapping.cpp）

### 核心逻辑

```cpp
// 1. 每帧点云转换到全局坐标系
for (int i = 0; i < feats_down_body->points.size(); i++) {
    pointBodyToWorld(&feats_down_body->points[i], &feats_down_world->points[i]);
}

// 2. 叠加累积（关键操作：+=）
*pcl_wait_save += *feats_down_world;  // 不是赋值(=)，而是追加(+=)
static int scan_wait_num = 0;
scan_wait_num++;

// 3. 保存策略
if (pcd_save_interval > 0 && scan_wait_num >= pcd_save_interval) {
    // 间隔保存模式：每N帧保存一次
    pcd_writer.writeBinary("PCD/scans_" + to_string(pcd_index) + ".pcd", *pcl_wait_save);
    pcl_wait_save->clear();  // 保存后清空，重新累积
    scan_wait_num = 0;
} else if (pcd_save_interval == -1) {
    // 一次性保存模式：退出时保存所有帧
    // （在程序结束时执行）
    pcd_writer.writeBinary("PCD/scans.pcd", *pcl_wait_save);
}
```

---

## ⚙️ 配置参数（mid360.yaml）

```yaml
pcd_save:
    pcd_save_en: False              # 是否启用PCD保存
    interval: -1                    # 保存间隔
                                    # -1: 累积所有帧，退出时一次性保存
                                    # >0: 每N帧保存一次，然后清空缓存
```

---

## 📋 三种保存模式对比

### 模式1：一次性保存（推荐：短时间建图）

```yaml
pcd_save:
    pcd_save_en: True
    interval: -1
```

**行为：**
- 累积所有帧到内存
- 按`Ctrl+C`退出时一次性保存

**输出文件：**
```
~/nav_self/nav_ws/PCD/scans.pcd (单个大文件，包含所有点)
```

**优点：**
- 最完整的地图（无遗漏）
- 文件管理简单

**缺点：**
- 长时间建图可能内存溢出
- 如果程序崩溃，数据全部丢失

---

### 模式2：分段保存（推荐：长时间建图）

```yaml
pcd_save:
    pcd_save_en: True
    interval: 100  # 每100帧保存一次
```

**行为：**
- 每累积100帧自动保存
- 保存后清空缓存，重新累积

**输出文件：**
```
~/nav_self/nav_ws/PCD/
├── scans_1.pcd   (第1-100帧)
├── scans_2.pcd   (第101-200帧)
├── scans_3.pcd   (第201-300帧)
└── ...
```

**优点：**
- 内存安全（定期清空）
- 分段备份（防止崩溃丢失所有数据）

**缺点：**
- 需要后续合并多个PCD文件

---

### 模式3：不保存

```yaml
pcd_save:
    pcd_save_en: False
    interval: -1
```

**行为：**
- 只用于实时导航，不保存地图

---

## 🔍 验证点云叠加效果

### 方法1：查看点云数量

```bash
# 查看PCD文件信息
pcl_viewer ~/nav_self/nav_ws/PCD/scans.pcd

# 在pcl_viewer窗口按 '5' 键查看点云强度分布
# 越密集的地方说明重复扫描次数越多
```

### 方法2：统计点云数量

```bash
# 提取点数信息
head -20 ~/nav_self/nav_ws/PCD/scans.pcd | grep POINTS
```

**示例输出：**
```
POINTS 5423891  # 542万个点（远超单帧的几千点）
```

**分析：**
- Livox Mid360单帧约5000-10000点
- 如果保存的PCD有几十万甚至上百万点 → 证明是多帧叠加

---

## 🎯 实际建图建议

### 短时间建图（<5分钟）
```yaml
pcd_save:
    pcd_save_en: True
    interval: -1  # 一次性保存
```

遥控小车匀速走完整个场地 → `Ctrl+C` → 自动保存

---

### 长时间建图（>10分钟）
```yaml
pcd_save:
    pcd_save_en: True
    interval: 200  # 每200帧保存一次
```

**后续合并PCD文件：**
```bash
cd ~/nav_self/nav_ws/PCD

# 使用PCL合并工具
pcl_concatenate_points_pcd scans_*.pcd -o merged_map.pcd

# 或使用Python脚本
python3 << 'EOF'
import open3d as o3d
import glob

pcd_files = sorted(glob.glob("scans_*.pcd"))
combined = o3d.geometry.PointCloud()

for f in pcd_files:
    pcd = o3d.io.read_point_cloud(f)
    combined += pcd
    print(f"Loaded {f}: {len(pcd.points)} points")

o3d.io.write_point_cloud("merged_map.pcd", combined)
print(f"Merged map saved: {len(combined.points)} total points")
EOF
```

---

## 🚨 常见误区

### ❌ 误区1："保存最后一帧点云"
**错误理解：** `scans.pcd`只保存退出前的最后一帧

**正确理解：** `scans.pcd`包含从启动到退出的**所有帧叠加**

---

### ❌ 误区2："需要手动触发保存"
**错误理解：** 每次想保存就调用ROS服务

**正确理解：** 
- `interval=-1`：自动累积，退出时自动保存
- `interval=100`：每100帧自动保存
- 无需手动触发

---

### ❌ 误区3："重复扫描会覆盖旧数据"
**错误理解：** 走过的地方再走一遍，点云会被新数据覆盖

**正确理解：** 
- 重复扫描会**增加点云密度**
- 使用`+=`追加，不是`=`替换
- Point-LIO的位姿估计保证新旧点云对齐

---

## 📊 点云质量优化

### 提高地图质量的技巧

1. **匀速移动**
   - 速度：0.2-0.5 m/s
   - 避免急转、急停（减少IMU误差）

2. **完整覆盖**
   - 走"回字形"路径
   - 确保LiDAR能看到所有区域

3. **适度重复**
   - 关键区域（门口、转角）可多次扫描
   - 增加点云密度，提高重定位精度

4. **环境要求**
   - 避免强光直射LiDAR
   - 避免大量移动物体（行人）
   - 首选静态场景

---

## 🔗 相关文件

- 配置文件：`nav_ws/src/pb2025_sentry_nav/02_point_lio/config/mid360.yaml`
- 核心代码：`nav_ws/src/pb2025_sentry_nav/02_point_lio/src/laserMapping.cpp`
- 输出目录：`~/nav_self/nav_ws/PCD/`

---

## 总结

✅ **Point-LIO的PCD地图是所有帧的累积叠加，不是单次快照**

✅ **建图时间越长、覆盖越完整，地图越详细**

✅ **配置`interval=-1`适合短时间建图，`interval>0`适合长时间建图**

✅ **重复扫描不会覆盖数据，只会增加点云密度**
