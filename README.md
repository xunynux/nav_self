# 本代码是基于北极熊导航开源以及未来的libxr串口开源而生产出的

记录这惨痛的一天，公历九月二十三日，农历八月十三，秋分。
以前我是不咋会用git管理，对这东西一直敬而远之，但是今日改变了我的想法......
事情的开端源于一次轮腿的打火花，然而并没有结束，接踵而来的就是导航小车的nuc似了，无法开机（悲），接着就是导航小车的电控把代码误删
这是我下定决心用git的决定因素（哀悼..)

## 启动流程
1. 赋予nuc权限
   、、、
   sudo chmod 777 /devttyACM0
   、、、
2. 启动串口
   、、、
   cd nav_self/ros2_libxr
   source install/setup.bash
   ros2 launch ros2_libxr ros2_libxr_launch.py
   、、、
4. 开启终端2，启动键盘操控验证是否通信
   、、、
   ros2 topic pub --once /move_mode std_msgs/msg/Int32 "{data: 1}"
   ros2 run teleop_twist_keyboard teleop_twist_keyboard 
   、、、
5. 开启终端3，启动导航
   、、、
   cd ~/King/nav_self/nav_ws && source install/setup.bash && \
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py \
  world:=rmul_2024 use_sim_time:=False slam:=False use_composition:=False
   、、、
