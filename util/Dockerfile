FROM ubuntu:24.04 AS verilator

RUN apt-get update && apt-get install -y \
    git help2man perl python3 make g++  \
    libfl2  libfl-dev zlib1g zlib1g-dev \
    autoconf flex bison

# Build Verilator 5.044
RUN git clone https://github.com/verilator/verilator && \
    cd verilator && \
    git checkout v5.044 && \
    autoconf && \
    ./configure --prefix=/usr/local/verilator && \
    make -j$(nproc) && \
    make install

FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    wget curl git \ 
    build-essential \
    cmake ninja-build ccache \
    openjdk-21-jdk \
    clang \
    && rm -rf /var/lib/apt/lists/*

# Copy Verilator from Builder
COPY --from=verilator /usr/local/verilator /usr/local

CMD ["/bin/bash"]
