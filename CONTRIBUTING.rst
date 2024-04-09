Code Contributions
==================
Contributions to this open-source project are welcome and always appreciated! Every line of code helps
us ensure a better developed project to users. We will always credit those who help out.

New to contributing
-------------------
If you're new to contributing towards this project, it is highly recommended to start off with installing
the library from PyPi using ``pip``. It is always best to install into a clean virtual environment:

.. code-block:: bash

    > python3 -m venv <env_name>
    > source <env_name>/bin/activate
    (<env_name>) > pip install swgoh_comlink

Once you have the library installed in Python, you are able to verify proper operation by launching an
interactive python console and loading the synchronous module. Once the module is loaded, a call to collect
the current game metadata will verify that both the swgoh-comlink package installation and comlink proxy
service are operating properly:

.. note:: The example below assumes that the comlink docker instance is running on the local machine using default settings. See the `setup instructions <https://github.com/swgoh-utils/swgoh-comlink>`_ for additional information.

.. code-block:: python

    (.venv) > .venv/bin/ipython
    IPython 8.23.0 -- An enhanced Interactive Python. Type '?' for help.

    In [1]: from swgoh_comlink import SwgohComlink

    In [2]: comlink = SwgohComlink()

    In [3]: metadata = comlink.get_game_metadata()

    In [4]: sorted(metadata.keys())
    Out[4]:
    ['assetSubpath',
     'assetVersion',
     'clientCache',
     'config',
     'debugMode',
     'gamedataRevision',
     'latestGamedataVersion',
     'latestLocalizationBundleVersion',
     'latestLocalizationRevision',
     'monoExtraMemoryAllocationDivisor',
     'qualityData',
     'resourceCacheMemoryLimit',
     'serverTimestamp',
     'serverVersion',
     'texFormat']

    In [5]:


Since we are an open-source project we expect all contributors to adhere to the `Code of Conduct`_.

Where to start
--------------
Our contributions start with an **Issue**. The issue should explain what the problem you're having is.
Issues are our way of tracking bugs that may be occurring with this library. Every contributor
is recommended to start with an Issue, as this helps numerous contributors and developers on various teams keep
track of requests, bugs and miscellaneous details.

Issue specifications
********************
Whenever there is an Issue created, they must follow the according criterion:

- An Issue must not be a duplicate of an existing one.
- A bug Issue must have all fields filled out.

Failure to comply to these factors will result in the Issue being closed with a comment and/or label.
Some Issues may be closed by the discretion of the core development team for reasons that exclude
these factors.

Create a fork
*************
The first step in developing a potential solution to the issue raised is to create a fork of the
``development`` branch in your local GitHub account. Next create a new branch within your fork from
the ``development`` branch with a name containing the issue number created above. Develop your solution
and commit the new code to your new branch. Once you are satisfied with the solution and completed successful
testing of the functionality, push the commits to your GitHub fork. A **Pull Request** can then be created
from your new code commits.

See the `GitHub documentation <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo>`_ for more information.

Pull Request specifications
***************************
In order to propose a solution to the issue, you start a **Pull Request**. Linking the issue in this
(known as a PR) allows us to easily identify what bugs have been correlated with the code requesting
to be changed in the source, and allow other developers to contribute where needed.

When a PR is made, you **must** be targeting the ``development`` branch for the specific minor version of
the library. This is our development branch that we use whenever we're working on any bug-fixing, breaking
changes and/or overall new features. Our development workflow for changes is from this branch to ``main``,
and then releases are built from there before being published to PyPi.

A pull request must additionally adhere to these following requirements:

- Each git commit made on your fork must use `conventional commits`_.
- The pull request must be up-to-date with ``development`` before requesting a review.
- A ``pre-commit`` commit must exist and pass *all* checks before requesting a review.

See the `GitHub documentation <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request>`_ for more information.

Recognizing contributors
------------------------
When a PR is successfully merged into one of the development branches, the GitHub user will automatically
be added to the contributor list of the repository. The git commit history on a file will also subsequently
be updated by GitHub to include your user signature.

.. _Code of Conduct: https://github.com/swgoh-utils/comlink-python/blob/main/CODE_OF_CONDUCT.md
.. _conventional commits: https://www.conventionalcommits.org/en/v1.0.0/
