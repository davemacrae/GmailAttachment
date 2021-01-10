# GmailAttachment

First follow API enable instructions at https://developers.google.com/gmail/api/quickstart/python

API reference: https://googleapis.github.io/google-api-python-client/docs/

You will need to get an API key prior to first running the application.

```
usage: get_attachment.py [-h] [--output OUTPUT] [--label LABEL]
                         [--limit LIMIT] [--count] [--delete] [--verbose]
                         [--unread] [--noclobber]

This application downloads attachments from a GMAIL account

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Specify the target directory for downloads
  --label LABEL         Specify the target label for getting messages
  --limit LIMIT, -l LIMIT
                        limit the number of attachments downloaded
  --count, -c           Just calculate number of available messages and exit
  --delete, -d          Delete messages at GMAIL rather than just archive
  --verbose, -v         Verbose output
  --unread, -u          Only get unread messages from inbox, default is to get
                        all, even if archived)
  --noclobber           Don't overwrite existing files
```

Still a work in progress.

