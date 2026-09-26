import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterValue


def generate_launch_description():
    mysystem_share_dir = get_package_share_directory("mysystem")
    urdf_path = os.path.join(mysystem_share_dir, "urdf", "robot.urdf")
    with open(urdf_path, "r") as f:
        robot_description = f.read()

    use_rviz = LaunchConfiguration("use_rviz")

    declare_use_rviz_cmd = DeclareLaunchArgument(
        "use_rviz",
        default_value="True",
        description="Whether to start RViz2 to visualize the robot model",
    )

    robot_state_publisher_cmd = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": ParameterValue(robot_description, value_type=str)}],
    )

    rviz_cmd = Node(
        condition=IfCondition(use_rviz),
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
    )

    ld = LaunchDescription()

    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(robot_state_publisher_cmd)
    ld.add_action(rviz_cmd)

    return ld
