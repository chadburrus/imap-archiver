# Introduction

A basic email archival tool for use over IMAP.  It organizes email into folders based on the year and date of the email.  I run it from a cron job nightly to keep my archive up to date.

# Assumptions

This was written and tested against Gmail's IMAP implementation, and has some inherent assumptions based on that implementation.  For example:

1. The email to process is in a single Archive folder (in GTD fashion), like Gmail's "All Mail" label.  The name of that folder is configurable in the parameters file, but defaults to Gmail's version.
2. A sub-folder is created by creating a folder containing a "/", as per Gmail's design.
3. Mail should be kept in both the yearly folder and the monthly folder.  Since a Gmail label is essentially a tag on the email, this means only one copy of the email is actually kept.
4. Creating a folder multiple times on the IMAP server does *NOT* produce any ill side affects.
5. Your user name and password are stored in some form of keychain or keyring supported by Python's [`keyring`](https://pypi.python.org/pypi/keyring) module.

# Dependencies

Python and the `email` and `keyring` modules are the only real dependencies.  Make sure they're installed, and you should be good to go

    pip install email keyring

# Todo

1.  Add usage information.
2.  Better documentation.
3. Clean up option passing.
4. Better error handling.
