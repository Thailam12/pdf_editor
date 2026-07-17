#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIBS_DIR="${SCRIPT_DIR}/libs"
BUILD_DIR="${SCRIPT_DIR}/build"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_wsl() {
    if grep -qi microsoft /proc/version 2>/dev/null; then
        return 0
    fi
    if [ -n "$WSL_DISTRO_NAME" ]; then
        return 0
    fi
    return 1
}

detect_package_manager() {
    if command -v apt-get &> /dev/null; then
        echo "apt"
    elif command -v dnf &> /dev/null; then
        echo "dnf"
    elif command -v pacman &> /dev/null; then
        echo "pacman"
    elif command -v apk &> /dev/null; then
        echo "apk"
    else
        echo "unknown"
    fi
}

install_dependencies() {
    local pkg_mgr=$(detect_package_manager)
    log_info "Detected package manager: ${pkg_mgr}"

    local missing=()

    if ! pkg-config --exists mupdf 2>/dev/null; then
        missing+=("mupdf-dev" "libmupdf-dev" "mupdf")
    fi

    if ! pkg-config --exists openssl 2>/dev/null; then
        missing+=("libssl-dev" "openssl-devel")
    fi

    if ! command -v cmake &> /dev/null; then
        missing+=("cmake")
    fi

    if ! command -v gcc &> /dev/null; then
        missing+=("gcc" "g++")
    fi

    if ! command -v pkg-config &> /dev/null; then
        missing+=("pkg-config")
    fi

    if [ ${#missing[@]} -eq 0 ]; then
        log_info "All dependencies already installed."
        return 0
    fi

    log_warn "Missing packages detected. Installing..."

    case $pkg_mgr in
        apt)
            sudo apt-get update -qq
            sudo apt-get install -y -qq \
                build-essential cmake pkg-config \
                libmupdf-dev mupdf-tools \
                libssl-dev zlib1g-dev \
                2>/dev/null || {
                    sudo apt-get install -y -qq \
                        build-essential cmake pkg-config \
                        libmupdf-dev \
                        libssl-dev zlib1g-dev
                }
            ;;
        dnf)
            sudo dnf install -y \
                gcc gcc-c++ cmake pkg-config \
                mupdf-devel \
                openssl-devel zlib-devel
            ;;
        pacman)
            sudo pacman -S --needed --noconfirm \
                base-devel cmake pkgconf \
                mupdf \
                openssl zlib
            ;;
        apk)
            sudo apk add --no-cache \
                build-base cmake pkgconf \
                mupdf-dev \
                openssl-dev zlib-dev
            ;;
        *)
            log_error "Unknown package manager. Please install manually:"
            echo "  - CMake >= 3.16"
            echo "  - GCC/G++ with C++17 support"
            echo "  - MuPDF development headers and libraries"
            echo "  - OpenSSL development headers"
            echo "  - zlib development headers"
            echo "  - pkg-config"
            return 1
            ;;
    esac

    log_success "Dependencies installed."
}

find_mupdf_headers() {
    local search_paths=(
        /usr/include
        /usr/local/include
        /usr/include/mupdf
        /usr/local/include/mupdf
    )

    for path in "${search_paths[@]}"; do
        if [ -f "${path}/fitz.h" ] || [ -f "${path}/mupdf/fitz.h" ]; then
            echo "${path}"
            return 0
        fi
    done

    return 1
}

find_mupdf_library() {
    local lib_names=(
        "mupdf-third"
        "mupdf"
        "libmupdf.so"
        "libmupdf-third.so"
    )

    local search_paths=(
        /usr/lib
        /usr/local/lib
        /usr/lib/x86_64-linux-gnu
        /usr/lib/aarch64-linux-gnu
    )

    for name in "${lib_names[@]}"; do
        for path in "${search_paths[@]}"; do
            if [ -f "${path}/lib${name}.so" ] || [ -f "${path}/${name}.so" ] || \
               [ -f "${path}/lib${name}.a" ] || [ -f "${path}/${name}.a" ]; then
                echo "${path}"
                return 0
            fi
        done
    done

    local found=$(find /usr -name "libmupdf*.so*" -o -name "libmupdf*.a" 2>/dev/null | head -1)
    if [ -n "$found" ]; then
        dirname "$found"
        return 0
    fi

    return 1
}

check_compiler() {
    if ! command -v gcc &> /dev/null; then
        log_error "GCC not found. Please install build-essential or gcc."
        return 1
    fi

    if ! command -v g++ &> /dev/null; then
        log_error "G++ not found. Please install g++."
        return 1
    fi

    local gcc_version=$(gcc -dumpversion)
    local gxx_version=$(g++ -dumpversion)
    log_info "GCC version: ${gcc_version}"
    log_info "G++ version: ${gxx_version}"

    local major=$(echo "$gcc_version" | cut -d. -f1)
    if [ "$major" -lt 7 ]; then
        log_warn "GCC < 7 detected. C++17 support may be limited."
    fi

    return 0
}

check_cmake() {
    if ! command -v cmake &> /dev/null; then
        log_error "CMake not found. Please install cmake >= 3.16."
        return 1
    fi

    local cmake_version=$(cmake --version | head -1 | grep -oP '\d+\.\d+')
    log_info "CMake version: ${cmake_version}"
    return 0
}

build_project() {
    log_info "Building PDF native extensions..."

    mkdir -p "${BUILD_DIR}"
    mkdir -p "${LIBS_DIR}"

    cd "${BUILD_DIR}"

    log_info "Running CMake configuration..."
    cmake "${SCRIPT_DIR}" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=gcc \
        -DCMAKE_CXX_COMPILER=g++ \
        2>&1

    if [ $? -ne 0 ]; then
        log_error "CMake configuration failed."
        return 1
    fi

    local nproc=$(nproc 2>/dev/null || echo 4)
    log_info "Building with ${nproc} parallel jobs..."

    cmake --build . --config Release -j "${nproc}" 2>&1

    if [ $? -ne 0 ]; then
        log_error "Build failed."
        return 1
    fi

    log_success "Build completed successfully."
}

copy_libraries() {
    log_info "Copying libraries to ${LIBS_DIR}..."

    local libs=(
        "libpdf_renderer.so"
        "libpdf_search_engine.so"
        "libpdf_compressor.so"
        "libpdf_ocr_preprocess.so"
        "libpdf_crypto.so"
        "libpdf_export.so"
    )

    for lib in "${libs[@]}"; do
        local found=$(find "${BUILD_DIR}" -name "${lib}*" -type f 2>/dev/null)
        if [ -n "$found" ]; then
            cp -v ${found} "${LIBS_DIR}/"
        else
            log_warn "Library ${lib} not found in build directory."
        fi
    done

    log_info "Libraries in ${LIBS_DIR}:"
    ls -la "${LIBS_DIR}/"*.so* 2>/dev/null || log_warn "No .so files found."
}

print_summary() {
    echo ""
    echo "============================================="
    log_success "Build Summary"
    echo "============================================="
    echo ""
    echo "Libraries built:"
    ls -la "${LIBS_DIR}/"*.so* 2>/dev/null || echo "  (none found)"
    echo ""
    echo "Usage from Python:"
    echo ""
    echo "  import ctypes"
    echo "  lib = ctypes.CDLL('${LIBS_DIR}/libpdf_renderer.so')"
    echo ""
    echo "  Or use cdll:"
    echo "  lib = ctypes.CDLL('${LIBS_DIR}/libpdf_crypto.so')"
    echo ""
    echo "============================================="
}

main() {
    echo ""
    echo "============================================="
    echo "  PDF Editor - Native Extensions Builder"
    echo "============================================="
    echo ""

    if check_wsl; then
        log_info "Running inside WSL."
    else
        log_warn "Not running in WSL. Proceeding anyway..."
    fi

    check_compiler
    check_cmake

    log_info "Checking and installing dependencies..."
    install_dependencies

    log_info "Locating MuPDF..."
    local mupdf_include=$(find_mupdf_headers)
    local mupdf_lib=$(find_mupdf_library)

    if [ -n "$mupdf_include" ]; then
        log_info "MuPDF headers: ${mupdf_include}"
    else
        log_warn "MuPDF headers not found. CMake will try pkg-config."
    fi

    if [ -n "$mupdf_lib" ]; then
        log_info "MuPDF library: ${mupdf_lib}"
    else
        log_warn "MuPDF library not found. CMake will try pkg-config."
    fi

    build_project

    if [ $? -ne 0 ]; then
        log_error "Build failed. Check the output above for errors."
        exit 1
    fi

    copy_libraries
    print_summary

    log_success "All done!"
}

main "$@"
