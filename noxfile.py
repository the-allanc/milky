try:
    from nox_poetry import session
except ImportError:
    from nox import session

import nox

nox.options.sessions = "tests", "lint", "mypy", "safety"
nox.options.stop_on_first_error = True

locations = 'src', 'tests', 'noxfile.py'


@session
def tests(session, extralibs=['httpx']):  # noqa: B006
    session.install(".")
    session.install(
        "vcrpy @ git+https://github.com/the-allanc/vcrpy.git@httpx-cassette-compatibility"
    )
    session.install(
        "pytest", "pytest-cov", "pytest-recording", "typeguard", "typing_extensions"
    )
    if extralibs:
        session.install(*extralibs)

    args = ["pytest", "--cov"]
    if extralibs == ['requests', 'httpx']:
        args.append("--typeguard-packages=milky")
        session.env['TYPE_CHECKING'] = '1'
    session.run(*args, *session.posargs)


@session(python='3.10')
@nox.parametrize(
    'extralibs',
    [
        nox.param([], id='noclient'),
        nox.param(['requests', 'defusedxml'], id='requests-with-defused'),
        nox.param(['requests', 'httpx'], id='both-clients'),
    ],
)
def test_lib_variants(session, extralibs):
    tests(session, extralibs)


@session(python=False)
def list_test_lib_variant_sessions(session):  # noqa: ARG001
    # https://stackoverflow.com/questions/66747359/how-to-generate-a-github-actions-build-matrix-that-dynamically-includes-a-list-o
    import json

    sessions_list = [
        f"test_lib_variants({param})" for param in test_lib_variants.parametrize
    ]
    print(json.dumps(sessions_list))  # noqa: T201


@session(python='3.10')
def lint(session):
    reqs = session.poetry.export_requirements()
    session.install('-r', str(reqs))

    # Start with the ruff stuff.
    session.run('ruff', *locations)

    # List plugins and fail if any are missing.
    session.run('flakeheaven', 'plugins')
    session.run('flakeheaven', 'missed')

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
    session.run("safety", "check", f"--file={reqs}", "--full-report")


@session(python='3.10')
def mypy(session):
    # Using pip to install, rather than Poetry:
    #   https://github.com/python-poetry/poetry/issues/5193
    reqs = session.poetry.export_requirements()
    session.install('-r', str(reqs))
    session.install('types-requests')
    args = session.posargs or ['src/']
    session.run("mypy", *args)
    session.run("pytype", "--disable=import-error", *args)


@session
def mkdocs(session):
    session.install('mkdocs', 'mkdocstrings[python]', 'mkdocs-material')
    session.run('pip', 'install', '-e', '.')
    session.run('mkdocs', 'build')
