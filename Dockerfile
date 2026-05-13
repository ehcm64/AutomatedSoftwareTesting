FROM theosotr/sqlite3-test

RUN sudo apt update \
	&& sudo apt install -y python3 python3-pip python3-venv lcov

RUN cd /home/test/sqlite3-src && \
    CFLAGS="-g -O0 --coverage -fsanitize=address,undefined -fno-omit-frame-pointer" \
    LDFLAGS="--coverage -fsanitize=address,undefined" \
    ./configure --enable-all && \
    ASAN_OPTIONS=detect_leaks=0 make -j$(nproc)

WORKDIR /home/test/fuzzer

COPY . .

RUN python3 -m venv /home/test/.venv && \
    /home/test/.venv/bin/pip install .

RUN sudo ln -sf /home/test/.venv/bin/test-db /usr/bin/test-db
