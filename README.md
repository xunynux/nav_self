# 让小车自主实现从A到B的导航
## 本代码是基于北极熊导航开源以及未来的libxr串口开源而生产

### 引言
记录这惨痛的一天，公历九月二十三日，农历八月十三，秋分。
以前我是不咋会用git管理，对这东西一直敬而远之，但是今日改变了我的想法......
事情的开端源于一次轮腿的打火花，然而并没有结束，接踵而来的就是导航小车的nuc似了，无法开机（悲），接着就是导航小车的电控把代码误删
这是我下定决心用git的决定因素（哀悼..)

### 代码结构

```
nav_self/
├── ros2_libxr/                  # 串口桥（含 libxr / SharedTopic 子模块）
│   └── src/{ros2_libxr, referee_interfaces, auto_aim_interfaces}
└── nav_ws/                      # colcon 工作区
    └── src/
        ├── ros2_libxr           -> ../../ros2_libxr/src/ros2_libxr          # 三个符号链接
        ├── referee_interfaces   -> ../../ros2_libxr/src/referee_interfaces
        ├── auto_aim_interfaces  -> ../../ros2_libxr/src/auto_aim_interfaces
        ├── mysystem/            # 本车 URDF + mesh
        └── pb2025_sentry_nav/   # 北极熊导航栈
            ├── 01_livox_ros_driver2       雷达驱动
            ├── 02_point_lio               激光惯性里程计
            ├── 03_loam_interface          雷达位姿 → 底盘位姿
            ├── 04_sensor_scan_generation  发 odom→base_footprint TF、/sensor_scan
            ├── 05_pointcloud_to_laserscan 3D 点云 → 2D /obstacle_scan
            ├── 06_small_gicp_relocalization 先验 PCD + ICP，发 map→odom
            ├── 07_pb_omni_pid_pursuit_controller 全向路径跟踪（Nav2 插件）
            ├── 08_pb2025_robot_description  空目录，实际 URDF 用 mysystem
            └── 09_pb2025_nav_bringup      launch / 参数 / 地图 / PCD / rviz
```

数据链：`Livox → point_lio → loam_interface → sensor_scan_generation → pointcloud_to_laserscan → Nav2 → /cmd_vel → ros2_libxr → 下位机`

## 编译
```
cd ~/nav_self/nav_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release -DROS_EDITION=ROS2 -DDISTRO_ROS=jazzy
```

## 启动流程
1. 赋予nuc权限
   ```
   sudo chmod 777 /dev/ttyACM0
   ```
2. 启动串口
   ```
   cd ~/nav_self/nav_ws
   source install/setup.bash
   ros2 launch ros2_libxr ros2_libxr_launch.py
   ```
3. 开启终端2，启动键盘操控验证是否通信
   ```
   ros2 topic pub --once /move_mode std_msgs/msg/Int32 "{data: 1}"
   ros2 run teleop_twist_keyboard teleop_twist_keyboard 
   ```
4. 可选，启动建图
   ```
   cd ~/nav_self/nav_ws
   source install/setup.bash
   ros2 launch pb2025_nav_bringup slam_launch.py \
   use_sim_time:=False

   ```

5. 开启终端3，启动导航
   ```
   cd ~/nav_self/nav_ws && source install/setup.bash && \
   ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py \
   world:=rmul_2024 use_sim_time:=False slam:=False use_composition:=False
   ```
### 吃屎日记

**9.21** 任务发布：让导航小车自主从A点到B点。代码分别从北极熊和hyx仓库中调取，组成代码的基础框架，hyx提供和电控通信的ros2_libxr串口，360驱动调用暑假时本人实验成功的驱动包，其余功能包从暑假跑通的北极熊导航上调取。

**9.22** 基于dmx的实车调试对ros2_libxr进行修改，加入move_mode，同时整理昨天拉取的包，更改路径相关之类的，删去没有用上的链接多的功能包之类的，精简代码。

**9.23** 记录这惨痛的一天（悲），公历2026年9月23日，农历八月十三，秋分，事情起源于一次轮腿的打火花，紧接着就是导航小车的nuc突然似了后续查询是静电原因（似乎有些触动）（请将这一天载入队史，深刻建议这天实验室放假别调车了），在之后就是哨兵电控误删代码，一系列事情的促使下，第一次正式使用git管理代码，项目本身进度几乎为零

**9.24** 由于nuc送去维修，导航小车在另外的人手里，我借用dmx之前用360扫出的地图，我试图先在gazebo和rviz上进行仿真实验代码，然后ai给我跑的gazebo是一坨大便，启动时无法显示出图像，一片空白，导致rviz的TF显示出现报错，TF找不到了，在之后就是vscode突然似了，打开没一会就报错，遂放弃，梯子似乎也出现问题，导致ai也无法启用

**9.25** 基于昨天的网络问题，让ai冷静一天后发现本人的clash verge无法处在美国IP会导致网络直接链接超时，遂放弃选用只在美国免费的opencode的API，换用MiMo-V2.6-Flash，并放弃了用gazebo进行仿真，选择试图仅rviz显示机器人描述功能包和建好的地图，反复修改一直出现TF问题，因为是robot_joint之类的话题没有发布，好不容易折腾好后续又发现机器人model无法显示，只能看见各关节的坐标轴，折腾了几个小时发现是因为我导入的地图是2D的，导致rviz默认2D无法显示机器人model（吃到了💩），这个时候我的代码已经被改到面目全非了，我想着之前提交了较为完整代码到github上，索性直接把家目录下的源码删干净打算从github上重新拉，结果发现我对ros2_libxr功能包的修改全都不见了，怒而关电脑

**9.26** 为解决昨天的问题，我试图回溯之前删去的源码，我记得出第一次提交外后续我还有一次提交，但是死活找不到之前的提交，无法找回我对ros2_libxr的修改，后续才发现是因为ros2_libxr是由于我直接从hyx仓库上fork的代码，导致该功能包被git识别为gitlink，我在vscode上直接提交的无法作用在ros2_libxr上，不得不从vscode的保存记录上找回，万幸还在，再次处理之前删代码残留的问题后，开始上实车测试，完成了串口，雷达调用，安静状态下调用里程计

**9.27**开始正式测试导航功能，发现局部代价地图和先验地图没有对上，两者成四十五度，后续改用foxglove进行调试局部代价地图同先验地图，偶然发现会出现成垂直状态，后面阅读北极熊实车部署指南发现是因为机器人描述文件中雷达的固定连接名同point_lio不一样，point_lio没有被调用，调整过来后TF掉了（有💩），后续没找出具体问题粗暴的将所有命名改为aft_mapped（暂未出现问题），改正过后启动导航发现四十五度问题还是存在，经过排查后发现先验地图多转了四十五度（神来了也绷不住），源于我的先验地图直接照搬的dmx但是我打代码比dmx多一个从雷达转到base_link的功能包导致先验地图被多转了，事实证明即使是同一辆车同一个调车处也不建议跳过建图（哽咽），调试时由于小车轮子突然疯了暂时搁置

**9.28** 经过休整，开始正式启动导航，初次尝试成功，但后续复现时小车却疯了（这很神秘），重新启动时发现小车的局部代价地图识别前方为障碍物，但前方是空旷区域（有鬼），尝试将膨胀半径调低有所缓解但还是识别为障碍物，将小车架起来后发现识别为空，初步判定是将地面识别为了障碍物（哽咽），因为 min_obstacle_height = 0.0，这个参数为高度过滤阈值，于是部分地板在局部代价地图中 z > 0，被认为是障碍物，进而导致重定位失效。局部代价地图中这个参数相对于 odom，全局代价地图中相对于 map，同时 map 与 odom 也有高度差，所以两个参数不能一致。odom到map的变换由ICP提供，即 06_small_gicp_relocalization 这个包，所以每次局部代价地图更新，这个变换会随着局部代价地图更新而更新。所以全局代价地图的高度基准不会一直不变。base_link和base_footprint处于同一地方（这不对，再也不偷懒了），导致map和odom转到base_link太低了（悲）。解决后，出现新问题在foxglove上发目标点小车并不动，但检查了不是串口问题发现是因为因为foxglove的默认的话题为 /move_base_simple/goal，而实际上的话题名为 /goal_pose，修正后小车终于实现A到B的自主导航
