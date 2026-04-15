FROM theosotr/sqlite3-test

RUN sudo apt update \
	&& sudo apt install -y python3 python3-pip python3-venv
WORKDIR /home/test/fuzzer