# To install just on a per-project basis
# 1. Activate your virtual environemnt
# 2. uv add --dev rust-just
# 3. Use just within the activated environment

drive_uuid := "77688511-78c5-4de3-9108-b631ff823ef4"
#drive_uuid := "8425-155D"

user :=  file_stem(home_dir())
def_drive := join("/media", user, drive_uuid)
project := file_stem(justfile_dir())
local_env := join(justfile_dir(), ".env")


# list all recipes
default:
    just --list

# Install tools globally
tools:
    uv tool install twine
    uv tool install ruff

# Add conveniente development dependencies
dev:
    uv add --dev pytest

# Build the package
build:
    rm -fr dist/*
    uv build

# Generate a requirements file
requirements:
    uv pip compile pyproject.toml -o requirements.txt

# Publish the package to PyPi
publish pkg="zptess": build
    twine upload -r pypi dist/*
    uv run --no-project --with {{pkg}} --refresh-package {{pkg}} \
        -- python -c "from {{pkg}} import __version__; print(__version__)"

# Publish to Test PyPi server
test-publish pkg="zptess": build
    twine upload --verbose -r testpypi dist/*
    uv run --no-project  --with {{pkg}} --refresh-package {{pkg}} \
        --index-url https://test.pypi.org/simple/ \
        --extra-index-url https://pypi.org/simple/ \
        -- python -c "from {{pkg}} import __version__; print(__version__)"


# upgrades library and uv.lock
upgrade library:
    uv pip install --upgrade {{library}}
    uv lock --upgrade

pull:
    git pull --rebase --tags

push:
    git push --tags

run mode="dev":
    #!/usr/bin/env bash
    set -exuo pipefail
    cp tess.medium.db tess.db
    uv run tess-db-server --console --trace --config config.toml


# Adds lica source library as dependency. 'version' may be a tag or branch
api-dev version="main" pkg="tessdb-api" uri="STARS4ALL/tessdb-api":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Removing previous {{pkg}} dependency"
    uv remove {{pkg}} || echo "Ignoring non existing {{pkg}} library";
    if [[ "{{ version }}" =~ [0-9]+\.[0-9]+\.[0-9]+ ]]; then
        echo "Adding {{pkg}} source library --tag {{ version }}"; 
        uv add git+https://github.com/{{uri}} --tag {{ version }};
    else
        echo "Adding {{pkg}} source library branch --branch {{ version }}";
        uv add git+https://github.com/{{uri}} --branch {{ version }};
    fi

# Adds lica release library as dependency with a given version
api-rel version="" pkg="tessdb-api":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Removing previous {{pkg}} dependency"
    uv remove {{pkg}} || echo "Ignoring non existing {{pkg}} library";
    echo "Adding release version of {{pkg}} library {{ version }}";
    uv add --refresh-package {{pkg}} {{pkg}} {{ version }};



# Backup .env to storage unit
env-bak drive=def_drive: (check_mnt drive) (env-backup join(drive, "env", project))

# Restore .env from storage unit
env-rst drive=def_drive: (check_mnt drive) (env-restore join(drive, "env", project))


# Starts a new SQLite database export migration cycle   
anew verbose="":
    #!/usr/bin/env bash
    set -exuo pipefail
    uv sync --reinstall
    uv run tess-db-alarms-schema --console --log-file tessdb.log {{ verbose }}

# Starts a new SQLD database export migration cycle
# we need to add 127.0.0.1 *.db.sarna.dev to /etc/local/hosts
# and DATABASE_URL=sqlite+libsql://nixnox.db.sarna.dev:8080
anew2 env="devel":
    #!/usr/bin/env bash
    set -exuo pipefail
    env={{env}}
    uv sync --reinstall
    curl -X DELETE http://localhost:8082/v1/namespaces/${env}
    curl -X POST http://localhost:8082/v1/namespaces/${env}/create -d '{}' -H "Content-Type: application/json" 
    uv run nx-db-schema --console --log-file nixnox.log
    uv run nx-db-populate --console --trace --log-file nixnox.log all --batch-size 25000

# =============
# PyTest driver
# =============

test pkg module:
    uv run pytest tests/{{pkg}}/test_{{module}}.py

testf pkg module func:
    uv run pytest tests/{{pkg}}/test_{{module}}.py::test_{{func}}


# ================ #
# HTTP API TESTING #
# ================ #

hello port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X GET http://localhost:{{port}}/v1)
    echo $response
    
stats port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X GET http://localhost:{{port}}/v1/stats)
    echo $response


pause port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X POST http://localhost:{{port}}/v1/server/pause -d '{}' -H "Content-Type: application/json")
    echo $response
    
resume port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X POST http://localhost:{{port}}/v1/server/resume -d '{}' -H "Content-Type: application/json")
    echo $response

reload port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X POST http://localhost:{{port}}/v1/server/reload -d '{}' -H "Content-Type: application/json")
    echo $response

flush port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X POST http://localhost:{{port}}/v1/server/flush -d '{}' -H "Content-Type: application/json")
    echo $response

plog-set name level port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X PUT http://localhost:{{port}}/v1/ploggers/{{name}} -d '{"name": "{{name}}", "level": "{{level}}"}' -H "Content-Type: application/json")
    echo $response

plog-get name port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X GET http://localhost:{{port}}/v1/ploggers/{{name}})
    echo $response

plog-list port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X GET http://localhost:{{port}}/v1/ploggers)
    echo $response

log-list port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X GET http://localhost:{{port}}/v1/loggers)
    echo $response

log-get name port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X GET http://localhost:{{port}}/v1/loggers/{{name}})
    echo $response

log-set name level port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X PUT http://localhost:{{port}}/v1/loggers/{{name}} -d '{"name": "{{name}}", "level": "{{level}}"}' -H "Content-Type: application/json")
    echo $response

filter-get name port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X GET http://localhost:{{port}}/v1/filter/{{name}}/config)
    echo $response

# set filter to Sampler divisor buffered=true/false
filter-set name divisor buffered port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X PUT http://localhost:{{port}}/v1/filter/{{name}}/config -d '{"divisor": {{divisor}}, "buffered": {{buffered}}}' -H "Content-Type: application/json")
    echo $response


filter-state name port="8080":
    #!/usr/bin/env bash   
    set -euo pipefail
    response=$(curl -s -X GET http://localhost:{{port}}/v1/filter/{{name}})
    echo $response

# --------------
# Alarms utility
# --------------

alarm:
    #!/usr/bin/env bash
    uv run tess-db-alarms --console --trace

# =======================================================================

[private]
check_mnt mnt:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ ! -d  {{ mnt }} ]]; then
        echo "Drive not mounted: {{ mnt }}"
        exit 1 
    fi

[private]
env-backup bak_dir:
    #!/usr/bin/env bash
    set -exuo pipefail
    if [[ ! -f  {{ local_env }} ]]; then
        echo "Can't backup: {{ local_env }} doesn't exists"
        exit 1 
    fi
    mkdir -p {{ bak_dir }}
    cp {{ local_env }} {{ bak_dir }}
    cp config.toml {{ bak_dir }}
    cp tdbalarm.db  {{ bak_dir }}
  
[private]
env-restore bak_dir:
    #!/usr/bin/env bash
    set -euxo pipefail
    if [[ ! -f  {{ bak_dir }}/.env ]]; then
        echo "Can't restore: {{ bak_dir }}/.env doesn't exists"
        exit 1 
    fi
    cp {{ bak_dir }}/.env {{ local_env }}
    cp {{ bak_dir }}/config.toml .
    cp {{ bak_dir }}/tdbalarm.db .
