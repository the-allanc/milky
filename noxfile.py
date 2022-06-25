import tempfile

import nox

nox.options.sessions = "tests", "lint", "safety"


@nox.session
@nox.parametrize(
    'python,clientlibs',
    [
        ('3.8', []),
        ('3.8', ['httpx']),
        ('3.8', ['requests']),
        ('3.8', ['requests', 'httpx']),
        ('3.10', ['httpx']),
    ],
)
def tests(session, clientlibs):
    session.run("poetry", "install", external=True)
    for lib in clientlibs:
        session.run("pip", "install", lib)
    session.run("pytest", "--cov")


@nox.session(reuse_venv=True)
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


@nox.session
def safety(session):
    with tempfile.NamedTemporaryFile() as requirements:
        session.run(
            "poetry",
            "export",
            "--dev",
            "--format=requirements.txt",
            "--without-hashes",
            f"--output={requirements.name}",
            external=True,
        )
        session.install("safety")
        session.run("safety", "check", f"--file={requirements.name}", "--full-report")
