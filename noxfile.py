import nox

@nox.session
@nox.parametrize('python,clientlibs', [
    ('3.8', []),
    ('3.8', ['httpx']),
    ('3.8', ['requests']),
    ('3.8', ['requests', 'httpx']),
    ('3.10', ['httpx']),
])
def tests(session, clientlibs):
    session.run("poetry", "install", external=True)
    for lib in clientlibs:
        session.run("pip", "install", lib)
    session.run("pytest", "--cov")
