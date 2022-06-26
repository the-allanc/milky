import nox
from nox_poetry import session

nox.options.sessions = "tests", "lint", "safety"
nox.options.stop_on_first_error = True


@session
@nox.parametrize(
    'python,extralibs',
    [
        ('3.8', []),
        ('3.8', ['httpx']),
        ('3.8', ['requests', 'defusedxml']),
        ('3.8', ['requests', 'httpx']),
        ('3.10', ['httpx']),
    ],
)
def tests(session, extralibs):
    session.install(".")
    session.install(
        "vcrpy @ git+https://github.com/the-allanc/vcrpy.git@httpx-cassette-compatibility"
    )
    session.install("pytest", "pytest-cov", "pytest-recording")
    if extralibs:
        session.install(*extralibs)
    session.run("pytest", "--cov")


@session(reuse_venv=True)
def lint(session):
    session.install(
        'flakeheaven',
        'flake8-bandit',
        'flake8-bugbear',
        'flake8-warnings',
        'dlint',
        'flake8-pie',
        'flake8-simplify',
        'flake8-comprehensions',
        'flake8-use-fstring',
        'flake8-cognitive-complexity',
        'flake8-executable',
        'flake8-expression-complexity',
        'flake8-noqa',
        'yesqa',
    )

    # We want to reuse the same environment, so this is the hack
    # to achieve that.
    if tuple(session.posargs)[:1] == ('run-yesqa',):
        session.run('yesqa', *session.posargs[1:])
        return

    # List plugins and fail if any are missing.
    session.run('flakeheaven', 'plugins')
    session.run('flakeheaven', 'missed')

    # Run flakeheaven and then run the flake8-noqa tool afterwards.
    # The two aren't compatible with each other since flake8-noqa tries
    # to override the file checker in flake8 in a way that isn't
    # compatible with how flakeheaven works.
    session.run('flakeheaven', 'lint', 'src', 'tests', 'noxfile.py')
    session.run('flake8', '--select=NQA0', 'src', 'tests', 'noxfile.py')


@session
def safety(session):
    reqs = session.poetry.export_requirements()
    session.install("safety")
    session.run("safety", "check", f"--file={reqs}", "--full-report")
