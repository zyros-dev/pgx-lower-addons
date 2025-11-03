# ============================================================================
# Stage 1: Builder - compiles pgx-lower extension and PostgreSQL
# ============================================================================
FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV LLVM_VERSION=20
ENV PG_VERSION=17.6
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    ninja-build \
    git \
    wget \
    curl \
    bc \
    bison \
    flex \
    python3 \
    python3-pip \
    lsb-release \
    software-properties-common \
    gnupg \
    zlib1g-dev \
    libreadline-dev \
    libssl-dev \
    libicu-dev \
    pkg-config \
    libgtest-dev \
    libzstd-dev \
    locales \
    && rm -rf /var/lib/apt/lists/* \
    && locale-gen en_US.UTF-8 \
    && update-locale LANG=en_US.UTF-8

# Install CMake 3.31
RUN wget https://github.com/Kitware/CMake/releases/download/v3.31.6/cmake-3.31.6-linux-x86_64.sh && \
    chmod +x cmake-3.31.6-linux-x86_64.sh && \
    ./cmake-3.31.6-linux-x86_64.sh --skip-license --prefix=/usr/local && \
    rm cmake-3.31.6-linux-x86_64.sh

# Install GCC 14
RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test && \
    apt-get update && \
    apt-get install -y gcc-14 g++-14 libstdc++-14-dev && \
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-14 100 && \
    update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-14 100 && \
    rm -rf /var/lib/apt/lists/*

# Install LLVM 20 with MLIR support
RUN wget https://apt.llvm.org/llvm.sh && \
    chmod +x llvm.sh && \
    ./llvm.sh ${LLVM_VERSION} all && \
    rm llvm.sh && \
    update-alternatives --install /usr/bin/clang clang /usr/lib/llvm-${LLVM_VERSION}/bin/clang 100 && \
    update-alternatives --install /usr/bin/clang++ clang++ /usr/lib/llvm-${LLVM_VERSION}/bin/clang++ 100

RUN apt-get update && apt-get install -y \
        libmlir-${LLVM_VERSION}-dev \
        mlir-${LLVM_VERSION}-tools \
        llvm-${LLVM_VERSION}-dev \
        libc++-${LLVM_VERSION}-dev \
        libc++abi-${LLVM_VERSION}-dev \
    && rm -rf /var/lib/apt/lists/* \
    && mv /usr/lib/llvm-${LLVM_VERSION}/include/cxxabi.h /usr/lib/llvm-${LLVM_VERSION}/include/cxxabi.h.bak

# Build PostgreSQL from source
RUN wget https://ftp.postgresql.org/pub/source/v${PG_VERSION}/postgresql-${PG_VERSION}.tar.gz && \
    tar -xzf postgresql-${PG_VERSION}.tar.gz && \
    cd postgresql-${PG_VERSION} && \
    CC=clang CXX=clang++ ./configure --prefix=/usr/local/pgsql --with-openssl --with-icu && \
    make -j$(nproc) && \
    make install && \
    cd / && \
    rm -rf postgresql-${PG_VERSION} postgresql-${PG_VERSION}.tar.gz

# Set up environment for pgx-lower build
ENV PATH="/usr/local/pgsql/bin:/usr/lib/llvm-${LLVM_VERSION}/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/pgsql/lib:/usr/lib/llvm-${LLVM_VERSION}/lib:${LD_LIBRARY_PATH}"
ENV MLIR_DIR="/usr/lib/llvm-${LLVM_VERSION}/lib/cmake/mlir"
ENV LLVM_DIR="/usr/lib/llvm-${LLVM_VERSION}/lib/cmake/llvm"

# Clone and build pgx-lower
WORKDIR /build
RUN git clone https://github.com/zyrosdev/pgx-lower.git . && \
    mkdir -p build-release && \
    cd build-release && \
    cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_ONLY_EXTENSION=ON .. && \
    cmake --build . && \
    cmake --install .

# ============================================================================
# Stage 2: Runtime - slim image with PostgreSQL + extension
# ============================================================================
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV PG_VERSION=17.6
ENV LLVM_VERSION=20

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3 \
    libreadline8 \
    libicu74 \
    libzstd1 \
    zlib1g \
    locales \
    ca-certificates \
    wget \
    gosu \
    sudo \
    llvm-${LLVM_VERSION}-runtime \
    libmlir-${LLVM_VERSION} \
    && rm -rf /var/lib/apt/lists/* \
    && locale-gen en_US.UTF-8 \
    && update-locale LANG=en_US.UTF-8

# Create postgres user
RUN useradd -m -d /var/lib/postgresql -s /bin/bash postgres && \
    mkdir -p /var/lib/postgresql/data && \
    chown -R postgres:postgres /var/lib/postgresql

# Copy PostgreSQL binaries and libraries from builder
COPY --from=builder /usr/local/pgsql /usr/local/pgsql

# Copy entrypoint script
COPY docker/pgx-lower/entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create IR temp directory
RUN mkdir -p /tmp/pgx_ir && chmod 777 /tmp/pgx_ir

# Set up environment
ENV PATH="/usr/local/pgsql/bin:/usr/lib/llvm-${LLVM_VERSION}/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/pgsql/lib:/usr/lib/llvm-${LLVM_VERSION}/lib:${LD_LIBRARY_PATH}"

WORKDIR /var/lib/postgresql
EXPOSE 54326

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["postgres"]
