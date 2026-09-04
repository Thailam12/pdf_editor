cmake_minimum_required(VERSION 3.16)
project(pdf_native_extensions C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O2 -fPIC")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra -O2 -fPIC")
set(CMAKE_BUILD_TYPE Release)

find_package(PkgConfig REQUIRED)

find_library(FITZ_LIBRARY NAMES mupdf mupdf-third HINTS /usr/lib /usr/local/lib /usr/lib/x86_64-linux-gnu)
find_library(MUPDF_LIBRARY NAMES mupdf mupdf-third HINTS /usr/lib /usr/local/lib /usr/lib/x86_64-linux-gnu)

find_path(FITZ_INCLUDE_DIR fitz.h PATHS /usr/include /usr/local/include /usr/include/mupdf HINTS /usr/local/include/mupdf)
find_path(MUPDF_PDF_INCLUDE_DIR mupdf/pdf.h PATHS /usr/include /usr/local/include HINTS /usr/local/include/mupdf)

find_package(OpenSSL REQUIRED)
find_package(ZLIB REQUIRED)

if(NOT FITZ_LIBRARY)
    pkg_check_modules(FITZ REQUIRED mupdf>=1.18)
    set(FITZ_LIBRARIES ${FITZ_LIBRARIES} ${FITZ_STATIC_LDFLAGS})
endif()

set(COMMON_INCLUDES
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${OPENSSL_INCLUDE_DIR}
    ${ZLIB_INCLUDE_DIRS}
)

if(FITZ_INCLUDE_DIR)
    list(APPEND COMMON_INCLUDES ${FITZ_INCLUDE_DIR})
endif()
if(MUPDF_PDF_INCLUDE_DIR)
    list(APPEND COMMON_INCLUDES ${MUPDF_PDF_INCLUDE_DIR})
endif()

set(COMMON_SOURCES
    common.cpp
)

set(COMMON_LIBRARIES
    ${OPENSSL_LIBRARIES}
    ${ZLIB_LIBRARIES}
)

if(FITZ_LIBRARY)
    list(APPEND COMMON_LIBRARIES ${FITZ_LIBRARY})
elseif(FITZ_LIBRARIES)
    list(APPEND COMMON_LIBRARIES ${FITZ_LIBRARIES})
endif()

add_library(pdf_renderer SHARED
    ${COMMON_SOURCES}
    renderer.cpp
)
target_include_directories(pdf_renderer PRIVATE ${COMMON_INCLUDES})
target_link_libraries(pdf_renderer PRIVATE ${COMMON_LIBRARIES})
set_target_properties(pdf_renderer PROPERTIES
    PREFIX ""
    OUTPUT_NAME "pdf_renderer"
    SOVERSION 1
    VERSION 2026.4
)

add_library(pdf_search_engine SHARED
    ${COMMON_SOURCES}
    search_engine.cpp
)
target_include_directories(pdf_search_engine PRIVATE ${COMMON_INCLUDES})
target_link_libraries(pdf_search_engine PRIVATE ${COMMON_LIBRARIES})
set_target_properties(pdf_search_engine PROPERTIES
    PREFIX ""
    OUTPUT_NAME "pdf_search_engine"
    SOVERSION 1
    VERSION 2026.4
)

add_library(pdf_compressor SHARED
    ${COMMON_SOURCES}
    compressor.cpp
)
target_include_directories(pdf_compressor PRIVATE ${COMMON_INCLUDES})
target_link_libraries(pdf_compressor PRIVATE ${COMMON_LIBRARIES})
set_target_properties(pdf_compressor PROPERTIES
    PREFIX ""
    OUTPUT_NAME "pdf_compressor"
    SOVERSION 1
    VERSION 2026.4
)

add_library(pdf_ocr_preprocess SHARED
    ${COMMON_SOURCES}
    ocr_preprocess.cpp
)
target_include_directories(pdf_ocr_preprocess PRIVATE ${COMMON_INCLUDES})
target_link_libraries(pdf_ocr_preprocess PRIVATE ${COMMON_LIBRARIES})
set_target_properties(pdf_ocr_preprocess PROPERTIES
    PREFIX ""
    OUTPUT_NAME "pdf_ocr_preprocess"
    SOVERSION 1
    VERSION 2026.4
)

add_library(pdf_crypto SHARED
    ${COMMON_SOURCES}
    crypto.cpp
)
target_include_directories(pdf_crypto PRIVATE ${COMMON_INCLUDES})
target_link_libraries(pdf_crypto PRIVATE ${COMMON_LIBRARIES})
set_target_properties(pdf_crypto PROPERTIES
    PREFIX ""
    OUTPUT_NAME "pdf_crypto"
    SOVERSION 1
    VERSION 2026.4
)

add_library(pdf_export SHARED
    ${COMMON_SOURCES}
    export.cpp
)
target_include_directories(pdf_export PRIVATE ${COMMON_INCLUDES})
target_link_libraries(pdf_export PRIVATE ${COMMON_LIBRARIES})
set_target_properties(pdf_export PROPERTIES
    PREFIX ""
    OUTPUT_NAME "pdf_export"
    SOVERSION 1
    VERSION 2026.4
)

set(LIBS_OUTPUT_DIR ${CMAKE_CURRENT_SOURCE_DIR}/libs)

set_target_properties(pdf_renderer PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${LIBS_OUTPUT_DIR})
set_target_properties(pdf_search_engine PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${LIBS_OUTPUT_DIR})
set_target_properties(pdf_compressor PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${LIBS_OUTPUT_DIR})
set_target_properties(pdf_ocr_preprocess PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${LIBS_OUTPUT_DIR})
set_target_properties(pdf_crypto PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${LIBS_OUTPUT_DIR})
set_target_properties(pdf_export PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${LIBS_OUTPUT_DIR})

install(TARGETS
    pdf_renderer
    pdf_search_engine
    pdf_compressor
    pdf_ocr_preprocess
    pdf_crypto
    pdf_export
    LIBRARY DESTINATION lib
)

install(FILES common.h DESTINATION include)

message(STATUS "MuPDF include dirs: ${FITZ_INCLUDE_DIR} ${MUPDF_PDF_INCLUDE_DIR}")
message(STATUS "MuPDF libraries: ${FITZ_LIBRARY}")
message(STATUS "OpenSSL: ${OPENSSL_VERSION}")
message(STATUS "Output directory: ${LIBS_OUTPUT_DIR}")
