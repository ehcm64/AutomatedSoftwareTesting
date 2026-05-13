FROM theosotr/sqlite3-test

# Install system dependencies
RUN sudo apt update \
	&& sudo apt install -y python3 python3-pip python3-venv lcov

# Compile the patched SQLite version with gcov coverage and ASAN/UBSAN sanitizers
# This is required for code coverage evaluation and finding bugs with sanitizers.
RUN cd /home/test/sqlite3-src && \
    CFLAGS="-g -O0 --coverage -fsanitize=address,undefined -fno-omit-frame-pointer" \
    LDFLAGS="--coverage -fsanitize=address,undefined" \
    ./configure --enable-all && \
    ASAN_OPTIONS=detect_leaks=0 make -j$(nproc)

WORKDIR /home/test/fuzzer

# Copy the fuzzer source code into the image
COPY . .

# Create a virtual environment and install the fuzzer package inside it.
# This ensures a clean installation and isolation from system packages.
RUN python3 -m venv /home/test/.venv && \
    /home/test/.venv/bin/pip install .

# Ensure the executable is at /usr/bin/test-db as required by the handout.
# The symlink points to the script in the virtual environment.
RUN sudo ln -sf /home/test/.venv/bin/test-db /usr/bin/test-db

# Ensure the 'test' user owns the fuzzer directory, the venv, and the compiled sqlite.
#RUN sudo chown -R test:test /home/test/fuzzer /home/test/sqlite3-src /home/test/.venv
