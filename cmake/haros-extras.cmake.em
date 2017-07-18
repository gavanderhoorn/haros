if (_HAROS_EXTRAS_INCLUDED_)
  return()
endif()
set(_HAROS_EXTRAS_INCLUDED_ TRUE)

set(HAROS_REPORT_LOCATION "${CATKIN_DEVEL_PREFIX}/haros_report_${PROJECT_NAME}")

macro(_haros_create_targets)
  if (NOT TARGET haros_report)
    add_custom_target(haros_report)
  endif()

  if (NOT TARGET haros_report_${PROJECT_NAME})
    add_custom_target(haros_report_${PROJECT_NAME})
    add_dependencies(haros_report haros_report_${PROJECT_NAME})
  endif()
endmacro()

function(haros_report)
  _haros_create_targets()
  add_custom_command(TARGET haros_report_${PROJECT_NAME} POST_BUILD
        WORKING_DIRECTORY ${PROJECT_SOURCE_DIR} 
        COMMAND haros analyse
        COMMAND rm -Rf ${HAROS_REPORT_LOCATION}
        COMMAND cp -Rv ~/.haros/viz ${HAROS_REPORT_LOCATION})
endfunction()
