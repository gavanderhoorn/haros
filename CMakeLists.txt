cmake_minimum_required(VERSION 2.8.3)
project(haros)

find_package(catkin REQUIRED COMPONENTS catkin_pip)

catkin_pip_python_setup()

catkin_pip_requirements(${CMAKE_CURRENT_SOURCE_DIR}/reqs.txt)

catkin_pip_package(haros)

# this depends on gavanderhoorn/catkin_pip@947dd38
catkin_package(CFG_EXTRAS haros-extras.cmake)
