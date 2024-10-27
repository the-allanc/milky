try:
    from nox_poetry import session
except ImportError:
    from nox import session

import os

import nox

# When running on Github, let all the sessions be selected.
if not os.environ.get('GITHUB_WORKSPACE'):
    nox.options.sessions = "tests", "lint", "mypy", "safety"
    nox.options.stop_on_first_error = True

locations = 'src', 'tests', 'noxfile.py'


@session
def tests(session, extralibs=['requests']):  # noqa: B006
    session.install(".")
    session.install("pytest", "pytest-cov", "pytest-recording")
    if extralibs:
        session.install(*extralibs)

    session.run("pytest", "--cov", *session.posargs)


@session(python='3.10')
@nox.parametrize(
    'extralibs',
    [
        nox.param([], id='noclient'),
        nox.param(['requests', 'httpx'], id='both-clients'),
    ],
)
def test_lib_variants(session, extralibs):
    tests(session, extralibs)


@session(python='3.10')
def lint(session):
    reqs = session.poetry.export_requirements()
    session.install('-r', str(reqs))

    # Start with the ruff stuff.
    session.run('ruff', 'check', '--fix', *locations)

    # List plugins and fail if any are missing.
    session.run('flakeheaven', 'plugins')
    session.run('flakeheaven', 'missed', success_codes=(0, 41))

    # Run flakeheaven and then run the flake8-noqa tool afterwards.
    # The two aren't compatible with each other since flake8-noqa tries
    # to override the file checker in flake8 in a way that isn't
    # compatible with how flakeheaven works.
    session.run('flakeheaven', 'lint', *locations)
    session.run('flake8', '--select=NQA0', *locations)


@session
def safety(session):
    reqs = session.poetry.export_requirements()
    session.install("safety")

    ignorables = []

    # https://data.safetycli.com/v/70612/f17/
    ignorables.append("--ignore=70612")

    session.run("safety", "check", f"--file={reqs}", "--full-report", *ignorables)


@session(python='3.10')
def mypy(session):
    # Using pip to install, rather than Poetry:
    #   https://github.com/python-poetry/poetry/issues/5193
    reqs = session.poetry.export_requirements()
    session.install('-r', str(reqs))
    session.install('types-requests')
    args = session.posargs or ['src/']
    session.run("mypy", *args)


@session
def mkdocs(session):
    session.install('mkdocs', 'mkdocstrings[python]', 'mkdocs-material')
    session.run('pip', 'install', '-e', '.')
    session.run('mkdocs', 'build')
