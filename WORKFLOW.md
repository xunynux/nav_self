# 哨兵机器人导航系统完整工作流程

## 系统架构总览

```
串口通信层 (ros2_libxr) 
    ↓ 订阅 /cmd_vel，发布底盘数据
LiDAR + IMU (Livox Driver)
    ↓ 发布点云 /livox/lidar 和 IMU /livox/imu
Point-LIO (激光-惯性里程计)
    ↓ 发布 LiDAR 在房间中的位姿 lidar_odom
loam_interface (坐标转换)
    ↓ 转换为底盘在房间中的位姿 odom
Nav2 导航栈
    ↓ 发布速度指令 /cmd_vel
```

---

## 第一步：验证串口通信

### 1.1 检查串口设备
```bash
# 查看USB设备（查找VID=16d0, PID=1492）
lsusb

# 查看串口权限
ls -l /dev/ttyACM* /dev/ttyUSB*

# 添加当前用户到dialout组（首次使用需要）
sudo usermod -aG dialout $USER
# 注销后重新登录生效

# 或临时授权
sudo chmod 666 /dev/ttyACM0  # 根据实际设备修改
```

### 1.2 编译并启动串口节点
```bash
cd ~/nav_self/nav_ws

# 编译ros2_libxr包
colcon build --packages-select ros2_libxr --symlink-install

# source环境
source install/setup.bash

# 启动串口桥接节点
ros2 launch ros2_libxr ros2_libxr_launch.py
```

**预期输出：**
```
[INFO] [rm_serial_driver]: LibXR UART initialized
[INFO] [rm_serial_driver]: Serial port opened: 16d0:1492
```

### 1.3 验证串口通信

**方法1：发布测试速度指令**
```bash
# 新终端1：监听串口节点输出
ros2 topic echo /cmd_vel

# 新终端2：发布速度指令（让小车前进0.3m/s）
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

**预期结果：**
- 串口节点终端显示：`Received cmd_vel: vx=0.000000, vy=0.300000, wz=0.000000`
- 实体小车应该向前移动（如果下位机正常）

**方法2：检查裁判系统数据上传**
```bash
# 查看可用话题
ros2 topic list | grep referee

# 监听裁判系统数据（需要下位机连接裁判系统）
ros2 topic echo /referee/robot_status
ros2 topic echo /referee/game_status
```

---

## 第二步：启动LiDAR和里程计

### 2.1 配置LiDAR网络（首次使用）

编辑 LiDAR 配置：
```bash
nano ~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/config/reality/mid360_user_config.json
```

确认LiDAR IP配置：
```json
{
  "lidar_configs": [
    {
      "ip": "192.168.1.100",
      "pcl_data_type": 1,
      "pattern_mode": 0
    }
  ],
  "host_net_info": {
    "host_ip": "192.168.1.50",
    "lidar_subnet_mask": "255.255.255.0"
  }
}
```

### 2.2 测试LiDAR单独运行
```bash
cd ~/nav_self/nav_ws
source install/setup.bash

# 启动LiDAR驱动
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

**验证LiDAR数据：**
```bash
# 新终端：检查点云话题
ros2 topic hz /livox/lidar  # 应该显示 ~10Hz
ros2 topic echo /livox/lidar --no-arr  # 查看点云数据（不显示数组）

# 检查IMU话题
ros2 topic hz /livox/imu  # 应该显示 ~200Hz
```

### 2.3 启动Point-LIO里程计
```bash
# 编译Point-LIO
cd ~/nav_self/nav_ws
colcon build --packages-select point_lio --symlink-install
source install/setup.bash

# 启动Point-LIO（会自动订阅 /livox/lidar 和 /livox/imu）
ros2 run point_lio pointlio_mapping \
  --ros-args --params-file \
  ~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/config/reality/nav2_params.yaml
```

**验证里程计输出：**
```bash
# 检查Point-LIO发布的位姿
ros2 topic echo /aft_mapped_to_init  # LiDAR位姿（lidar_odom坐标系）

# 检查点云配准结果
ros2 topic hz /cloud_registered  # 配准后的点云
```

---

## 第三步：建图（SLAM模式）

### 3.1 启动完整SLAM系统
```bash
cd ~/nav_self/nav_ws
source install/setup.bash

# 启动建图launch（包含：LiDAR驱动 + Point-LIO + SLAM Toolbox + Map Saver）
ros2 launch pb2025_nav_bringup slam_launch.py \
  use_sim_time:=False
```

**此命令会启动：**
1. `map_saver_server` - 地图保存服务
2. `slam_toolbox` - 2D地图构建
3. `point_lio` - 点云建图（会保存PCD文件）
4. `static_transform_publisher` - 发布 map → odom 的静态变换

### 3.2 用遥控器驱动小车建图

**方法A：使用键盘控制（测试用）**
```bash
# 新终端：安装并启动键盘控制
sudo apt install ros-jazzy-teleop-twist-keyboard
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args --remap /cmd_vel:=/cmd_vel
```

**方法B：使用实体遥控器**
- 连接RC遥控器到接收机
- 下位机会通过串口将遥控器指令转换为底盘速度
- 此时小车由遥控器控制，ROS系统只负责记录数据

### 3.3 启动RViz2可视化
```bash
# 新终端
cd ~/nav_self/nav_ws
source install/setup.bash

ros2 launch pb2025_nav_bringup rviz_launch.py \
  rviz_config:=~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/rviz/nav2_default_view.rviz
```

**在RViz2中检查：**
- **TF树**：确认 `map → odom → base_footprint → base_link → livox_frame` 完整
- **PointCloud2** (`/cloud_registered`)：显示白色点云
- **Map** (`/map`)：显示2D占据栅格地图（黑色=障碍，白色=自由）
- **Path**：显示机器人轨迹

### 3.4 遥控小车完成建图

1. **遥控小车走完整个场地**
   - 覆盖所有需要导航的区域
   - 尽量让小车匀速移动，避免急转急停
   - 确保LiDAR能看到场地边界和障碍物

2. **监控建图质量**
   ```bash
   # 查看Point-LIO状态
   ros2 topic echo /Odometry  # 检查位姿是否稳定
   
   # 查看SLAM Toolbox地图更新
   ros2 topic hz /map  # 应该持续更新
   ```

### 3.5 保存地图

## ⚠️ 重要说明：点云地图是叠加保存的！

**Point-LIO的建图机制：**
- ✅ **逐帧累积**：每一帧LiDAR扫描都会叠加到全局点云地图中
- ✅ **实时对齐**：Point-LIO自动估计位姿，确保新帧与已有地图对齐
- ✅ **全局坐标系**：所有点云统一在`camera_init`坐标系下
- ⚠️ **不是单次快照**：最终的PCD文件包含整个建图过程中所有扫描的点

**建图质量建议：**
1. 遥控小车**匀速移动**，避免急转急停（减少运动畸变）
2. **完整覆盖**场地所有区域（漏扫的地方不会出现在地图中）
3. **重复扫描**关键区域可以增加点云密度
4. 建图时间越长，累积的点云越多，文件越大

---

**方法1：使用ROS2服务保存2D地图**
```bash
# 保存为地图文件（.pgm + .yaml）
ros2 run nav2_map_server map_saver_cli -f ~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/map/reality/my_map
```

**生成的文件：**
- `my_map.yaml` - 地图元数据（分辨率、原点）
- `my_map.pgm` - 栅格地图图像

**方法2：Point-LIO自动保存PCD点云地图（叠加累积）**

**重要：Point-LIO保存的PCD是所有帧的叠加点云，不是单次快照！**

在建图前配置：
```bash
# 编辑Point-LIO配置文件
nano ~/nav_self/nav_ws/src/pb2025_sentry_nav/02_point_lio/config/mid360.yaml

# 修改pcd_save部分：
pcd_save:
    pcd_save_en: True               # 启用PCD保存
    interval: -1                    # -1=退出时一次性保存所有帧
                                    # >0=每N帧保存一次（避免内存溢出）
```

**保存行为：**
- **interval: -1** → 累积所有帧，按Ctrl+C退出时保存为 `~/nav_self/nav_ws/PCD/scans.pcd`
- **interval: 100** → 每100帧自动保存为 `scans_1.pcd`, `scans_2.pcd`, ...（适合长时间建图）

**建图过程：**
1. Point-LIO实时估计机器人位姿
2. 将每一帧点云转换到全局坐标系（`camera_init`）
3. 逐帧叠加到内存缓存 `pcl_wait_save`
4. 退出时（或达到interval）写入PCD文件

**优点：**
- 完整的3D稠密地图（包含所有扫描过的点）
- 自动对齐（Point-LIO的位姿估计已校正）
- 可用于后续的重定位和精细地图处理

**检查保存的文件：**
```bash
# 查看保存的2D地图
ls -lh ~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/map/reality/

# 查看Point-LIO保存的PCD
ls -lh ~/nav_self/nav_ws/PCD/
```

---

## 第四步：地图处理

### 4.1 检查2D地图质量
```bash
# 用图片查看器打开
eog ~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/map/reality/my_map.pgm
```

**地图质量标准：**
- 白色（自由空间）= 可通行区域
- 黑色（障碍）= 墙壁、柱子
- 灰色（未知）= LiDAR未扫描到的区域
- 边界清晰，没有大量噪点

### 4.2 编辑地图（可选）
如果地图有噪点或需要手动标注禁行区，使用GIMP：
```bash
sudo apt install gimp
gimp ~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/map/reality/my_map.pgm
```

**编辑技巧：**
- 用**黑色画笔**填充障碍物
- 用**白色画笔**清除噪点
- 保存为 `.pgm` 格式（灰度图）

### 4.3 移动地图到标准位置
```bash
# 将地图文件复制到导航配置目录
cp ~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/map/reality/my_map.* \
   ~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/map/reality/rmul_2024.yaml
cp ~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/map/reality/my_map.pgm \
   ~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/map/reality/rmul_2024.pgm

# 编辑YAML文件，修改image字段
nano ~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/map/reality/rmul_2024.yaml
```

确保 `image: rmul_2024.pgm`

### 4.4 处理PCD点云地图（用于重定位）
```bash
# 复制PCD到导航配置目录
cp ~/nav_self/nav_ws/PCD/scans.pcd \
   ~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/pcd/reality/rmul_2024.pcd
```

---

## 第五步：启动导航系统

### 5.1 关闭SLAM系统
```bash
# 在之前运行slam_launch.py的终端按 Ctrl+C
# 确保所有SLAM相关节点已停止
```

### 5.2 启动完整导航系统
```bash
cd ~/nav_self/nav_ws
source install/setup.bash

# 启动导航launch（会加载地图和PCD先验）
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py \
  world:=rmul_2024 \
  use_sim_time:=False \
  slam:=False
```

**此命令会启动：**
1. **robot_state_publisher** - 发布机器人URDF模型
2. **livox_ros_driver2** - LiDAR驱动
3. **point_lio** - 里程计（加载先验PCD地图）
4. **small_gicp_relocalization** - 全局重定位
5. **loam_interface** - LiDAR → 底盘坐标转换
6. **sensor_scan_generation** - 传感器TF发布
7. **pointcloud_to_laserscan** - 3D→2D转换
8. **map_server** - 提供2D地图
9. **nav2全栈** - 规划器、控制器、行为树
10. **rviz2** - 可视化

### 5.3 设置初始位姿（重要！）

在RViz2中：
1. 点击工具栏 **"2D Pose Estimate"**
2. 在地图上点击机器人的**实际位置**
3. 拖动箭头设置**朝向**

**或使用命令行：**
```bash
ros2 topic pub --once /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
  "{header: {frame_id: 'map'}, 
    pose: {pose: {position: {x: 1.0, y: 2.0, z: 0.0}, 
                   orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}}}"
```

**验证重定位成功：**
- 点云与地图应该对齐
- `/map` → `/odom` 的TF变换应该稳定

### 5.4 发布导航目标

**方法1：RViz2可视化设置**
1. 点击 **"2D Nav Goal"** 工具
2. 在地图上点击**目标位置**
3. 拖动箭头设置**目标朝向**

**方法2：命令行发布目标**
```bash
# 发送目标点 (x=3.0, y=4.0)
ros2 topic pub --once /goal_pose geometry_msgs/msg/PoseStamped \
  "{header: {frame_id: 'map'}, 
    pose: {position: {x: 3.0, y: 4.0, z: 0.0}, 
           orientation: {x: 0.0, y: 0.0, z: 0.707, w: 0.707}}}"
```

**方法3：使用Nav2 Action（推荐）**
```bash
# 安装Nav2工具
sudo apt install ros-jazzy-nav2-simple-commander

# Python脚本发送导航目标
python3 << 'EOF'
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator

rclpy.init()
navigator = BasicNavigator()

# 设置目标点A
goal_pose_A = PoseStamped()
goal_pose_A.header.frame_id = 'map'
goal_pose_A.header.stamp = navigator.get_clock().now().to_msg()
goal_pose_A.pose.position.x = 3.0
goal_pose_A.pose.position.y = 4.0
goal_pose_A.pose.orientation.w = 1.0

# 发送目标
navigator.goToPose(goal_pose_A)

# 等待完成
while not navigator.isTaskComplete():
    feedback = navigator.getFeedback()
    print(f"Distance remaining: {feedback.distance_remaining:.2f}m")

result = navigator.getResult()
if result == TaskResult.SUCCEEDED:
    print('Goal succeeded!')
else:
    print('Goal failed!')

navigator.lifecycleShutdown()
rclpy.shutdown()
EOF
```

---

## 第六步：多点导航任务

### 6.1 定义巡航路径点
```bash
# 创建导航脚本
nano ~/nav_self/multi_goal_nav.py
```

```python
#!/usr/bin/env python3
import rclpy
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from geometry_msgs.msg import PoseStamped

def create_pose(x, y, yaw_deg):
    """创建目标位姿"""
    import math
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.position.z = 0.0
    
    # 将角度转换为四元数
    yaw_rad = math.radians(yaw_deg)
    pose.pose.orientation.z = math.sin(yaw_rad / 2.0)
    pose.pose.orientation.w = math.cos(yaw_rad / 2.0)
    return pose

def main():
    rclpy.init()
    navigator = BasicNavigator()
    
    # 定义巡航点（示例：矩形路径）
    waypoints = [
        create_pose(2.0, 1.0, 0),     # A点：x=2m, y=1m, 朝向东
        create_pose(2.0, 4.0, 90),    # B点：x=2m, y=4m, 朝向北
        create_pose(5.0, 4.0, 180),   # C点：x=5m, y=4m, 朝向西
        create_pose(5.0, 1.0, 270),   # D点：x=5m, y=1m, 朝向南
        create_pose(2.0, 1.0, 0),     # 返回A点
    ]
    
    print(f"开始执行 {len(waypoints)} 点巡航任务...")
    
    for i, goal in enumerate(waypoints):
        goal.header.stamp = navigator.get_clock().now().to_msg()
        print(f"\n正在前往第 {i+1} 个点: ({goal.pose.position.x}, {goal.pose.position.y})")
        
        navigator.goToPose(goal)
        
        while not navigator.isTaskComplete():
            feedback = navigator.getFeedback()
            if feedback:
                print(f"  剩余距离: {feedback.distance_remaining:.2f}m", end='\r')
        
        result = navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            print(f"\n✓ 第 {i+1} 个点到达成功")
        else:
            print(f"\n✗ 第 {i+1} 个点失败，跳过")
    
    print("\n巡航任务完成！")
    navigator.lifecycleShutdown()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

运行多点导航：
```bash
chmod +x ~/nav_self/multi_goal_nav.py
python3 ~/nav_self/multi_goal_nav.py
```

---

## 常见问题排查

### 问题1：串口无法打开
```bash
# 检查设备是否存在
ls -l /dev/ttyACM* /dev/ttyUSB*

# 检查权限
groups | grep dialout  # 应该包含dialout

# 检查USB连接
dmesg | tail -20
```

### 问题2：LiDAR无数据
```bash
# 检查网络连接
ping 192.168.1.100  # Ping LiDAR IP

# 检查话题
ros2 topic list | grep livox
ros2 topic hz /livox/lidar
```

### 问题3：TF树断裂
```bash
# 查看TF树
ros2 run tf2_tools view_frames
evince frames.pdf

# 检查缺失的变换
ros2 run tf2_ros tf2_echo map odom
ros2 run tf2_ros tf2_echo odom base_footprint
```

### 问题4：导航不规划路径
```bash
# 检查代价地图
ros2 topic echo /local_costmap/costmap --no-arr
ros2 topic echo /global_costmap/costmap --no-arr

# 检查规划器状态
ros2 node info /planner_server
ros2 node info /controller_server
```

### 问题5：小车不动
```bash
# 检查速度指令是否发布
ros2 topic echo /cmd_vel

# 检查串口节点是否收到
# 应该在串口终端看到："Received cmd_vel: vx=..."

# 手动发送测试指令
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.1, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

---

## 快速启动脚本

### 创建启动脚本
```bash
nano ~/nav_self/start_navigation.sh
```

```bash
#!/bin/bash
cd ~/nav_self/nav_ws
source install/setup.bash

# 启动串口通信
gnome-terminal -- bash -c "ros2 launch ros2_libxr ros2_libxr_launch.py; exec bash" &
sleep 2

# 启动导航系统
gnome-terminal -- bash -c "ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py world:=rmul_2024 use_sim_time:=False slam:=False; exec bash" &

echo "导航系统启动完成！"
echo "请在RViz2中设置初始位姿(2D Pose Estimate)，然后发布目标点(2D Nav Goal)"
```

```bash
chmod +x ~/nav_self/start_navigation.sh
~/nav_self/start_navigation.sh
```

---

## 总结

**完整流程：**
1. ✅ 验证串口通信 → 测试 `/cmd_vel` 发布
2. ✅ 启动LiDAR + Point-LIO → 验证点云和里程计
3. ✅ 遥控器建图 → 保存 `.pgm` 和 `.pcd` 文件
4. ✅ 处理地图 → 放入 `map/reality/` 和 `pcd/reality/`
5. ✅ 启动导航 → 设置初始位姿
6. ✅ 发布目标点 → 小车自主导航

**关键文件位置：**
- 地图：`~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/map/reality/rmul_2024.yaml`
- PCD：`~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/pcd/reality/rmul_2024.pcd`
- 配置：`~/nav_self/nav_ws/src/pb2025_sentry_nav/09_pb2025_nav_bringup/config/reality/nav2_params.yaml`
