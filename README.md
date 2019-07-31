[![Build Status](https://travis-ci.org/databio/refgenieserver.svg?branch=master)](https://travis-ci.org/databio/refgenieserver)

# refgenieserver

This folder contains code for an API to provide reference genomes.

## How to `serve`

### Building container

1. In the same directory as the `Dockerfile`:

```
docker build -t refgenieserverim .
```

### Running container for development:

Mount a directory of files to serve at `/genomes`:

```
docker run --rm -p 80:80 --name refgenieservercon \
  -v $(pwd)/files:/genomes \
  refgenieserverim refgenieserver serve -c refgenie.yaml 
```

### Running container for production:

2. Run the container from the image you just built:

```
docker run --rm -d -p 80:80 \
  -v /path/to/genomes_archive:/genomes \
  --name refgenieservercon \
  refgenieserverim refgenieserver serve -c /genomes/genome_config.yaml 
```

Make sure the `genome_config.yaml` filename matches what you've named your configuration file! We use `-d` to detach so it's in background. Terminate container when finished:

You shouldn't need to mount the app (`-v /path/to/refgenieserver:/app`) because in this case we're running it directly.

```
docker stop refgenieservercon
```


### Interacting with the API web server

Navigate to [http://localhost/](http://localhost/) to see the server in action.

You can see the automatic docs and interactive swagger openAPI interface at [http://localhost/docs](http://localhost/docs). That will also tell you all the endpoints, etc.


### Monitoring for errors

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

## How to `archive`

Another functionality of the package is archivization of the assets (creating a directory structure and asset archives needed for the server)

In order to do this just make sure the config points to the directory where you want to store the servable archives -- it's `genome_archive` key in the YAML file (it is __not__ added automatically by [`refgenie init`](http://refgenie.databio.org/en/latest/usage/#refgenie-init-help)). 

And then run: 
```
refgenieserver archive -c CONFIG
````
It just requires a `-c` argument or `$REFGENIE` environment variable to be set that point to the config file listing the assets the are to be archived.

This command will result in:
- creation of the `genome_archive` directory
- creation of a server config file in that directory. With couple of extra asset attributes, like `checksum` or `size`
- creation of a directory structure that can be then used to serve the assets

In case you already have some of the assets archived and just want to add a new one, use:

```
refgenieserver archive -c CONFIG -g GENOME -a ASSET
```


