# 快速参考卡片

**项目**: SMBU PolarBear 哨兵机器人导航系统  
**用途**: 常用命令和操作速查  

---

## 🚀 快速启动

### 1. 编译工作空间

```bash
cd /home/xuny/nav_self/nav_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

### 2. 启动导航系统（完整版）

```bash
# 终端1: 启动导航栈
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py

# 终端2: 启动串口通信
ros2 launch ros2_libxr ros2_libxr_launch.py

# 终端3: 启动RViz2可视化
ros2 launch pb2025_nav_bringup rviz_launch.py
```

### 3. 测试机器人模型显示

```bash
ros2 launch mysystem display.launch.py
```

---

## 🔍 调试命令

### TF变换检查

```bash
# 查看TF树
ros2 run tf2_tools view_frames
evince frames.pdf

# 查看特定变换
ros2 run tf2_ros tf2_echo map odom
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link lidar_frame

# 实时监控TF
ros2 topic echo /tf --no-arr
ros2 topic echo /tf_static --no-arr
```

### 话题监控

```bash
# 查看所有话题
ros2 topic list

# 导航相关话题
ros2 topic echo /cmd_vel                    # 速度指令
ros2 topic echo /odom                       # 里程计
ros2 topic echo /scan                       # 2D激光扫描
ros2 topic echo /livox/lidar                # 3D点云

# 裁判系统话题
ros2 topic echo /referee/robot_status       # 机器人状态
ros2 topic echo /referee/game_status        # 比赛状态
ros2 topic echo /referee/rfid_status        # RFID增益点
ros2 topic echo /our_outpost_hp             # 前哨站血量

# 云台话题
ros2 topic echo /serial/gimbal_joint_state  # 云台关节状态

# 查看话题频率
ros2 topic hz /cmd_vel
ros2 topic hz /odom
ros2 topic hz /scan
```

### 节点检查

```bash
# 查看所有节点
ros2 node list

# 查看节点详情
ros2 node info /robot_state_publisher
ros2 node info /rm_serial_driver
ros2 node info /point_lio
ros2 node info /controller_server

# 查看参数
ros2 param list /controller_server
ros2 param get /controller_server plugin_names
```

### 串口调试

```bash
# 查看USB设备
lsusb | grep -i "16d0:1492"

# 查看串口设备
ls -l /dev/ttyUSB* /dev/ttyACM*

# 检查串口权限
groups | grep dialout

# 查看内核日志（插拔USB后）
dmesg | tail -20

# 测试串口发送
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.1, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" \
  --once
```

---

## 🎮 运动控制测试

### 手动控制底盘

```bash
# 前进 (ROS +x = 底盘 +y)
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --once

# 后退
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: -0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --once

# 左平移 (ROS +y = 底盘 -x)
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.5, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --once

# 右平移
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: -0.5, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --once

# 逆时针旋转
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.3}}" --once

# 顺时针旋转
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: -0.3}}" --once

# 停止
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --once

# 斜向移动 (前进+左平移)
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.5, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --once
```

### 哨兵姿态切换

```bash
# 进攻模式
ros2 topic pub /referee/set_pose referee_interfaces/msg/SetPose "{pose: 0}" --once

# 防御模式
ros2 topic pub /referee/set_pose referee_interfaces/msg/SetPose "{pose: 1}" --once

# 移动模式
ros2 topic pub /referee/set_pose referee_interfaces/msg/SetPose "{pose: 2}" --once
```

---

## 📊 性能监控

### CPU和内存

```bash
# 查看ROS节点资源占用
top -p $(pgrep -d',' -f ros)

# 查看具体进程
htop

# ROS2进程树
pstree -p | grep -A 10 ros
```

### 话题带宽和频率

```bash
# 带宽统计
ros2 topic bw /livox/lidar
ros2 topic bw /scan

# 频率统计
ros2 topic hz /cmd_vel
ros2 topic hz /odom
ros2 topic hz /referee/robot_status

# 延迟统计
ros2 topic delay /cmd_vel
```

### 系统信息

```bash
# ROS2版本
ros2 --version

# 已安装的包
ros2 pkg list | wc -l

# 工作空间包列表
colcon list

# 环境变量
env | grep ROS
printenv | grep -E "ROS|AMENT"
```

---

## 📝 日志查看

### ROS2日志

```bash
# 查看所有日志
ros2 log list

# 实时日志
ros2 run rqt_console rqt_console

# 命令行日志级别
ros2 run <package> <executable> --ros-args --log-level debug
```

### 系统日志

```bash
# 查看USB设备日志
dmesg | grep -i usb

# 查看串口日志
dmesg | grep -i tty

# 查看内核日志
journalctl -f
```

---

## 🛠️ 常见问题快速修复

### 问题1: TF变换缺失

```bash
# 检查TF发布者
ros2 topic info /tf
ros2 topic info /tf_static

# 验证robot_state_publisher运行
ros2 node list | grep robot_state

# 重启robot_state_publisher
ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$(xacro /path/to/robot.urdf)"
```

### 问题2: 串口无法打开

```bash
# 添加用户到dialout组
sudo usermod -a -G dialout $USER
# 重新登录生效

# 临时授权（不推荐）
sudo chmod 666 /dev/ttyUSB0

# 查看串口占用
lsof | grep ttyUSB
```

### 问题3: 编译失败

```bash
# 清理构建缓存
rm -rf build/ install/ log/

# 安装缺失依赖
rosdep install --from-paths src --ignore-src -r -y

# 单独编译失败的包
colcon build --packages-select <package_name> --event-handlers console_direct+
```

### 问题4: RViz2不显示机器人

```bash
# 检查URDF加载
ros2 param get /robot_state_publisher robot_description

# 检查mesh文件路径
ros2 pkg prefix mysystem
ls $(ros2 pkg prefix mysystem)/share/mysystem/meshes/

# 重新设置Fixed Frame
# RViz2 → Global Options → Fixed Frame → base_footprint
```

---

## 🔧 配置文件位置

| 配置 | 路径 |
|-----|------|
| URDF模型 | `src/mysystem/urdf/robot.urdf` |
| Nav2参数 | `src/09_pb2025_nav_bringup/params/*.yaml` |
| Livox配置 | `src/01_livox_ros_driver2/config/*.json` |
| 串口配置 | `src/ros2_libxr/src/ros2libxr.cpp:57` |
| 启动文件 | `src/09_pb2025_nav_bringup/launch/*.py` |
| 依赖列表 | `../dependencies.repos` |

---

## 📚 文档链接

| 文档 | 路径 |
|-----|------|
| 项目总结 | `/home/xuny/nav_self/PROJECT_SUMMARY.md` |
| 更改日志 | `/home/xuny/nav_self/nav_ws/CHANGELOG.md` |
| ros2_libxr指南 | `/home/xuny/nav_self/nav_ws/ROS2_LIBXR_GUIDE.md` |
| 坐标变换说明 | `/home/xuny/nav_self/1.md` |

---

## 🎯 关键参数速查

### 串口配置

```cpp
// ros2libxr.cpp:57
VID: "16d0"
PID: "1492"
波特率: 115200
数据位: 8
停止位: 1
校验: 无
```

### 坐标变换关系

```
ROS cmd_vel → 底盘 move_vec
linear.x  →  vy  (前进)
linear.y  →  -vx (左平移，取反)
angular.z →  wz  (旋转)
```

### TF树关键帧

```
map          # 全局地图帧（固定）
└─ odom      # 里程计帧（累积误差）
   └─ base_footprint  # 机器人地面投影
      └─ base_link    # 机器人中心
         └─ lidar_frame  # 激光雷达
```

---

## ⚡ 一键命令

### 完整系统启动脚本

创建 `start_navigation.sh`:
```bash
#!/bin/bash
source /home/xuny/nav_self/nav_ws/install/setup.bash

# 终端复用器启动
tmux new-session -d -s nav_system

# 窗口1: 导航栈
tmux send-keys -t nav_system:0 \
  'ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py' C-m

# 窗口2: 串口通信
tmux split-window -v -t nav_system:0
tmux send-keys -t nav_system:0.1 \
  'sleep 3 && ros2 launch ros2_libxr ros2_libxr_launch.py' C-m

# 窗口3: RViz2
tmux split-window -h -t nav_system:0.0
tmux send-keys -t nav_system:0.2 \
  'sleep 5 && ros2 launch pb2025_nav_bringup rviz_launch.py' C-m

# 连接到会话
tmux attach -t nav_system
```

使用:
```bash
chmod +x start_navigation.sh
./start_navigation.sh
```

### 停止所有ROS节点

```bash
# 方法1: 使用pkill
pkill -9 -f ros2

# 方法2: 使用tmux
tmux kill-session -t nav_system

# 方法3: 停止串口节点
ros2 lifecycle set /rm_serial_driver shutdown
```

---

**最后更新**: 2026-09-22  
**维护者**: SMBU PolarBear Robotics Team
