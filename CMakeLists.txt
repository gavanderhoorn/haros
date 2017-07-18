cmake_minimum_required(VERSION 2.8.3)
project(haros)

find_package(catkin REQUIRED)
catkin_package(CFG_EXTRAS haros-extras.cmake)
install(DIRECTORY cmake
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

install(DIRECTORY harosviz
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
