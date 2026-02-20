# Python TUI for Importing Tasks to OpenProject

To run the Textual App:

    $ pixi run start

To install the package locally:

    $ pip install op_importer

## Getting Started

Obtain an API key from your OpenProject installation. See [here]() for how.

Paste the key into a `.env` file in your working directory together with the URL for your
OpenProject:

    OPENPROJECT_API_KEY="<yourAPIkeywillhavelotsoflettersandnumbers02938329909809098089>"
    OPENPROJECT_API_URL="https://my.openproject.com/api/v3"

Prepare a csv file with the exact headers::

    subject,description,project,status,work_package_type,startDate,dueDate

Run the App from the command line, select your CSV file and upload your new work packages
to your OpenProject installation

## Develop op_importer

Clone the repository

    git clone https://github.com/openenergytransition/op_importer

Change directory

    cd op_importer

Install the environment using pixi

    pixi install

Run the op_importer

    pixi run start

Run the tests

    pixi run test

## Install and Maintain OpenProject

If you want to test op_importer locally, you'll need to setup an
install of OpenProject. The easiest way to do this is via a Docker
container.

Generate a random secret:

    head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32 ; echo ''

Spin up the container

    sudo docker run -d -p 8080:80 --name openproject \
    -e SECRET_KEY_BASE=<your random secret> \
    -e OPENPROJECT_HOST__NAME=localhost:8080 \
    -e OPENPROJECT_HTTPS=false \
    -e OPENPROJECT_DEFAULT__LANGUAGE=en \
    -v /var/lib/openproject/pgdata:/var/openproject/pgdata \
    -v /var/lib/openproject/assets:/var/openproject/assets \
    openproject/openproject:16

Stop the container

    sudo docker stop openproject

Start it again

    sudo docker start openproject

Remove the container

    sudo docker rm openproject


# Restore a backup

Create the folders

    mkdir -p /var/lib/openproject/{pgdata,assets}

Initalise the database (Ctrl + C once `Database Setup Finished` shown)

    docker run --rm -v /var/lib/openproject/pgdata:/var/openproject/pgdata -it openproject/openproject:16

Restore the dump (note postgres 17 required)

    docker run --rm -d --name postgres -v /var/lib/openproject/pgdata:/var/lib/postgresql/data postgres:17

Copy SQL dump into container and start psql

    docker cp openproject.sql postgres:/
    docker exec -it postgres psql -U postgres

Restore dump in psql

    DROP DATABASE openproject;
    CREATE DATABASE openproject OWNER openproject;

    \c openproject
    \i openproject.sql

Once this has finished you can quit psql (using \q) and the container (exit).

Start the container as described in the installation section mounting `/var/lib/openproject/pgdata`
(and `/var/lib/openproject/assets/` for attachments).
