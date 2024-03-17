Contributions
=============
Contributions to this open-source project are welcome and always appreciated! Every line of code helps
to ensure a more robustly developed project. We will always credit those who help out.

New to contributing
-------------------
If you're new to contributing towards this project, it is suggested that you start off with installing
the library off of pip:

On Linux or MacOS:

.. code-block:: bash

    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install swgoh-comlink

On Windows (using cmd.exe):

.. code-block:: bash

    python -m venv c:\<path>\<to>\.venv
    C:\> <venv>\Scripts\activate.bat
    python -m pip install swgoh-comlink

On Windows (using PowserShell):

.. code-block:: bash

    python -m venv c:\<path>\<to>\.venv
    PS C:\> <venv>\Scripts\Activate.ps1
    python -m pip install swgoh-comlink

Once you have the library installed in Python, you should then be able to instantiate an instance
of the synchronous module and make a request for the current game data. It is recommend to enable the
built in logger maintain a log of events and procedures internally that may happen before, during or after an
error may be produced:

.. code-block:: python

    from swgoh_comlink import SwgohComlink

    client = SwgohComlink(default_logger=True) # assuming that the comlink service is running locally on the default ports
    game_data = comlink.get_game_data()

We are an open-source project that expects all contributors to adhere to a basic `Code of Conduct`_.

Where to start
--------------
Contributions start with the creation of an **Issue**. The issue should explain what the problem you're having is.
Issues are our way of tracking bugs that may be occurring with this library. Every contributor
is required to start with an Issue, as this helps numerous contributors and developers on various teams keep
track of requests, bugs and miscellaneous details.

Issue specifications
********************
Whenever there is an Issue created, they must follow the according criterion:

- An Issue must not be a duplicate of an existing one.
- A bug Issue must have all fields filled out.
- A request Issue must have support from a pre-determined amount of users.
- A miscellaneous Issue must:
    - Target a third-party repository if it is an issue correlated between the two.
    - Specify external issues that tie into library installation or performance.

Failure to comply to these factors will result in the Issue being closed with a comment and/or label.
Some Issues may be closed by the discretion of varying development teams for reasons that exclude
these factors.

Pull Request specifications
***************************
Start by creating a fork of the ``main`` branch of the repository. In your fork, create a new branch with
the Issue number in it's name. Once all of the suggested changes have been made and committed to your forked
branch, you start a **Pull Request**. The Pull Request (PR) template provides additional details on the formatting
and required information for successful submission.

When a PR is made, you **must** be targeting the ``development`` branch. This branch is where all active
development work on any bug-fixing, breaking changes and/or overall new features happens. Committed and verified
changes in the development branch are merged into the ``main`` branch. Formal releases are generated from the main branch.

A pull request must additionally adhere to these following requirements:

- Each git commit made on your fork must use `conventional commits`_.
- The pull request must be up-to-date with ``development`` before requesting a review.
- A ``pre-commit`` commit must exist and pass *all* checks before requesting a review.
- A review must be requested from at least one maintainer of the library.

Recognizing contributors
------------------------
When a PR is successfully merged into one of the development branches, the GitHub user will automatically
be added to the contributor list of the repository. The git commit history on a file will also subsequently
be updated by GitHub to include your user signature.

.. _Code of Conduct: https://github.com/swgoh-utils/swgoh-comlink/blob/master/CODE-OF-CONDUCT.md
.. _conventional commits: https://www.conventionalcommits.org/en/v1.0.0/
