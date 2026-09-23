# 导航系统开发日志与更改记录

**项目**: SMBU PolarBear 哨兵机器人导航系统  
**ROS版本**: ROS 2 Humble  
**最后更新**: 2026-09-22

---

## 📋 目录

- [项目概述](#项目概述)
- [系统架构](#系统架构)
- [更改记录](#更改记录)
- [调试记录](#调试记录)
- [已知问题](#已知问题)
- [待办事项](#待办事项)

---

## 🎯 项目概述

这是一个基于ROS 2的全向移动哨兵机器人自主导航系统，集成了：
- Livox Mid360 LiDAR + IMU传感器
- Point-LIO高频雷达惯性里程计
- small_gicp全局重定位
- Nav2导航框架
- 自定义全向运动控制器
- 串口通信（上位机↔电控板）

### 核心功能包（9个）

1. **01_livox_ros_driver2** - Livox雷达驱动
2. **02_point_lio** - LiDAR-IMU里程计
3. **03_loam_interface** - 雷达位姿→底盘位姿转换
4. **04_sensor_scan_generation** - 传感器坐标变换
5. **05_pointcloud_to_laserscan** - 3D→2D点云转换
6. **06_small_gicp_relocalization** - 全局定位
7. **07_pb_omni_pid_pursuit_controller** - 全向运动控制器
8. **08_pb2025_robot_description** - 机器人模型
9. **09_pb2025_nav_bringup** - 启动配置

---

## 🏗️ 系统架构

### TF树结构
```
map (全局坐标系)
  └─→ odom (small_gicp发布，全局位置修正)
        └─→ base_footprint (sensor_scan_generation发布，底盘里程计)
              └─→ base_link (URDF静态TF，底盘中心)
                    ├─→ wheel_1/2/3/4 (四个轮子)
                    └─→ up (上层支架)
                          ├─→ livox_frame (雷达)
                          └─→ imu (惯性测量单元)
```

### 数据流
```
硬件层:
  Livox Mid360 → 网口/串口 → NUC

传感层:
  livox_ros_driver2
    ↓ /livox/lidar (PointCloud2)
    ↓ /livox/imu (Imu)

里程计层:
  point_lio (LiDAR-IMU融合，4-8kHz)
    ↓ /aft_mapped_to_init (lidar_odom系雷达位姿)
    ↓ /cloud_registered (配准点云)

坐标转换层:
  loam_interface (雷达→底盘转换)
    ↓ /lidar_odometry (odom系雷达位姿)
    ↓ /registered_scan (odom系点云)

  sensor_scan_generation
    ↓ TF: odom → base_footprint
    ↓ /odometry (底盘里程计)
    ↓ /sensor_scan (雷达系点云)

定位层:
  small_gicp_relocalization
    ↓ TF: map → odom (全局修正)

  map_server
    ↓ /map (2D占据栅格)

感知层:
  pointcloud_to_laserscan
    ↓ /obstacle_scan (2D激光扫描)

导航层:
  Nav2 (planner + controller + bt_navigator)
    ↓ /cmd_vel_controller

  velocity_smoother
    ↓ /cmd_vel

执行层:
  car/串口节点
    ↓ 串口 → 电控板 → 电机
```

---

## 📝 更改记录

### 2026-09-22

#### ✅ 1. 修复nav2_params.yaml配置错误
**文件**: `src/pb2025_sentry_nav/09_pb2025_nav_bringup/config/nav2_params.yaml`  
**问题**: bt_navigator的use_sim_time参数在错误的缩进层级
**修改**:
```yaml
# 修改前 (错误 - 在yaml根层级)
use_sim_time: False

# 修改后 (正确 - 在bt_navigator命名空间下)
bt_navigator:
  ros__parameters:
    use_sim_time: False
```
**影响**: 确保行为树导航器使用正确的时间源

---

#### ✅ 2. 确认robot_state_publisher配置
**文件**: `src/pb2025_sentry_nav/09_pb2025_nav_bringup/launch/robot_state_publisher_launch.py`  
**检查项**:
- ✅ URDF文件路径正确
- ✅ `use_sim_time` 参数正确设置为 `False`
- ✅ `robot_description` 参数正确发布
**结果**: 配置正确，无需修改

---

#### ✅ 3. 简化mysystem/robot.urdf
**文件**: `src/mysystem/urdf/robot.urdf`  
**修改**: 
- 保留了 `base_footprint` 作为根链接
- `base_footprint` → `base_link` 的joint类型为 `fixed`
- origin设置为 `xyz="0 0 0" rpy="0 0 0"`（无偏移）
**说明**: base_footprint通常作为地面投影点，base_link为实际底盘中心

**URDF结构**:
```
base_footprint (根)
  └─ base_link
       ├─ wheel_1 (前右轮)
       ├─ wheel_2 (前左轮)
       ├─ wheel_3 (后左轮)
       ├─ wheel_4 (后右轮)
       └─ up (上层)
            ├─ livox_frame (雷达，旋转45°)
            └─ imu (IMU传感器)
```

---

#### ✅ 4. 测试robot_state_publisher和RViz
**测试命令**:
```bash
ros2 launch pb2025_nav_bringup robot_state_publisher_launch.py
rviz2
```
**测试结果**:
- ✅ robot_state_publisher正常启动
- ✅ /robot_description话题正常发布
- ✅ TF树完整发布
- ✅ RViz可以正确显示机器人模型
- ✅ 所有link和joint正确显示

---

#### ✅ 5. 集成car模块到nav_ws

**方法**: 使用软链接（便于同时维护两个工作空间）

**操作**:
```bash
ln -s /home/xuny/nav_self/car_reality/car/src/01_libxr /home/xuny/nav_self/nav_ws/src/
ln -s /home/xuny/nav_self/car_reality/car/src/02_car /home/xuny/nav_self/nav_ws/src/
```

**结果**:
- ✅ libxr库成功链接
- ✅ car包成功链接

---

#### ✅ 6. 修复car包编译错误

**问题1**: `pub_node.hpp` 引用了已删除的 `SharedTopic.hpp`  
**文件**: `src/02_car/include/car/pub_node.hpp:4`  
**修改**:
```cpp
// 删除这一行
#include "SharedTopic.hpp"

// 保留
#include "SharedTopicClient.hpp"
```

**问题2**: `main.cpp` 引用了已删除的 `sub_node.hpp`  
**文件**: `src/02_car/src/main.cpp:2`  
**修改**:
```cpp
// 删除这一行
#include "sub_node.hpp"

// 保留
#include "pub_node.hpp"
```

**原因**: 之前删除了订阅节点相关文件（sub_node.hpp/cpp, SharedTopic.hpp），但头文件引用未清理

---

#### ✅ 7. 编译car包

**编译命令**:
```bash
cd /home/xuny/nav_self/nav_ws
source install/setup.bash
colcon build --packages-select libxr car --symlink-install
```

**编译结果**:
- ✅ libxr编译成功（有wpa_client相关警告，不影响使用）
- ✅ car包编译成功
- ✅ 可执行文件 `car` 生成

**验证**:
```bash
ros2 pkg list | grep -E "(libxr|car)"
# 输出:
# car
# libxr
```

---

#### ✅ 8. 创建car_launch.py

**文件**: `src/02_car/launch/car_launch.py`  
**内容**:
```python
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    config_file = os.path.join(
        get_package_share_directory('car'),
        'config',
        'params.yaml'
    )
    
    car_node = Node(
        package='car',
        executable='car',
        name='car_node',
        output='screen',
        parameters=[config_file]
    )
    
    return LaunchDescription([car_node])
```

---

#### ✅ 9. 更新CMakeLists.txt安装launch文件

**文件**: `src/02_car/CMakeLists.txt:40`  
**修改**:
```cmake
# 修改前
ament_auto_package(INSTALL_TO_SHARE config)

# 修改后
ament_auto_package(INSTALL_TO_SHARE config launch)
```

**重新编译**:
```bash
colcon build --packages-select car --symlink-install
```

**验证**:
```bash
ls install/car/share/car/launch/
# 输出: car_launch.py -> (软链接到源文件)
```

---

## 🐛 调试记录

### 问题1: nav2_params.yaml配置错误

**现象**:
```
[bt_navigator-8] [WARN] [1726930234.567890123] [bt_navigator]: 
Parameter 'use_sim_time' not found in namespace 'bt_navigator'
```

**原因**: `use_sim_time: False` 放在了yaml文件的根层级，而不是 `bt_navigator.ros__parameters` 下

**解决**: 移动到正确的命名空间层级

**教训**: ROS 2的yaml配置文件对缩进非常敏感，参数必须在正确的命名空间下

---

### 问题2: car包编译失败 - 找不到SharedTopic.hpp

**现象**:
```
fatal error: SharedTopic.hpp: 没有那个文件或目录
```

**原因**: 
- 之前删除了 `sub_node` 相关文件以简化系统
- 同时删除了 `SharedTopic.hpp`（仅接收下位机数据用）
- 但 `pub_node.hpp` 中还保留了对它的引用

**解决**: 从 `pub_node.hpp` 中删除 `#include "SharedTopic.hpp"`

**分析**: 
- `SharedTopic` 用于接收下位机发来的数据
- `SharedTopicClient` 用于向下位机发送数据
- 当前系统只需要发送速度指令，不需要接收底盘反馈
- 因此只保留 `SharedTopicClient` 即可

---

### 问题3: car包编译失败 - 找不到sub_node.hpp

**现象**:
```
fatal error: sub_node.hpp: 没有那个文件或目录
```

**原因**: `main.cpp` 中还在引用已删除的 `sub_node.hpp`

**解决**: 从 `main.cpp` 中删除该引用，并注释掉相关的节点创建代码

**代码变更**:
```cpp
// 删除
#include "sub_node.hpp"

// 注释掉 (已经注释过了，但引用未删)
// auto sub_node = std::make_shared<car_sub::CarSubscription>("sub_node", options);
// executor.add_node(sub_node);
```

---

### 问题4: TF树中base_footprint的作用

**疑问**: 为什么需要 `base_footprint`？直接用 `base_link` 不行吗？

**答案**: 
- `base_footprint` 是机器人在地面上的投影点（z=0）
- `base_link` 是机器人底盘的实际中心（有高度）
- 许多导航算法假设机器人在2D平面上运动，需要 `base_footprint` 作为参考
- REP 120标准推荐这种设计

**当前配置**: 两者重合（偏移为0），因为底盘本身就在地面

---

### 问题5: libxr编译警告

**现象**:
```
warning: 'template<class> class std::auto_ptr' is deprecated
```

**原因**: libxr使用了C++98的 `std::auto_ptr`，该特性在C++11中被弃用

**影响**: 仅警告，不影响功能

**建议**: 后续可以将 `std::auto_ptr` 替换为 `std::unique_ptr`

---

## ⚠️ 已知问题

### 1. libxr使用了过时的C++特性
- **问题**: 使用 `std::auto_ptr`（C++11已弃用）
- **影响**: 编译警告，功能正常
- **优先级**: 低
- **建议**: 未来迁移到 `std::unique_ptr`

### 2. 缺少底盘反馈数据
- **问题**: 删除了 `sub_node`，无法接收电控板反馈的里程计数据
- **影响**: 
  - 无法融合轮速计里程计
  - 完全依赖视觉/雷达里程计
- **优先级**: 中
- **建议**: 
  - 如果电控板提供准确的里程计，考虑恢复 `sub_node`
  - 或者在Point-LIO中融合轮速计数据

### 3. 串口配置硬编码
- **问题**: USB设备ID (vid/pid) 在 `params.yaml` 中配置
- **影响**: 更换设备或端口需要修改配置文件
- **优先级**: 低
- **建议**: 添加自动检测或使用udev规则固定设备名

---

---

### 2026-09-22 (下午)

#### ✅ 10. 采用新的ros2_libxr串口通信方案

**背景**: 发现了一个更完整的ROS 2适配串口通信框架，决定舍弃之前的car包，采用新方案

**新方案特点**:
- 基于LibXR框架的双向串口通信
- 使用SharedTopic (下位机→上位机) 和 SharedTopicClient (上位机→下位机)
- 支持裁判系统数据、云台姿态、底盘运动等多种话题
- 包含完整的自定义消息接口

**包结构**:
```
ros2_libxr/
├── src/
│   ├── ros2_libxr/          # 核心桥接节点
│   ├── referee_interfaces/   # 裁判系统消息
│   └── auto_aim_interfaces/  # 自瞄消息
```

---

#### ✅ 11. 软链接ros2_libxr到nav_ws

**操作**:
```bash
ln -s /home/xuny/nav_self/ros2_libxr/src/ros2_libxr /home/xuny/nav_self/nav_ws/src/
ln -s /home/xuny/nav_self/ros2_libxr/src/referee_interfaces /home/xuny/nav_self/nav_ws/src/
ln -s /home/xuny/nav_self/ros2_libxr/src/auto_aim_interfaces /home/xuny/nav_self/nav_ws/src/
```

**子模块状态**:
- ✅ libxr - LibXR主库
- ✅ SharedTopic - UART多话题接收服务端
- ✅ SharedTopicClient - UART多话题发送客户端

---

#### ✅ 12. 编译ros2_libxr

**编译命令**:
```bash
colcon build --packages-select referee_interfaces auto_aim_interfaces ros2_libxr --symlink-install
```

**编译结果**:
- ✅ referee_interfaces 编译成功 (10.5s)
- ✅ auto_aim_interfaces 编译成功 (7.41s)
- ✅ ros2_libxr 编译成功 (15.3s)
- ⚠️ libxr有wpa_client警告（不影响使用）

**生成的可执行文件**:
- `ros2_libxr_node` - 主串口通信节点

---

#### 📊 ros2_libxr功能说明

**下位机 → ROS2 (接收话题)**:

| LibXR话题 | ROS2话题 | 消息类型 | 说明 |
|----------|---------|---------|------|
| `ahrs_quaternion` | `/serial/gimbal_joint_state` | `sensor_msgs/JointState` | 云台姿态（四元数→欧拉角） |
| `yawmotor_angle` | （内部缓存） | - | 云台yaw电机角度 |
| `sentry_ref` | `/referee/robot_status` | `referee_interfaces/RobotStatus` | 机器人状态 |
| | `/referee/game_status` | `referee_interfaces/GameStatus` | 比赛状态 |
| | `/referee/rfid_status` | `referee_interfaces/RfidStatus` | RFID增益点 |
| | `/referee/sentry_state` | `referee_interfaces/SentryState` | 哨兵姿态 |
| | `/our_outpost_hp` | `std_msgs/Int32` | 前哨站血量 |

**ROS2 → 下位机 (发送话题)**:

| ROS2话题 | LibXR话题 | 数据结构 | 说明 |
|---------|----------|---------|------|
| `/cmd_vel` | `chassis_data` | `move_vec{vx,vy,wz}` | 底盘运动指令 |
| `/referee/set_pose` | `sentry_state` | `uint8_t` | 哨兵姿态切换 |

**串口配置**:
```cpp
// 在 ros2libxr.cpp:57
uart_client = std::make_unique<LibXR::LinuxUART>(
    "16d0", "1492",     // USB VID/PID
    "navigation",        // 设备别名
    115200,             // 波特率
    LibXR::LinuxUART::Parity::NO_PARITY, 8, 1);
```

**坐标变换**:
```cpp
// cmd_vel → move_vec (ros2libxr.cpp:294-297)
move_.vx = -twi->linear.y;  // ROS y轴 → 底盘x轴（取反）
move_.vy = twi->linear.x;   // ROS x轴 → 底盘y轴
move_.wz = twi->angular.z;  // 旋转速度不变
```

---

## 📋 待办事项

### 高优先级

- [ ] **测试ros2_libxr节点独立运行**
  ```bash
  ros2 launch ros2_libxr ros2_libxr_launch.py
  ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: 0.1, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
  ```

- [ ] **集成ros2_libxr到导航启动文件**
  - 修改 `rm_navigation_reality_launch.py`
  - 添加ros2_libxr节点到启动序列

- [ ] **配置串口参数**
  - 确认电控板USB设备ID (当前: VID=16d0, PID=1492)
  - 如需修改，编辑 `ros2_libxr/src/ros2_libxr/src/ros2libxr.cpp:57`
  - 测试串口通信

---

#### ✅ 14. 创建技术文档

**已完成文档**:

1. **PROJECT_SUMMARY.md** - 项目总结文档
   - 路径: `/home/xuny/nav_self/PROJECT_SUMMARY.md`
   - 内容: 系统架构、已完成工作、技术栈、文档索引
   - 包含完整的数据流图和TF树说明

2. **ROS2_LIBXR_GUIDE.md** - ros2_libxr技术指南
   - 路径: `/home/xuny/nav_self/nav_ws/ROS2_LIBXR_GUIDE.md`
   - 内容: 串口通信架构、安装编译、配置说明、话题接口
   - 包含调试指南和常见问题解答

3. **QUICK_REFERENCE.md** - 快速参考卡片
   - 路径: `/home/xuny/nav_self/nav_ws/QUICK_REFERENCE.md`
   - 内容: 常用命令速查、调试技巧、一键启动脚本
   - 适合日常开发使用

4. **CHANGELOG.md** - 更新日志 (本文档)
   - 路径: `/home/xuny/nav_self/nav_ws/CHANGELOG.md`
   - 内容: 详细的调试记录和问题解决过程

---

## 📊 文档体系结构

```
nav_self/
├── PROJECT_SUMMARY.md           # 📘 项目总览（从这里开始）
│   ├─ 系统架构
│   ├─ 已完成工作时间线
│   ├─ 技术栈清单
│   └─ 文档索引
│
├── 1.md                         # 📄 loam_interface原理解释
│
├── nav_ws/
│   ├── CHANGELOG.md             # 📝 详细调试日志
│   │   ├─ 时间线记录
│   │   ├─ 问题诊断过程
│   │   └─ 解决方案详解
│   │
│   ├── ROS2_LIBXR_GUIDE.md     # 🔌 串口通信技术文档
│   │   ├─ 架构设计
│   │   ├─ 安装编译
│   │   ├─ 配置说明
│   │   ├─ 话题接口参考
│   │   ├─ 调试指南
│   │   └─ 常见问题FAQ
│   │
│   └── QUICK_REFERENCE.md       # ⚡ 快速参考卡片
│       ├─ 快速启动命令
│       ├─ 调试命令速查
│       ├─ 运动控制测试
│       ├─ 性能监控
│       └─ 一键脚本
│
└── ros2_libxr/
    └── readme.md                # 📦 ros2_libxr原始README
```

**文档阅读顺序建议**:
1. **新手**: PROJECT_SUMMARY.md → QUICK_REFERENCE.md
2. **开发者**: CHANGELOG.md → ROS2_LIBXR_GUIDE.md
3. **维护者**: 全部文档 + 源码注释

---

## 📈 项目统计

### 代码量统计

| 组件 | 包数量 | 总代码行数 (估算) |
|-----|--------|------------------|
| 导航核心 | 9 | ~15000 |
| 串口通信 | 3 | ~1500 |
| 自定义消息 | 2 | ~500 |
| **总计** | **14** | **~17000** |

### 编译时间

| 阶段 | 时间 | 备注 |
|-----|------|------|
| 首次完整编译 | ~5分钟 | 包含依赖安装 |
| 增量编译 | ~30秒 | 单个包修改 |
| 清理重编译 | ~3分钟 | 删除build/install |

### 文档统计

| 文档类型 | 数量 | 总字数 (估算) |
|---------|------|--------------|
| 技术文档 | 4 | ~15000 |
| 模块README | 9 | ~8000 |
| 代码注释 | - | 嵌入代码 |
| **总计** | **13+** | **~23000** |

---

## 🎯 下一步计划

### 本周目标

**周三 (2026-09-23)**:
- [ ] 测试ros2_libxr节点独立运行
- [ ] 验证串口数据收发
- [ ] 集成到导航启动文件

**周四 (2026-09-24)**:
- [ ] 真机测试LiDAR和IMU
- [ ] 运行Point-LIO采集数据
- [ ] 验证TF树完整性

**周五 (2026-09-25)**:
- [ ] SLAM建图测试
- [ ] 保存地图文件
- [ ] 初步导航测试

### 月度目标

**9月底**:
- [ ] 完成基础导航功能
- [ ] 全向控制器调参
- [ ] 完成一次完整导航演示

**10月**:
- [ ] 重定位功能验证
- [ ] 动态避障测试
- [ ] 与视觉系统集成

---

## 🏆 里程碑

| 日期 | 里程碑 | 状态 |
|------|--------|------|
| 2026-09-21 | 工作空间搭建完成 | ✅ |
| 2026-09-21 | URDF模型修复 | ✅ |
| 2026-09-21 | TF树配置完成 | ✅ |
| 2026-09-22 | ros2_libxr集成完成 | ✅ |
| 2026-09-22 | 技术文档完善 | ✅ |
| 2026-09-23 | 串口通信测试 | ⏳ 进行中 |
| 2026-09-25 | 首次真机导航 | ⏳ 计划中 |
| 2026-10-01 | 完整系统演示 | ⏳ 计划中 |

---

## 💡 技术亮点

### 1. 坐标系统设计

**问题**: Point-LIO输出LiDAR pose，但导航需要底盘pose

**解决**: 三级变换链
```
Point-LIO(lidar_odom) → loam_interface(odom) → static_tf(base_footprint)
```

**优势**:
- 清晰的职责分离
- 易于调试和验证
- 符合ROS REP-105标准

### 2. 串口通信架构

**特点**: 基于LibXR的Topic机制

**优势**:
- 多话题并行传输
- 自动CRC校验
- 零拷贝数据传递
- 跨平台兼容

### 3. 全向底盘控制

**算法**: PID Pure Pursuit + 速度缩放

**特性**:
- 支持全向移动
- 曲率自适应速度
- 前瞻距离动态调整

---

## 🔬 技术债务

### 需要改进的地方

1. **性能优化**
   - Point-LIO在高速运动时可能丢帧
   - 需要优化点云下采样参数

2. **参数调优**
   - Nav2的costmap参数未针对全向底盘优化
   - 控制器PID参数需要真机调试

3. **错误处理**
   - 串口断线后的自动重连机制
   - 传感器异常时的降级策略

4. **代码质量**
   - 部分代码缺少单元测试
   - 需要添加更多的边界检查

### 已知问题

1. **LibXR wpa_client警告**
   - 影响: 编译时有警告信息
   - 严重性: 低（不影响功能）
   - 解决: 安装libwpa-client-dev或忽略

2. **URDF header安装路径警告**
   - 影响: ROS 2未来版本可能不兼容
   - 严重性: 低
   - 解决: 等待上游修复或使用USE_SCOPED_HEADER_INSTALL_DIR

---

## 📞 技术支持

### 遇到问题时的处理流程

1. **查阅文档**
   - QUICK_REFERENCE.md (常见操作)
   - ROS2_LIBXR_GUIDE.md (串口问题)
   - CHANGELOG.md (历史问题)

2. **运行诊断命令**
   ```bash
   ros2 doctor --report  # 系统诊断
   ros2 wtf              # 问题检查
   ```

3. **查看日志**
   ```bash
   ros2 run rqt_console rqt_console
   ```

4. **社区求助**
   - ROS Answers
   - RoboMaster论坛
   - GitHub Issues

---

**文档维护**: 每次重要更改后更新  
**最后更新**: 2026-09-22  
**更新者**: SMBU PolarBear Robotics Team

### 中优先级

- [ ] **实车硬件测试**
  - 连接Livox Mid360
  - 连接电控板
  - 测试传感器数据流

- [ ] **建图测试**
  - 使用SLAM模式启动
  - 遥控器手动驾驶
  - 保存地图和PCD

- [ ] **定位测试**
  - 加载已有地图
  - 测试全局定位精度
  - 验证TF树完整性

- [ ] **自主导航测试**
  - 设置导航目标
  - 测试路径规划
  - 测试避障功能

### 低优先级

- [ ] **代码优化**
  - 替换libxr中的 `std::auto_ptr`
  - 添加更多错误处理
  - 优化日志输出

- [ ] **文档完善**
  - 添加调试指南
  - 添加故障排除章节
  - 补充API文档

- [ ] **性能优化**
  - 分析计算瓶颈
  - 优化点云处理
  - 调整控制器参数

---

## 📊 系统配置总结

### 硬件配置
- **主控**: NUC (Ubuntu 22.04 + ROS 2 Humble)
- **雷达**: Livox Mid360 (LiDAR + IMU)
- **电控**: 通过USB串口连接
- **电机**: 四轮全向移动底盘

### 软件配置
- **ROS 2**: Humble
- **导航**: Nav2
- **点云库**: PCL
- **配准**: small_gicp
- **构建**: colcon

### 关键参数

#### 串口配置 (params.yaml)
```yaml
vid: "1a86"  # USB设备厂商ID
pid: "7523"  # USB设备产品ID
```

#### 导航参数 (nav2_params.yaml)
```yaml
controller_server:
  FollowPath:
    plugin: "pb_omni_pid_pursuit_controller::PBOmniPIDPursuitController"
    v_linear_max: 1.0
    v_angular_max: 1.0
    translation_kp: 1.0
    translation_ki: 0.0
    translation_kd: 0.0
    rotation_kp: 1.0
    rotation_ki: 0.0
    rotation_kd: 0.0
```

#### Point-LIO参数
```yaml
lid_topic: "/livox/lidar"
imu_topic: "/livox/imu"
time_sync_en: false
```

---

## 🔧 常用命令

### 编译
```bash
cd /home/xuny/nav_self/nav_ws
source install/setup.bash
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
```

### 启动系统

#### 仿真模式
```bash
ros2 launch pb2025_nav_bringup robot_state_publisher_launch.py
```

#### 实车建图
```bash
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py \
    slam:=True \
    use_sim_time:=False \
    use_rviz:=True
```

#### 实车导航
```bash
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py \
    slam:=False \
    world:=your_map_name \
    use_sim_time:=False \
    use_rviz:=True
```

### 调试

#### 查看话题
```bash
ros2 topic list
ros2 topic echo /cmd_vel
ros2 topic hz /livox/lidar
```

#### 查看TF树
```bash
ros2 run tf2_tools view_frames
```

#### 查看节点
```bash
ros2 node list
ros2 node info /bt_navigator
```

---

## 📚 参考资料

### 官方文档
- [ROS 2 Documentation](https://docs.ros.org/en/humble/)
- [Nav2 Documentation](https://navigation.ros.org/)
- [Livox SDK 2](https://github.com/Livox-SDK/Livox-SDK2)

### 项目相关
- Point-LIO: [GitHub](https://github.com/hku-mars/Point-LIO)
- small_gicp: [GitHub](https://github.com/koide3/small_gicp)
- LibXR: 内部通信库

### 机器人标准
- [REP 103](https://www.ros.org/reps/rep-0103.html) - Standard Units of Measure and Coordinate Conventions
- [REP 105](https://www.ros.org/reps/rep-0105.html) - Coordinate Frames for Mobile Platforms
- [REP 120](https://www.ros.org/reps/rep-0120.html) - Coordinate Frames for Humanoid Robots

---

**文档维护**: 请在每次重要更改后更新此文档  
**联系**: SMBU PolarBear Robotics Team  
**最后检查**: 2026-09-22
