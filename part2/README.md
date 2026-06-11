# Automated Software Testing
## Part 2: Automated Reduction of Bug-Triggering SQL Queries

### Building the Docker image
```
docker build -t sql-reducer .
```

### Running the container
We will mount the query folder to the container. Since we need to be able to overwrite those file with our reduced queries, and we also need to create the `query.sql` file for the executor, we will give the required permissions.
```
docker run -it -v "<path/to/queries>":/home/test/queries -w /home/test/queries sql-reducer
sudo chown -R test:test .
```

### Available commands
```
reducer --query <path/to/query.sql> --test <path/to/oracle.sh>
```