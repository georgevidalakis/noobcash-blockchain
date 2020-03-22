# Installation

1. Install mandatory requirements (Ubuntu):

    ```bash
    $ sudo apt update
    $ sudo apt install git python3 python3-pip
    $ pip3 install virtualenv # no sudo
    ```

1. Clone repo:

    ```bash
    $ git clone https://github.com/georgevidalakis/ECE_NTUA_distributed_2019_20 noobcash
    $ cd noobcash
    ```

1. Register commit hooks:

    ```bash
    $ cp etc/pre-commit .git/hooks/pre-commit
    $ chmod +x .git/hooks/pre-commit
    ```

1. Create a new [virtual environment](https://realpython.com/python-virtual-environments-a-primer/) for Python, in noobcash/.venv:

    ```bash
    $ ~/.local/bin/virtualenv .venv
    ```

1. Activate virtual environment. Should be done every time a new terminal is instantiated:

    ```bash
    $ source .venv/bin/activate
    ```

1. Install project dependencies (as a developer):

    ```bash
    $ pip install -e .[dev]
    ```
