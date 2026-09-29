cmake_minimum_required(VERSION 3.11)
project(small_gicp_relocalization)

## Use C++14
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

## By adding -Wall and -Werror, the compiler does not ignore warnings anymore,
## enforcing cleaner code.
# add_definitions(-Wall -Werror)

## Export compile commands for clangd
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

#######################
## Find dependencies ##
#######################

find_package(ament_cmake_auto REQUIRED)
find_package(OpenMP REQUIRED)
ament_auto_find_build_dependencies()

# Add small_gicp dependency
# NOTE: FetchContent 需要访问 github.com，本网络 443 端口不通（curl 超时），
#       因此改用 ROS 官方 vendor 包 ros-jazzy-small-gicp-vendor。
#       保留原写法作存档：
# include(FetchContent)
# fetchcontent_declare(
#   small_gicp
#   GIT_REPOSITORY https://github.com/koide3/small_gicp.git
#   GIT_TAG "master"
# )
# fetchcontent_makeavailable(small_gicp)
#
# 顺序不能换：small_gicp_vendor 的 config 会把 vendor 安装前缀
# PREPEND 进 CMAKE_PREFIX_PATH，后面的 find_package(small_gicp) 才找得到。
find_package(small_gicp_vendor REQUIRED)
find_package(small_gicp REQUIRED)

###########
## Build ##
###########

ament_auto_add_library(${PROJECT_NAME} SHARED
  DIRECTORY src
)

# vendor 包导出的 target 是 small_gicp::small_gicp（见 small_gicp-targets.cmake:59），
# 裸名 small_gicp 会被当成 -lsmall_gicp 交给链接器，且不会带上头文件搜索路径。
target_link_libraries(${PROJECT_NAME} OpenMP::OpenMP_CXX small_gicp::small_gicp)

rclcpp_components_register_node(${PROJECT_NAME}
  PLUGIN small_gicp_relocalization::SmallGicpRelocalizationNode
  EXECUTABLE ${PROJECT_NAME}_node
)

#############
## Testing ##
#############

if(BUILD_TESTING)
  set(ament_cmake_clang_format_CONFIG_FILE "${CMAKE_SOURCE_DIR}/.clang-format")
  set(ament_cmake_clang_tidy_CONFIG_FILE "${CMAKE_SOURCE_DIR}/.clang-tidy")
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

#############
## Install ##
#############

ament_auto_package(
  USE_SCOPED_HEADER_INSTALL_DIR
  INSTALL_TO_SHARE
  launch
)
