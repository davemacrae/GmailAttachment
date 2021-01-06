#!/usr/bin/python3

from __future__ import print_function
import pickle
import os
import sys
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

    # TODO: What is the correct error handling here
    service = build('gmail', 'v1', credentials=login())
    labelID = get_labels(service, labelName='frame')

    messages = get_messages(service, labelID)

    if not messages:
        print('No unread messages found.')
    else:
        print('Found', len(messages), 'Unread Message(s)')
        for message in messages:
            get_message_content(service, message['id'])
            mark_message_read(service, message['id'])
            pass


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


def get_labels(service, labelName=None):
    # Call the Gmail API

    """
    We want to get a list of all labels that are defined in our GMAIL account.
    When we get the list this includes the name of the label and the ID. It is the ID that we need for subsequent
    calls to the API.

    :param service: Authorized Gmail API service instance.
    :param labelName: the label that tags the messages we're interested in

    The function returns the ID of the required label.

    """
    results, labels, labelId = None, None, None

    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
    except errors.HttpError as error:   # this is probably not the best solution
        print('An error occurred: %s' % error)

    if not labels:
        print('No labels found.')
    else:
        for label in labels:
            if label['name'] == labelName:
                labelId = label['id']

    return labelId


def get_messages(service, label=None):
    """
    We want to get a list of all messages (defined by a specific label if required)
    We should also only get unread messages.

    :param service: Authorized Gmail API service instance.
    :param label: the label that tags the messages we're interested in

    """

    # Even if label is not specified, we want to only retrieve UNREAD messages
    # If "label" is not defined then we will retrieve all unread messages from the mailbox.
    # TODO: need to determine if we want to retrieve all UNREAD messages (which is the current behavior) or just
    #  those that haven't been archived.
    #  i.e. do we need to make INBOX part of the label list.

    if label is None:
        label = ['UNREAD']
    else:
        label = [label, 'UNREAD']

    messages = []

    try:
        """
            Loop through the messages in the GMAIL inbox. 
            Gmail returns a maximum of 100 messages in a call with nextPageToken set to indicate
            that there are more messages.
            
            The call that retrieves that last block will not have this set.
        """
        # get the initial set of messages (if any)
        results = service.\
            users().\
            messages().\
            list(userId='me', labelIds=label, pageToken=None).execute()
        messages.extend(results.get('messages', []))

        while results.get('nextPageToken'):
            # if nextPageToken is set then there are more messages to retrieve.
            results = service.\
                users().\
                messages().\
                list(userId='me', labelIds=label, pageToken=results.get('nextPageToken')).execute()
            # extend the message list to include the new ones retrieved.
            messages.extend(results.get('messages', []))

    except errors.HttpError as error:   # this is probably not the best solution
        print('An error occurred: %s' % error)

    return messages


def get_message_content(service, msg_id):
    """
    Get and store attachment from Message with given id.

    :param service: Authorized Gmail API service instance.
    :param msg_id: ID of Message containing attachment.
    """

    uid = 'me'
    # TODO: Should probably make this an arg
    outputDir = 'output/'

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

                # it appears that filename can contain non-safe characters like "/", i.e. it has a full path
                # this appears to be because the UNIX mail command includes the full path of the attachment as given:
                #   mail -A ~/PycharmProjects/frame/ACF1083.jpg frame@macrae.org.uk
                # we should do a basename on the filename to just get the bit we need.

                path = outputDir + os.path.basename(part['filename'])
                print("Save File:", path)
                try:
                    with open(path, 'wb') as f:
                        f.write(file_data)
                except OSError as err:
                    print("OS error: {0}".format(err))
                    sys.exit(1)
                except Exception:
                    print("Unexpected error:", sys.exc_info()[0])
                    raise

    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def mark_message_read(service, msg_id):
    """
    We now need to mark the message as read.
    This is done by removing the UNREAD label
    The message is also archived by removing the INBOX label.

    :param service: Authorized Gmail API service instance.
    :param msg_id: ID of message to be altered
    """
    uid = 'me'
    message = None

    try:
        message = service. \
            users(). \
            messages(). \
            modify(userId=uid, id=msg_id, body={'removeLabelIds': ['UNREAD', 'INBOX']}).execute()
    except errors.HttpError as error:
        print('An error occurred: %s' % error)

    # need to check that the UNREAD label has been removed.

    labelIDs = message.get('labelIds')
    if 'UNREAD' in labelIDs:
        print("Something went wrong, label UNREAD still there")
    else:
        print("Message", msg_id, "marked as Read")

    pass


if __name__ == '__main__':
    # TODO: Need to have some kind of argument parsing
    #   output folder
    #   verbosity level
    #   do we want to limit the number of files
    #   do we want to overwrite existing files
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(1)
        except SystemExit:
            # noinspection PyProtectedMember
            os._exit(1)