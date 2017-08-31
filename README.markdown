[![Build Status](https://travis-ci.org/hypothesis/lti.svg?branch=master)](https://travis-ci.org/hypothesis/lti)
[![codecov](https://codecov.io/gh/hypothesis/lti/branch/master/graph/badge.svg)](https://codecov.io/gh/hypothesis/lti)
[![Updates](https://pyup.io/repos/github/hypothesis/lti/shield.svg)](https://pyup.io/repos/github/hypothesis/lti/)
[![Python 3](https://pyup.io/repos/github/hypothesis/lti/python-3-shield.svg)](https://pyup.io/repos/github/hypothesis/lti/)

# Hypothesis Canvas App

## Development

### Setting up a dev environment

You will need:

* Git
* Python
* Virtualenv
* Docker
* ...

To get the Canvas app running in a dev environment:

1. Set up a dev install of Canvas: <https://github.com/instructure/canvas-lms/wiki/Quick-Start>.

   Tip: you might want to install Canvas inside a virtual machine, to avoid
   installing all that stuff onto your host machine. If you do so you'll have
   to setup virtual machine <-> host machine networking though.

   Tip: Canvas runs on port 3000 by default, which is a port already used by
   the Hypothesis client in development. I moved Canvas to port 3333 in my
   Canvas virtual machine's port forwarding config.

1. You'll also need to install Redis and configure your Canvas dev install to
   use Redis, even though Canvas's Quick Start docs don't say to do so.

   The easiest way to install Redis is by using Docker. Install Docker if you
   don't have it already and then just run:

   ```bash
   $ docker run -p 6379:6379 redis
   ```

   Redis will now be running on <http://localhost:6379/>. You won't see
   anything there in a web browser though because Redis doesn't respond to
   HTTP. Instead you can test it by installing
   [redis-cli](https://redis.io/topics/rediscli) then running `redis-cli ping`:

   ```bash
   $ redis-cli ping
   PONG
   ```

   After installing Redis follow the parts of the
   [Canvas Redis configuration docs](https://github.com/instructure/canvas-lms/wiki/Production-Start#redis)
   where it says to edit your `cache-store.yml` and `redis.yml` files, but
   note that you don't need to do the `chown` and `chmod` commands.

   Here's my `cache-store.yml` file:

   ```
   development:
     cache_store: redis_store
   ```

   And here's my `redis.yml` file:

   ```
   development:
     servers:
     - redis://localhost:6379
   ```

   Tip: if Canvas is running inside a virtual machine and Redis is running in
   a Docker container on the host machine, then the Redis URL above will have
   to be the IP address of the host machine as seen from inside the virtual
   machine, instead of `localhost`. If you setup your virtual machine using
   Vagrant this is `redis://10.0.2.2:6379`.

1. Run a PostgreSQL database for the Hypothesis Canvas app to use.

   The easiest way to run a database with the configuration that the app
   expects is with Docker. The first time you run it you'll need to use this
   command to create and run the `lti-postgres` docker container:

   ```bash
   $ sudo docker run -p 5433:5432 --name lti-postgres postgres
   ```

   Subsequently you can just re-start the already-created container with:

   ```bash
   sudo docker start -a lti-postgres
   ```

   **Tip**: You can connect to this database to inspect its contents by
   installing [psql](https://www.postgresql.org/docs/current/static/app-psql.html)
   and then running:

   ```bash
   $ psql postgresql://postgres@localhost:5433/postgres
   ```

   **Tip**: If you want to delete all your data and reset your dev database,
   an easy way to do so is just to delete the whole docker container:

   ```bash
   $ sudo docker rm lti-postgres
   ```

   You can then re-create the container by re-running the `docker run` command
   above.

1. Run an instance of [Via](https://github.com/hypothesis/via) locally.

1. Clone the Hypothesis Canvas app's GitHub repository:

   ```bash
   $ git clone https://github.com/hypothesis/lti.git
   $ cd lti
   ```

1. Set the environment variables that the app needs to values suitable for
   local development:

   ```bash
   export LTI_SERVER="http://localhost:8001"
   export LTI_CREDENTIALS_URL="http://localhost:8001/lti_credentials"
   export VIA_URL="http://localhost:9080"
   ```

1. Run the development server. First create and activate a Python virtual
   environment for the Canvas app and then run:

   ```bash
   $ make dev
   ```

1. Add the development Hypothesis Canvas app to a course and an assignment in
   your development Canvas instance. Follow the
   [Installing the App][installing_the_app] and [Using the App][using_the_app]
   google docs.

   Tip: In my developer key the **Redirect URI (Legacy)** is set to
   `http://localhost:8001/token_callback`.
   
   In the Canvas app's settings I set the **Config URL** to
   `http://10.0.0.2:8001/config` because I have Canvas running inside a VM and
   `10.0.0.2` is the address of my host machine (where the Hypothesis Canvas
   app is running) as seen from within the VM. If you don't have Canvas running
   inside a VM then the Config URL would be `http://localhost:8001/config`.

   Other app URLs, for example the **Launch URL**, are called from the browser
   rather than from the Canvas server, so they should be `localhost:8001` even
   if you're running Canvas inside a VM.

### Running the tests

1. Create the test database. You only need to do this once:

   ```bash
   $ psql postgresql://postgres@localhost:5433/postgres -c "CREATE DATABASE lti_test;"
   ```

2. Run the tests:

   ```bash
   $ make test
   ```

### Getting a shell

`make shell` will get you a Python shell with a Pyramid registry, request, etc.
Useful for debugging or trying things out in development:

```bash
$ make shell
```

**Tip**: If you install `pyramid_ipython` then `make shell` will give you an
IPython shell instead of a plain Python one:

```
$ pip install pyramid_ipython
```

There are also `pyramid_` packages for `bpython`, `ptpython`, etc.

### Running the linters

```bash
$ make lint
```

### Managing Python dependencies

We use `pip-tools` to manage Python dependencies: <https://github.com/jazzband/pip-tools>.

#### To add a new Python dependency

Python dependencies are tracked in the [requirements.in][] file
or [requirements-dev.in][] if the requirement is only needed in development
environments and not in production.

In addition `requirements.in` is compiled to produce a [requirements.txt][]
file that pins the version numbers of all dependencies for deterministic
production builds. 

**If you've added a new Python dependency**:

1. Add it to `requirements.in` or `requirements-dev.in`.

   You don't usually need to specify the version number of a dependency in
   `requirements.in` or `requirements-dev.in`, nor do you need to list
   dependencies of dependencies, you can just list the top-level dependencies.

2. **If you've added a dependency to `requirements.in`** then update
   `requirements.txt` by running `pip-compile`:

   ```bash
   $ pip-compile --output-file requirements.txt requirements.in
   ```

3. Commit all changed requirements files - `requirements.in`,
   `requirements-dev.in` and `requirements.txt` - to git.

#### To upgrade a Python dependency

For example to upgrade the `requests` dependency to the latest version run:

```bash
$ pip-compile --upgrade-package requests
```

then commit the modified `requirements.txt` file to git.

You can also just run `pip-compile --upgrade` to upgrade all dependencies at
once.

[requirements.in]: requirements.in
[requirements-dev.in]: requirements-dev.in
[requirements.txt]: requirements.txt
[installing_the_app]: https://docs.google.com/document/d/13FFtk2qRogtU3qxR_oa3kq2ak-S_p7HHVnNM12eZGy8/edit# "Installing the App Google Doc"
[using_the_app]: https://docs.google.com/document/d/1EvxGoX81H8AWDcskDph8dmu4Ov4gMSkGGXr5_5ggx3I/edit# "Using the App Google Doc"

### Making changes to model code

If you've made any changes to the database schema (for example: added or
removed a SQLAlchemy ORM class, or added, removed or modified a
`sqlalchemy.Column` on an ORM class) then you need to create a database
migration script that can be used to upgrade the production database from the
previous to your new schema.

**See Also**: [Some tips on writing good migration scripts in the h docs](http://h.readthedocs.io/en/latest/developing/making-changes-to-model-code/#batch-deletes-and-updates-in-migration-scripts).

We use [Alembic](http://alembic.zzzcomputing.com/en/latest/) to create and run
migration scripts. See the Alembic docs (and look at existing scripts in
[lti/migrations/versions](lti/migrations/versions)) for details, but the basic
steps to create a new migration script for h are:

1. Create the revision script by running `alembic revision`, for example:

   ```bash
   $ alembic -c conf/alembic.ini revision -m "Add the foobar table."
   ```

   This will create a new script in [lti/migrations/versions](lti/migrations/versions).

1. Edit the generated script, fill in the `upgrade()` and `downgrade()` methods.

   See <http://alembic.zzzcomputing.com/en/latest/ops.html#ops> for details.

   **Note**: Not every migration should have a ``downgrade()`` method. For
   example if the upgrade removes a max length constraint on a text field, so
   that values longer than the previous max length can now be entered, then a
   downgrade that adds the constraint back may not work with data created using
   the updated schema.

1. Stamp your database.

   Before running any upgrades or downgrades you need to stamp the database
   with its current revision, so Alembic knows which migration scripts to run:

   ```bash
   $ alembic -c conf/alembic.ini stamp <revision_id>
   ```

   `<revision_id>` should be the revision corresponding to the version of the
   code that was present when the current database was created. The will
   usually be the `down_revision` from the migration script that you've just
   generated.

1. Test your `upgrade()` function by upgrading your database to the most recent
   revision. This will run all migration scripts newer than the revision that
   your db is currently stamped with, which usually means just your new
   revision script:

   ```bash
   $ alembic -c conf/alembic.ini upgrade head
   ```

   After running this command inspect your database's schema to check that it's
   as expected, and run the app to check that everything is working.

   **Note**: You should make sure that there's some repesentative data in the
   relevant columns of the database before testing upgrading and downgrading
   it. Some migration script crashes will only happen when there's data
   present.

1. Test your `downgrade()` function:

   ```bash
   $ alembic -c conf/alembic.ini downgrade -1
   ```

   After running this command inspect your database's schema to check that it's
   as expected. You can then upgrade it again:

   ```bash
   $ alembic -c conf/alembic.ini upgrade +1
   ```

### Adding OAuth credentials to the production and QA apps

The production LTI app runs in a Docker container on an Amazon EC2 instance.
To login to this server and modify the database you need to:

1. Checkout the playbook repo and run its `h-ssh` tool to ssh into the
   production LTI EC2 instance:

   ```bash
   $ sh ./tools/h-ssh prod lti
   ```

   **Note**: In order for this to work you'll need to have your local ssh
   configured correctly, see the playbook repo's README.

1. On the EC2 instance run `docker ps` to see the name of the app's docker container:

   ```bash
   $ sudo docker ps
   ```

1. Now run `docker exec` to run a shell inside the docker container:

   ```bash
   $ sudo docker exec -it nostalgic_shockley sh
   ```

1. In the docker container, run `pshell`:

   ```bash
   $ PYTHONPATH=. pshell conf/production.ini
   ```

1. In `pshell` add the new `OAuth2Credentials` to the database and commit the transaction:

   ```python
   >>> from lti.models import OAuth2Credentials
   >>> request.db.add(OAuth2Credentials(client_id=u'10000000000007', client_secret=u'1AN***VvS', authorization_server=u'https://hypothesis.instructure.com'))
   >>> request.tm.commit()
   ```
