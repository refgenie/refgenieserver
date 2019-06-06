# refgenieserver

This folder contains code for an API to provide reference genomes.

## Building container

1. In the same directory as the `Dockerfile`:

```
docker build -t refgenieserverim .
```

## Running container for development:

Mount a directory of files to serve at `/genomes`:

```
docker run --rm -p 80:80 --name refgenieservercon -v $(pwd):/app -v $(pwd)/files:/genomes refgenieserverim refgenieserver -c refgenie.yaml serve
```

## Running container for production:

2. Run the container from the image you just built:

```
docker run --rm -d -p 80:80 -v /path/to/genomes_archive:/genomes --name refgenieservercon refgenieserver -c /genomes/genome_config.yaml serve 
```

Make sure the `genome_config.yaml` filename matches what you've named your configuration file! We use `-d` to detach so it's in background. Terminate container when finished:

You shouldn't need to mount the app (`-v /path/to/refgenieserver:/app`) because in this case we're running it directly.

```
docker stop refgenieservercon
```


## Interacting with the API web server

Navigate to [http://localhost/](http://localhost/) to see the server in action.

You can see the automatic docs and interactive swagger openAPI interface at [http://localhost/docs](http://localhost/docs). That will also tell you all the endpoints, etc.


## Monitoring for errors

Attach to container to see debug output:

```
docker attach refgenieservercon
```

Grab errors:

```
docker events | grep -oP "(?<=die )[^ ]+"
```

View those error codes:

```
docker logs <error_code>
```

Enter an interactive shell to explore the container contents:

```
docker exec -it refgenieservercon sh
```
