"""Check Python's HTTPS trust before setup downloads; never weaken verification."""
import ssl
import sys


def check_trust():
    try:
        context = ssl.create_default_context()
        trusted = context.get_ca_certs()
    except (OSError, ssl.SSLError) as error:
        raise RuntimeError(
            'Python could not load its HTTPS certificate configuration. '
            'Check SSL_CERT_FILE/SSL_CERT_DIR if you configured them. '
            'Certificate verification remains enabled.'
        ) from error
    if not trusted:
        raise RuntimeError(
            'Python has no trusted root certificates configured. Setup stopped before downloads.\n'
            'For the python.org Mac installation, open Finder > Applications > Python 3.12 > '
            'Install Certificates.command. Wait for "update complete", then reopen Set up.command.\n'
            'If your organisation manages certificates, ask its IT administrator for the approved '
            'Python CA configuration. Do not disable HTTPS certificate verification.'
        )
    return len(trusted)


if __name__ == '__main__':
    try:
        count = check_trust()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    print(f'Python HTTPS trust configured ({count} CA certificates); verification stays enabled.')
