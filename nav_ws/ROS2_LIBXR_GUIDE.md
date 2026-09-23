# ROS2-LibXR 串口通信技术文档

**项目**: SMBU PolarBear 哨兵机器人导航系统  
**模块**: 上下位机串口通信桥接  
**最后更新**: 2026-09-22

---

## 📋 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [安装与编译](#安装与编译)
- [配置说明](#配置说明)
- [话题接口](#话题接口)
- [使用方法](#使用方法)
- [调试指南](#调试指南)
- [常见问题](#常见问题)

---

## 🎯 概述

ros2_libxr是一个ROS 2与嵌入式下位机之间的**双向串口通信桥接框架**，基于LibXR通信库实现。

### 核心功能

1. **双向通信**
   - 下位机 → 上位机: 接收云台姿态、裁判系统数据
   - 上位机 → 下位机: 发送底盘运动指令、姿态切换命令

2. **多话题支持**
   - 使用LibXR的Topic机制管理多个数据流
   - SharedTopic (接收端) 和 SharedTopicClient (发送端)

3. **自动数据转换**
   - 二进制数据 ↔ ROS 2消息
   - 四元数 → 欧拉角
   - 坐标系变换

---

## 🏗️ 架构设计

### 数据流向图

```
┌─────────────┐                                          ┌─────────────┐
│   下位机     │                                          │   上位机     │
│  (STM32)    │                                          │   (NUC)     │
└──────┬──────┘                                          └──────┬──────┘
       │                                                         │
       │ UART (115200 baud)                                     │
       │ USB CDC (VID:16d0 PID:1492)                           │
       │                                                         │
       ▼                                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LibXR Communication Layer                     │
├─────────────────────────────────────────────────────────────────┤
│  • LinuxUART: USB串口驱动 (linux_uart.hpp)                     │
│  • SharedTopic: 多话题接收服务端 (SharedTopic/)                │
│  • SharedTopicClient: 多话题发送客户端 (SharedTopicClient/)    │
│  • Topic机制: 发布-订阅模式                                     │
└─────────────────────────────────────────────────────────────────┘
       │                                                         │
       │ LibXR::Topic                                            │
       │                                                         │
       ▼                                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              RMSerialDriver (ROS 2 Node)                        │
├─────────────────────────────────────────────────────────────────┤
│  • 注册LibXR话题回调                                            │
│  • 数据格式转换                                                 │
│  • 坐标系变换                                                   │
│  • 发布/订阅ROS 2话题                                           │
└─────────────────────────────────────────────────────────────────┘
       │                                                         │
       │ ROS 2 Topics                                            │
       │                                                         │
       ▼                                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ROS 2 Network                              │
│  /cmd_vel, /serial/gimbal_joint_state, /referee/*, etc.        │
└─────────────────────────────────────────────────────────────────┘
```

### 包结构

```
ros2_libxr/
├── src/
│   ├── ros2_libxr/                    # 主包
│   │   ├── include/
│   │   │   ├── ros2_libxr/
│   │   │   │   └── ros2libxr.hpp      # 类定义、数据结构
│   │   │   ├── SharedTopic/           # [submodule] 接收端
│   │   │   └── SharedTopicClient/     # [submodule] 发送端
│   │   ├── src/
│   │   │   └── ros2libxr.cpp          # 实现代码
│   │   ├── launch/
│   │   │   └── ros2_libxr_launch.py   # 启动文件
│   │   ├── libxr/                     # [submodule] LibXR主库
│   │   ├── CMakeLists.txt
│   │   └── package.xml
│   │
│   ├── referee_interfaces/             # 裁判系统消息包
│   │   ├── msg/
│   │   │   ├── RobotStatus.msg        # 机器人状态
│   │   │   ├── GameStatus.msg         # 比赛状态
│   │   │   ├── RfidStatus.msg         # RFID增益点
│   │   │   ├── SentryState.msg        # 哨兵姿态
│   │   │   └── SetPose.msg            # 姿态设置指令
│   │   ├── CMakeLists.txt
│   │   └── package.xml
│   │
│   └── auto_aim_interfaces/            # 自瞄消息包
│       ├── msg/
│       │   ├── Send.msg
│       │   ├── Velocity.msg
│       │   └── Target.msg
│       ├── CMakeLists.txt
│       └── package.xml
│
├── readme.md                           # 项目文档
└── LICENSE
```

---

## 🔧 安装与编译

### 1. 克隆仓库（已完成）

仓库位于: `/home/xuny/nav_self/ros2_libxr`

### 2. 初始化子模块（已完成）

```bash
cd /home/xuny/nav_self/ros2_libxr
git submodule update --init --recursive
```

**子模块清单**:
- `src/ros2_libxr/libxr` - LibXR主库 (commit: 006996a)
- `src/ros2_libxr/include/SharedTopic` - 接收端 (auto-20260503-031041)
- `src/ros2_libxr/include/SharedTopicClient` - 发送端 (auto-20260503-203817)

### 3. 软链接到工作空间（已完成）

```bash
cd /home/xuny/nav_self/nav_ws/src
ln -s /home/xuny/nav_self/ros2_libxr/src/ros2_libxr .
ln -s /home/xuny/nav_self/ros2_libxr/src/referee_interfaces .
ln -s /home/xuny/nav_self/ros2_libxr/src/auto_aim_interfaces .
```

### 4. 编译

```bash
cd /home/xuny/nav_self/nav_ws
source install/setup.bash
colcon build --packages-select referee_interfaces auto_aim_interfaces ros2_libxr --symlink-install
```

**编译顺序**:
1. referee_interfaces (接口包)
2. auto_aim_interfaces (接口包)
3. ros2_libxr (依赖前两者)

**编译结果**:
- ✅ 3个包全部编译成功
- ⚠️ libxr有wpa_client警告（不影响串口通信功能）

---

## ⚙️ 配置说明

### 串口配置

**位置**: `src/ros2_libxr/src/ros2libxr.cpp:57-58`

```cpp
uart_client = std::make_unique<LibXR::LinuxUART>(
    "16d0", "1492",              // USB设备 VID/PID
    "navigation",                 // 设备别名
    115200,                       // 波特率
    LibXR::LinuxUART::Parity::NO_PARITY,  // 无校验
    8,                            // 8数据位
    1                             // 1停止位
);
```

**如何修改串口配置**:

1. **查看USB设备ID**:
   ```bash
   lsusb
   # 输出示例: Bus 001 Device 005: ID 16d0:1492 MCS Digistump DigiSpark
   ```

2. **修改VID/PID**:
   ```cpp
   uart_client = std::make_unique<LibXR::LinuxUART>(
       "YOUR_VID", "YOUR_PID",  // 替换为实际设备ID
       ...
   ```

3. **修改波特率** (如果需要):
   ```cpp
   115200  →  修改为其他值 (常用: 9600, 115200, 921600)
   ```

4. **重新编译**:
   ```bash
   colcon build --packages-select ros2_libxr --symlink-install
   ```

### LibXR话题注册

**位置**: `include/ros2_libxr/ros2libxr.hpp:196-215`

```cpp
static void XRobotMain(LibXR::HardwareContainer &hw) {  
  using namespace LibXR;
  static ApplicationManager appmgr;

  // 接收话题 (下位机 → 上位机)
  static SharedTopic shared_topic_rx(
      hw, appmgr, "uart_client", 256,
      {{"ahrs_quaternion"},       // 云台姿态四元数
       {"yawmotor_angle"},        // 云台yaw电机角度
       {"sentry_ref"}}            // 裁判系统数据包
  );
  
  // 发送话题 (上位机 → 下位机)
  static SharedTopicClient shared_topic_tx(
      hw, appmgr, "uart_client", 16,
      {{"chassis_data"},          // 底盘运动指令
       {"sentry_state"}}          // 哨兵姿态切换
  );
}
```

**新增话题的步骤**:

1. **在XRobotMain中注册话题名**
2. **在RMSerialDriver构造函数中创建LibXR::Topic对象**
3. **注册回调函数处理数据**
4. **创建对应的ROS 2发布者/订阅者**

---

## 📡 话题接口

### 下位机 → ROS2 (接收方向)

#### 1. 云台姿态

**LibXR话题**: `ahrs_quaternion`  
**数据类型**: `LibXR::Quaternion<float>`  
**ROS2话题**: `/serial/gimbal_joint_state`  
**消息类型**: `sensor_msgs/JointState`

**数据流**:
```
下位机四元数 → convert_quaternion_to_euler() → 欧拉角(pitch, yaw, roll)
  ↓
JointState.position[0] = pitch (从AHRS)
JointState.position[1] = yaw (从yawmotor_angle缓存)
```

**代码位置**: `ros2libxr.cpp:133-162`

---

#### 2. 云台yaw电机角度

**LibXR话题**: `yawmotor_angle`  
**数据类型**: `float`  
**用途**: 内部缓存，用于组合云台关节状态

**代码位置**: `ros2libxr.cpp:166-172`

---

#### 3. 裁判系统数据包

**LibXR话题**: `sentry_ref`  
**数据类型**: `RobotGameRefereePack` (复合结构体)

**拆解为5个ROS2话题**:

| ROS2话题 | 消息类型 | 内容 |
|---------|---------|------|
| `/referee/robot_status` | `referee_interfaces/RobotStatus` | 机器人ID、等级、血量、功率限制等 |
| `/referee/game_status` | `referee_interfaces/GameStatus` | 比赛类型、进程、剩余时间 |
| `/referee/rfid_status` | `referee_interfaces/RfidStatus` | 23个增益点状态位图 |
| `/referee/sentry_state` | `referee_interfaces/SentryState` | 哨兵当前姿态(0/1/2) |
| `/our_outpost_hp` | `std_msgs/Int32` | 己方前哨站血量 |

**RobotGameRefereePack结构** (`ros2libxr.hpp:183-191`):
```cpp
struct [[gnu::packed]] RobotGameRefereePack {
  RobotStatus robot_status;   // 机器人状态
  GameStatus game_status;     // 比赛信息
  SentryInfo sentry_info;     // 哨兵决策信息
  RFID rfid;                  // RFID模块状态(32位位图)
  uint16_t bullet_17_remain;  // 17mm弹丸允许发弹量
  uint16_t our_outpose;       // 己方前哨站血量
  uint16_t red_base;          // 己方基地血量
};
```

**代码位置**: `ros2libxr.cpp:176-269`

---

### ROS2 → 下位机 (发送方向)

#### 1. 底盘运动指令

**ROS2话题**: `/cmd_vel`  
**消息类型**: `geometry_msgs/Twist`  
**LibXR话题**: `chassis_data`  
**数据类型**: `move_vec{vx, vy, wz}`

**坐标变换**:
```cpp
// ros2libxr.cpp:294-297
move_.vx = -twi->linear.y;   // ROS y轴 → 底盘x轴 (取反)
move_.vy = twi->linear.x;    // ROS x轴 → 底盘y轴
move_.wz = twi->angular.z;   // 旋转速度不变
```

**为什么需要坐标变换？**
- ROS标准: x前, y左, z上 (右手坐标系)
- 底盘定义: x左, y前, z上
- 因此需要交换并取反

**代码位置**: `ros2libxr.cpp:294-302`

---

#### 2. 哨兵姿态切换

**ROS2话题**: `/referee/set_pose`  
**消息类型**: `referee_interfaces/SetPose`  
**LibXR话题**: `sentry_state`  
**数据类型**: `uint8_t`

**姿态编码**:
- `0` - 进攻模式
- `1` - 防御模式
- `2` - 移动模式

**代码位置**: `ros2libxr.cpp:106-112`

---

## 🚀 使用方法

### 启动串口通信节点

```bash
# 方式一: 使用launch文件 (推荐)
ros2 launch ros2_libxr ros2_libxr_launch.py

# 方式二: 直接运行节点
ros2 run ros2_libxr ros2_libxr_node
```

### 测试底盘运动

```bash
# 前进 (ROS x轴正向 = 底盘y轴正向)
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" \
  --once

# 左平移 (ROS y轴正向 = 底盘x轴负向)
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.5, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" \
  --once

# 原地旋转
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.3}}" \
  --once

# 停止
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" \
  --once
```

### 监控接收数据

```bash
# 查看云台姿态
ros2 topic echo /serial/gimbal_joint_state

# 查看机器人状态
ros2 topic echo /referee/robot_status

# 查看比赛状态
ros2 topic echo /referee/game_status

# 查看RFID增益点
ros2 topic echo /referee/rfid_status

# 查看前哨站血量
ros2 topic echo /our_outpost_hp
```

### 切换哨兵姿态

```bash
# 切换到进攻模式
ros2 topic pub /referee/set_pose referee_interfaces/msg/SetPose "{pose: 0}" --once

# 切换到防御模式
ros2 topic pub /referee/set_pose referee_interfaces/msg/SetPose "{pose: 1}" --once

# 切换到移动模式
ros2 topic pub /referee/set_pose referee_interfaces/msg/SetPose "{pose: 2}" --once
```

---

## 🔍 调试指南

### 1. 检查串口连接

```bash
# 查看USB设备
lsusb | grep -i "16d0:1492"

# 查看串口设备
ls -l /dev/ttyUSB* /dev/ttyACM*

# 查看串口权限
groups | grep dialout
# 如果当前用户不在dialout组，需要添加:
# sudo usermod -a -G dialout $USER
# (需要重新登录生效)
```

### 2. 查看节点日志

```bash
# 启动时查看详细日志
ros2 run ros2_libxr ros2_libxr_node --ros-args --log-level debug

# 查看节点信息
ros2 node info /rm_serial_driver

# 查看节点话题
ros2 node list
ros2 topic list | grep -E "cmd_vel|serial|referee"
```

### 3. 检查数据流

```bash
# 查看话题发布频率
ros2 topic hz /serial/gimbal_joint_state
ros2 topic hz /referee/robot_status

# 查看话题延迟
ros2 topic delay /cmd_vel

# 查看话题带宽
ros2 topic bw /cmd_vel
```

### 4. LibXR终端调试

ros2_libxr内置了LibXR终端线程，可以在运行时查看通信状态。

**启动后可用的命令**:
```
shared_topic:uart_client monitor   # 查看接收带宽(Mbps)
```

### 5. 常用调试技巧

**问题**: 节点启动但没有数据
```bash
# 1. 检查串口是否打开
ros2 run ros2_libxr ros2_libxr_node 2>&1 | grep -i "uart"

# 2. 检查下位机是否发送数据
# 使用串口调试工具(minicom/screen)查看原始数据

# 3. 检查LibXR话题注册
ros2 run ros2_libxr ros2_libxr_node 2>&1 | grep -i "topic"
```

**问题**: 发送数据但下位机无响应
```bash
# 1. 检查cmd_vel是否发布
ros2 topic echo /cmd_vel

# 2. 在代码中查看调试输出
# ros2libxr.cpp:298-300 有打印:
# "Received cmd_vel: vx=..., vy=..., wz=..."

# 3. 检查坐标变换是否正确
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 1.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
# 应该输出: vx=0.0, vy=1.0, wz=0.0
```

---

## ❓ 常见问题

### Q1: 编译时出现 "wpa_client not found" 警告

**原因**: LibXR的WiFi功能需要wpa_client库，但串口通信不需要

**解决**: 忽略该警告，不影响串口功能。如需消除警告:
```bash
sudo apt install libwpa-client-dev libnm-dev
```

---

### Q2: 节点启动失败 "Permission denied"

**原因**: 当前用户没有串口访问权限

**解决**:
```bash
sudo usermod -a -G dialout $USER
# 重新登录或重启
```

**临时解决** (不推荐):
```bash
sudo chmod 666 /dev/ttyUSB0  # 或对应的串口设备
```

---

### Q3: 找不到串口设备 "No such device"

**检查步骤**:
1. 确认USB线已连接
2. 查看设备是否被识别: `lsusb`
3. 查看内核日志: `dmesg | tail -20`
4. 检查VID/PID是否正确

**可能原因**:
- USB线损坏或接触不良
- 下位机未上电
- VID/PID配置错误
- 驱动未加载 (CDC-ACM)

---

### Q4: 接收数据但格式错误

**可能原因**:
1. **下位机与上位机数据结构不匹配**
   - 检查结构体定义 (ros2libxr.hpp)
   - 确认字节对齐 `[[gnu::packed]]`

2. **字节序问题**
   - LibXR默认使用小端序
   - 确认下位机也使用小端序

3. **CRC校验失败**
   - LibXR自动处理CRC
   - 检查下位机CRC实现

---

### Q5: 发送数据无响应

**调试步骤**:
1. 确认ROS2话题有数据: `ros2 topic echo /cmd_vel`
2. 确认回调函数被调用 (查看日志)
3. 确认下位机话题名一致
4. 使用示波器/逻辑分析仪查看TX线

---

### Q6: 坐标变换结果不符合预期

**测试矩阵**:

| ROS cmd_vel | 期望底盘运动 | move_vec实际值 |
|------------|------------|---------------|
| linear.x=1.0 | 前进 | vx=0, vy=1.0 |
| linear.y=1.0 | 左平移 | vx=-1.0, vy=0 |
| angular.z=1.0 | 逆时针旋转 | wz=1.0 |

**如需调整坐标变换**:
修改 `ros2libxr.cpp:294-297`

---

## 📚 参考资料

### 相关文件

- [readme.md](/home/xuny/nav_self/ros2_libxr/readme.md) - 项目README
- [ros2libxr.hpp](/home/xuny/nav_self/ros2_libxr/src/ros2_libxr/include/ros2_libxr/ros2libxr.hpp) - 类定义
- [ros2libxr.cpp](/home/xuny/nav_self/ros2_libxr/src/ros2_libxr/src/ros2libxr.cpp) - 实现代码
- [CMakeLists.txt](/home/xuny/nav_self/ros2_libxr/src/ros2_libxr/CMakeLists.txt) - 构建配置

### LibXR库

- [LibXR GitHub](https://github.com/Jiu-xiao/libxr)
- [LibXR README](/home/xuny/nav_self/ros2_libxr/src/ros2_libxr/libxr/README.md)
- [LibXR 中文文档](/home/xuny/nav_self/ros2_libxr/src/ros2_libxr/libxr/README.zh-CN.md)

### ROS 2文档

- [ROS 2 Serial通信](https://docs.ros.org/en/humble/Tutorials.html)
- [geometry_msgs/Twist](https://docs.ros2.org/foxy/api/geometry_msgs/msg/Twist.html)
- [sensor_msgs/JointState](https://docs.ros2.org/foxy/api/sensor_msgs/msg/JointState.html)

---

**文档维护**: 请在串口通信相关修改后更新此文档  
**联系**: SMBU PolarBear Robotics Team  
**最后检查**: 2026-09-22
