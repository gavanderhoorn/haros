if (_HAROS_EXTRAS_INCLUDED_)
  return()
endif()
set(_HAROS_EXTRAS_INCLUDED_ TRUE)

set(HAROS_REPORT_LOCATION "${CMAKE_CURRENT_BINARY_DIR}/haros_report")

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
        COMMAND haros init
        COMMAND haros -C ${PROJECT_SOURCE_DIR} analyse -t ${HAROS_REPORT_LOCATION})
endfunction()
