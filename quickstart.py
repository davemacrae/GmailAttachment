#!/usr/bin/python3

from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64
from apiclient import errors

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


def main():
    """
    Based on examples from: https://developers.google.com/gmail/api/quickstart/python
    Shows basic usage of the Gmail API.
    Find all unread messages with label "frame"
    Download any attachments to these messages
    mark the message as read by removing label "UNREAD"
    archive message by removing label "INBOX"
    """

    service = build('gmail', 'v1', credentials=login())
    want = get_labels(service, want='frame')
    # need to check if "want" was filled

    get_messages(service, want)


def login():
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.

    gmail_creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            gmail_creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not gmail_creds or not gmail_creds.valid:
        if gmail_creds and gmail_creds.expired and gmail_creds.refresh_token:
            gmail_creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            gmail_creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(gmail_creds, token)
    return gmail_creds


def get_labels(service, want=None):
    # Call the Gmail API

    # If we want to get the ID of a specific label, pass this through in the 'want' parameter.

    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    wantId = ''

    if not labels:
        print('No labels found.')
    else:
        for label in labels:
            if label['name'] == want:
                wantId = label['id']

    return wantId


def get_messages(service, label=None):
    # Call the Gmail API

    """
    We want to get a list of all messages (defined by a specific label if required)
    We should also only get unread messages.
    """

    if label is None:
        label = ['UNREAD']
    else:
        label = [label, 'UNREAD']

    messages = []
    results = service.users().messages().list(userId='me', labelIds=label, pageToken=None).execute()
    messages.extend(results.get('messages', []))

    while results.get('nextPageToken'):
        results = service.users().messages().list(userId='me', labelIds=label, pageToken=results.get('nextPageToken')).execute()
        messages.extend(results.get('messages', []))

    if not messages:
        print('No unread messages found.')
    else:
        print('Found', len(messages), 'Unread Message(s)')
        for message in messages:
            # get_message_content(service, message['id'])
            # mark_message_read(service, message['id'])
            pass
    pass


def get_message_content(service, msg_id):
    """Get and store attachment from Message with given id.

    :param service: Authorized Gmail API service instance.
    :param msg_id: ID of Message containing attachment.
    """

    uid = 'me'

    try:
        message = service.users().messages().get(userId=uid, id=msg_id).execute()

        for part in message['payload']['parts']:
            if part['filename']:
                if 'data' in part['body']:
                    data = part['body']['data']
                else:
                    att_id = part['body']['attachmentId']
                    att = service. \
                        users(). \
                        messages(). \
                        attachments().get(userId=uid, messageId=msg_id, id=att_id).execute()
                    data = att['data']
                file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                path = part['filename']
                print("Save File:", path)
                with open(path, 'wb') as f:
                    f.write(file_data)

    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def mark_message_read(service, msg_id):
    # We now need to mark the message as read.

    uid = 'me'

    message = service. \
        users(). \
        messages(). \
        modify(userId=uid, id=msg_id, body={'removeLabelIds': ['UNREAD', 'INBOX']}).execute()
    # need to check that the UNREAD label has been removed.

    if 'UNREAD' in message['labelIds']:
        print("Something went wrong, label UNREAD still there")
    else:
        print("Message", msg_id, "marked as Read")

    pass


if __name__ == '__main__':
    main()
