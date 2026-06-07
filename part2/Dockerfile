FROM theosotr/sqlite3-reducer

RUN sudo apt update \
	&& sudo apt install -y python3 python3-pip python3-venv

WORKDIR /home/test/reducer

COPY . .

RUN python3 -m venv /home/test/.venv && \
/home/test/.venv/bin/pip install .

RUN sudo ln -sf /home/test/.venv/bin/reducer /usr/bin/reducer

