FROM theosotr/sqlite3-test

RUN sudo apt update \
	&& sudo apt install -y python3 python3-pip python3-venv
WORKDIR /home/test/fuzzer

# For final submission image, we will need to copy the source code and install the package. 
# For now, we can just mount the source code as a volume when running the container, so we don't need to copy it in the image.
# COPY . .
# RUN pip install -e .
# RUN ln -s $(which test-db) /usr/bin/test-db
