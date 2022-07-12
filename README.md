# GmailAttachment

First follow API enable instructions at https://developers.google.com/gmail/api/quickstart/python

API reference: https://googleapis.github.io/google-api-python-client/docs/

You will need to get an API key prior to first running the application. This must be
stored in a file named "credentials.json".

If no "token.pickle" file exists, a browser window will be shown asking you to log into the 
appropriate GMAIL account.

```
usage: get_attachment.py [-h] [--output/-o OUTPUT] [--config DIR] [--label LABEL]
                         [--limit LIMIT] [--count/-c] [--delete] [--trash]
                         [--verbose/-v] [--unread] [--noclobber]

This application downloads attachments from a GMAIL account

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Specify the target directory for downloads
  --config DIR          Specify the directory containing GMAIL credentials
  --label LABEL         Specify the target label for getting messages
  --limit LIMIT, -l LIMIT
                        limit the number of attachments downloaded
  --count, -c           Just calculate number of available messages and exit
  --delete              Delete messages at GMAIL rather than just archive
  --trash               Trash messages at GMAIL rather than just archive
  --verbose, -v         Verbose output
  --unread, -u          Only get unread messages from inbox, default is to get
                        all unread even if archived)
  --noclobber           Don't overwrite existing files


```

Still a work in progress.

